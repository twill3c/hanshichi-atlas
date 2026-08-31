"""半七の年齢に関する言明の台帳(F-06)。

なぜ抽出器だけでは足りないか
----------------------------
一人称の年齢言明を機械抽出すると、**誰が言っているか**が落ちる。
01「お文の魂」の「わたしが丁度二十歳の時だから、元治元年」は、抽出すれば
半七の言葉に見えるが、前後を読むと語り手の叔父(「Ｋのおじさん」)の台詞である ——
本文はその直後に「と、おじさんは先ず冒頭を置いた」と明記している。

したがってこの台帳は、**話者の帰属を根拠つきで手で確定する**。抽出器は候補を出すだけで、
``speaker`` を決めない(HC-012)。台帳が本文から離れていかないよう、
記録した引用が本文に逐語で在ることをテストで固定する(T-403)。

数え年
------
江戸・明治の年齢は数え年である。生まれた年を 1 歳とするので

    生年 = その年 - 年齢 + 1

言明の粒度は年なので、生年もそれ以上の精度を主張しない(HC-016)。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

#: 半七の年齢言明の台帳。
#:
#: quote      本文に逐語で在る引用(T-403 が検査する)
#: speaker    誰の年齢か。半七以外も、混同を防ぐために載せる
#: evidence   話者をそう判断した根拠。本文に逐語で在ること(T-403)
#: year       言明が指す西暦年
#: year_basis その西暦年をどう決めたか
STATEMENTS: list[dict[str, Any]] = [
    {
        "story": "02",
        "speaker": "半七",
        "quote": "忘れもしない天保丑年の十二月で、わたくしが十九の年の暮でした",
        "evidence": "半七老人の功名話はこうであった。",
        "age": 19,
        "year": 1841,
        "year_basis": "天保丑年。天保の期間で丑年は 1841 のみ(= 天保十二年)。"
        "同じ話が直後に「天保十二年の暦ももう終りに近づいた」と書き、二経路が一致する",
    },
    {
        "story": "47",
        "speaker": "半七",
        "quote": "その安政二年はわたくしが三十三の年で、云わば男の働き盛りでしたから",
        "evidence": "老人は「金の蝋燭」という昔の探偵物語をはじめた。",
        "age": 33,
        "year": 1855,
        "year_basis": "安政二年 = 1855(era_table による)",
    },
    {
        "story": "01",
        "speaker": "半七",
        "quote": "半七は七十を三つ越したとか云っていたが",
        "evidence": "わたしが半七によく逢うようになったのは、それから十年の後で、"
        "あたかも日清戦争が終りを告げた頃であった。",
        "age": 73,
        "year": 1895,
        "year_basis": "日清戦争の終結(下関条約)は明治二十八年 = 1895。"
        "語り手が半七と会うようになった時期として本文が置いている",
    },
    {
        "story": "01",
        "speaker": "Ｋのおじさん(語り手の叔父)",
        "quote": "わたしが丁度二十歳の時だから、元治元年",
        "evidence": "と、おじさんは先ず冒頭を置いた。",
        "age": 20,
        "year": 1864,
        "year_basis": "元治元年 = 1864(era_table による)",
        "note": "半七の言明として読むと生年が 1845 になり、02・47・01 の三件と 22 年ずれる。"
        "話者は半七ではないので、矛盾ではない",
    },
]


def birth_year(st: dict[str, Any]) -> int:
    """数え年から生年を出す。"""
    return st["year"] - st["age"] + 1


def build() -> dict:
    hanshichi = [s for s in STATEMENTS if s["speaker"] == "半七"]
    births = sorted({birth_year(s) for s in hanshichi})
    rows = [
        {
            **s,
            "birth_year": birth_year(s),
        }
        for s in STATEMENTS
    ]
    return {
        "method": "本文の年齢言明から数え年で生年を逆算する。話者の帰属は本文の根拠つきで手で確定した",
        "statements": rows,
        "hanshichi_birth_candidates": births,
        "converges": len(births) == 1,
        "spread": (max(births) - min(births)) if births else None,
    }


def main() -> None:
    res = build()
    (ROOT / "data" / "hanshichi_age.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for r in res["statements"]:
        print(f"  {r['story']} {r['speaker']:22s} {r['year']}年 {r['age']}歳 → 生年 {r['birth_year']}")
    print(f"半七の生年候補: {res['hanshichi_birth_candidates']} / 収束: {res['converges']}")


if __name__ == "__main__":
    main()
