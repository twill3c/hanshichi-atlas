"""青空文庫からの採録(F-01 / F-02 / N-02 / N-03)。

一覧は作家ページの HTML を読まず、青空文庫が公式に配布している
``list_person_all_extended_utf8.zip`` から取る。作家ページは表示用の整形が入るが、
この CSV は書誌そのもので、文字遣い種別・本文 URL・図書カード URL を欄として持つ。

採録の規律(HC-012)
------------------
- 題名からの推定で確定しない。作品名が「半七捕物帳」の行を全部取り、
  文字遣い種別で series / out_of_series に分ける
- 件数オラクルはコーパス自身の手がかりに求める —— 副題の先頭 2 桁が通番になっている。
  「全 69 話」という外部の定数は使わない(G-01 / T-101)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"

LIST_URL = "https://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip"
TITLE = "半七捕物帳"
UA = "hanshichi-atlas/0.1 (fleet research project; contact via github.com/twill3c)"
SLEEP_SEC = 1.0  # N-02: 取得間隔 1 秒以上

#: 通番を持たない関連作。series には入れない(T-102)。
ESSAY_WORK_ID = "049532"


def _get(url: str, cache_name: str | None = None) -> bytes:
    """HTTP GET。cache_name を与えるとローカルキャッシュ優先(N-02)。"""
    if cache_name:
        cached = CACHE / cache_name
        if cached.exists():
            return cached.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        body = r.read()
    if cache_name:
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / cache_name).write_bytes(body)
    time.sleep(SLEEP_SEC)
    return body


def build_works_index() -> dict:
    """公式 CSV から半七捕物帳の全行を取り出す(F-01)。"""
    blob = _get(LIST_URL, "list_person_all_extended_utf8.zip")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = z.namelist()[0]
        reader = csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"))
        rows = [r for r in reader if r["作品名"] == TITLE]
    if not rows:
        raise RuntimeError("作品名『半七捕物帳』の行が CSV に無い")

    series, others = [], []
    for r in rows:
        entry = {
            "work_id": r["作品ID"],
            "subtitle": r["副題"],
            "variant": r["文字遣い種別"],
            "card_url": r["図書カードURL"],
            "text_url": r["XHTML/HTMLファイルURL"],
            "encoding": r["XHTML/HTMLファイル符号化方式"],
            "published": r["公開日"],
            "base_book": r["底本名1"],
        }
        no = r["副題"][:2]
        if r["文字遣い種別"] == "新字新仮名" and no.isdigit():
            entry["no"] = no
            entry["title"] = r["副題"][3:].strip()
            series.append(entry)
        else:
            others.append(entry)

    # 随筆は作品名が別なので上の抽出では拾えない。別途 1 行だけ取りに行く。
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = z.namelist()[0]
        reader = csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"))
        for r in reader:
            if r["作品ID"] == ESSAY_WORK_ID:
                others.append(
                    {
                        "work_id": r["作品ID"],
                        "subtitle": r["作品名"],
                        "variant": r["文字遣い種別"],
                        "card_url": r["図書カードURL"],
                        "text_url": r["XHTML/HTMLファイルURL"],
                        "encoding": r["XHTML/HTMLファイル符号化方式"],
                        "published": r["公開日"],
                        "base_book": r["底本名1"],
                    }
                )
                break

    series.sort(key=lambda e: e["no"])
    return {
        "provenance": {
            "source_url": LIST_URL,
            "fetched_at": dt.date.today().isoformat(),
            "note": "青空文庫 公開作品リスト(拡張版)。作品名『半七捕物帳』の全行と、"
            "関連随筆(作品ID 049532)を採録した",
        },
        "series": series,
        "out_of_series": others,
    }


def fetch_texts(index: dict) -> int:
    """各話の本文 XHTML を取得して UTF-8 で保存する(F-02)。

    戻り値は実際に HTTP アクセスした件数(T-104 はこれが 0 になることを見る)。
    """
    RAW.mkdir(parents=True, exist_ok=True)
    hits = 0
    for w in index["series"]:
        dest = RAW / f"{w['no']}.html"
        if dest.exists() and dest.stat().st_size > 1000:
            continue
        req = urllib.request.Request(w["text_url"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req) as r:
            blob = r.read()
        hits += 1
        enc = "shift_jis" if "ShiftJIS" in w["encoding"].replace("_", "") else "utf-8"
        # newline="" は必須。既定(None)だと '\n' が os.linesep に置換され、
        # 原文の CRLF が CR+CRLF に膨らむ(2026-08-31 に全 69 話で実際に起きた)。
        with dest.open("w", encoding="utf-8", newline="") as f:
            f.write(blob.decode(enc, errors="strict"))
        w["local_encoding"] = "utf-8"
        w["source_encoding"] = enc
        w["fetched_at"] = dt.date.today().isoformat()
        time.sleep(SLEEP_SEC)
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-only", action="store_true")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    index = build_works_index()
    if not args.index_only:
        hits = fetch_texts(index)
        print(f"HTTP 取得 {hits} 件 / 採録 {len(index['series'])} 話")
    (DATA / "aozora_works.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"→ {DATA / 'aozora_works.json'}")


if __name__ == "__main__":
    main()
