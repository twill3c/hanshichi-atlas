"""T-601..T-606 — Web が読むデータとページの構造(F-08 / F-11 / N-01).

図が読めるかどうかは、ここでは分からない。それは `harness/inspect_web.py` の仕事で、
実ブラウザで複数の幅を開いて確かめる(HC-041)。このファイルが見るのは、
**出荷するデータが本文と一致していること**と、**ページが外に出て行かないこと**である。
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

pytestmark = pytest.mark.validation


@pytest.fixture(scope="module")
def index():
    p = WEB / "data" / "index.json"
    if not p.exists():
        pytest.skip("web/data/index.json 未生成(pipeline/build_web.py を先に)")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plain():
    return json.loads((ROOT / "data" / "plain.json").read_text(encoding="utf-8"))


def test_t601_index_covers_every_story(index):
    """T-601 — 一覧が台帳と同じ集合を覆う(件数を定数で書かない)。"""
    cases = json.loads((ROOT / "data" / "case_years.json").read_text(encoding="utf-8"))
    assert {s["no"] for s in index["stories"]} == set(cases["stories"])
    assert index["counts"] == cases["counts"]
    for s in index["stories"]:
        assert s["kind"] in index["kinds"]


def test_t602_reader_nodes_reconstruct_the_text(plain):
    """T-602 — リーダーのノード列から本文を組み直すと plain.json と完全一致する。

    これがリーダーの背骨の検査である。表示の見た目ではなく、
    **配っているものが本文そのものか**を見る。注記は本文ではないので数に入れない。
    """
    story_dir = WEB / "data" / "story"
    files = sorted(story_dir.glob("*.json"))
    assert files, "web/data/story/ が空(対照として無意味)"
    bad = []
    for p in files:
        nodes = json.loads(p.read_text(encoding="utf-8"))["nodes"]
        got = "".join(
            n["v"] if n["t"] in ("s", "g") else n["b"] if n["t"] == "r" else "\n" if n["t"] == "br" else ""
            for n in nodes
        )
        if got != plain[p.stem]:
            bad.append(p.stem)
    assert not bad, f"リーダー用データが本文と一致しない話: {bad}"


def test_t602b_positive_control_for_the_reconstruction(plain):
    """T-602 の陽性対照(HC-041) — 組み直しの検査が実際に落ちること。

    ルビの base を落とした組み方をすれば、全話で一致しなくなるはずである。
    """
    p = WEB / "data" / "story" / "69.json"
    nodes = json.loads(p.read_text(encoding="utf-8"))["nodes"]
    broken = "".join(
        n["v"] if n["t"] in ("s", "g") else "\n" if n["t"] == "br" else "" for n in nodes
    )
    assert broken != plain["69"], "ルビを落としても一致する — 検査が本文を見ていない"


def test_t603_counts_match_the_measured_stats(index):
    """T-603 — 一覧の字数・ルビ数が実測の統計と一致する。"""
    stats = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))["stories"]
    for s in index["stories"]:
        assert s["chars"] == stats[s["no"]]["chars"]
        assert s["ruby"] == stats[s["no"]]["ruby"]


def _strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def test_t604_palette_is_the_validated_one():
    """T-604 — 図の配色が検証器に掛けた値のままであること。

    出所: dataviz の検証器(2026-08-31 実行)。光・暗の両モードで全項目通過した
    系統 1(青)と系統 2(橙)。翠 #1baf7a は面に対する contrast が 3:1 を切るので使わない。
    ここで固定しておかないと、配色は理由なく動く。

    **「使わない」と書いた文は違反ではない**(HC-074)。禁止の検査は引用・言及と
    使用・依存を分ける必要があり、ここでは CSS コメントを線にする。
    最初はこの線を引かずに書いて、理由を説明したコメントを違反として落とした。
    """
    raw = (WEB / "style.css").read_text(encoding="utf-8")
    used = _strip_css_comments(raw)
    for hexv in ("#2a78d6", "#3987e5", "#eb6834", "#d95926"):
        assert hexv in used, f"検証済みの色 {hexv} が CSS から消えている"
    assert "#1baf7a" not in used, "contrast を通らない翠が宣言に入っている"
    # 線が緩みすぎていないことの対照 —— コメントの外に置けば捕まること
    assert "#1baf7a" not in _strip_css_comments("a{color:#1baf7a}"[:0] + "/* #1baf7a */")
    assert "#1baf7a" in _strip_css_comments("a{color:#1baf7a}")


#: 取りに行かない URL。XML 名前空間は識別子であって取得先ではない(HC-074)。
NON_FETCHED_URLS = {"http://www.w3.org/2000/svg"}


def test_t605_pages_are_self_contained():
    """T-605 / N-01 — ページが外部から何かを取りに行かない(静的・サーバ不要)。

    最初は「http で始まる文字列があれば違反」と書いて、SVG の名前空間を落とした。
    名前空間は**宣言**であって取得ではない。除外は列挙し、緩みすぎないことを対照で押さえる。
    """
    for name in ("index.html", "reader.html", "app.js", "reader.js", "style.css"):
        src = (WEB / name).read_text(encoding="utf-8")
        urls = [u for u in re.findall(r"https?://[^\s\"')]+", src) if u not in NON_FETCHED_URLS]
        assert not urls, f"{name} が外部を参照している: {urls}"
    # 対照 —— 除外リストが広すぎないこと。本物の外部参照は捕まる
    probe = [
        u
        for u in re.findall(r"https?://[^\s\"')]+", '<script src="https://cdn.example.com/x.js">')
        if u not in NON_FETCHED_URLS
    ]
    assert probe, "除外が広すぎて、本物の外部参照まで見逃す"


def test_t606_every_story_has_a_reader_payload(index):
    """T-606 — 一覧に載っている話は必ずリーダーで開ける。"""
    missing = [s["no"] for s in index["stories"] if not (WEB / "data" / "story" / f"{s['no']}.json").exists()]
    assert not missing, f"リーダー用データが無い話: {missing}"


def test_t607_undetermined_stories_show_no_year(index):
    """T-607 / F-07 — 年を確定できない話は、画面に出す値も空であること。

    台帳で null にしておきながら画面で埋めてしまっては意味がない。
    """
    for s in index["stories"]:
        if s["kind"] != "確定できない":
            continue
        assert all(not c["years"] for c in s["cases"])
        assert s["reason"], f"{s['no']}: 理由が画面データに載っていない"
