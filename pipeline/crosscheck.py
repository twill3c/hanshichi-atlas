"""本文内部の年代照合(F-05 / T-307)。

半七の本文は年を二通りに書く。元号年(「文化九年」)と干支(「申年」)である。
同じ年について両方を書いている箇所では、**本文だけで検算できる** ——
外部の年譜も、綺堂研究も要らない。この照合は循環しない(G-03)。

照合の二段階
------------
strict(語の内側): 一つの表記が数と干支の両方を含む。「文化九申年」「文化三、丙寅年」
adjacent(隣接): 元号年の直後に干支年が続く。「文化九年――申年」「弘化二年巳年」

どちらも「同じ年を指している」ことが表記の形から言える。
これに対し、話をまたいで「たぶん同じ事件だろう」と結び付ける照合は**しない** ——
それは本文が言っていないことを前提に置くことになる。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pipeline.era_scan import scan
from pipeline.kanshi import BRANCHES, STEMS, kanshi_of
from pipeline.era_table import to_western

ROOT = Path(__file__).resolve().parents[1]

#: 元号年の直後に干支年が続くとみなす窓(文字数)。
#: 「文化九年――申年」の「――」を跨げる幅として実測(2026-08-31)で決めた。
ADJACENT_WINDOW = 6

_ETO_YEAR = re.compile(rf"(?P<stem>[{STEMS}])?(?P<branch>[{BRANCHES}])年")


def crosscheck_text(no: str, text: str, table: dict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hit in scan(text):
        if hit["form"] != "year" or hit["year"] is None:
            continue
        western = to_western(hit["era"], hit["year"], table)
        actual = kanshi_of(western)

        # strict — 表記の内側に干支がある
        if hit.get("eto"):
            claimed = (hit.get("stem") or "") + hit["eto"]
            rows.append(
                {
                    "story": no,
                    "kind": "strict",
                    "expr": hit["raw"],
                    "western": western,
                    "claimed": claimed,
                    "actual": actual,
                    "agrees": actual.endswith(hit["eto"])
                    and (not hit.get("stem") or actual.startswith(hit["stem"])),
                    "evidence": hit["context"],
                }
            )
            continue

        # adjacent — 直後に干支年が続く
        end = hit["pos"] + len(hit["raw"])
        window = text[end : end + ADJACENT_WINDOW]
        if m := _ETO_YEAR.search(window):
            claimed = (m.group("stem") or "") + m.group("branch")
            rows.append(
                {
                    "story": no,
                    "kind": "adjacent",
                    "expr": hit["raw"] + window[: m.end()],
                    "western": western,
                    "claimed": claimed,
                    "actual": actual,
                    "agrees": actual.endswith(m.group("branch"))
                    and (not m.group("stem") or actual.startswith(m.group("stem"))),
                    "evidence": text[max(0, hit["pos"] - 20) : end + m.end() + 20].replace(
                        "\n", " "
                    ),
                }
            )
    return rows


def build() -> dict:
    table = json.loads((ROOT / "data" / "era_table.json").read_text(encoding="utf-8"))
    texts = json.loads((ROOT / "data" / "plain.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for no, t in sorted(texts.items()):
        rows.extend(crosscheck_text(no, t, table))
    disagree = sum(1 for r in rows if not r["agrees"])
    return {
        "method": "本文が元号年と干支の両方を書いている箇所だけを照合する。"
        "外部の年譜を用いないので循環しない(G-03)",
        "checked": len(rows),
        "agree": len(rows) - disagree,
        "disagree": disagree,
        "rows": rows,
    }


def main() -> None:
    res = build()
    (ROOT / "data" / "date_crosscheck.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"照合 {res['checked']} 件 / 一致 {res['agree']} / 不一致 {res['disagree']}")
    for r in res["rows"]:
        mark = "一致" if r["agrees"] else "不一致"
        print(f"  {r['story']} {mark} {r['expr']} → {r['western']} は {r['actual']}")


if __name__ == "__main__":
    main()
