"""T-401..T-404 — 半七の年齢言明と、目玉ゲート G-05 の判定(F-06)."""

import json
from pathlib import Path

import pytest

from pipeline.age import STATEMENTS, birth_year, build

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def texts():
    p = ROOT / "data" / "plain.json"
    if not p.exists():
        pytest.skip("data/plain.json 未生成")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_t401_counted_age_arithmetic():
    """T-401 — 数え年から生年を出す式。

    期待値の出所: 数え年の定義(生まれた年を 1 歳とする)。
    生年 = その年 - 年齢 + 1。
    """
    assert birth_year({"year": 1855, "age": 33}) == 1823
    assert birth_year({"year": 1841, "age": 19}) == 1823
    assert birth_year({"year": 1895, "age": 73}) == 1823


@pytest.mark.validation
def test_t403_ledger_quotes_are_verbatim_in_the_text(texts):
    """T-403 — 台帳の引用と根拠が、本文に逐語で在る。

    台帳は手で作るので、本文から離れていける。離れたらここで落ちる。
    """
    assert STATEMENTS, "台帳が空"
    for s in STATEMENTS:
        t = texts[s["story"]]
        assert s["quote"] in t, f"{s['story']}: 引用が本文に無い — {s['quote']}"
        assert s["evidence"] in t, f"{s['story']}: 話者の根拠が本文に無い — {s['evidence']}"


@pytest.mark.unit
def test_t402_flagship_gate_g05():
    """T-402 / G-05 — 目玉ゲートの判定。

    SPEC の当初の目玉は「半七の生年は本文の中で矛盾する」だった。
    実測(2026-08-31)の結果、半七に帰属する三つの言明はいずれも生年 1823 に収束し、
    **主張は成立しなかった**。G-05 の規定に従って目玉は取り下げてある。

    このテストは、取り下げの根拠である収束を固定する。将来ここが破れたら
    (新たな言明が見つかる・帰属が変わる)、SPEC を書き換え直す合図になる。
    """
    res = build()
    assert res["converges"], (
        f"半七の生年が収束しなくなった: {res['hanshichi_birth_candidates']} — "
        "SPEC の目玉の扱いを見直すこと"
    )
    assert res["hanshichi_birth_candidates"] == [1823]


@pytest.mark.unit
def test_t404_uncle_is_not_hanshichi():
    """T-404 — 22 年のずれは矛盾ではなく別人であることを固定する。

    01 の「わたしが丁度二十歳の時だから、元治元年」を半七に帰属させると
    生年 1845 になり、三件と 22 年ずれる。この誤りを二度踏まないための対照。
    """
    uncle = [s for s in STATEMENTS if s["speaker"].startswith("Ｋのおじさん")]
    assert len(uncle) == 1
    assert birth_year(uncle[0]) == 1845
    hanshichi = {birth_year(s) for s in STATEMENTS if s["speaker"] == "半七"}
    assert 1845 not in hanshichi
    assert min(hanshichi) - birth_year(uncle[0]) == -22
