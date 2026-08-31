"""元号 → 西暦の換算表(G-03)。

循環の禁止
----------
この表は **半七の本文から作らない**。外部の権威(ja.wikipedia「元号一覧 (日本)」の
一覧表)を独立に取得し、そこから導出する。本文の年号解釈をこの表の検証に使ってはならない。

改元日の西暦を使ってはならない
------------------------------
元号の改元は旧暦の年の途中で起こり、**年の番号は改元後も引き継がれる**。
たとえば安政への改元は「嘉永七年十一月二十七日(1855年1月15日)」だが、
嘉永七年 = 安政元年であり、その年の大半は西暦 1854 年に当たる。
改元日の西暦年をそのまま採ると安政元年が 1855 になり、**1 年ずれる**。

正しい導出は次の再帰である:

    元年(E) の西暦 = 元年(前元号) の西暦 + (改元時の前元号の年 - 1)

必要な種は一つだけ(慶長元年 = 1596)。以後は表の「始期」欄の**和暦**から順に決まる。

保証粒度(HC-016)
----------------
保証するのは **年** である。旧暦の年始は西暦の 1〜2 月に当たるため、
「和暦 N 年」は西暦 Y 年のうち約 11 か月と Y+1 年の 1〜2 か月にまたがる。
本アプリはこのずれを無視し、Y を「その和暦年の西暦年」とする。
月日の精度を要求してはならない。
"""

from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = DATA / "cache"

PAGE = "元号一覧 (日本)"
API = "https://ja.wikipedia.org/w/api.php"
UA = "hanshichi-atlas/0.1 (fleet research project; contact via github.com/twill3c)"

#: 再帰の種。江戸時代の最初の元号。
SEED = ("慶長", 1596)

#: 独立に持つ検算アンカー(HC-065 の二経路一致)。
#: 出所は一般に流通している和暦西暦対照(改元年の通説値)であり、
#: 上の再帰導出とは別経路で得た値である。一致しなければ導出か表のどちらかが誤っている。
ANCHORS = {
    "慶安": 1648,
    "元禄": 1688,
    "寛延": 1748,
    "明和": 1764,
    "文化": 1804,
    "文政": 1818,
    "天保": 1830,
    "弘化": 1844,
    "嘉永": 1848,
    "安政": 1854,
    "万延": 1860,
    "文久": 1861,
    "元治": 1864,
    "慶応": 1865,
    "明治": 1868,
}

_KANJI = {"元": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


class EraTableError(Exception):
    """表の仮定が崩れた。黙って違う値を出さず、ここで止める。"""


def kanji_year(s: str) -> int:
    """「元」「十七」「20」などの年表記を整数にする。1〜99 のみ扱う。

    一覧表の始期欄は算用数字(「元和10年」)だが、本文側は漢数字なので両方受ける。
    """
    if s == "元":
        return 1
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    if s.isdigit():
        return int(s)
    if "十" not in s:
        if len(s) != 1 or s not in _KANJI:
            raise EraTableError(f"読めない年: {s}")
        return _KANJI[s]
    head, _, tail = s.partition("十")
    tens = _KANJI[head] if head else 1
    ones = _KANJI[tail] if tail else 0
    return tens * 10 + ones


def fetch_wikitext() -> str:
    q = urllib.parse.urlencode(
        {
            "action": "parse",
            "page": PAGE,
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
        }
    )
    cached = CACHE / "gengo_ichiran.json"
    if cached.exists():
        blob = cached.read_bytes()
    else:
        req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
        with urllib.request.urlopen(req) as r:
            blob = r.read()
        CACHE.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(blob)
    return json.loads(blob)["parse"]["wikitext"]


#: 表の行から「元号名」と「始期の和暦」を取る。
#: 例: !rowspan="3"|[[寛永]] … |rowspan="3"|元和10年2月30日<br>（1624年4月17日）
_NAME = re.compile(r"^!(?:rowspan=\"\d+\"\|)?\[\[(?P<name>[^\]|]+?)(?:\s*\([^)]*\))?(?:\|[^\]]*)?\]\]")
_START = re.compile(r"(?P<prev>[一-龥]{2})(?P<year>元|[0-9０-９]+|[一二三四五六七八九十]+)年\s*(?:\[\[)?[０-９0-9一二三四五六七八九十]+月")


def parse_eras(wikitext: str) -> list[tuple[str, str, int]]:
    """(元号, 改元元の元号, 改元元の年) の列を、江戸時代の節から順に返す。"""
    i = wikitext.find("江戸時代 ===")
    if i < 0:
        raise EraTableError("『江戸時代』の節が見つからない")
    j = wikitext.find("=== 近代", i)
    section = wikitext[i : j if j > 0 else len(wikitext)]

    out: list[tuple[str, str, int]] = []
    current: str | None = None
    for line in section.splitlines():
        if m := _NAME.match(line):
            current = m.group("name")
            continue
        if current and (m := _START.search(line)):
            out.append((current, m.group("prev"), kanji_year(m.group("year"))))
            current = None
    if not out:
        raise EraTableError("元号を 1 件も抽出できなかった")
    return out


def build() -> dict:
    """元号 → 元年の西暦 の表を作る。"""
    wikitext = fetch_wikitext()
    rows = parse_eras(wikitext)

    first: dict[str, int] = {SEED[0]: SEED[1]}
    order = [SEED[0]]
    for name, prev, year in rows:
        if name in first:
            continue
        if prev not in first:
            # 種より前の元号から改元している = 江戸時代の外。飛ばす。
            continue
        first[name] = first[prev] + year - 1
        order.append(name)

    # 明治は「近代」の節にあるため、表の抽出には掛からない。
    # 慶応4年 = 明治元年 という関係だけを使って導出する(改元日の西暦は使わない)。
    if "慶応" in first and "明治" not in first:
        first["明治"] = first["慶応"] + 4 - 1
        order.append("明治")

    # 二経路一致(HC-065): 独立に持つアンカーと突き合わせる
    mismatch = {k: (v, first.get(k)) for k, v in ANCHORS.items() if first.get(k) != v}
    if mismatch:
        raise EraTableError(f"導出値がアンカーと不一致(期待, 導出): {mismatch}")

    return {
        "provenance": {
            "source": f"ja.wikipedia.org「{PAGE}」の一覧表(wikitext)",
            "source_url": f"{API}?action=parse&page={urllib.parse.quote(PAGE)}&prop=wikitext",
            "fetched_at": dt.date.today().isoformat(),
            "derivation": "改元日の西暦ではなく、改元元の和暦年から再帰で導出した"
            "(元年(E) = 元年(前元号) + 改元時の前元号の年 - 1)。種は慶長元年=1596",
            "cross_check": f"独立に持つアンカー {len(ANCHORS)} 件と一致することを確認した",
            "granularity": "年。旧暦の年始と西暦の年始のずれ(1〜2 か月)は無視する",
            "note": "半七の本文からは作っていない(G-03)",
        },
        "first_year": {k: first[k] for k in order},
        "anchors": ANCHORS,
    }


def to_western(era: str, year: int, table: dict) -> int:
    """和暦 → 西暦(年)。表に無い元号は例外にする。"""
    first = table["first_year"]
    if era not in first:
        raise EraTableError(f"表に無い元号: {era}")
    if year < 1:
        raise EraTableError(f"年が不正: {era}{year}")
    return first[era] + year - 1


def main() -> None:
    table = build()
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "era_table.json").write_text(
        json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"元号 {len(table['first_year'])} 件 → {DATA / 'era_table.json'}")


if __name__ == "__main__":
    main()
