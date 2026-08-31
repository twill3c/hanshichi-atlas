"""本文中の元号年の走査(F-05)。

なぜ「元号 + 年」では足りないか
--------------------------------
69 話全域の棚卸し(2026-08-31 実測、元号語 233 件)によると、元号語のうしろに来るものは
一様ではない。年を指しているものと、そうでないものが混在する。

年を指すもの:

    元治元年 / 安政三年 / 天保十二年 / 明治廿五年   元号 + 数 + 年
    文化九申年                                     元号 + 数 + 干支 + 年
    天保丑年 / 安政午年 / 寛政申年                 元号 + 干支 + 年(数が無い)
    明治七、八年                                   範囲
    慶応初年 / 天保初年                            初年
    天保年中                                       期間

年を指さないもの(撃ってはならない):

    明治座(劇場名) / 慶長小判(貨幣) / 万延版(絵図の版) / 天保度改革 /
    安政の大地震 / 明治時代 / 明治以後 / 安政と年号 / 文化文政のころ

とくに **明治座・慶長小判・万延版**は、元号語の直後に別の語が続くだけで、
素朴な「元号 .{0,3} 年」の正規表現は「明治座を見物にゆくと、廊下で……」のような
遠くの「年」を拾ってしまう。走査は元号語の**直後**だけを見る。

黙って通る道を作らない(HC-075)
------------------------------
``scan`` は元号語の出現を **すべて** 分類して返す。分類は ``FORMS`` に列挙した
有限集合で、どれにも当てはまらない形は ``not_a_year`` ではなく例外にする —— と
したいところだが、「年を指さない」用法は語彙的に開いている(人名・屋号・地名に
元号語が入りうる)ため、ここは ``not_a_year`` を明示的な分類として置く。
そのうえで **年を指す側**は閉じた形の集合として書き、陽性・陰性の対照(G-06)で
両側から押さえる。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

#: 分類の全体。これ以外の値を返してはならない(T-303)。
FORMS = frozenset(
    {
        "year",  # 元号 + 数(+干支) + 年 —— 西暦に換算できる
        "year_eto",  # 元号 + 干支 + 年 —— 数が無い。元号の期間内で干支から絞る
        "year_kanshi",  # 元号 + 十干十二支(年の字が無い) —— 落款など。60 年周期で一意
        "year_range",  # 元号 + 数、数 + 年 —— 範囲
        "first_years",  # 元号 + 初年
        "period",  # 元号 + 年中 / 年間
        "not_a_year",  # 元号語だが年を指さない
    }
)

#: 西暦に換算してよい分類(F-07 の材料)。
DATED_FORMS = frozenset({"year", "year_eto", "year_kanshi"})

#: 一般則で書くと危うい、一度きりの表記。本文の根拠を添えて明示的に置く。
#: 黙って捨てず、一般則も作らない —— 根拠ごと台帳に載せる(HC-012)。
LITERARY_EXCEPTIONS = {
    "慶安二二": {
        "era": "慶安",
        "year": 4,
        "form": "year",
        "story": "50",
        "evidence": "慶安二二は即ち慶安四年で、由井正雪、丸橋忠弥らが謀叛の年です。"
        "あからさまに四年と書かずに、",
        "note": "四(死)を忌んで二二と書いた絵馬の落款。本文が自ら答えを書いている"
        "珍しい例なので、一般則にせず例外として登録する",
    }
}

_ETO = "子丑寅卯辰巳午未申酉戌亥"
_KAN = "元一二三四五六七八九十廿"
_JIKKAN = "甲乙丙丁戊己庚辛壬癸"

_NUM = {"元": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _era_names() -> list[str]:
    table = json.loads((ROOT / "data" / "era_table.json").read_text(encoding="utf-8"))
    # 長い名から当てる必要は無い(すべて 2 文字)が、順序を固定しておく
    return sorted(table["first_year"], key=len, reverse=True)


try:
    ERAS = _era_names()
except FileNotFoundError:  # 表を作る前でも import はできるようにする
    ERAS = []

_ERA_RE = re.compile("|".join(ERAS)) if ERAS else re.compile(r"(?!)")


def kanji_num(s: str) -> int:
    """「元」「十二」「廿五」を整数にする。1〜99。"""
    if s == "元":
        return 1
    if s.startswith("廿"):
        rest = s[1:]
        return 20 + (_NUM[rest] if rest else 0)
    if "十" not in s:
        return _NUM[s]
    head, _, tail = s.partition("十")
    return (_NUM[head] if head else 1) * 10 + (_NUM[tail] if tail else 0)


# 元号語の**直後**に来る形。順序が意味を持つ(長いものから当てる)。
# 「の」を挟む形(「慶応の元年」)があるので、年の指定の前に助詞 1 文字を許す。
# ただし「安政の大地震」「明治の初年」を撃たないよう、助詞のあとは
# 年の指定が直に続く場合に限る。
_P = r"(?:の)?"
_RANGE = re.compile(rf"^{_P}(?P<a>[{_KAN}]+)、(?P<b>[{_KAN}]+)年")
_YEAR = re.compile(rf"^{_P}(?P<n>[{_KAN}]+)(?:、)?(?P<stem>[{_JIKKAN}])?(?P<eto>[{_ETO}])?年")
_ETO_YEAR = re.compile(rf"^{_P}(?:[{_JIKKAN}])?(?P<eto>[{_ETO}])年")
# 落款など、年の字を伴わない十干十二支。十干が付く形だけを採る
# (十二支だけで年の字も無い形は、年を指すとは限らないので採らない)。
_KANSHI = re.compile(rf"^(?P<kanshi>[{_JIKKAN}][{_ETO}])")
_FIRST = re.compile(r"^初年")
_PERIOD = re.compile(r"^年(?:中|間)")


def scan(text: str) -> list[dict[str, Any]]:
    """元号語の出現をすべて分類して返す。"""
    out: list[dict[str, Any]] = []
    for m in _ERA_RE.finditer(text):
        era = m.group(0)
        tail = text[m.end() : m.end() + 8]
        rec: dict[str, Any] = {
            "era": era,
            "pos": m.start(),
            "form": "not_a_year",
            "year": None,
            "eto": None,
            "raw": era,
            "context": text[max(0, m.start() - 24) : m.end() + 24].replace("\n", " "),
        }
        if mm := _RANGE.match(tail):
            rec.update(
                form="year_range",
                year=kanji_num(mm.group("a")),
                raw=era + mm.group(0),
            )
        elif mm := _YEAR.match(tail):
            rec.update(
                form="year",
                year=kanji_num(mm.group("n")),
                eto=mm.group("eto"),
                stem=mm.group("stem"),
                raw=era + mm.group(0),
            )
        elif mm := _ETO_YEAR.match(tail):
            rec.update(form="year_eto", eto=mm.group("eto"), raw=era + mm.group(0))
        elif mm := _KANSHI.match(tail):
            rec.update(
                form="year_kanshi",
                eto=mm.group("kanshi")[1],
                kanshi=mm.group("kanshi"),
                raw=era + mm.group(0),
            )
        elif exc := LITERARY_EXCEPTIONS.get(era + tail[: len(era)]):
            rec.update(
                form=exc["form"],
                year=exc["year"],
                raw=era + tail[: len(era)],
                exception=True,
            )
        elif _FIRST.match(tail):
            rec.update(form="first_years", year=1, raw=era + "初年")
        elif mm := _PERIOD.match(tail):
            rec.update(form="period", raw=era + mm.group(0))
        out.append(rec)
    return out


def dated(text: str) -> list[dict[str, Any]]:
    """西暦に換算しうる元号年だけを返す。"""
    return [r for r in scan(text) if r["form"] in DATED_FORMS]
