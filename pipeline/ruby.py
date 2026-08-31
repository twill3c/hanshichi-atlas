"""ルビの解剖(F-10)。

誰が振ったルビか
----------------
底本は光文社文庫『時代推理小説 半七捕物帳』全 6 巻(1985 年初版)である。
したがって **ここにあるルビは大正の連載時のものではなく、昭和末の校訂による**。
綺堂が振ったルビとして読んではならない。

測ったこと
----------
1. **ルビが付くとき、それはその話での初出か。** 掃除した語で 97.7%(実測 2026-09-01)
2. **同じ語は、現れる話のうちどれだけで振られるか。** 約 4 割にとどまる ——
   つまりルビは「難しい語」の印ではない。同じ語が、ある話では振られ、別の話では振られない
3. 底本の巻ごとの密度は 7.2〜9.8/千字と幅があるが、早い巻と遅い巻で
   同じ語の初出ルビ率はほとんど変わらず(39.7% / 38.4%)、長さとの相関も弱い(r = -0.23)。
   **なぜ振られたり振られなかったりするのかは、本文だけからは説明できなかった**

掃除(contaminated)について
--------------------------
素の出現とルビ付きの出現を数えるとき、次の語は数から外す。外さないと、
別の語を同じ語として数えてしまう。

- 1 文字の語(他語の一部に紛れる)
- 読みが二通り以上ある語(家《うち》と家《いえ》は別の語)
- 他のルビ語の一部になる語(「出来」は「出来る」の一部にもなる)
"""

from __future__ import annotations

import collections
import json
import math
import re
from pathlib import Path
from typing import Any

from pipeline.aozora_parser import extract_main_text, parse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

BASE_BOOK = "光文社文庫『時代推理小説 半七捕物帳』全 6 巻(1985 年初版)"
_VOL = re.compile(r"（([一二三四五六])）")
EARLY, LATE = set("一二三"), set("四五六")


def _layout(no: str) -> tuple[str, list[tuple[int, int, str, str]]]:
    """素のテキストと、ルビが覆う範囲を同時に作る。"""
    nodes = parse(extract_main_text((DATA / "raw" / f"{no}.html").read_text(encoding="utf-8")))
    buf: list[str] = []
    spans: list[tuple[int, int, str, str]] = []
    pos = 0
    after_br = False
    for n in nodes:
        if n["kind"] == "text":
            v = n["text"].replace("\r\n", "\n")
            if after_br and v.startswith("\n"):
                v = v[1:]
            after_br = False
            buf.append(v)
            pos += len(v)
        elif n["kind"] == "ruby":
            spans.append((pos, pos + len(n["base"]), n["base"], n["yomi"]))
            buf.append(n["base"])
            pos += len(n["base"])
            after_br = False
        elif n["kind"] == "gaiji":
            buf.append(n["alt"])
            pos += len(n["alt"])
            after_br = False
        elif n["kind"] == "raw" and n["tag"] == "br":
            buf.append("\n")
            pos += 1
            after_br = True
    return "".join(buf), spans


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den


def _correlations(per_story: list[dict]) -> dict:
    """相関は一つの数で出さない。

    最長の一話を外すと r は 0.92 から 0.72 へ、長い上位 5 話を外すと 0.65 へ落ちる
    (実測 2026-09-01)。**相関は長い話の梃子にかなり支えられている**。
    一つの数だけを出すと「きれいに比例する」という以上の印象を与えるので、
    外したときの値も併せて出す。
    """
    def r(rows: list[dict], key: str) -> float:
        return round(_pearson([x["chars"] for x in rows], [x[key] for x in rows]), 3)

    by_len = sorted(per_story, key=lambda s: -s["chars"])
    return {
        "chars_vs_ruby": r(per_story, "ruby"),
        "chars_vs_ruby_without_longest": r(by_len[1:], "ruby"),
        "chars_vs_ruby_without_top5": r(by_len[5:], "ruby"),
        "longest": {"no": by_len[0]["no"], "title": by_len[0]["title"], "chars": by_len[0]["chars"]},
        "chars_vs_density": r(per_story, "density"),
    }


