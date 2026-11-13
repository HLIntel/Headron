"""Spreadsheet formulas for the data kit: parsed and evaluated, never executed.

`headron data calc` recomputes a workbook's formulas from the cells they read and holds each result
to the value the spreadsheet cached, and `--formula` evaluates one expression against any table the
kit reads, so a CSV is addressable as A1 cells too. Both live in datakit.py; this module is the
language: Excel's numbers, "text", TRUE/FALSE, error literals, A1 and $A$1 references, ranges,
Sheet!A1 and 'My sheet'!A1, + - * / ^ & % and the six comparisons, and the functions in FUNCTIONS
and LAZY. A tokenizer and a precedence parser build a tuple tree; nothing reaches eval or exec.

WHAT IT CANNOT READ IT REFUSES. A function, a defined name, a whole-column reference or an array
formula this module does not implement raises Unsupported, and the caller reports NOT RUN with the
reason: a guessed value would let a wrong cached figure pass. Excel's own errors (#DIV/0!, #N/A ...)
are values: XlError is raised through an expression and returned as its result, as Excel does.
"""

from __future__ import annotations

import math
import operator
import re
from collections.abc import Callable, Iterator
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal, InvalidOperation
from statistics import median

MAX_RANGE_CELLS = 1_000_000  # a reference wider than this is refused before a grid is built
_SHEET = r"(?:'(?:[^']|'')+'|[A-Za-z_][\w.]*)!"
_CELL = r"\$?[A-Za-z]{1,3}\$?\d+"
TOKEN = re.compile(
    r"\s*(?:(?P<str>\"(?:[^\"]|\"\")*\")"
    r"|(?P<err>#(?:DIV/0!|VALUE!|REF!|NAME\?|N/A|NUM!|NULL!))"
    r"|(?P<func>[A-Za-z_][\w.]*)(?=\s*\()"
    rf"|(?P<ref>(?:{_SHEET})?{_CELL}(?::{_CELL})?)(?![\w(!:])"
    r"|(?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"
    r"|(?P<bool>TRUE|FALSE)(?![\w(])"
    r"|(?P<op><>|<=|>=|[-+*/^&=<>%(),]))",
    re.I,
)
BINARY = {"=": 1, "<>": 1, "<": 1, ">": 1, "<=": 1, ">=": 1, "&": 2, "+": 3, "-": 3, "*": 4, "/": 4, "^": 5}


class XlError(Exception):
    """An Excel error value: raised through an expression, returned as the formula's result."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

    def __eq__(self, other: object) -> bool:
        return isinstance(other, XlError) and other.code == self.code

    def __hash__(self) -> int:
        return hash(self.code)

    def __str__(self) -> str:
        return self.code


class Unsupported(Exception):
    """Syntax or a function this module does not implement: the caller's verdict is NOT RUN."""


# ---- addresses ---------------------------------------------------------------------------------


def col_index(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + ord(ch) - 64
    return n


def col_letters(n: int) -> str:
    letters = ""
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def address(cell: str) -> tuple[int, int]:
    """(row, column) of an A1 or $A$1 address."""
    found = re.fullmatch(r"\$?([A-Za-z]{1,3})\$?(\d+)", cell)
    if not found:
        raise Unsupported(f"not a cell address: {cell!r}")
    return int(found[2]), col_index(found[1])


def _ref(text: str) -> tuple:
    sheet, _, cells = text.rpartition("!")
    sheet = sheet[1:-1].replace("''", "'") if sheet.startswith("'") else sheet
    first, _, last = cells.partition(":")
    (r1, c1), (r2, c2) = address(first), address(last or first)
    top, left, bottom, right = min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2)
    if (bottom - top + 1) * (right - left + 1) > MAX_RANGE_CELLS:
        raise Unsupported(f"range {cells} is wider than {MAX_RANGE_CELLS} cells")
    return ("ref", sheet or None, top, left, bottom, right, bool(last))


