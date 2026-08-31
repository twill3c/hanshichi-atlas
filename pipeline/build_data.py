"""L1 のデータ生成を一本にまとめる入口。

    python -m pipeline.build_data

取得済みの `data/raw/` から、以下を作る。すべてリポジトリに載せる ——
`data/cache/` は取得の一時置き場であって、生成物ではない。

    data/plain.json          話ごとの素のテキスト(ルビの base を残し、yomi を落とした形)
    data/eras.json           元号語の全出現とその分類
    data/date_crosscheck.json 元号年と干支の内部照合
    data/hanshichi_age.json  半七の年齢言明の台帳
    data/stats.json          話ごとの基礎統計
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline import age, crosscheck
from pipeline.aozora_parser import extract_main_text, parse, plain_text, ruby_pairs
from pipeline.era_scan import scan

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"


def _write(name: str, obj: object) -> None:
    (DATA / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"  → data/{name}")


def build() -> None:
    works = json.loads((DATA / "aozora_works.json").read_text(encoding="utf-8"))
    titles = {w["no"]: w["title"] for w in works["series"]}

    plain: dict[str, str] = {}
    stats: dict[str, dict] = {}
    eras: dict[str, list] = {}

    for w in works["series"]:
        no = w["no"]
        src = RAW / f"{no}.html"
        if not src.exists():
            raise FileNotFoundError(f"本文が無い: {src}(pipeline/fetch_aozora.py を先に)")
        nodes = parse(extract_main_text(src.read_text(encoding="utf-8")))
        text = plain_text(nodes)
        plain[no] = text
        rubies = ruby_pairs(nodes)
        hits = scan(text)
        eras[no] = hits
        stats[no] = {
            "no": no,
            "title": titles[no],
            "chars": len(text),
            "ruby": len(rubies),
            "ruby_unique": len({b for b, _ in rubies}),
            "era_mentions": len(hits),
            "dated_mentions": sum(1 for h in hits if h["form"].startswith("year")),
        }

    _write("plain.json", plain)
    _write("stats.json", {"note": "話ごとの基礎統計(実測)", "stories": stats})
    _write(
        "eras.json",
        {
            "note": "元号語の全出現。form は era_scan.FORMS のいずれか。未分類は作らない(G-04)",
            "by_story": eras,
        },
    )
    _write("date_crosscheck.json", crosscheck.build())
    _write("hanshichi_age.json", age.build())

    total = sum(s["chars"] for s in stats.values())
    print(f"{len(stats)} 話 / 総 {total:,} 字 / ルビ {sum(s['ruby'] for s in stats.values()):,}")


if __name__ == "__main__":
    build()