def build() -> dict:
    works = {w["no"]: w for w in json.loads((DATA / "aozora_works.json").read_text(encoding="utf-8"))["series"]}
    layouts = {no: _layout(no) for no in sorted(works)}
    yomi_of: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for _, spans in layouts.values():
        for _, _, base, yomi in spans:
            yomi_of[base][yomi] += 1

    all_bases = set(yomi_of)
    multi = {b for b, c in yomi_of.items() if len(c) > 1}
    clean = {
        b
        for b in all_bases
        if len(b) >= 2 and b not in multi and not any(b in o and o != b for o in all_bases)
    }

    per_story = []
    first_ok = first_ng = 0
    exceptions: list[dict[str, Any]] = []
    appear = collections.defaultdict(lambda: {"early": 0, "early_ruby": 0, "late": 0, "late_ruby": 0})

    for no, (text, spans) in layouts.items():
        vol = _VOL.search(works[no]["base_book"])
        vol = vol.group(1) if vol else "?"
        covered: set[int] = set()
        for a, b, _, _ in spans:
            covered.update(range(a, b))
        in_story = {b for _, _, b, _ in spans}
        for base in in_story & clean:
            i = text.find(base)
            if i < 0:
                continue
            if i in covered:
                first_ok += 1
            else:
                first_ng += 1
                if len(exceptions) < 40:
                    exceptions.append(
                        {"story": no, "base": base, "excerpt": text[max(0, i - 20) : i + 20].replace("\n", " ")}
                    )
        key = "early" if vol in EARLY else "late"
        for base in clean:
            i = text.find(base)
            if i < 0:
                continue
            appear[base][key] += 1
            if i in covered:
                appear[base][key + "_ruby"] += 1
        per_story.append(
            {
                "no": no,
                "title": works[no]["title"],
                "vol": vol,
                "chars": len(text),
                "ruby": len(spans),
                "uniq": len(in_story),
                "density": round(len(spans) / len(text) * 1000, 2),
            }
        )

    both = [b for b, k in appear.items() if k["early"] and k["late"]]
    e_r = sum(appear[b]["early_ruby"] for b in both)
    e_o = sum(appear[b]["early"] for b in both)
    l_r = sum(appear[b]["late_ruby"] for b in both)
    l_o = sum(appear[b]["late"] for b in both)

    by_vol: dict[str, dict[str, int]] = collections.defaultdict(lambda: {"stories": 0, "chars": 0, "ruby": 0})
    for s in per_story:
        v = by_vol[s["vol"]]
        v["stories"] += 1
        v["chars"] += s["chars"]
        v["ruby"] += s["ruby"]
    vols = [
        {"vol": v, **d, "density": round(d["ruby"] / d["chars"] * 1000, 2)}
        for v, d in sorted(by_vol.items())
    ]

    counts = collections.Counter()
    story_count: dict[tuple[str, str], set] = collections.defaultdict(set)
    for no, (_, spans) in layouts.items():
        for _, _, base, yomi in spans:
            counts[(base, yomi)] += 1
            story_count[(base, yomi)].add(no)
    words = [
        {"base": b, "yomi": y, "count": n, "stories": len(story_count[(b, y)])}
        for (b, y), n in counts.most_common()
    ]

    chars = [s["chars"] for s in per_story]
    return {
        "base_book": BASE_BOOK,
        "caveat": "ルビは大正の連載時のものではなく、底本(1985 年)の校訂による",
        "total": sum(s["ruby"] for s in per_story),
        "unique_words": len(counts),
        "unique_bases": len(all_bases),
        "multi_yomi": sorted(
            (
                {"base": b, "yomi": dict(yomi_of[b].most_common())}
                for b in multi
            ),
            key=lambda d: -sum(d["yomi"].values()),
        )[:40],
        "multi_yomi_count": len(multi),
        "clean_bases": len(clean),
        "first_occurrence": {
            "ruby_on_first": first_ok,
            "ruby_elsewhere": first_ng,
            "rate": round(first_ok / (first_ok + first_ng), 4),
            "exceptions": exceptions,
        },
        "per_story_rate": {
            "words": len(both),
            "early_ruby": e_r,
            "early_appear": e_o,
            "early_rate": round(e_r / e_o, 4),
            "late_ruby": l_r,
            "late_appear": l_o,
            "late_rate": round(l_r / l_o, 4),
        },
        "correlations": _correlations(per_story),
        "volumes": vols,
        "stories": per_story,
        "words": words,
    }


def main() -> None:
    r = build()
    (DATA / "ruby.json").write_text(
        json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    f = r["first_occurrence"]
    p = r["per_story_rate"]
    print(f"ルビ {r['total']:,} / 異なり(語と読みの組) {r['unique_words']:,} / 読みが二通り以上 {r['multi_yomi_count']}")
    print(f"初出にルビ: {f['ruby_on_first']}/{f['ruby_on_first'] + f['ruby_elsewhere']} = {f['rate'] * 100:.1f}%")
    print(f"同じ語が現れる話のうち振られる割合: 早い巻 {p['early_rate'] * 100:.1f}% / 遅い巻 {p['late_rate'] * 100:.1f}%")
    print(f"字数とルビ総数の相関 r = {r['correlations']['chars_vs_ruby']}")


if __name__ == "__main__":
    main()