def shift(text: str, rows: int, cols: int) -> str:
    """A shared formula's text moved by (rows, cols): relative parts move, $-anchored parts stay; spacing is not kept."""

    def moved(m: re.Match) -> str:
        col = m[2] if m[1] else col_letters(col_index(m[2]) + cols)
        row = int(m[4]) if m[3] else int(m[4]) + rows
        if not col or row < 1:
            return "#REF!"
        return f"{m[1]}{col}{m[3]}{row}"

    out = []
    for kind, tok in tokenize(text):
        if kind == "ref":
            sheet, bang, cells = tok.rpartition("!")
            tok = sheet + bang + re.sub(r"(\$?)([A-Za-z]{1,3})(\$?)(\d+)", moved, cells)
        out.append(tok)
    return ("=" if text.strip().startswith("=") else "") + "".join(out)  # workbook <f> text has no "="


# ---- parsing -----------------------------------------------------------------------------------


def tokenize(text: str) -> list[tuple[str, str]]:
    body, pos, out = text.strip().removeprefix("="), 0, []
    while body[pos:].strip():
        found = TOKEN.match(body, pos)
        if not found or not found.lastgroup:
            raise Unsupported(
                f"cannot read {body[pos : pos + 24].strip()!r} (a defined name or syntax not implemented)"
            )
        out.append((found.lastgroup, found[found.lastgroup]))
        pos = found.end()
    return out


class _Parser:
    def __init__(self, toks: list[tuple[str, str]]) -> None:
        self.toks, self.i = toks, 0

    def peek(self) -> tuple[str, str]:
        return self.toks[self.i] if self.i < len(self.toks) else ("end", "")

    def take(self) -> tuple[str, str]:
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, text: str) -> None:
        if self.take() != ("op", text):
            raise Unsupported(f"expected {text!r}")

    def expr(self, floor: int) -> tuple:
        left = self.unary()
        while (prec := BINARY.get(self.peek()[1], 0) if self.peek()[0] == "op" else 0) >= floor and prec:
            op = self.take()[1]
            left = ("bin", op, left, self.expr(prec + 1))  # every Excel operator is left-associative
        return left

    def unary(self) -> tuple:
        if self.peek() in (("op", "-"), ("op", "+")):
            sign = self.take()[1]
            operand = self.unary()  # binds tighter than ^, as Excel's does: -2^2 is 4
            return ("neg", operand) if sign == "-" else operand
        return self.primary()

    def primary(self) -> tuple:
        kind, text = self.take()
        if kind == "func":
            node = self.call(
                text.upper().removeprefix("_XLFN.").removeprefix("_XLWS.")
            )  # how a saved file names newer ones
        elif kind == "ref":
            node = _ref(text)
        elif (kind, text) == ("op", "("):
            node = self.expr(1)
            self.expect(")")
        elif kind in LITERAL:
            node = ("lit", LITERAL[kind](text))
        else:
            raise Unsupported(f"unexpected {text or 'end of formula'!r}")
        while self.peek() == ("op", "%"):
            self.take()
            node = ("pct", node)
        return node

    def call(self, name: str) -> tuple:
        self.expect("(")
        args = [] if self.peek() == ("op", ")") else [self.arg()]
        while self.peek() == ("op", ","):
            self.take()
            args.append(self.arg())
        self.expect(")")
        return ("call", name, args)

    def arg(self) -> tuple:
        return ("lit", None) if self.peek() in (("op", ","), ("op", ")")) else self.expr(1)  # IF(A1,,2)


LITERAL: dict[str, Callable[[str], object]] = {
    "num": float,
    "str": lambda t: t[1:-1].replace('""', '"'),
    "bool": lambda t: t.upper() == "TRUE",
    "err": lambda t: XlError(t.upper()),
}


def parse(text: str) -> tuple:
    parser = _Parser(tokenize(text))
    tree = parser.expr(1)
    if parser.i != len(parser.toks):
        raise Unsupported(f"unexpected {parser.peek()[1]!r} after a complete expression")
    return tree


# ---- values ------------------------------------------------------------------------------------


def to_num(v: object) -> float:
    if isinstance(v, XlError):
        raise v
    if isinstance(v, bool) or v is None:
        return float(bool(v))
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().replace(",", ""))
    except ValueError:
        raise XlError("#VALUE!") from None


