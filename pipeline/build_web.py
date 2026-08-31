"""Web ページが読むデータを作る(F-08 / F-11)。

    python -m pipeline.build_web

出力は `web/data/` の下に置く。ページは静的で、サーバも API も要らない(N-01)。

    web/data/index.json        69 話の一覧(年表と表が読む)
    web/data/story/{no}.json   ルビ付き本文(リーダーが読む)

語りの年について
----------------
「明治○年」を本文に書く話は 8 話しかない(2026-08-31 実測)。残りの話は語りの現在を
年で書かず、季節や祭りで置く。したがって語りの層は**そこだけ点が立つ**のが正しく、
埋めてはならない。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.aozora_parser import extract_main_text, parse
from pipeline.era_table import to_western

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WEB = ROOT / "web" / "data"


def _load(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def build_index() -> dict:
    works = _load("aozora_works.json")
    stats = _load("stats.json")["stories"]
    cases = _load("case_years.json")
    eras = _load("eras.json")["by_story"]
    table = _load("era_table.json")

    stories = []
    for w in works["series"]:
        no = w["no"]
        rec = cases["stories"][no]
        frame = sorted(
            {
                to_western(h["era"], h["year"], table)
                for h in eras[no]
                if h["form"] == "year" and h["era"] == "明治" and h["year"]
            }
        )
        stories.append(
            {
                "no": no,
                "title": w["title"],
                "chars": stats[no]["chars"],
                "ruby": stats[no]["ruby"],
                "ruby_unique": stats[no]["ruby_unique"],
                "kind": rec["kind"],
                "reason": rec["reason"],
                "cases": [
                    {
                        "years": c["years"],
                        "uncertain": c.get("uncertain", False),
                        "spans": c.get("spans", False),
                        "derived": c.get("derived", False),
                        "evidence": c["evidence"],
                        "note": c["note"],
                    }
                    for c in rec["cases"]
                ],
                "frame_years": frame,
                "card_url": w["card_url"],
            }
        )

    pl = _load("places.json")
    age = _load("hanshichi_age.json")
    birth = age["hanshichi_birth_candidates"][0]
    return {
        "generated_from": "data/*.json(pipeline/build_data.py の生成物)",
        "hanshichi": {
            "birth_year": birth,
            "first_case_year": 1841,
            "note": "生年は本文の三つの言明が収束した値。初陣は 02「石灯籠」が"
            "「彼の初陣の功名」と書く年",
            "statements": age["statements"],
        },
        "kinds": cases["kinds"],
        "counts": cases["counts"],
        "crossrefs": [
            {k: r[k] for k in ("from", "to", "title", "agrees", "basis", "expected", "actual", "evidence")}
            for r in _load("crossrefs.json")["rows"]
        ],
        "shared_events": _load("shared_events.json")["events"],
        "places": {
            "method": pl["method"],
            "mapped": pl["places"],
            "unresolved": pl["unresolved"],
            "not_in_gazetteer": pl["not_in_gazetteer"],
            "rejected": pl["rejected"],
            "rejected_examples": _rejected_examples(),
            "mentions": pl["mentions"],
            "by_story": pl["by_story"],
        },
        "stories": stories,
    }


def _rejected_examples() -> list[dict]:
    """不採用の理由を画面にも出す。見えない除外は、見ていない除外と区別がつかない。"""
    from pipeline.places import REJECT

    return [{"label": k, "reason": v} for k, v in sorted(REJECT.items())]


def build_story(no: str) -> dict:
    """リーダー用。ルビは base と yomi を分けて持ち、注記は別立てにする。"""
    html = (DATA / "raw" / f"{no}.html").read_text(encoding="utf-8")
    nodes = parse(extract_main_text(html))
    out: list[dict[str, Any]] = []
    after_br = False
    for n in nodes:
        k = n["kind"]
        if k == "text":
            # 組版は <br /> の直後に生の改行を置く。改行が二度入らないよう、
            # br の直後の改行 1 個だけを落とす(plain_text と同じ規則)。
            v = n["text"].replace("\r\n", "\n")
            if after_br and v.startswith("\n"):
                v = v[1:]
            after_br = False
            if v:
                out.append({"t": "s", "v": v})
        elif k == "ruby":
            out.append({"t": "r", "b": n["base"], "y": n["yomi"]})
            after_br = False
        elif k == "gaiji":
            out.append({"t": "g", "v": n["alt"]})
            after_br = False
        elif k == "note":
            out.append({"t": "n", "v": n["text"]})
        elif k == "raw" and n["tag"] == "br":
            out.append({"t": "br"})
            after_br = True
        # 字下げ div・中見出し h4・傍点 em/strong は L3 では落とす。
        # 中見出しを持つのは 69 話中 16 話だけで、節の区切りには使えない(L1 実測)。
    return {"no": no, "nodes": out}


def main() -> None:
    (WEB / "story").mkdir(parents=True, exist_ok=True)
    index = build_index()
    (WEB / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    print(f"  → web/data/index.json({len(index['stories'])} 話)")
    (WEB / "ruby.json").write_text(
        (DATA / "ruby.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    print("  → web/data/ruby.json")
    total = 0
    for s in index["stories"]:
        blob = json.dumps(build_story(s["no"]), ensure_ascii=False, separators=(",", ":"))
        p = WEB / "story" / f"{s['no']}.json"
        p.write_text(blob + "\n", encoding="utf-8")
        total += len(blob)
    print(f"  → web/data/story/*.json({len(index['stories'])} 件 / {total / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
