"""話どうしの相互参照とその年代照合(F-07 / G-09)。

半七物の 69 話は互いを題名で参照する。「いつぞや『金の蝋燭』というお話をしたことが
ありましょう」「現に去年の三月、半七が『異人の首』の捕物で横浜へ出張った時に」——
参照の言い回しには**年の主張**が含まれることがあり、それを参照先の事件年と
突き合わせられる。

なぜ循環しないか
----------------
参照元の事件年も参照先の事件年も、それぞれの話が自分の本文で書いている年である。
照合はその二つの独立な記述を突き合わせるだけで、外部の年譜も、こちらの推定も要らない。
食い違いが出たらそれは**綺堂の書き損じか、こちらの事件年の判定違いか**のどちらかで、
どちらであってもそこを見に行く価値がある。

いま語られている事件はどれか
----------------------------
一つの話に事件が二つある場合(10 / 34 / 39)、参照が置かれた位置より前にある
最後の事件を「いま語っている事件」とみなす。位置を見ずに一つ目を採ると、
39「少年少女の死」の後半に置かれた 22 への参照が一話目の年と比べられてしまう。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pipeline.case_years import build as build_cases
from pipeline.era_scan import scan
from pipeline.era_table import to_western

ROOT = Path(__file__).resolve().parents[1]

#: 照合の窓は**題名を含む一文**に限る。
#:
#: 最初は前後の文字数で窓を切ったが、それでは参照と関係のない年を拾って
#: 誤って不一致を出した(2026-08-31 実測、2 件)。
#:
#:   44→16  「明治三十一年の十月、…かつてこの老人から聴かされた「津の国屋」の怪談が
#:           思い出されるような宵」 —— 明治三十一年は語り手が老人を訪ねた年であって、
#:           『津の国屋』の事件年の主張ではない
#:   59→55  「その翌年、即ち文久二年の…流行しました。いつぞや『かむろ蛇』のお話のときに、
#:           安政五年のコロリのことを」 —— 「翌年」は句点の前の文に属する
#:
#: そこで (1) 相対の言い回しは題名と同じ文にあること、(2) 明示の元号年は
#: 題名と同じ文の**あと**にあること、を要求する。正しく撃てる参照は減るが、
#: 撃ったものは根拠が同じ文の中で閉じている。**取りこぼす側に倒す** ——
#: 過大に主張するより取りこぼす方がよい。

#: 相対の言い回し → 参照先の年の差。
RELATIVE = {
    "去年": -1,
    "前年": -1,
    "昨年": -1,
    "この年": 0,
    "その年": 0,
    "同じ年": 0,
    "この翌月": 0,
    "翌月": 0,
    "翌年": 1,
    "あくる年": 1,
}

_TITLE = re.compile(r"[『「]([^』」\n]{2,10})[』」]")


def _current_case(rec: dict, pos: int) -> dict | None:
    """その位置で語られている事件(位置より前にある最後の事件)。"""
    cands = [c for c in rec["cases"] if c["pos"] <= pos]
    return (cands or rec["cases"] or [None])[-1]


def _years_of(rec: dict) -> list[int]:
    return sorted({y for c in rec["cases"] for y in c["years"]})


def build(cases: dict | None = None) -> dict:
    """cases を差し込めるようにしてあるのは、対照(T-510)で台帳をずらすため。"""
    texts = json.loads((ROOT / "data" / "plain.json").read_text(encoding="utf-8"))
    works = json.loads((ROOT / "data" / "aozora_works.json").read_text(encoding="utf-8"))
    table = json.loads((ROOT / "data" / "era_table.json").read_text(encoding="utf-8"))
    cases = cases if cases is not None else build_cases()["stories"]
    by_title = {w["title"]: w["no"] for w in works["series"]}

    rows: list[dict[str, Any]] = []
    for src, text in sorted(texts.items()):
        for m in _TITLE.finditer(text):
            dst = by_title.get(m.group(1))
            if dst is None or dst == src:
                continue
            sent_start = max(text.rfind("。", 0, m.start()), text.rfind("\n", 0, m.start())) + 1
            sent_end = text.find("。", m.end())
            sent_end = sent_end + 1 if sent_end >= 0 else len(text)
            window = text[sent_start:sent_end]
            after = text[m.end() : sent_end]
            evidence = window.replace("\n", " ").strip()
            dst_years = _years_of(cases[dst])
            row: dict[str, Any] = {
                "from": src,
                "to": dst,
                "title": m.group(1),
                "agrees": None,
                "basis": "同じ文の中に年の主張が無い",
                "expected": None,
                "actual": dst_years,
                "evidence": evidence,
            }

            # (1) 相対の言い回し
            src_case = _current_case(cases[src], m.start())
            word = next((w for w in RELATIVE if w in window), None)
            if word and src_case and src_case["years"]:
                base = src_case["years"][0]
                expected = base + RELATIVE[word]
                row.update(
                    agrees=expected in dst_years,
                    basis=f"相対「{word}」: {base} {RELATIVE[word]:+d}",
                    expected=expected,
                )
                rows.append(row)
                continue

            # (2) 窓の中に元号年が直接書かれている
            named = [h for h in scan(after) if h["form"] == "year" and h["year"]]
            if named:
                expected = to_western(named[0]["era"], named[0]["year"], table)
                row.update(
                    agrees=expected in dst_years,
                    basis=f"明示「{named[0]['raw']}」",
                    expected=expected,
                )
            rows.append(row)

    checked = [r for r in rows if r["agrees"] is not None]
    disagree = sum(1 for r in rows if r["agrees"] is False)
    return {
        "method": "話どうしの参照に含まれる年の主張を、参照先の事件年と突き合わせる。"
        "どちらの年も各話が自分の本文で書いたもので、外部の正解を使わない",
        "found": len(rows),
        "checked": len(checked),
        "agree": len(checked) - disagree,
        "disagree": disagree,
        "rows": rows,
    }


def main() -> None:
    res = build()
    (ROOT / "data" / "crossrefs.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"参照 {res['found']} 件 / 年を照合できた {res['checked']} 件 / 不一致 {res['disagree']}")
    for r in res["rows"]:
        if r["agrees"] is None:
            continue
        mark = "一致" if r["agrees"] else "不一致"
        print(f"  {r['from']}→{r['to']} 『{r['title']}』 {mark}  {r['basis']} → 期待 {r['expected']} / 実際 {r['actual']}")


if __name__ == "__main__":
    main()