def to_text(v: object) -> str:
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() and abs(v) < 1e15 else f"{v:.15g}"
    return "" if v is None else str(v)


def to_bool(v: object) -> bool:
    if isinstance(v, str):
        if v.upper() not in ("TRUE", "FALSE"):
            raise XlError("#VALUE!")
        return v.upper() == "TRUE"
    return to_num(v) != 0


def scalar(v: object) -> object:
    """One value: a one-cell range is its cell, a wider one is #VALUE! (no implicit intersection)."""
    if isinstance(v, list):
        if len(v) != 1 or len(v[0]) != 1:
            raise XlError("#VALUE!")
        v = v[0][0]
    if isinstance(v, XlError):
        raise v
    return v


def _rank(v: object) -> tuple:
    if isinstance(v, bool):
        return (2, v)
    if isinstance(v, str):
        return (1, v.lower())
    return (0, v)


def compare(op: str, a: object, b: object) -> bool:
    """Excel's ordering: numbers < text < booleans, text without case, blank as the other side's zero."""
    a = _blank_as(b) if a is None else a
    b = _blank_as(a) if b is None else b
    x, y = _rank(a), _rank(b)
    return {"=": x == y, "<>": x != y, "<": x < y, ">": x > y, "<=": x <= y, ">=": x >= y}[op]


def _blank_as(other: object) -> object:
    return "" if isinstance(other, str) else (False if isinstance(other, bool) else 0.0)


def _finite(x: float) -> float:
    if math.isnan(x) or math.isinf(x):
        raise XlError("#NUM!")
    return x


def _div(a: float, b: float) -> float:
    if b == 0:
        raise XlError("#DIV/0!")
    return a / b


def _pow(a: float, b: float) -> float:
    if a == 0 and b <= 0:
        raise XlError("#NUM!" if b == 0 else "#DIV/0!")
    try:
        return _finite(math.pow(a, b))
    except (OverflowError, ValueError):
        raise XlError("#NUM!") from None


ARITH: dict[str, Callable[[float, float], float]] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": _div,
    "^": _pow,
}


# ---- evaluation --------------------------------------------------------------------------------

Cell = Callable[[str | None, int, int], object]  # (sheet or None for the formula's own, row, column)


def evaluate(text: str, cell: Cell, sheet: str | None = None) -> object:
    """The formula's value (float, str, bool, None for blank, or an XlError). Raises Unsupported."""
    tree = parse(text)
    try:
        value = scalar(_eval(tree, cell, sheet))
    except XlError as err:
        return err
    return 0.0 if value is None else value  # a formula showing a blank cell shows 0, as Excel's does


def _eval(node: tuple, cell: Cell, sheet: str | None) -> object:
    kind = node[0]
    if kind == "lit":
        return scalar(node[1])
    if kind == "ref":
        _, where, top, left, bottom, right, ranged = node
        grid = [[cell(where or sheet, r, c) for c in range(left, right + 1)] for r in range(top, bottom + 1)]
        return grid if ranged else scalar(grid)
    if kind == "call":
        return _call(node[1], node[2], lambda n: _eval(n, cell, sheet))
    values = [scalar(_eval(n, cell, sheet)) for n in node[2 if kind == "bin" else 1 :]]
    if kind == "neg":
        return -to_num(values[0])
    if kind == "pct":
        return to_num(values[0]) / 100
    op, (a, b) = node[1], values
    if op in ARITH:
        return _finite(ARITH[op](to_num(a), to_num(b)))
    return to_text(a) + to_text(b) if op == "&" else compare(op, a, b)


def _call(name: str, args: list[tuple], run: Callable[[tuple], object]) -> object:
    if name in LAZY:
        return LAZY[name](args, run)
    fn = FUNCTIONS.get(name)
    if fn is None:
        raise Unsupported(f"function {name} is not implemented")
    values = [run(a) for a in args]
    try:
        return fn(*values)
    except TypeError:
        raise Unsupported(f"{name} with {len(values)} argument(s) is not implemented") from None


# ---- functions ---------------------------------------------------------------------------------


