"""T-301..T-304 — 元号年の抽出と換算(F-05 / G-03 / G-06)."""

import json
from pathlib import Path

import pytest

from pipeline.era_scan import FORMS, dated, scan
from pipeline.era_table import EraTableError, to_western

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"


def _fixture_lines(name):
    for line in (FIX / name).read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            yield line.split("\t")


@pytest.fixture(scope="module")
def table():
    p = ROOT / "data" / "era_table.json"
    if not p.exists():
        pytest.skip("data/era_table.json 未生成")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_t301_positive_control():
    """T-301 / G-06 — 捕まえるべき元号年をすべて捕まえる。

    期待値の出所: フィクスチャ行頭に書いた実測値(2026-08-31)。
    """
    rows = list(_fixture_lines("era_positive.txt"))
    assert rows, "陽性対照が空(対照として無意味)"
    for no, expect, text in rows:
        era, year, eto = expect.split(",")
        got = dated(text)
        assert len(got) == 1, f"{no}: 1 件のはずが {len(got)} 件 — {got}"
        g = got[0]
        assert g["era"] == era, f"{no}: 元号 {g['era']} != {era}"
        assert g["year"] == (int(year) if year else None), f"{no}: 年 {g['year']} != {year}"
        assert (g["eto"] or "") == eto, f"{no}: 干支 {g['eto']} != {eto}"


@pytest.mark.unit
def test_t302_negative_control():
    """T-302 / G-06 — 元号語を含むが年ではない例で 1 件も撃たない。"""
    rows = list(_fixture_lines("era_negative.txt"))
    assert rows, "陰性対照が空(対照として無意味)"
    for no, text in rows:
        got = dated(text)
        assert got == [], f"{no}: 誤検出 {got} — {text}"


@pytest.mark.unit
def test_t302b_negative_lines_actually_contain_era_words():
    """T-302 の前提を assert で固定する(HC-079)。

    陰性対照は「元号語を含むのに年として撃たない」ことを主張する。
    元号語すら入っていない行が混ざると、対照は何も言わなくなる。
    """
    for no, text in _fixture_lines("era_negative.txt"):
        assert scan(text), f"{no}: 元号語を 1 件も含まない行が陰性対照に混じっている"


@pytest.mark.validation
def test_t303_full_corpus_coverage():
    """T-303 / G-04 — 全 69 話で走査が例外を出さず、未分類が 0 件(F-05)。

    走査対象が空でないことも確かめる。
    """
    p = ROOT / "data" / "plain.json"
    if not p.exists():
        pytest.skip("data/plain.json 未生成")
    texts = json.loads(p.read_text(encoding="utf-8"))
    assert len(texts) > 0
    total = 0
    for no, t in texts.items():
        for hit in scan(t):
            total += 1
            assert hit["form"] in FORMS, f"{no}: 未知の分類 {hit['form']}"
    assert total > 0, "元号語が 1 件も見つからない(走査が働いていない)"


@pytest.mark.unit
def test_t304_era_table_is_independent_of_the_text(table):
    """T-304 / G-03 — 換算表が本文に由来しないこと。"""
    prov = table["provenance"]
    assert "wikipedia" in prov["source_url"]
    assert "半七" not in prov["source"]
    assert prov["fetched_at"]
    # 換算の粒度は年。SPEC の保証粒度を超える主張をしない。
    assert "年" in prov["granularity"]


@pytest.mark.unit
def test_t304b_conversion_handles_the_ansei_boundary(table):
    """T-304 — 改元日の西暦を採ると 1 年ずれる境界(安政)で正しいこと。

    期待値の出所: 一般に流通する和暦西暦対照の通説値。安政元年 = 1854。
    改元日そのものは 1855-01-15 なので、改元日基準の実装はここで落ちる。
    """
    assert to_western("安政", 1, table) == 1854
    assert to_western("安政", 7, table) == 1860  # 安政七年 = 万延元年の年
    assert to_western("元治", 1, table) == 1864
    assert to_western("明治", 1, table) == 1868
    with pytest.raises(EraTableError):
        to_western("令和", 1, table)
