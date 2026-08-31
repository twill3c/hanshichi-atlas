"""各話の事件年の台帳(F-07)。

なぜ規則ひとつで決め打ちしないか
--------------------------------
本文の元号年は三種類が混ざる。**語りの現在(明治)**、**事件の年**、
**作中人物や事物の由来(回想)**である。位置や順序で機械的に選ぼうとすると必ず外れる ——
49「大阪屋花鳥」は最初の江戸年号(天保六年)が花鳥の経歴の説明で、事件は 4 つ後の
天保十二年から始まる。逆に 60「青山の仇討」は芝居の初演年(嘉永四年)がそのまま事件年である。

そこで **決定は手で下し、引用は機械に取らせる**。台帳が持つのは
「どの言及を採ったか」の番号だけで、根拠の文は毎回本文から切り出す。
書き写さないので転記のずれが起こらず、本文が変われば検査(T-502)が落ちる。

さらに台帳の年は **本文から抽出した候補の集合に閉じ込める**(T-503)。
手で作る台帳は年を発明できてしまうので、そこに枷を掛ける。
候補に無い年を採るときは ``derived`` を立てて導出を書く —— 13「弁天娘」の
「安政と年号のあらたまった年」と 38「人形使い」の「安政の末年」がこれに当たる。

分類
----
半七の事件            半七自身が手がけた事件
半七以前の聞き伝え     半七の生年(1823)より前に置かれた事件。半七の探索ではない
確定できない          本文に年の手がかりが無い。**推定で埋めない**
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

KINDS = ("半七の事件", "半七以前の聞き伝え", "確定できない")

#: 台帳。hits は data/eras.json の「年を指す言及」の番号(0 起点)。
#: 一つの話に事件が二つある場合は cases を二つ書く(10 / 34 / 39)。
CASES: dict[str, dict[str, Any]] = {}


def _c(hits, note="", **kw):
    return {"hits": list(hits), "note": note, **kw}


def _story(no, kind, cases, reason=""):
    CASES[no] = {"kind": kind, "cases": cases, "reason": reason}


_HANSHICHI = "半七の事件"
_OLD = "半七以前の聞き伝え"
_NONE = "確定できない"

# fmt: off
_story("01", _HANSHICHI, [_c([0], "語り手の叔父が「元治元年」と年を置いて語る半七の探索")])
_story("02", _HANSHICHI, [_c([1], "半七の初陣。天保丑年と天保十二年の二通りで書かれ、両者は一致する")])
_story("03", _HANSHICHI, [_c([1])])
_story("04", _HANSHICHI, [_c([0])])
_story("05", _NONE, [], reason="年代の言及が本文に無い。枠の季節(五月末の氷川祭)しか書かれない")
_story("06", _NONE, [], reason="年代の言及が本文に無い。枠の季節(十一月の酉の市)しか書かれない")
_story("07", _HANSHICHI, [_c([0])])
_story("08", _HANSHICHI, [_c([0])])
_story("09", _HANSHICHI, [_c([0])])
_story("10", _HANSHICHI, [_c([0], "一話目"), _c([1], "二話目。老人が続けてもう一件語る")])
_story("11", _HANSHICHI, [_c([0])])
_story("12", _HANSHICHI, [_c([0])])
_story("13", _HANSHICHI, [_c([], "改元の言い方で年を置く", derived=True, years=[1854],
      anchor="安政と年号のあらたまった年",
      derivation="「安政と年号のあらたまった年」= 嘉永七年 = 安政元年 = 1854。"
                 "61『吉良の脇指』が「その年号が安政と改まったのは十二月五日」と説明している")])
_story("14", _HANSHICHI, [_c([0])])
_story("15", _HANSHICHI, [_c([0])])
_story("16", _HANSHICHI, [_c([0])])
_story("17", _HANSHICHI, [_c([0, 1], "本文が「文久三年か元治元年」と決めかねている", uncertain=True)])
_story("18", _OLD, [_c([1], "一度目の流行"), _c([2], "二度目の流行。半七の生前")])
_story("19", _HANSHICHI, [_c([0])])
_story("20", _HANSHICHI, [_c([0])])
_story("21", _HANSHICHI, [_c([0])])
_story("22", _HANSHICHI, [_c([0])])
_story("23", _HANSHICHI, [_c([0])])
_story("24", _OLD, [_c([0], "『御仕置例書』の日付による。半七の生まれる 75 年前")])
_story("25", _HANSHICHI, [_c([0])])
_story("26", _HANSHICHI, [_c([3], "前置きの日野家息女一件(文化四年)は五十幾年前の由来")])
_story("27", _HANSHICHI, [_c([0])])
_story("28", _HANSHICHI, [_c([1], "文久元年の無雪は前振りで、事件は翌文久二年の大雪")])
_story("29", _HANSHICHI, [_c([0])])
_story("30", _HANSHICHI, [_c([0])])
_story("31", _HANSHICHI, [_c([0], "万延元年は同心藤四郎の高名の由来、天保元年は容疑者の生年")])
_story("32", _HANSHICHI, [_c([0])])
_story("33", _OLD, [_c([0], "文政四年。半七の生まれる二年前")])
_story("34", _HANSHICHI, [_c([0], "一話目"), _c([1], "二話目")])
_story("35", _HANSHICHI, [_c([1], "冒頭の落款「嘉永庚戌」も同じ嘉永三年を指す")])
_story("36", _HANSHICHI, [_c([0])])
_story("37", _HANSHICHI, [_c([0], "文化四年は永代橋落橋の由来、弘化二・三年は登場人物の生年")])
_story("38", _HANSHICHI, [_c([], "本文が年代の記憶を放棄している", derived=True, years=[1859, 1860],
      uncertain=True, anchor="なんでも安政の末年でしたろう",
      derivation="「安政の末年」。安政は 1854–1860 なので末年は安政六年(1859)か"
                 "安政七年(=万延元年、1860)。本文は「年代はたしかに覚えていません」と断る")])
_story("39", _HANSHICHI, [_c([0], "一話目"), _c([1], "二話目")])
_story("40", _HANSHICHI, [_c([0], "安政六年・万延元年は横浜開港の由来")])
_story("41", _HANSHICHI, [_c([0])])
_story("42", _HANSHICHI, [_c([0])])
_story("43", _NONE, [], reason="江戸の年代の言及が無い。明治七、八年は堤が崩された年で、枠の側")
_story("44", _HANSHICHI, [_c([1], "明治三十一年は枠(語り手が老人を訪ねた年)")])
_story("45", _HANSHICHI, [_c([0])])
_story("46", _HANSHICHI, [_c([0])])
_story("47", _HANSHICHI, [_c([1], "御金蔵破りの年。半七はこの年を「三十三の年」と言う")])
_story("48", _HANSHICHI, [_c([1], "天保十二年は『和合人』第三篇の刊年")])
_story("49", _HANSHICHI, [_c([5], "天保六〜十一年は花鳥の経歴、天保十三年は仕置の年")])
_story("50", _HANSHICHI, [_c([5], "慶安四年は絵馬の落款、嘉永六年は黒船の由来")])
_story("51", _HANSHICHI, [_c([0])])
_story("52", _HANSHICHI, [_c([0], "嘉永四年は控え帳の古い記録、安政五年は前年のコロリ")])
_story("53", _HANSHICHI, [_c([1], "本文は「一月はまだ万延二年のわけですが」と改元の月まで断る")])
_story("54", _HANSHICHI, [_c([0], "高野長英の捕物(嘉永三年十月)を軸に、その冬から翌春へ続く")])
_story("55", _HANSHICHI, [_c([0])])
_story("56", _HANSHICHI, [_c([3], "弘化四年〜安政六年は種痘の由来。本文が「このお話の文久二年」と言う")])
_story("57", _HANSHICHI, [_c([0])])
_story("58", _HANSHICHI, [_c([2], "文化九年は菊人形の起源、安政三年は団子坂の由来")])
_story("59", _HANSHICHI, [_c([1], "文久元年は団子坂の一件(58)、安政元年は写真術の由来")])
_story("60", _HANSHICHI, [_c([1], "佐倉宗吾の初演年がそのまま事件の年。見物に出て来た百姓の一件")])
_story("61", _HANSHICHI, [_c([1, 3], "嘉永六年十二月から翌安政元年へまたがる", spans=True)])
_story("62", _HANSHICHI, [_c([1], "元治元年は歩兵隊募集の由来、慶応三年は末尾の余話")])
_story("63", _HANSHICHI, [_c([0], "御金蔵破りの翌日の出来事。嘉永三年は三八の経歴")])
_story("64", _HANSHICHI, [_c([0])])
_story("65", _OLD, [_c([0], "文化九年。半七の生まれる十一年前")])
_story("66", _HANSHICHI, [_c([0], "本文が「これからのお話は安政六年七月以後の事」と断る")])
_story("67", _HANSHICHI, [_c([1], "明和五年・元禄十四年は碁盤の由来、慶応四年は後日談")])
_story("68", _HANSHICHI, [_c([0])])
_story("69", _OLD, [_c([0], "文化九年。吉五郎(半七の親分)の世代の事件で、半七は登場しない")])
# fmt: on


def _dated_hits(no: str) -> list[dict]:
    eras = json.loads((ROOT / "data" / "eras.json").read_text(encoding="utf-8"))["by_story"]
    return [h for h in eras[no] if h["form"].startswith("year")]


def _table() -> dict:
    return json.loads((ROOT / "data" / "era_table.json").read_text(encoding="utf-8"))["first_year"]


def _west(h: dict, tbl: dict) -> int | None:
    if h["form"] == "year" and h["year"]:
        return tbl[h["era"]] + h["year"] - 1
    return None


def candidate_years(no: str) -> set[int]:
    """その話の本文から機械抽出できる年の集合(T-503 の枷)。"""
    tbl = _table()
    return {y for h in _dated_hits(no) if (y := _west(h, tbl)) is not None}


def _sentence(text: str, pos: int) -> str:
    """位置を含む一文を切り出す。引用は書き写さず、ここで取る。"""
    start = max(text.rfind("。", 0, pos), text.rfind("\n", 0, pos)) + 1
    end = text.find("。", pos)
    end = end + 1 if end >= 0 else min(len(text), pos + 60)
    return text[start:end].strip()


def build() -> dict:
    texts = json.loads((ROOT / "data" / "plain.json").read_text(encoding="utf-8"))
    tbl = _table()
    stories: dict[str, Any] = {}
    counts: dict[str, int] = {}

    for no, rec in CASES.items():
        hits = _dated_hits(no)
        text = texts[no]
        cases = []
        for c in rec["cases"]:
            if c.get("derived"):
                anchor = c["anchor"]
                if anchor not in text:
                    raise ValueError(f"{no}: derived の anchor が本文に無い — {anchor}")
                cases.append(
                    {
                        "years": list(c["years"]),
                        "evidence": _sentence(text, text.index(anchor)),
                        "derived": True,
                        "derivation": c["derivation"],
                        "pos": text.index(anchor),
                        "uncertain": c.get("uncertain", False),
                        "note": c["note"],
                    }
                )
                continue
            years, ev, poss = [], [], []
            for i in c["hits"]:
                if i >= len(hits):
                    raise IndexError(f"{no}: 言及 {i} が無い(全 {len(hits)} 件)")
                y = _west(hits[i], tbl)
                if y is None:
                    raise ValueError(f"{no}: 言及 {i} は西暦に換算できない形")
                years.append(y)
                ev.append(_sentence(text, hits[i]["pos"]))
                poss.append(hits[i]["pos"])
            cases.append(
                {
                    "years": sorted(set(years)),
                    "evidence": ev[0],
                    "evidence_all": ev,
                    "pos": min(poss),
                    "uncertain": c.get("uncertain", False),
                    "spans": c.get("spans", False),
                    "note": c["note"],
                }
            )
        stories[no] = {"kind": rec["kind"], "reason": rec["reason"], "cases": cases}
        counts[rec["kind"]] = counts.get(rec["kind"], 0) + 1

    return {
        "method": "決定は本文を読んで手で下し、根拠の文は本文から機械で切り出す。"
        "年は本文から抽出した候補の集合に閉じ込める(T-503)",
        "kinds": list(KINDS),
        "counts": counts,
        "stories": stories,
    }


def main() -> None:
    res = build()
    (ROOT / "data" / "case_years.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("分類:", res["counts"])
    ys = sorted(y for s in res["stories"].values() for c in s["cases"] for y in c["years"])
    print(f"事件年 {len(ys)} 件 / 範囲 {min(ys)}–{max(ys)}")


if __name__ == "__main__":
    main()