def _cells(args: tuple) -> Iterator[tuple[object, bool]]:
    """Every value the arguments carry, and whether it came from a range (Excel coerces only typed ones)."""
    for a in args:
        if isinstance(a, list):
            yield from ((v, True) for row in a for v in row)
        else:
            yield a, False


def _flat(v: object) -> list:
    return [x for row in v for x in row] if isinstance(v, list) else [v]


def _grid(v: object) -> list[list]:
    return v if isinstance(v, list) else [[v]]


def _numbers(*args: object) -> list[float]:
    """SUM's rule: a range gives its numbers and skips text, a typed argument is coerced."""
    out = []
    for v, ranged in _cells(args):
        if isinstance(v, XlError):
            raise v
        if not ranged:
            out.append(to_num(v))
        elif isinstance(v, float):
            out.append(v)
    return out


def _avg(xs: list[float]) -> float:
    if not xs:
        raise XlError("#DIV/0!")
    return sum(xs) / len(xs)


def _rounder(mode: str) -> Callable[..., float]:
    def run(x: object, digits: object = 0.0) -> float:
        try:
            step = Decimal(1).scaleb(-int(to_num(digits)))
            return float(Decimal(repr(to_num(x))).quantize(step, rounding=mode))
        except InvalidOperation:
            raise XlError("#NUM!") from None

    return run


def _criterion(crit: object) -> Callable[[object], bool]:
    """SUMIF's test: ">5", "<>x", "a*" (wildcards on text) or a value meaning equals."""
    op, target = "=", scalar(crit)
    if isinstance(target, str):
        found = re.fullmatch(r"(<>|<=|>=|=|<|>)?(.*)", target, re.S)
        op, target = found[1] or "=", found[2]
        try:
            target = float(target.replace(",", ""))
        except ValueError:
            target = {"TRUE": True, "FALSE": False}.get(target.upper(), target)
    if isinstance(target, str) and op in ("=", "<>"):
        pattern = re.compile(re.escape(target).replace(r"\*", ".*").replace(r"\?", "."), re.I | re.S)
        return lambda v: (pattern.fullmatch(to_text(v)) is not None) == (op == "=")
    return lambda v: compare(op, v, target) if v is not None and _rank(v)[0] == _rank(target)[0] else op == "<>"


def _picked(keys: object, crit: object, values: object = None) -> list[float]:
    hit = _criterion(crit)
    pairs = zip(_flat(keys), _flat(keys if values is None else values), strict=False)
    return [v for k, v in pairs if hit(k) and isinstance(v, float)]


def _position(keys: list, value: object, mode: int) -> int:
    """MATCH: 0 the first equal key (wildcards on text), 1 the last key <= value, -1 the last >= value."""
    value = scalar(value)
    if mode == 0:
        hit = _criterion("=" + value if isinstance(value, str) else value)
        found = [i for i, k in enumerate(keys) if k is not None and hit(k)]
    else:
        op = "<=" if mode > 0 else ">="
        found = [
            i for i, k in enumerate(keys) if k is not None and _rank(k)[0] == _rank(value)[0] and compare(op, k, value)
        ]
    if not found:
        raise XlError("#N/A")
    return found[0] if mode == 0 else found[-1]


def _lookup(value: object, table: object, index: object, approx: object, across: bool) -> object:
    rows = _grid(table)
    rows = [list(col) for col in zip(*rows, strict=True)] if across else rows
    k = int(to_num(index))
    if k < 1:
        raise XlError("#VALUE!")
    if k > len(rows[0]):
        raise XlError("#REF!")
    return rows[_position([r[0] for r in rows], value, 1 if to_bool(approx) else 0)][k - 1]


def _index(array: object, row: object, col: object = None) -> object:
    rows = _grid(array)
    r, c = int(to_num(row)), int(to_num(col)) if col is not None else 1
    if len(rows) == 1 and col is None:
        r, c = 1, r  # INDEX(A1:E1, 3) is the third cell of a single row
    if r == 0 or c == 0:
        raise Unsupported("INDEX with a row or column of 0 returns an array")
    if not (1 <= r <= len(rows) and 1 <= c <= len(rows[0])):
        raise XlError("#REF!")
    return rows[r - 1][c - 1]


