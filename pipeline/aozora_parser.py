"""青空文庫 XHTML の本文パーサー(F-03 / F-04)。

設計方針
--------
往復検査(G-02)を満たすことを最優先にする。すなわち ``serialize(parse(x)) == x`` が
恒等になるよう、解釈しなかったマークアップは **raw を持ったまま** 運ぶ。
解釈するのは分析に必要な三つだけ —— ルビ・入力者注・外字 —— で、それ以外の
タグ(div の字下げ、h4 の中見出し、em/strong の傍点)は raw ノードとして通す。

タグの棚卸しは 69 話全域の実測(2026-08-31)に基づく:

    br 7264 / ruby 10686 / rb 10686 / rt 10686 / rp 21372
    div.jisage_5 65 / div.jisage_2 1 / div.burasage 1
    h4.naka-midashi 65 / a.midashi_anchor 65
    em.sesame_dot 92 / strong.SESAME_DOT 353
    img.gaiji 55 / span.notes 27
    実体参照(&…;) 0 件

中見出し h4 を持つのは 69 話中 16 話だけである(53 話は節番号が素のテキスト)。
したがって **h4 を節の区切りとして当てにしてはならない**。

仮定が崩れたら落ちる検算(HC-075)
--------------------------------
- ``extract_main_text`` は開始・終了の目印が一意に在ることを確かめ、無ければ例外にする
- ``parse`` は未知のタグに出会ったら raw として通すが、``UNPARSED_TAGS`` に無い
  タグ名は ``UnknownMarkup`` で落とす。黙って通る道を作らない
"""

from __future__ import annotations

import re
from typing import Any

MAIN_OPEN = '<div class="main_text">'
BIB_OPEN = '<div class="bibliographical_information">'

#: raw のまま通すことが分かっているタグ(2026-08-31 実測の棚卸しに基づく)。
#: ここに無いタグ名に出会ったら例外にする —— 新しい組版が入ったことに気づくため。
UNPARSED_TAGS = frozenset({"br", "div", "h4", "a", "em", "strong"})

_RUBY = re.compile(
    r"<ruby><rb>(?P<base>.*?)</rb>"
    r"<rp>(?P<rp1>.*?)</rp><rt>(?P<yomi>.*?)</rt><rp>(?P<rp2>.*?)</rp>"
    r"</ruby>",
    re.S,
)
_NOTE = re.compile(r'<span class="notes">(?P<text>.*?)</span>', re.S)
_IMG = re.compile(r"<img\b[^>]*>")
_TAG = re.compile(r"<(?P<close>/?)(?P<name>[A-Za-z][A-Za-z0-9]*)\b[^>]*>")
_ALT = re.compile(r'alt="(?P<alt>[^"]*)"')


class UnknownMarkup(Exception):
    """棚卸しに無いタグに出会った。黙って通さず、ここで止める。"""


def extract_main_text(html: str) -> str:
    """XHTML 全文から ``main_text`` の中身を切り出す。

    目印が無い/複数あるときは例外にする(仮定が崩れたら落ちる)。
    """
    if html.count(MAIN_OPEN) != 1:
        raise UnknownMarkup(f"main_text の開始が {html.count(MAIN_OPEN)} 個ある")
    if html.count(BIB_OPEN) != 1:
        raise UnknownMarkup(f"底本情報の開始が {html.count(BIB_OPEN)} 個ある")
    start = html.index(MAIN_OPEN) + len(MAIN_OPEN)
    end = html.index(BIB_OPEN)
    if end <= start:
        raise UnknownMarkup("底本情報が本文より前にある")
    body = html[start:end]
    # main_text を閉じる </div> は本文の末尾にある。切り出しからは外す。
    tail = body.rstrip()
    if not tail.endswith("</div>"):
        raise UnknownMarkup("main_text の末尾が </div> で終わっていない")
    cut = body.rindex("</div>")
    return body[:cut]


