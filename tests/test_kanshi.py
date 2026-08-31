"""T-305..T-307 — 干支の解決と、本文内部の年代照合(F-05)."""

import json
from pathlib import Path

import pytest

from pipeline.kanshi import KanshiError, kanshi_index, year_of_kanshi, years_with_branch

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.unit
def test_t305_sexagenary_anchor():
    """T-305 — 干支の基準点。

    期待値の出所: 干支紀年法の定義。西暦 4 年が甲子であり、以後 60 年周期。
    1864 年(元治元年)が甲子であることは広く知られた対照であり、
    「甲子園」の名の由来となった 1924 年もまた甲子である(1924 = 1864 + 60)。
    """
    assert kanshi_index(1864) == 0  # 甲子
    assert kanshi_index(1924) == 0
    assert kanshi_index(1865) == 1  # 乙丑


@pytest.mark.unit
def test_t306_kanshi_resolves_within_an_era():
    """T-306 — 元号の期間内で干支から年を一意に決める。

    期待値の出所: 35「半七先生」の落款「嘉永庚戌」(実測 2026-08-31)。
    嘉永は 1848–1854 の 7 年しかないので、庚戌(60 年に 1 度)は一意に決まる。
    """
    table = json.loads((ROOT / "data" / "era_table.json").read_text(encoding="utf-8"))
    assert year_of_kanshi("庚戌", "嘉永", table) == 1850  # 嘉永三年
    # 十二支だけでも、元号が 12 年以下なら一意に決まる
    assert years_with_branch("丑", "天保", table) == [1841]  # 天保十二年
    assert years_with_branch("午", "安政", table) == [1858]  # 安政五年
    # 一意に決まらない場合は複数返す(黙って 1 つ選ばない)
    assert len(years_with_branch("子", "明治", table)) > 1


@pytest.mark.unit
def test_t306b_unknown_kanshi_raises():
    """T-306 — 知らない干支は黙って通さない。"""
    table = json.loads((ROOT / "data" / "era_table.json").read_text(encoding="utf-8"))
    with pytest.raises(KanshiError):
        year_of_kanshi("甲甲", "嘉永", table)


@pytest.mark.validation
def test_t307_internal_cross_check_of_dates():
    """T-307 — 本文が元号年と干支の両方を書いている箇所で、両者が一致する。

    これは**非循環のオラクル**である。綺堂の年代表記が内部で整合しているかを、
    外部の年譜を持ち込まずに測れる。一致しない箇所があればそれ自体が発見なので、
    ここでは「一致率 100%」を要求せず、**判定できたものが 1 件以上あること**と
    **不一致があれば列挙されること**を保証する(SPEC の保証粒度を超えない — HC-016)。
    """
    p = ROOT / "data" / "date_crosscheck.json"
    if not p.exists():
        pytest.skip("data/date_crosscheck.json 未生成")
    res = json.loads(p.read_text(encoding="utf-8"))
    assert res["checked"] > 0, "照合できた箇所が 1 件も無い(オラクルが働いていない)"
    for row in res["rows"]:
        assert row["agrees"] in (True, False)
        assert row["evidence"], "根拠の本文が記録されていない"
    # 不一致は捨てずに残す
    assert res["disagree"] == sum(1 for r in res["rows"] if not r["agrees"])


@pytest.mark.validation
def test_t308_crosscheck_positive_control():
    """T-308 — 照合が実際に不一致を捕まえられることを確かめる(HC-041 / HC-080)。

    「不一致 0 件」は、照合が働いていなくても同じ緑を返す。
    換算表を 1 年ずらせば全件が落ちるはずで、落ちないならこの照合は何も見ていない。
    """
    from pipeline.crosscheck import crosscheck_text

    tp = ROOT / "data" / "era_table.json"
    xp = ROOT / "data" / "plain.json"
    if not (tp.exists() and xp.exists()):
        pytest.skip("データ未生成")
    table = json.loads(tp.read_text(encoding="utf-8"))
    texts = json.loads(xp.read_text(encoding="utf-8"))
    shifted = {**table, "first_year": {k: v + 1 for k, v in table["first_year"].items()}}

    ok = [r for no, t in texts.items() for r in crosscheck_text(no, t, table)]
    bad = [r for no, t in texts.items() for r in crosscheck_text(no, t, shifted)]
    assert ok, "照合対象が空(対照として無意味)"
    assert len(ok) == len(bad), "ずらした表で照合の件数まで変わっている"
    assert sum(1 for r in bad if not r["agrees"]) == len(bad), (
        "1 年ずらしても不一致にならない — 照合が干支を見ていない"
    )