def _mid(text: object, start: object, count: object) -> str:
    s, n = int(to_num(start)), int(to_num(count))
    if s < 1 or n < 0:
        raise XlError("#VALUE!")
    return to_text(text)[s - 1 : s - 1 + n]


def _right(text: object, count: object = 1.0) -> str:
    n = int(to_num(count))
    if n < 0:
        raise XlError("#VALUE!")
    return to_text(text)[len(to_text(text)) - n :] if n else ""


def _mod(a: object, b: object) -> float:
    x, y = to_num(a), to_num(b)
    return x - y * math.floor(_div(x, y))


def _logic(join: Callable[[list[bool]], bool]) -> Callable[..., bool]:
    def run(*args: object) -> bool:
        flags = [to_bool(v) for v, ranged in _cells(args) if not ranged or isinstance(v, (bool, float, XlError))]
        if not flags:
            raise XlError("#VALUE!")
        return join(flags)

    return run


def _sumproduct(*arrays: object) -> float:
    cols = [_flat(a) for a in arrays]
    if len({len(c) for c in cols}) != 1:
        raise XlError("#VALUE!")
    for v in (v for c in cols for v in c if isinstance(v, XlError)):
        raise v
    return sum(math.prod(v if isinstance(v, float) else 0.0 for v in row) for row in zip(*cols, strict=True))


def _count(*args: object) -> float:
    """COUNT: numbers in a range, and typed arguments that read as numbers."""
    total = 0
    for v, ranged in _cells(args):
        if ranged:
            total += isinstance(v, float) and not isinstance(v, bool)
            continue
        try:
            to_num(v)
        except XlError:
            continue
        total += 1
    return float(total)


def _need(xs: list[float], code: str = "#NUM!") -> list[float]:
    if not xs:
        raise XlError(code)
    return xs


def _sqrt(x: object) -> float:
    n = to_num(x)
    if n < 0:
        raise XlError("#NUM!")
    return math.sqrt(n)


def _left(text: object, count: object = 1.0) -> str:
    n = int(to_num(count))
    if n < 0:
        raise XlError("#VALUE!")
    return to_text(scalar(text))[:n]


def _choose(index: object, *options: object) -> object:
    i = int(to_num(scalar(index)))
    if not 1 <= i <= len(options):
        raise XlError("#VALUE!")
    return options[i - 1]


def _textjoin(sep: object, skip_empty: object, *texts: object) -> str:
    parts = [to_text(v) for v, _ in _cells(texts)]
    return to_text(sep).join(p for p in parts if p or not to_bool(skip_empty))


def _substitute(text: object, old: object, new: object, nth: object = None) -> str:
    s, o, n = to_text(text), to_text(old), to_text(new)
    if not o:
        return s
    if nth is None:
        return s.replace(o, n)
    k, at = int(to_num(nth)), -1
    for _ in range(max(k, 0)):
        at = s.find(o, at + 1)
        if at < 0:
            return s
    return s[:at] + n + s[at + len(o) :] if k > 0 else s


