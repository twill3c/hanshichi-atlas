"""実ブラウザ検品(HC-041 / HC-078 / HC-080)。

    python harness/inspect_web.py            # 検品する
    python harness/inspect_web.py --control  # 検品器自身が壊れていないか確かめる

なぜ要るか
----------
図が読めるか、表が潰れていないかは、テストの緑では分からない。
「要素が在る」「本文が出ている」の検査は、列が一文字ずつ折り返していても通る。
そこで実ブラウザで開き、**複数の幅**で見て、機械で捕まえられる代理指標を置く ——
横の溢れと縦の伸びすぎ。代理指標は目視の代わりではなく、目視を忘れたときの網である。

検品器の書き方(HC-080)
----------------------
- 要素名や実装の同一性に依存しない。数えるときは名前ではなく子の総数で数える
- 掴み置きせず毎回引き直す(再描画で要素は作り直される)
- 失敗は終了コードで知らせる。パイプの先で終了コードがすり替わらないよう、
  このスクリプト自身が最後に集計して exit する
- **陽性対照を持つ**(--control)。異常を仕込んだ木に対して実際に落ちること
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import json
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

#: 見る幅。1 つの幅だけでは列の潰れも図の細長化も見えない(HC-078)。
WIDTHS = [(1280, 900), (760, 1000), (390, 844)]

#: 縦の伸びすぎの目安。1 ページが これを超えたら、まず表を疑う。
MAX_PAGE_HEIGHT = 16000


@contextlib.contextmanager
def serve(directory: Path):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))

    class Quiet(socketserver.TCPServer):
        allow_reuse_address = True

    with Quiet(("127.0.0.1", 0), handler) as httpd:
        httpd.RequestHandlerClass.log_message = lambda *a, **k: None
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}"
        finally:
            httpd.shutdown()


class Report:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.notes: list[str] = []

    def check(self, ok: bool, msg: str) -> None:
        (self.notes if ok else self.problems).append(("OK  " if ok else "NG  ") + msg)


def inspect(base: str, rep: Report) -> None:
    expected = json.loads((ROOT / "data" / "case_years.json").read_text(encoding="utf-8"))
    n_stories = len(expected["stories"])

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h in WIDTHS:
            page = browser.new_page(viewport={"width": w, "height": h})
            errors: list[str] = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))

            page.goto(f"{base}/index.html", wait_until="networkidle")
            page.wait_for_selector("#tbl tbody tr")

            rep.check(not errors, f"[{w}px] 年表: コンソールエラー {len(errors)} 件 {errors[:2]}")

            # 表は全話ぶん出ているか。行数は定数で書かず、台帳の話数と突き合わせる
            rows = page.locator("#tbl tbody tr").count()
            rep.check(rows == n_stories, f"[{w}px] 年表: 表の行 {rows} / 台帳 {n_stories}")

            # 図の点は「名前」でなく子の総数で数える
            dots = page.locator("#main-chart circle").count() + page.locator("#old-chart circle").count()
            rep.check(dots > 0, f"[{w}px] 年表: 図の点 {dots} 個")

            over = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            rep.check(over <= 1, f"[{w}px] 年表: 横の溢れ {over}px")

            height = page.evaluate("() => document.documentElement.scrollHeight")
            rep.check(height <= MAX_PAGE_HEIGHT, f"[{w}px] 年表: ページの高さ {height}px")

            # 図が細長い柱になっていないか(縦横比)
            box = page.locator("#main-chart").bounding_box()
            rep.check(
                box is not None and box["width"] > box["height"],
                f"[{w}px] 年表: 主図の縦横 {box and round(box['width'])}x{box and round(box['height'])}",
            )

            # 吹き出しが出るか(振る舞いで確かめる)
            page.locator("#main-chart circle").first.hover()
            page.wait_for_timeout(120)
            tip_visible = page.locator("#tip").is_visible()
            rep.check(tip_visible, f"[{w}px] 年表: 点にかざすと吹き出しが出る")

            # 並べ替えが効くか — 先頭行の通番が変わること
            first_before = page.locator("#tbl tbody tr td").first.inner_text()
            page.locator('button.seg[data-sort="year"]').click()
            page.wait_for_timeout(120)
            first_after = page.locator("#tbl tbody tr td").first.inner_text()
            rep.check(
                first_before != first_after,
                f"[{w}px] 年表: 事件年代順にすると先頭が {first_before} → {first_after}",
            )

            # 捜査圏
            errors.clear()
            page.goto(f"{base}/map.html", wait_until="networkidle")
            page.wait_for_selector("#ptbl tbody tr")
            rep.check(not errors, f"[{w}px] 捜査圏: コンソールエラー {len(errors)} 件 {errors[:2]}")
            # 図は 2 面ある。全体の図が表と一致し、核の図はその部分集合であること
            core_dots = page.locator("#map-chart circle").count()
            wide_dots = page.locator("#wide-chart circle").count()
            rows = page.locator("#ptbl tbody tr").count()
            rep.check(wide_dots == rows, f"[{w}px] 捜査圏: 全体の図の点 {wide_dots} と表の行 {rows} が一致")
            rep.check(
                0 < core_dots < wide_dots,
                f"[{w}px] 捜査圏: 核の図 {core_dots} 点は全体 {wide_dots} 点の一部",
            )
            labels = page.locator("#map-chart text").count()
            rep.check(labels > 5, f"[{w}px] 捜査圏: 図に出した地名 {labels} 件")
            box = page.locator("#map-chart").bounding_box()
            rep.check(
                box is not None and 0.3 < box["height"] / box["width"] < 1.6,
                f"[{w}px] 捜査圏: 図の縦横 {box and round(box['width'])}x{box and round(box['height'])}",
            )
            before = page.locator("#map-chart text").count()
            page.select_option("#storysel", "69")
            page.wait_for_timeout(150)
            rep.check(
                page.locator("#map-chart text").count() != before,
                f"[{w}px] 捜査圏: 話を選ぶと図が描き変わる",
            )
            over = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            rep.check(over <= 1, f"[{w}px] 捜査圏: 横の溢れ {over}px")

            # リーダー
            errors.clear()
            page.goto(f"{base}/reader.html?w=69", wait_until="networkidle")
            page.wait_for_selector("#body p")
            rep.check(not errors, f"[{w}px] リーダー: コンソールエラー {len(errors)} 件 {errors[:2]}")

            paras = page.locator("#body p").count()
            rubies = page.locator("#body ruby").count()
            rep.check(paras > 10, f"[{w}px] リーダー: 段落 {paras}")
            rep.check(rubies > 100, f"[{w}px] リーダー: ルビ {rubies}")

            # ルビの切り替えが効くか — 実際に見えなくなること
            rt = page.locator("#body ruby rt").first
            rep.check(rt.is_visible(), f"[{w}px] リーダー: 既定でルビが見えている")
            page.locator("#rubytoggle").click()
            page.wait_for_timeout(100)
            rep.check(not rt.is_visible(), f"[{w}px] リーダー: 切ると本当に消える")

            over = page.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            rep.check(over <= 1, f"[{w}px] リーダー: 横の溢れ {over}px")

            page.close()
        browser.close()


def make_broken_copy(dst: Path) -> None:
    """陽性対照 — 検品器が実際に異常を捕まえられるか確かめるための壊した木。

    横に溢れる要素を足す。「異常なし」を返す検品器が、本当に異常を見つけられるか。
    """
    shutil.copytree(ROOT / "web", dst, dirs_exist_ok=True)
    css = dst / "style.css"
    css.write_text(
        css.read_text(encoding="utf-8") + "\n.tablewrap { overflow-x: visible; }\ntable { min-width: 2400px; }\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true", help="壊した木に当てて、検品器が落ちることを確かめる")
    args = ap.parse_args()

    if args.control:
        with tempfile.TemporaryDirectory() as td:
            broken = Path(td) / "web"
            make_broken_copy(broken)
            rep = Report()
            with serve(broken) as base:
                inspect(base, rep)
            if rep.problems:
                print(f"陽性対照 OK — 壊した木で {len(rep.problems)} 件を検出した")
                for p in rep.problems[:4]:
                    print("   ", p)
                return 0
            print("陽性対照 NG — 壊した木でも異常なしと言った。検品器が働いていない")
            return 1

    rep = Report()
    with serve(ROOT / "web") as base:
        inspect(base, rep)
    for line in rep.notes:
        print(" ", line)
    if rep.problems:
        print(f"\n検品 NG — {len(rep.problems)} 件")
        for p in rep.problems:
            print("   ", p)
        return 1
    print(f"\n検品 OK — {len(rep.notes)} 項目、問題なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
