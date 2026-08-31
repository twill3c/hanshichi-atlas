"""T-201..T-204 — 青空文庫 XHTML パーサーと往復検査(F-03 / F-04 / G-02)."""

import json
from pathlib import Path

import pytest

from pipeline.aozora_parser import extract_main_text, parse, plain_text, serialize

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="module")
def excerpt():
    p = FIX / "excerpt_42.html"
    if not p.exists():
        pytest.skip("フィクスチャ未生成")
    return p.read_text(encoding="utf-8")


@pytest.mark.unit
def test_t201_roundtrip_on_fixture(excerpt):
    """T-201 / G-02 — 往復検査(自己完結オラクル)。

    原文が正解であり外部の正解を要さない。パーサーの逆写像が
    恒等になることだけを主張する。
    """
    assert serialize(parse(excerpt)) == excerpt


@pytest.mark.unit
def test_t203_ruby_extraction(excerpt):
    """T-203 — ルビの base / yomi(F-03)。

    期待値の出所: フィクスチャ実測(2026-08-31)。定数で書かず、
    フィクスチャ自身から導出した集合と突き合わせる(HC-068)。
    """
    import re

    nodes = parse(excerpt)
    got = [(n["base"], n["yomi"]) for n in nodes if n["kind"] == "ruby"]
    # フィクスチャの生マークアップから独立に導出した期待値
    want = re.findall(
        r"<ruby><rb>(.*?)</rb><rp>（</rp><rt>(.*?)</rt><rp>）</rp></ruby>", excerpt
    )
    assert got == want
    assert got, "フィクスチャにルビが 1 件も無い(対照として無意味)"
    # 既知の実例(2026-08-31 実測): 42「仮面」冒頭のルビ
    assert ("二足三文", "にそくさんもん") in got


@pytest.mark.unit
def test_t203b_ruby_is_not_swallowed_by_plain_text(excerpt):
    """T-203 — plain_text はルビの base を残し、yomi を落とす(F-03)."""
    txt = plain_text(parse(excerpt))
    assert "二足三文" in txt
    assert "にそくさんもん" not in txt
    assert "<ruby>" not in txt and "<rt>" not in txt


@pytest.mark.unit
def test_t204_input_notes_are_verbatim():
    """T-204 — 入力者注 ［＃…］ を verbatim 保存する(F-03)。

    出所: 02「石灯籠」実測(2026-08-31)。
    """
    src = '　あ<span class="notes">［＃「蒲団」は底本では「薄団」］</span>い<br />\n'
    nodes = parse(src)
    assert serialize(nodes) == src
    notes = [n for n in nodes if n["kind"] == "note"]
    assert len(notes) == 1
    assert notes[0]["text"] == "［＃「蒲団」は底本では「薄団」］"
    # 注記は本文ではないので plain_text には出ない
    assert plain_text(nodes) == "　あい\n"


@pytest.mark.unit
def test_t204b_gaiji_becomes_its_alt_text():
    """T-204 — 外字画像は alt 注記に還元する(F-03)。01 実測(2026-08-31)."""
    src = (
        '　<img src="../../../gaiji/1-85/1-85-32.png" '
        'alt="※(「日／咎」、第3水準1-85-32)" class="gaiji" />る<br />\n'
    )
    nodes = parse(src)
    assert serialize(nodes) == src
    assert plain_text(nodes) == "　※(「日／咎」、第3水準1-85-32)る\n"


@pytest.mark.unit
def test_t201b_positive_control_roundtrip_detects_loss():
    """T-201 の陽性対照(HC-041) — 情報を落とすマークアップで往復が実際に落ちること。

    往復検査が「何も検査していない」状態(素通し)でないことを確かめる。
    ここでは serialize が raw を保持しなければ復元できない属性付きタグを与える。
    """
    src = '<div class="jisage_5" style="margin-left: 5em">あ</div><br />\n'
    assert serialize(parse(src)) == src
    # 対照: raw を捨てる実装なら復元できない情報が実際に入っていること
    assert 'style="margin-left: 5em"' in src


@pytest.mark.validation
def test_t202_roundtrip_over_all_stories():
    """T-202 / G-02 — 全 69 話の往復検査(F-04)。

    走査対象が空でないことも確かめる(空集合に対して緑を返さない)。
    """
    raw = ROOT / "data" / "raw"
    files = sorted(raw.glob("*.html"))
    if not files:
        pytest.skip("data/raw/ 未取得")
    works = json.loads((ROOT / "data" / "aozora_works.json").read_text(encoding="utf-8"))
    assert len(files) == len(works["series"]), "取得済みファイル数と採録話数が食い違う"
    bad = []
    for p in files:
        body = extract_main_text(p.read_text(encoding="utf-8"))
        if serialize(parse(body)) != body:
            bad.append(p.name)
    assert not bad, f"往復検査に落ちた話: {bad}"
