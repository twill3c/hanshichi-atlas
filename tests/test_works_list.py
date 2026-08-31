"""T-101..T-104 — 作品一覧の採録(F-01 / F-02 / G-01)."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKS = ROOT / "data" / "aozora_works.json"

pytestmark = pytest.mark.validation


@pytest.fixture(scope="module")
def works():
    if not WORKS.exists():
        pytest.skip("data/aozora_works.json 未生成(pipeline/fetch_aozora.py を先に実行)")
    return json.loads(WORKS.read_text(encoding="utf-8"))


def test_t101_serial_numbers_form_a_contiguous_set(works):
    """T-101 / G-01 — 通番の集合オラクル。

    期待値の出所: コーパス自身の手がかり。青空文庫の副題は
    「01 お文の魂」のように先頭 2 桁が連番になっている。
    外部の「全 69 話」という定数には頼らず、抽出した通番が
    1 から最大値までの整数を欠落なく覆うことで書く(HC-016)。
    """
    nos = [w["no"] for w in works["series"]]
    assert nos, "series が空"
    assert len(nos) == len(set(nos)), f"通番が重複: {sorted(nos)}"
    ints = sorted(int(n) for n in nos)
    assert set(ints) == set(range(1, max(ints) + 1)), (
        f"通番に欠番がある: 欠けているのは {sorted(set(range(1, max(ints) + 1)) - set(ints))}"
    )
    # 通番は 2 桁ゼロ詰めで保持する(並べ替えの安定のため)
    assert all(len(n) == 2 and n.isdigit() for n in nos)


def test_t102_out_of_series_entries_are_separated(works):
    """T-102 — 旧字旧仮名版と随筆を series に混ぜない(F-01)."""
    assert all(w["variant"] == "新字新仮名" for w in works["series"])
    others = {w["work_id"] for w in works["out_of_series"]}
    assert "049532" in others, "随筆「半七捕物帳の思い出」(49532)が out_of_series に無い"
    series_ids = {w["work_id"] for w in works["series"]}
    assert not (series_ids & others), "series と out_of_series が重複している"
    # 旧字旧仮名の 01 が out_of_series 側に落ちていること
    assert any(w["variant"] == "旧字旧仮名" for w in works["out_of_series"])


def test_t103_provenance_present(works):
    """T-103 / N-03 — 出所と取得日(F-01)."""
    assert works["provenance"]["source_url"].startswith("https://www.aozora.gr.jp/")
    assert works["provenance"]["fetched_at"]
    for w in works["series"]:
        assert w["text_url"].startswith("https://www.aozora.gr.jp/")
        assert w["card_url"].startswith("https://www.aozora.gr.jp/")


def test_t105_raw_files_keep_the_source_line_endings(works):
    """T-105 — 保存した原文の改行が膨らんでいないこと(F-02 / N-03)。

    Path.write_text を newline 指定なしで呼ぶと、Windows では原文の CRLF が
    CR+CRLF に膨らむ。2026-08-31 に全 69 話でこれが起きた。読み戻すと改行が
    二重になるが、下流で畳んでしまうと症状が消えるので、**保存物そのものを見る**。
    """
    raw = ROOT / "data" / "raw"
    files = sorted(raw.glob("*.html"))
    assert files, "data/raw が空(対照として無意味)"
    bad = [p.name for p in files if b"\r\r\n" in p.read_bytes() or b"\n\r" in p.read_bytes()]
    assert not bad, f"改行が膨らんでいる話: {bad}"


def test_t104_every_series_work_has_a_local_text(works):
    """T-104 — 採録した全話の本文が data/raw にある(F-02)."""
    raw = ROOT / "data" / "raw"
    missing = [w["no"] for w in works["series"] if not (raw / f"{w['no']}.html").exists()]
    assert not missing, f"本文が取得されていない話: {missing}"
