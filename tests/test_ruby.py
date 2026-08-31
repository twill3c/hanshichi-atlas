"""T-801..T-806 — ルビの解剖(F-10)."""

import json
from pathlib import Path

import pytest

from pipeline.ruby import BASE_BOOK, build

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.validation


@pytest.fixture(scope="module")
def ruby():
    p = ROOT / "data" / "ruby.json"
    if not p.exists():
        pytest.skip("data/ruby.json 未生成")
    return json.loads(p.read_text(encoding="utf-8"))


def test_t801_provenance_says_who_added_the_ruby(ruby):
    """T-801 — ルビの出所が書いてあり、大正のものだと言っていないこと。

    底本は光文社文庫(1985 年初版)で、ルビは昭和末の校訂による。
    この断りが消えると、ページは「綺堂が振ったルビ」という誤った話をする。
    """
    assert "1985" in ruby["base_book"] and "光文社" in ruby["base_book"]
    assert ruby["base_book"] == BASE_BOOK
    assert "大正" in ruby["caveat"] and "校訂" in ruby["caveat"]


def test_t802_totals_match_the_measured_stats(ruby):
    """T-802 — ルビの総数が L1 の実測と一致する(別経路で数えても同じ)。"""
    stats = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))["stories"]
    assert ruby["total"] == sum(s["ruby"] for s in stats.values())
    for s in ruby["stories"]:
        assert s["ruby"] == stats[s["no"]]["ruby"]
        assert s["chars"] == stats[s["no"]]["chars"]


def test_t803_first_occurrence_rate_is_high_and_measured(ruby):
    """T-803 — 「ルビが付くならその話の初出」がどれだけ成り立つか。

    実測 2026-09-01: 掃除した語 2,372 件で 4239/4338 = 97.7%。
    ここでは率を定数で固定せず、**分子と分母が整合していること**と、
    例外が捨てられずに残っていることを見る(SPEC の保証粒度を超えない)。
    """
    f = ruby["first_occurrence"]
    assert f["ruby_on_first"] + f["ruby_elsewhere"] > 1000, "標本が小さすぎる"
    # rate は小数 4 桁に丸めて保存してあるので、許容差はその粒度に合わせる。
    # SPEC の保証粒度を超える精度を要求しない(HC-016)。
    assert abs(f["rate"] - f["ruby_on_first"] / (f["ruby_on_first"] + f["ruby_elsewhere"])) < 1e-4
    assert f["rate"] > 0.9, f"初出率が {f['rate']:.3f} まで落ちた — 前提を見直すこと"
    assert f["exceptions"], "例外が 1 件も残っていない(捨てている疑い)"
    for e in f["exceptions"]:
        assert e["base"] in e["excerpt"]


def test_t804_the_per_story_rate_is_the_real_finding(ruby):
    """T-804 — 「同じ語でも、現れる話の一部でしか振られない」ことを固定する。

    これが F-10 の主張の土台である。もしこの率が 1 に近ければ
    「ルビ = その語が出るたび必ず付く印」になり、話がまるごと変わる。
    実測 2026-09-01: 早い巻 39.7% / 遅い巻 38.4%。
    """
    p = ruby["per_story_rate"]
    assert p["words"] > 100, "早い巻と遅い巻の両方に出る語が少なすぎる"
    assert 0.2 < p["early_rate"] < 0.8, "率が両端に寄っている — 測り方を見直すこと"
    assert 0.2 < p["late_rate"] < 0.8
    # 巻による差は小さい。**大きくなったら、それ自体が発見なので気づけるようにする**
    assert abs(p["early_rate"] - p["late_rate"]) < 0.1, (
        f"早い巻と遅い巻で差が開いた({p['early_rate']} / {p['late_rate']}) — "
        "校訂の方針が巻で違う可能性がある。SPEC を見直すこと"
    )


def test_t805_early_late_comparison_is_symmetric(ruby):
    """T-804 の前提を assert で固定する(HC-079)。

    比較は「早い巻と遅い巻の**両方に現れる語**」に限っている。
    片方にしか出ない語を混ぜると、語彙の違いを校訂の違いと取り違える。
    """
    p = ruby["per_story_rate"]
    assert p["early_appear"] > 0 and p["late_appear"] > 0
    assert p["early_ruby"] <= p["early_appear"]
    assert p["late_ruby"] <= p["late_appear"]


def test_t806_cleaning_rules_actually_exclude(ruby):
    """T-806 — 掃除の規則が効いていること。

    読みが二通り以上ある語(家《うち》/《いえ》)は数から外す。
    外さないと別の語を同じ語として数える。
    """
    assert ruby["multi_yomi_count"] > 0, "読みの揺れが 1 件も無い — 掃除が働いていない疑い"
    assert ruby["clean_bases"] < ruby["unique_bases"], "掃除で 1 件も減っていない"
    bases = {m["base"] for m in ruby["multi_yomi"]}
    assert "家" in bases, "家《うち》/《いえ》が揺れとして拾えていない"
    for m in ruby["multi_yomi"]:
        assert len(m["yomi"]) >= 2


def test_t807_rebuild_is_stable(ruby):
    """T-807 — 作り直しても同じ数が出る。"""
    again = build()
    assert again["total"] == ruby["total"]
    assert again["first_occurrence"]["rate"] == ruby["first_occurrence"]["rate"]
    assert again["per_story_rate"] == ruby["per_story_rate"]
