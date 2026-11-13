"""Cases for formula.py: Excel's precedence, coercion, errors and functions, against a small grid."""

from __future__ import annotations

import math

import formula

GRID = {
    (1, 1): "name",
    (1, 2): "qty",
    (1, 3): "price",
    (2, 1): "apple",
    (2, 2): 3.0,
    (2, 3): 1.5,
    (3, 1): "pear",
    (3, 2): 5.0,
    (3, 3): 2.0,
    (4, 1): "fig",
    (4, 2): 2.0,
    (4, 3): 4.0,
    (5, 1): None,
    (5, 2): True,
}


def cell(sheet: str | None, row: int, col: int) -> object:
    if sheet not in (None, "Data"):
        raise formula.XlError("#REF!")
    return GRID.get((row, col))


def ev(text: str) -> object:
    return formula.evaluate(text, cell, "Data")


CASES = [
    ("=1+2*3", 7.0),
    ("=-2^2", 4.0),  # Excel: unary minus binds tighter than ^
    ("=2^3^2", 64.0),  # and ^ is left-associative
    ("=2*3^2", 18.0),  # ^ binds tighter than *
    ("=50%", 0.5),
    ('="a"&1&TRUE', "a1TRUE"),
    ("=1=1.0", True),
    ('="A"="a"', True),  # text compares without case
    ("=ROUND(2.675,2)", 2.68),  # half away from zero on the written decimal
    ("=ROUND(-2.5,0)", -3.0),
    ("=ROUNDDOWN(-2.7,0)", -2.0),
    ("=INT(-2.5)", -3.0),
    ("=MOD(-3,2)", 1.0),
    ("=SUM(B2:B4)", 10.0),
    ("=SUM(B2:B5)", 10.0),  # a TRUE in a range is skipped, as Excel does
    ("=SUM(B2:B4,TRUE)", 11.0),  # but a typed TRUE argument counts
    ("=AVERAGE(C2:C4)", 2.5),
    ("=COUNT(A1:C5)", 6.0),
    ("=COUNTA(A1:A5)", 4.0),
    ("=COUNTBLANK(A1:A5)", 1.0),
    ("=SUMPRODUCT(B2:B4,C2:C4)", 22.5),
    ('=SUMIF(A2:A4,"p*",B2:B4)', 5.0),
    ('=COUNTIF(B2:B4,">2")', 2.0),
    ('=AVERAGEIF(C2:C4,"<>2")', 2.75),
    ('=VLOOKUP("pear",A2:C4,3,FALSE)', 2.0),
    ('=MATCH("fig",A1:A4,0)', 4.0),
    ("=INDEX(A1:C4,3,1)", "pear"),
    ('=HLOOKUP("qty",A1:C4,2,FALSE)', 3.0),
    ('=IF(B2>2,"big","small")', "big"),
    ("=IFERROR(1/0,-1)", -1.0),
    ('=IFS(B2>9,"a",B2>2,"b")', "b"),
    ("=ISBLANK(A5)", True),
    ("=A5+1", 1.0),  # a blank reads as 0 in arithmetic
    ("=A5", 0.0),  # and a formula returning a blank shows 0
    ('=LEFT("headron",4)&UPPER(MID("abc",2,1))', "headB"),
    ('=TRIM("  a   b ")', "a b"),
    ('=TEXTJOIN("-",TRUE,A2:A5)', "apple-pear-fig"),
    ('=SUBSTITUTE("a.b.c",".","",2)', "a.bc"),
    ('=VALUE("1,234.5")', 1234.5),
    ("=Data!B3*'Data'!C3", 10.0),
    ("=$B$2+B$3", 8.0),
    ('=CHOOSE(2,"x","y")', "y"),
    ("=AND(TRUE,1)", True),
    ("=XOR(TRUE,TRUE)", False),
    ("=MEDIAN(B2:B4)", 3.0),
    ("=SQRT(16)+ABS(-1)+SIGN(-9)", 4.0),
    ("=PI()", math.pi),
    ('=_xlfn.CONCAT("a",1)&_xlfn.IFS(TRUE,"b")', "a1b"),  # a saved workbook prefixes post-2007 functions
    ("=_xlfn._xlws.SUM(1,2)", 3.0),
]

ERRORS = [
    ("=1/0", "#DIV/0!"),
    ('=1+"x"', "#VALUE!"),
    ('=VLOOKUP("kiwi",A2:C4,2,FALSE)', "#N/A"),
    ("=SQRT(-1)", "#NUM!"),
    ("=Other!A1", "#REF!"),
    ("=INDEX(A1:C4,9,1)", "#REF!"),
    ("=ISNA(1)+(1/0)", "#DIV/0!"),
]

UNSUPPORTED = [
    "=FOO(1)",
    "=_xlfn.XLOOKUP(1,A1:A2,B1:B2)",
    "=_xlfn._xlws.SORT(A1:A2)",
    "=SUM(A:A)",
    "=total*2",
    "=1+",
    "=SUM(1,2",
    "=" + "+".join(["A1:ZZZ9999"]),
]


def test_values_match_excel():
    for text, want in CASES:
        got = ev(text)
        if isinstance(want, float):
            assert isinstance(got, float) and math.isclose(got, want, rel_tol=1e-12), (text, got)
        else:
            assert got == want and type(got) is type(want), (text, got)


def test_errors_are_values_with_excel_codes():
    for text, code in ERRORS:
        got = ev(text)
        assert isinstance(got, formula.XlError) and str(got) == code, (text, got)


def test_what_it_cannot_evaluate_is_unsupported_not_guessed():
    for text in UNSUPPORTED:
        try:
            got = ev(text)
        except formula.Unsupported:
            continue
        raise AssertionError(f"{text} evaluated to {got!r}; it must be Unsupported")


def test_shared_formula_shift_moves_relative_refs_only():
    assert formula.shift("=A1+$B$1+B$2+$C3", 2, 1) == "=B3+$B$1+C$2+$C5"
    assert formula.shift('=SUM(A1:A3)&"A1"', 1, 0) == '=SUM(A2:A4)&"A1"'
    assert formula.shift("=Data!A1*2", 0, 2) == "=Data!C1*2"


def test_columns_and_addresses_round_trip():
    for n in (1, 26, 27, 52, 703, 16384):
        assert formula.col_index(formula.col_letters(n)) == n
    assert formula.address("$AB$12") == (12, 28)


TESTS = [
    test_values_match_excel,
    test_errors_are_values_with_excel_codes,
    test_what_it_cannot_evaluate_is_unsupported_not_guessed,
    test_shared_formula_shift_moves_relative_refs_only,
    test_columns_and_addresses_round_trip,
]


if __name__ == "__main__":
    for test in TESTS:
        test()
        print(f"  ok    {test.__name__}")
