"""複数の話が同じ出来事を語るとき、日付が揃っているか(F-07 / G-10)。

半七物には、別々の話が同じ江戸の出来事に触れる箇所がある。御金蔵破り、安政の大コロリ、
安政の大地震、黒船 —— これらは事件の背景として繰り返し語られる。
**同じ出来事を二度書けば、書き手は二度間違えられる。**

この照合は循環しない。どちらの日付も綺堂が本文に書いたもので、外部の年表を持ち込まない。
食い違いが出たとき、それは綺堂の書き損じである(こちらの判定違いではない ——
判定が入る余地が無い)。

抽出
----
語が現れた文から「元号 + 年 + 月 + 日」を取る。月・日が書かれていなければ年だけを取る。
文をまたいで拾いに行かない —— 相互参照の照合で、窓を広げると関係のない年を拾うことを
実測している(crossrefs.py の注記)。
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any

from pipeline.era_table import to_western

ROOT = Path(__file__).resolve().parents[1]

#: 照合する主張。語で一括りにすると粗すぎる ——
#: 47「金の蝋燭」は御金蔵破りについて、押し込みの日・芝居の上演年・召し捕りの日を
#: それぞれ書いており、語だけで集めると別々の出来事の日付が同じ籠に入る(2026-08-31 実測)。
#: そこで**何と何を比べるのか**を主張ごとに書き、日付はその文から機械で取る。
#:
#: anchor は各話の本文に逐語で在ること(T-511 が検査する)。
CLAIMS: list[dict[str, Any]] = [
    {
        "fact": "御金蔵破りが起きた日",
        "mentions": [
            {"story": "47", "anchor": "藤岡藤十郎、野州無宿の富蔵、この二人が共謀して"},
            {"story": "63", "anchor": "藤岡藤十郎と野州無宿の富蔵が共謀して"},
        ],
    },
    {
        "fact": "安政の大コロリの年",
        "mentions": [
            {"story": "52", "anchor": "その前年、即ち安政五年の大コロリ"},
            {"story": "66", "anchor": "去年の安政五年は例の大コロリ"},
        ],
    },
    {
        "fact": "御金蔵破りの犯人が召し捕られた年",
        "mentions": [
            {"story": "47", "anchor": "安政四年二月二十六日に召し捕られ"},
            {"story": "47", "anchor": "犯人が何者であるか判然したのは、その翌々年、即ち安政四年"},
        ],
    },
]

_ERAS = None
_KAN = "元一二三四五六七八九十廿"
_NUM = {"元": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _kan(s: str) -> int:
    if s == "元":
        return 1
    if s.startswith("廿"):
        return 20 + (_NUM[s[1:]] if s[1:] else 0)
    if "十" not in s:
        return _NUM[s]
    head, _, tail = s.partition("十")
    return (_NUM[head] if head else 1) * 10 + (_NUM[tail] if tail else 0)


def _date_re(eras: list[str]) -> re.Pattern:
    return re.compile(
        rf"(?P<era>{'|'.join(eras)})(?P<y>[{_KAN}]+)年"
        rf"(?:(?P<m>[{_KAN}]+)月(?:(?P<d>[{_KAN}]+)日)?)?"
    )


def _sentence(text: str, pos: int) -> tuple[int, int]:
    start = max(text.rfind("。", 0, pos), text.rfind("\n", 0, pos)) + 1
    end = text.find("。", pos)
    return start, (end + 1 if end >= 0 else len(text))


def build() -> dict:
    texts = json.loads((ROOT / "data" / "plain.json").read_text(encoding="utf-8"))
    table = json.loads((ROOT / "data" / "era_table.json").read_text(encoding="utf-8"))
    date_re = _date_re(list(table["first_year"]))

    rows = []
    for claim in CLAIMS:
        hits: list[dict[str, Any]] = []
        for mention in claim["mentions"]:
            no, anchor = mention["story"], mention["anchor"]
            text = texts[no]
            if anchor not in text:
                raise ValueError(f"{no}: anchor が本文に無い — {anchor}")
            a, b = _sentence(text, text.index(anchor))
            sent = text[a:b]
            dm = date_re.search(sent)
            if not dm:
                raise ValueError(f"{no}: anchor の文に日付が無い — {sent[:60]}")
            hits.append(
                {
                    "story": no,
                    "year": to_western(dm.group("era"), _kan(dm.group("y")), table),
                    "month": _kan(dm.group("m")) if dm.group("m") else None,
                    "day": _kan(dm.group("d")) if dm.group("d") else None,
                    "date_text": dm.group(0),
                    "evidence": sent.replace("\n", " ").strip(),
                }
            )
        years = {h["year"] for h in hits}
        months = {h["month"] for h in hits if h["month"] is not None}
        days = {h["day"] for h in hits if h["day"] is not None}
        rows.append(
            {
                "event": claim["fact"],
                "stories": sorted({h["story"] for h in hits}),
                "years": sorted(years),
                "year_agrees": len(years) == 1,
                "month_agrees": len(months) <= 1,
                "day_agrees": len(days) <= 1,
                "mentions": hits,
            }
        )

    return {
        "method": "同じ出来事に触れる文から日付を取り、話をまたいで突き合わせる。"
        "どちらも綺堂が本文に書いた日付で、外部の年表を使わない",
        "checked": len(rows),
        "year_disagree": sum(1 for r in rows if not r["year_agrees"]),
        "month_disagree": sum(1 for r in rows if not r["month_agrees"]),
        "events": rows,
    }


def main() -> None:
    res = build()
    (ROOT / "data" / "shared_events.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"照合できた出来事 {res['checked']} 件 / 年の不一致 {res['year_disagree']} / 月の不一致 {res['month_disagree']}")
    for r in res["events"]:
        mark = "年一致" if r["year_agrees"] else "年不一致"
        mk2 = "月一致" if r["month_agrees"] else "月不一致"
        print(f"  {r['event']}({'/'.join(r['stories'])}) {mark} {mk2}")
        for h in r["mentions"]:
            print(f"      {h['story']}: {h['date_text']}")


if __name__ == "__main__":
    main()