def parse(body: str) -> list[dict[str, Any]]:
    """本文を、往復可能なノード列にする。"""
    nodes: list[dict[str, Any]] = []
    pos = 0
    buf: list[str] = []

    def flush() -> None:
        if buf:
            nodes.append({"kind": "text", "text": "".join(buf)})
            buf.clear()

    while pos < len(body):
        nxt = body.find("<", pos)
        if nxt < 0:
            buf.append(body[pos:])
            break
        buf.append(body[pos:nxt])

        if m := _RUBY.match(body, nxt):
            flush()
            nodes.append(
                {
                    "kind": "ruby",
                    "base": m.group("base"),
                    "yomi": m.group("yomi"),
                    "rp": (m.group("rp1"), m.group("rp2")),
                }
            )
            pos = m.end()
            continue

        if m := _NOTE.match(body, nxt):
            flush()
            nodes.append({"kind": "note", "text": m.group("text"), "raw": m.group(0)})
            pos = m.end()
            continue

        if m := _IMG.match(body, nxt):
            flush()
            alt = _ALT.search(m.group(0))
            nodes.append(
                {"kind": "gaiji", "alt": alt.group("alt") if alt else "", "raw": m.group(0)}
            )
            pos = m.end()
            continue

        if m := _TAG.match(body, nxt):
            name = m.group("name").lower()
            if name not in UNPARSED_TAGS:
                raise UnknownMarkup(f"棚卸しに無いタグ: <{name}> at {nxt}")
            flush()
            nodes.append({"kind": "raw", "raw": m.group(0), "tag": name})
            pos = m.end()
            continue

        # '<' で始まるがタグではない(本文中の不等号)。文字として扱う。
        buf.append("<")
        pos = nxt + 1

    flush()
    return nodes


def serialize(nodes: list[dict[str, Any]]) -> str:
    """``parse`` の逆写像。原文を復元する。"""
    out: list[str] = []
    for n in nodes:
        k = n["kind"]
        if k == "text":
            out.append(n["text"])
        elif k == "ruby":
            rp1, rp2 = n["rp"]
            out.append(
                f"<ruby><rb>{n['base']}</rb>"
                f"<rp>{rp1}</rp><rt>{n['yomi']}</rt><rp>{rp2}</rp></ruby>"
            )
        else:
            out.append(n["raw"])
    return "".join(out)


def plain_text(nodes: list[dict[str, Any]]) -> str:
    """分析用の素のテキスト。

    ルビは base を残して yomi を落とす。``<br />`` は改行にする。
    外字は alt 注記に還元する。入力者注は本文ではないので落とす。

    青空文庫の組版は ``<br />`` の直後に生の改行を置く。``<br />`` を改行にすると
    そのままでは 1 行が 2 回改行されるので、**br の直後に続く改行 1 個だけ**を落とす。
    「改行が二つ並んだら畳む」という書き方はしない —— それは
    ``<br />\\n<br />\\n`` の空行と区別がつかず、原文に無い畳み方をしてしまう。
    """
    out: list[str] = []
    after_br = False
    for n in nodes:
        k = n["kind"]
        if k == "text":
            t = n["text"]
            if after_br:
                if t.startswith("\r\n"):
                    t = t[2:]
                elif t[:1] in ("\n", "\r"):
                    t = t[1:]
            out.append(t)
            after_br = False
        elif k == "ruby":
            out.append(n["base"])
            after_br = False
        elif k == "gaiji":
            out.append(n["alt"])
            after_br = False
        elif k == "raw" and n["tag"] == "br":
            out.append("\n")
            after_br = True
        # note / その他のタグは落とす(after_br は保つ)
    return "".join(out).replace("\r\n", "\n")


def ruby_pairs(nodes: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """(base, yomi) の一覧。"""
    return [(n["base"], n["yomi"]) for n in nodes if n["kind"] == "ruby"]
