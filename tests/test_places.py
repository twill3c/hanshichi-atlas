"""T-701..T-708 — 地名の照合と採否の台帳(F-09 / G-12)."""

import json
from pathlib import Path

import pytest

from pipeline.places import ACCEPT, EDO_BBOX, REJECT, build, resolve

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.validation


@pytest.fixture(scope="module")
def places():
    p = ROOT / "data" / "places.json"
    if not p.exists():
        pytest.skip("data/places.json 未生成")
    return json.loads(p.read_text(encoding="utf-8"))


def test_t701_gazetteer_is_external(places):
    """T-701 / G-03 — 辞書が本文に由来しないこと。"""
    gaz = json.loads((ROOT / "data" / "gazetteer.json").read_text(encoding="utf-8"))
    prov = gaz["provenance"]
    assert "wikidata" in prov["source"].lower()
    assert prov["fetched_at"]
    assert "半七" not in prov["source"]
    assert prov["regions"], "どの範囲を取ったかが記録されていない"


def test_t702_every_matched_label_has_a_verdict(places):
    """T-702 / G-04 の精神 — 本文に当たった見出し語は、採るか採らないかが必ず書いてある。

    未分類を残さない。残すと「見ていない」ことが「問題なし」に見える。
    """
    assert places["unclassified"] == [], f"採否が書かれていない見出し語: {places['unclassified']}"
    assert places["matched_labels"] == places["accepted"] + places["rejected"]


def test_t703_rejections_carry_a_reason():
    """T-703 — 不採用にはすべて理由が書かれている。

    理由の無い除外は、誤検出を見ていないことと区別がつかない(HC-041)。
    """
    assert REJECT, "不採用が 1 件も無い — 目視していない疑い"
    for label, reason in REJECT.items():
        assert len(reason) >= 6, f"{label}: 理由が短すぎる"
    assert not (set(ACCEPT) & set(REJECT)), "同じ語が採用と不採用の両方にある"


def test_t704_known_false_positives_stay_out(places):
    """T-704 — 目視で見つけた誤検出が、地図に出ていないこと。

    出所: 2026-09-01 の全数目視。部分文字列・人名・座標違いの三種から代表を取る。
    """
    mapped = {p["label"] for p in places["places"]}
    for label in ("追憶", "大南", "戸越", "春日", "六月", "かんだ", "山田", "石田", "長崎", "柳原"):
        assert label not in mapped, f"{label} が地図に出ている({REJECT.get(label)})"


def test_t705_positive_control_the_matcher_actually_fires(places):
    """T-704 の対照 — 検査が空集合に対して緑を返していないこと(HC-041)。

    実際に地図へ出ている地名があり、既知の主要地名が含まれること。
    """
    mapped = {p["label"] for p in places["places"]}
    assert len(mapped) > 50, "地図に出る地名が少なすぎる — 照合が働いていない"
    for label in ("神田", "八丁堀", "深川", "本所", "吉原"):
        assert label in mapped, f"主要な地名 {label} が地図に出ていない"


def test_t706_all_coordinates_are_inside_the_edo_frame(places):
    """T-706 / G-12 — 地図に出す座標がすべて江戸の枠の中にある。

    枠を外れる点は同名の別地物である可能性が高い。
    """
    lo_lat, hi_lat, lo_lon, hi_lon = EDO_BBOX
    bad = [
        (p["label"], p["lat"], p["lon"])
        for p in places["places"]
        if not (lo_lat <= p["lat"] <= hi_lat and lo_lon <= p["lon"] <= hi_lon)
    ]
    assert not bad, f"江戸の枠の外にある点: {bad}"


def test_t707_ambiguous_places_are_not_placed():
    """T-707 — 同名の地物が離れて複数あるとき、編者が選ばずに未同定にする。

    出所: 実測(2026-09-01)。新宿は内藤新宿(35.6909,139.7061)と
    葛飾区新宿(35.7623,139.862)が約 10km 離れている。
    """
    far = [
        {"qid": "Q836198", "lat": 35.6909, "lon": 139.7061},
        {"qid": "Q11501780", "lat": 35.7623, "lon": 139.862},
    ]
    assert resolve("新宿", far) is None, "離れた同名候補から一つを選んでしまっている"
    near = [
        {"qid": "Q1", "lat": 35.6841, "lon": 139.7745},
        {"qid": "Q2", "lat": 35.6817, "lon": 139.7728},
    ]
    got = resolve("日本橋", near)
    assert got is not None and got["candidates_in_bbox"] == 2
    outside = [{"qid": "Q3", "lat": 34.3958, "lon": 132.4629}]
    assert resolve("八丁堀", outside) is None, "枠の外の候補を採ってしまっている"


def test_t708_unresolvable_places_are_listed(places):
    """T-708 / F-09 — 同定できない地名を黙って消さず、一覧に残す。

    とくに **半七の家(神田三河町)は辞書に無い**。これは地図の中心にあたる場所なので、
    出せないことを明示する。
    """
    assert "神田三河町" in places["not_in_gazetteer"]
    assert "三河町" in places["not_in_gazetteer"]
    assert "品川" in places["not_in_gazetteer"]
    for u in places["unresolved"]:
        assert u["reason"]


def test_t709_rebuild_is_stable(places):
    """T-709 — 作り直しても同じものが出る(生成が決定的)。"""
    again = build()
    assert [p["label"] for p in again["places"]] == [p["label"] for p in places["places"]]
    assert again["mentions"] == places["mentions"]


@pytest.mark.unit
def test_t710_longest_match_wins():
    """T-710 — 同じ位置では長い見出し語が勝ち、部分一致を二重に数えない。

    照合を正規表現の巨大な選択肢から辞書引きに書き換えたときに、
    この性質が失われていないことを固定する(HC-070: 実装を差し替えたら不変量の根拠を再導出する)。
    """
    from pipeline.places import find_mentions

    labels = ["神田", "神田三河町", "三河町", "橋"]
    got = find_mentions("神田三河町の半七", labels)
    assert [m["label"] for m in got] == ["神田三河町"]
    assert got[0]["offset"] == 0
    # 対照: 長い語が無ければ短い語で当たる
    assert [m["label"] for m in find_mentions("神田の半七", labels)] == ["神田"]
    # 重なる位置を二度数えない
    assert len(find_mentions("神田神田", labels)) == 2
