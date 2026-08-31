"""干支(十干十二支)と西暦の対応(F-05)。

半七の本文は年を二通りに書く。元号年(「天保十二年」)と干支(「天保丑年」)である。
同じ話が両方で書いていることがあり、そこは**本文の内部だけで検算できる**。
外部の年譜を正解として持ち込まないので、この照合は循環しない(G-03)。

基準
----
西暦 4 年を甲子とする干支紀年法の定義に依る。1864 年(元治元年)が甲子であり、
その 60 年後の 1924 年も甲子である(甲子園球場の名の由来)。
"""

from __future__ import annotations

STEMS = "甲乙丙丁戊己庚辛壬癸"  # 十干
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"  # 十二支


class KanshiError(Exception):
    """干支として読めないものを黙って通さない。"""


def kanshi_index(year: int) -> int:
    """西暦年の六十干支の番号(0 = 甲子)。"""
    return (year - 4) % 60


def kanshi_of(year: int) -> str:
    """西暦年の干支(例: 1864 → 甲子)。"""
    n = kanshi_index(year)
    return STEMS[n % 10] + BRANCHES[n % 12]


def _era_span(era: str, table: dict) -> range:
    """元号が覆う西暦年の範囲。

    次の元号の元年までを覆う。改元年は両方の元号に属するので、
    範囲は閉区間として扱う(和暦年は改元後も番号を引き継ぐため)。
    """
    first = table["first_year"]
    if era not in first:
        raise KanshiError(f"表に無い元号: {era}")
    names = list(first)
    i = names.index(era)
    start = first[era]
    end = first[names[i + 1]] if i + 1 < len(names) else start + 60
    return range(start, end + 1)


def year_of_kanshi(kanshi: str, era: str, table: dict) -> int:
    """十干十二支から、その元号の期間内の西暦年を決める。

    干支は 60 年周期なので、江戸期のどの元号(最長 21 年)でも高々 1 つに決まる。
    """
    if len(kanshi) != 2 or kanshi[0] not in STEMS or kanshi[1] not in BRANCHES:
        raise KanshiError(f"干支として読めない: {kanshi}")
    hits = [y for y in _era_span(era, table) if kanshi_of(y) == kanshi]
    if not hits:
        raise KanshiError(f"{era}の期間に{kanshi}年が無い")
    if len(hits) > 1:  # 60 年を超える元号は江戸期に無い。あれば表か実装が誤っている。
        raise KanshiError(f"{era}の期間に{kanshi}年が複数ある: {hits}")
    return hits[0]


def years_with_branch(branch: str, era: str, table: dict) -> list[int]:
    """十二支だけから候補年を返す。一意に決まらないときは複数返す。

    黙って 1 つ選ばない —— 決まらないことは、決まらないと言う。
    """
    if branch not in BRANCHES:
        raise KanshiError(f"十二支として読めない: {branch}")
    return [y for y in _era_span(era, table) if kanshi_of(y)[1] == branch]