FUNCTIONS: dict[str, Callable[..., object]] = {
    "SUM": lambda *a: math.fsum(_numbers(*a)),
    "AVERAGE": lambda *a: _avg(_numbers(*a)),
    "MIN": lambda *a: min(_numbers(*a), default=0.0),
    "MAX": lambda *a: max(_numbers(*a), default=0.0),
    "MEDIAN": lambda *a: float(median(_need(_numbers(*a)))),
    "PRODUCT": lambda *a: math.prod(_numbers(*a)),
    "COUNT": _count,
    "COUNTA": lambda *a: float(sum(v is not None for v, _ in _cells(a))),
    "COUNTBLANK": lambda *a: float(sum(v is None or v == "" for v, _ in _cells(a))),
    "SUMIF": lambda keys, crit, values=None: math.fsum(_picked(keys, crit, values)),
    "AVERAGEIF": lambda keys, crit, values=None: _avg(_picked(keys, crit, values)),
    "COUNTIF": lambda keys, crit: float(sum(map(_criterion(crit), _flat(keys)))),
    "SUMPRODUCT": _sumproduct,
    "ROUND": _rounder(ROUND_HALF_UP),
    "ROUNDUP": _rounder(ROUND_UP),
    "ROUNDDOWN": _rounder(ROUND_DOWN),
    "INT": lambda x: float(math.floor(to_num(x))),
    "ABS": lambda x: abs(to_num(x)),
    "SIGN": lambda x: float((to_num(x) > 0) - (to_num(x) < 0)),
    "MOD": _mod,
    "POWER": lambda a, b: _pow(to_num(a), to_num(b)),
    "SQRT": _sqrt,
    "PI": lambda: math.pi,
    "AND": _logic(all),
    "OR": _logic(any),
    "XOR": _logic(lambda flags: sum(flags) % 2 == 1),
    "NOT": lambda x: not to_bool(scalar(x)),
    "TRUE": lambda: True,
    "FALSE": lambda: False,
    "CHOOSE": _choose,
    "VLOOKUP": lambda v, t, k, approx=True: _lookup(v, t, k, approx, across=False),
    "HLOOKUP": lambda v, t, k, approx=True: _lookup(v, t, k, approx, across=True),
    "MATCH": lambda v, keys, mode=1.0: float(_position(_flat(keys), v, int(to_num(mode))) + 1),
    "INDEX": _index,
    "LEN": lambda t: float(len(to_text(scalar(t)))),
    "LEFT": _left,
    "RIGHT": _right,
    "MID": _mid,
    "UPPER": lambda t: to_text(scalar(t)).upper(),
    "LOWER": lambda t: to_text(scalar(t)).lower(),
    "TRIM": lambda t: " ".join(p for p in to_text(scalar(t)).split(" ") if p),
    "CONCAT": lambda *a: "".join(to_text(v) for v, _ in _cells(a)),
    "CONCATENATE": lambda *a: "".join(to_text(scalar(v)) for v in a),
    "TEXTJOIN": _textjoin,
    "SUBSTITUTE": _substitute,
    "EXACT": lambda a, b: to_text(scalar(a)) == to_text(scalar(b)),
    "VALUE": lambda t: to_num(scalar(t)),
    "N": lambda v: scalar(v) if isinstance(scalar(v), float) else float(scalar(v) is True),
}


def _if(args: list[tuple], run: Callable[[tuple], object]) -> object:
    if not 1 < len(args) < 4:
        raise Unsupported(f"IF with {len(args)} argument(s) is not implemented")
    if to_bool(scalar(run(args[0]))):
        return run(args[1])
    return run(args[2]) if len(args) == 3 else False


def _ifs(args: list[tuple], run: Callable[[tuple], object]) -> object:
    for test, then in zip(args[::2], args[1::2], strict=False):
        if to_bool(scalar(run(test))):
            return run(then)
    raise XlError("#N/A")


def _catching(only: str | None) -> Callable[[list[tuple], Callable[[tuple], object]], object]:
    """IFERROR and IFNA: the fallback when the value is an error (only #N/A for IFNA)."""

    def run(args: list[tuple], ev: Callable[[tuple], object]) -> object:
        try:
            return scalar(ev(args[0]))
        except XlError as err:
            if only and err.code != only:
                raise
            return ev(args[1])

    return run


def _is(test: Callable[[object], bool]) -> Callable[[list[tuple], Callable[[tuple], object]], bool]:
    """The IS functions: an error argument is a value to test, not an error to return."""

    def run(args: list[tuple], ev: Callable[[tuple], object]) -> bool:
        try:
            return test(scalar(ev(args[0])))
        except XlError as err:
            return test(err)

    return run


LAZY: dict[str, Callable[[list[tuple], Callable[[tuple], object]], object]] = {
    "IF": _if,
    "IFS": _ifs,
    "IFERROR": _catching(None),
    "IFNA": _catching("#N/A"),
    "ISERROR": _is(lambda v: isinstance(v, XlError)),
    "ISNA": _is(lambda v: v == XlError("#N/A")),
    "ISBLANK": _is(lambda v: v is None),
    "ISNUMBER": _is(lambda v: isinstance(v, float)),
    "ISTEXT": _is(lambda v: isinstance(v, str)),
    "ISLOGICAL": _is(lambda v: isinstance(v, bool)),
}
