"""T-501..T-508 — 事件年の台帳(F-07 / G-04 / G-08 / G-09)."""

import json
from pathlib import Path

import pytest

from pipeline.case_years import CASES, KINDS, build, candidate_years

ROOT = Path(__file__).resolve().parents[1]
HANSHICHI_BIRTH = 1823  # SPEC §1(三経路が収束した値)
HANSHICHI_FIRST_CASE = 1841  # 02「石灯籠」が「彼の初陣の功名」と書く年


@pytest.fixture(scope="module")
def texts():
    p = ROOT / "data" / "plain.json"
    if not p.exists():
        pytest.skip("data/plain.json 未生成")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def built():
    return build()["stories"]


@pytest.fixture(scope="module")
def works():
    return json.loads((ROOT / "data" / "aozora_works.json").read_text(encoding="utf-8"))


@pytest.mark.validation
def test_t501_every_story_is_classified(works):
    """T-501 / G-04 — 全 69 話が台帳にあり、どれも KINDS のいずれかに分類されている。

    「確定できない」も分類のひとつであって、未記載とは違う。
    """
    nos = {w["no"] for w in works["series"]}
    assert set(CASES) == nos, (
        f"台帳に無い話: {sorted(nos - set(CASES))} / 余分: {sorted(set(CASES) - nos)}"
    )
    for no, rec in CASES.items():
        assert rec["kind"] in KINDS, f"{no}: 未知の分類 {rec['kind']}"


@pytest.mark.validation
def test_t502_ledger_quotes_are_verbatim(texts, built):
    """T-502 — 台帳の根拠が本文に逐語で在る。

    台帳は手で作るので、本文から離れていける。離れたらここで落ちる。
    """
    assert built, "生成物が空"
    for no, rec in built.items():
        for c in rec["cases"]:
            assert c["evidence"] in texts[no], f"{no}: 根拠が本文に無い — {c['evidence']}"
            for e in c.get("evidence_all", []):
                assert e in texts[no], f"{no}: 根拠が本文に無い — {e}"


@pytest.mark.validation
def test_t503_ledger_years_come_from_the_text(built):
    """T-503 — 台帳の年は、本文から機械抽出した候補の中にある。

    これが台帳の一番大事な枷である。手で作る台帳は年を**発明**できてしまう。
    抽出済み候補の集合に閉じ込めておけば、少なくとも本文に書かれていない年は入らない。

    候補に無い年を書く場合は derived=True を明示し、その導出を根拠に書くこと
    (13「安政と年号のあらたまった年」・38「安政の末年」がこれに当たる)。
    """
    for no, rec in built.items():
        cands = candidate_years(no)
        for c in rec["cases"]:
            for y in c["years"]:
                if c.get("derived"):
                    assert c.get("derivation"), f"{no}: derived なのに導出が書かれていない"
                    continue
                assert y in cands, (
                    f"{no}: 年 {y} は本文の候補 {sorted(cands)} に無い。"
                    "derived=True と導出を書くか、年を直すこと"
                )


@pytest.mark.validation
def test_t504_hanshichi_cases_are_after_his_first_case(built):
    """T-504 / G-08 — 半七が手がけた事件は、初陣(1841)以降である。

    半七の生年 1823 より前の事件は、そもそも半七の事件ではありえない。
    この不等式に反する話は kind を分け直す合図になる。
    """
    bad = []
    for no, rec in built.items():
        if rec["kind"] != "半七の事件":
            continue
        for c in rec["cases"]:
            for y in c["years"]:
                if y < HANSHICHI_FIRST_CASE:
                    bad.append((no, y))
    assert not bad, f"半七の事件なのに初陣より前: {bad}"


@pytest.mark.validation
def test_t505_pre_hanshichi_stories_are_marked_as_such(built):
    """T-504 の対照 — 半七の生前の事件が実在し、別の分類になっていること(HC-079)。

    この対照が空になったら、T-504 は何も選り分けていない。
    """
    old = {
        no
        for no, rec in built.items()
        if rec["kind"] == "半七以前の聞き伝え"
        for c in rec["cases"]
        for y in c["years"]
        if y < HANSHICHI_BIRTH
    }
    assert old, "半七の生前に置かれた話が 1 件も無い — 分類が働いていない"


