"""地名辞書の取得(F-09)。

    python -m pipeline.gazetteer

なぜ本文から地名を「抽出」しないか
----------------------------------
接尾辞(町・坂・橋…)で拾う抽出器を書いて全 69 話に当ててみると、二方向に外れた
(2026-09-01 実測)。

- **拾いすぎ**: 普通・獄門・猪口・利口・閉口・不義密通・約束通、人名(岡崎・熊谷・水野)
- **拾い落とし**: 浅草・本所・麻布・本郷・芝・牛込・音羽・目白・根岸・王子・築地 ——
  接尾辞を持たない地名は原理的に掛からない

地名かどうかは表層形から決まらない。そこで **外部の地名辞書を先に用意し、
それを本文に照合する**(kiko-atlas の辞書照合方式)。辞書に無い地名は地図に出ないが、
それは「出せない」と分かる形で残せる。抽出器の取りこぼしは、黙って消える。

出所
----
Wikidata の SPARQL。東京都(Q1490)および神奈川県(Q34664)の行政区画に属し、
座標(P625)と日本語ラベルを持つ地物すべて。**半七の本文からは作らない**(G-03)。

WDQS は障害時に 1 分 1 リクエストへ絞られるので、問い合わせは県ごとに 1 回だけにし、
結果はキャッシュする。
"""

from __future__ import annotations

import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = DATA / "cache"

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "hanshichi-atlas/0.1 (fleet research project; contact via github.com/twill3c)"

#: 取りに行く行政区画。半七の足は江戸市中と、横浜・川崎あたりまで伸びる。
REGIONS = [
    ("tokyo", "Q1490", "東京都"),
    ("kanagawa", "Q34664", "神奈川県"),
]

QUERY = """
SELECT ?p ?label ?coord WHERE {
  ?p wdt:P131* wd:%s ; wdt:P625 ?coord .
  ?p rdfs:label ?label . FILTER(lang(?label)="ja")
}
"""


def _fetch(region_qid: str, cache_name: str) -> dict:
    cached = CACHE / cache_name
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    url = ENDPOINT + "?" + urllib.parse.urlencode(
        {"query": QUERY % region_qid, "format": "json"}
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    # WDQS は障害時に 429(1 req/min)を返す。待って繰り返す —— 諦めると
    # 「取れなかった」ことに気づかないまま空の辞書で先へ進んでしまう。
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                blob = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 7:
                raise
            print(f"    429 — {70} 秒待って再試行({attempt + 1}/8)")
            time.sleep(70)
    else:  # pragma: no cover
        raise RuntimeError("WDQS から取得できなかった")
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(blob)
    return json.loads(blob)


def _parse_point(wkt: str) -> tuple[float, float] | None:
    """'Point(139.7 35.6)' → (lat, lon)。読めない形は黙って通さない。"""
    if not wkt.startswith("Point(") or not wkt.endswith(")"):
        return None
    try:
        lon, lat = (float(v) for v in wkt[6:-1].split())
    except ValueError:
        return None
    return lat, lon


def build() -> dict:
    entries: dict[str, dict[str, Any]] = {}
    for key, qid, name in REGIONS:
        blob = _fetch(qid, f"wikidata_{key}.json")
        for b in blob["results"]["bindings"]:
            label = b["label"]["value"]
            pt = _parse_point(b["coord"]["value"])
            if pt is None:
                continue
            entity = b["p"]["value"].rsplit("/", 1)[-1]
            # 同じ名前が複数の地物に付くことがある。曖昧なものは採らない ——
            # 一意でない名前を黙って一つに決めると、地図が嘘をつく。
            rec = entries.setdefault(label, {"label": label, "qids": [], "coords": [], "region": name})
            rec["qids"].append(entity)
            rec["coords"].append([round(pt[0], 4), round(pt[1], 4)])

    out = []
    for rec in entries.values():
        uniq = {tuple(c) for c in rec["coords"]}
        out.append(
            {
                "label": rec["label"],
                "qid": rec["qids"][0] if len(set(rec["qids"])) == 1 else None,
                "qids": sorted(set(rec["qids"])),
                "lat": rec["coords"][0][0],
                "lon": rec["coords"][0][1],
                "ambiguous": len(uniq) > 1,
                "region": rec["region"],
            }
        )
    out.sort(key=lambda e: e["label"])
    return {
        "provenance": {
            "source": "Wikidata SPARQL (query.wikidata.org)",
            "query": QUERY.strip(),
            "regions": [{"key": k, "qid": q, "name": n} for k, q, n in REGIONS],
            "fetched_at": dt.date.today().isoformat(),
            "note": "半七の本文からは作っていない(G-03)。同じ名前が複数の地物に付く場合は "
            "ambiguous=true とし、座標を一つに決めない",
        },
        "count": len(out),
        "ambiguous": sum(1 for e in out if e["ambiguous"]),
        "entries": out,
    }


def main() -> None:
    # 県ごとに 1 回。WDQS が絞られているときのため、キャッシュが無いときだけ間を置く
    for i, (key, qid, _) in enumerate(REGIONS):
        if not (CACHE / f"wikidata_{key}.json").exists():
            if i:
                time.sleep(65)
            _fetch(qid, f"wikidata_{key}.json")
            print(f"  取得 {key}")
    g = build()
    (DATA / "gazetteer.json").write_text(
        json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"地名 {g['count']} 件(うち座標が一つに決まらない {g['ambiguous']} 件) → data/gazetteer.json")


if __name__ == "__main__":
    main()