@pytest.mark.validation
def test_t506_cross_references_agree_on_years():
    """T-506 / G-09 — 話どうしの相互参照が年代で食い違わない。

    69 話は互いを題名で参照する。参照の中に年の主張が含まれるとき、
    参照先の事件年と突き合わせられる。**外部の正解を使わない照合**である。

    食い違いがあればそれ自体が発見なので、一致率 100% は要求しない。
    照合できた件数が 0 でないことと、食い違いが列挙されることを保証する。
    """
    p = ROOT / "data" / "crossrefs.json"
    if not p.exists():
        pytest.skip("data/crossrefs.json 未生成")
    res = json.loads(p.read_text(encoding="utf-8"))
    assert res["checked"] > 0, "照合できた参照が 0 件(オラクルが働いていない)"
    assert res["disagree"] == sum(1 for r in res["rows"] if r["agrees"] is False)
    for r in res["rows"]:
        assert r["evidence"]


@pytest.mark.validation
def test_t507_build_is_consistent_with_the_ledger():
    """T-507 — 生成物が台帳と一致し、件数が集合で書かれている。"""
    res = build()
    assert set(res["stories"]) == set(CASES)
    counts = res["counts"]
    assert sum(counts.values()) == len(CASES)
    assert set(counts) <= set(KINDS)


@pytest.mark.validation
def test_t508_undetermined_stories_carry_a_reason(built):
    """T-508 / F-07 — 確定できない話は理由つきで null にする。推定で埋めない。"""
    for no, rec in built.items():
        if rec["kind"] != "確定できない":
            continue
        assert not rec["cases"] or all(not c["years"] for c in rec["cases"])
        assert rec.get("reason"), f"{no}: 確定できない理由が書かれていない"


@pytest.mark.validation
def test_t509_shared_event_dates():
    """T-509 / G-10 — 別々の話が同じ出来事に触れる箇所で、日付が揃っているか。

    実測(2026-08-31): 47「金の蝋燭」と 63「川越次郎兵衛」は同じ御金蔵破りを
    「安政二年二月六日」「安政二年三月六日」と書く。年は一致し、月が食い違う。
    これは綺堂の書き損じであり、こちらの判定が入る余地は無い(どちらも本文の日付そのもの)。

    ここでは食い違いを「無くすべきもの」として扱わない。**消えたら知らせる**。
    """
    from pipeline.shared_events import build as build_events

    res = build_events()  # anchor が本文に無ければ ValueError で落ちる
    assert res["checked"] >= 2, "照合できた主張が少なすぎる(対照として無意味)"
    gold = next(r for r in res["events"] if r["event"] == "御金蔵破りが起きた日")
    assert gold["year_agrees"], "年まで食い違うようになった — 台帳か本文を見直すこと"
    assert not gold["month_agrees"], (
        "既知の月の食い違い(二月六日 / 三月六日)が消えた — 抽出か本文が変わっている"
    )
    # 陰性対照: 揃っている主張もあること。揃わないものしか見ていない検査にしない
    assert any(r["month_agrees"] for r in res["events"]), "一致する主張が 1 件も無い"


@pytest.mark.validation
def test_t510_crossref_positive_control():
    """T-510 — 相互参照の照合が実際に食い違いを捕まえられること(HC-041 / HC-080)。

    「不一致 0 件」は、照合が働いていなくても同じ緑を返す。
    台帳の事件年を 1 年ずらせば、照合できた参照はすべて落ちるはずである。
    """
    from pipeline.crossrefs import build as build_refs

    ok = build_refs()
    assert ok["checked"] > 0, "照合できた参照が 0 件(対照として無意味)"

    # 一律にずらしてはいけない。相対の参照(「去年」「翌年」)は参照元も参照先も
    # 同じだけ動くので一致したままになり、対照にならない。**参照先だけ**を動かす。
    for row in ok["rows"]:
        if row["agrees"] is None:
            continue
        shifted = build()["stories"]
        for c in shifted[row["to"]]["cases"]:
            c["years"] = [y + 1 for y in c["years"]]
        bad = build_refs(cases=shifted)
        target = next(
            r for r in bad["rows"] if (r["from"], r["to"], r["evidence"]) == (row["from"], row["to"], row["evidence"])
        )
        assert target["agrees"] is False, (
            f"{row['from']}→{row['to']}: 参照先を 1 年ずらしても一致のまま — 照合が年を見ていない"
        )
