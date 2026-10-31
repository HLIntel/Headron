"""Data kit: read tables from data files, check them against a schema, trace a report's numbers.

`headron data read` turns CSV, TSV, JSON, JSONL, Excel and Markdown tables into one table shape, each
value carrying where it came from (`book.xlsx:Revenue!B3`, `rows.csv!C7`, `notes.md:12:amount`,
`data.json$[3].total`). `check` holds a table to a declared schema. `trace` takes every number a
report states and either names the source value it came from or marks it UNTRACED, so an agent's
summary of a spreadsheet or a research table can be proved number by number.

Standard library only; workbooks are read through artifacts.workbook_cells, behind the same zip,
DTD and size refusals as `headron inspect`. Nothing is extracted, executed or written.

Verdicts follow the repo's rule: PASS, FAIL or NOT RUN, exit 0, 1, 2. A number the report states is
never dropped: it is traced, UNTRACED, or ignored with the reason (code, date, time, version,
reference, ordinal, year, link). A derived figure (a total the report computed) is UNTRACED by
design: trace proves a number was read, not that arithmetic on it was right.
"""

from __future__ import annotations

import bisect
import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import artifacts

SCHEMA = "headron-data/1"
VERSION = "1.0.0"
MAX_TEXT_BYTES = 64 * 1024 * 1024
TYPES = ("integer", "number", "percent", "currency", "date", "boolean", "text")
SCHEMA_KEYS = {"table", "min_rows", "columns", "extra_columns"}
COLUMN_KEYS = {"type", "required", "unique", "min", "max", "enum"}
TRUTH = {"true", "false", "yes", "no"}
CURRENCY = "$€£¥"
SCALES = {
    "k": 3, "K": 3, "thousand": 3,
    "M": 6, "mn": 6, "million": 6,
    "B": 9, "bn": 9, "billion": 9,
    "T": 12, "tn": 12, "trillion": 12,
}  # fmt: skip

# One number as a person writes it: (1,234.5), -$3.2bn, 12%, 4.7 million. Units after it ("200ms") are
# left alone; a number glued to a word before it ("x86", "Q3", "FY2025") is not a number.
NUMBER = re.compile(
    r"(?<![\w./])"
    r"(?P<open>\()?"
    r"(?P<sign>[-−+])?"
    r"(?P<cur>[$€£¥])?"
    r"(?P<sign2>[-−])?"
    r"(?P<int>\d{1,3}(?:,\d{3})+|\d+)"
    r"(?P<frac>\.\d+)?"
    r"(?:(?P<scale>k|K|M|B|T|bn|mn|tn)\b|\s?(?P<word>thousand|million|billion|trillion)\b)?"
    r"(?P<pct>\s?%)?"
    r"(?(open)\))"
)
MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b\.?"
# Spans whose numbers are not quantities. Order matters: the first kind that covers a number names it.
MASKS: list[tuple[str, re.Pattern[str]]] = [
    ("code", re.compile(r"^(```|~~~).*?^\1", re.M | re.S)),
    ("code", re.compile(r"`[^`\n]+`")),
    ("link", re.compile(r"https?://[^\s)>\]]+|\]\([^)\s]+\)")),
    ("date", re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?|\b\d{1,2}/\d{1,2}/\d{2,4}\b")),
    ("date", re.compile(rf"\b{MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH}(?:,?\s+\d{{4}})?")),
    ("time", re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")),
    ("version", re.compile(r"\bv\d+(?:\.\d+)*\b|\b\d+\.\d+\.\d+[\w.+-]*")),
    ("reference", re.compile(r"#\d+\b|\[\d+(?:\s*[,–-]\s*\d+)*\]|\b[A-Z][A-Z0-9]+-\d+\b")),
    ("ordinal", re.compile(r"^\s*(?:[-*+]\s+)?\d+[.)](?=\s)|^#{1,6}\s+\d+(?:\.\d+)*\.?(?=\s)|\b\d+(?:st|nd|rd|th)\b", re.M)),
]  # fmt: skip


@dataclass(frozen=True)
class Num:
    """A written number: its value (scale applied), half a unit of its last shown digit, and form."""

    value: Decimal
    tolerance: Decimal
    percent: bool = False
    paren: bool = False
    signed: bool = False
    bare: bool = False  # no comma, fraction, currency, scale, sign or percent: may be a year


@dataclass
class Table:
    name: str
    columns: list[str]
    rows: list[list[str]] = field(default_factory=list)
    where: list[list[str]] = field(default_factory=list)  # each cell's locator, same shape as rows


@dataclass
class Loaded:
    file: str
    kind: str
    verdict: str  # PASS | FAIL | NOT RUN
    reason: str
    sha256: str = ""
    tables: list[Table] = field(default_factory=list)
    values: list[tuple[str, str]] = field(default_factory=list)  # (where, raw) for every scalar
    findings: list[artifacts.Finding] = field(default_factory=list)


def _num(match: re.Match[str]) -> Num:
    digits = match["int"].replace(",", "") + (match["frac"] or "")
    places = len(match["frac"]) - 1 if match["frac"] else 0
    exponent = SCALES.get(match["scale"] or match["word"] or "", 0)
    scale = Decimal(10) ** exponent
    value = Decimal(digits) * scale
    tolerance = Decimal(5) * Decimal(10) ** (-places - 1) * scale
    sign = match["sign"] or match["sign2"] or ""
    negative = bool(match["open"]) or sign in ("-", "−")
    form = (
        match["frac"],
        match["cur"],
        match["scale"],
        match["word"],
        match["pct"],
        match["sign"],
        match["sign2"],
        match["open"],
    )
    return Num(
        -value if negative else value,
        tolerance,
        percent=bool(match["pct"]),
        paren=bool(match["open"]),
        signed=bool(sign),
        bare="," not in match["int"] and not any(form),
    )


def parse_value(raw: str) -> Decimal | None:
    """A whole cell as one number (`1234567`, `1.2E+6`, `$1,234`, `12%` = 0.12, `(500)`), else None."""
    text = raw.strip()
    if not text:
        return None
    try:
        value = Decimal(text)
        return value if value.is_finite() else None
    except InvalidOperation:
        pass
    match = NUMBER.fullmatch(text)
    if match is None:
        return None
    num = _num(match)
    return num.value / 100 if num.percent else num.value


def kind_of(raw: str) -> str | None:
    """The narrowest type a raw value satisfies; None for an empty cell."""
    text = raw.strip()
    if not text:
        return None
    if text.lower() in TRUTH:
        return "boolean"
    if re.fullmatch(r"[-−+]?(?:\d{1,3}(?:,\d{3})+|\d+)", text):
        return "integer"
    try:
        date.fromisoformat(text[:10])
        if len(text) == 10 or datetime.fromisoformat(text.replace("Z", "+00:00")):
            return "date"
    except ValueError:
        pass
    if parse_value(text) is None:
        return "text"
    if text.endswith("%"):
        return "percent"
    if any(c in text for c in CURRENCY):
        return "currency"
    return "number"


ACCEPTS = {
    "integer": {"integer"},
    "number": {"integer", "number"},
    "percent": {"percent", "integer", "number"},  # a workbook stores 12% as 0.12
    "currency": {"currency", "integer", "number"},  # and $1,200 as 1200
    "date": {"date"},
    "boolean": {"boolean"},
    "text": set(TYPES),
}


def column_type(raws: list[str]) -> str:
    kinds = {k for k in map(kind_of, raws) if k}
    if not kinds:
        return "empty"
    for name in TYPES:
        if kinds <= ACCEPTS[name] and (name in kinds or name == "number"):
            return name
    return "mixed"


# ---------------------------------------------------------------- readers


def _col(n: int) -> str:
    letters = ""
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def _header(cells: list[str], width: int) -> list[str]:
    """Header names, padded to the widest row; a blank or repeated name takes its column letter."""
    header: list[str] = []
    for i, cell in enumerate(cells + [""] * (width - len(cells))):
        name = cell.strip() or _col(i + 1)
        header.append(f"{name} ({_col(i + 1)})" if name in header else name)
    return header


def _grid(name: str, rows: list[list[str]], locate) -> Table:
    """First row is the header; no cell is dropped. `locate(row_index, col_index)` names a cell."""
    width = max((len(row) for row in rows), default=0)
    table = Table(name, _header(rows[0], width) if rows else [])
    for r, row in enumerate(rows[1:], 1):
        table.rows.append(row + [""] * (width - len(row)))
        table.where.append([locate(r, c) for c in range(width)])
    return table


def _read_delimited(path: Path, text: str, loaded: Loaded) -> None:
    reader = csv.reader(io.StringIO(text), delimiter="\t" if path.suffix.lower() == ".tsv" else ",")
    numbered = [(reader.line_num, row) for row in reader if any(cell.strip() for cell in row)]
    rows = [row for _, row in numbered]
    loaded.tables.append(_grid(path.name, rows, lambda r, c: f"{path.name}!{_col(c + 1)}{numbered[r][0]}"))


def _scalar(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _leaves(node: object, at: str, out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        for key, child in node.items():
            _leaves(child, f"{at}.{key}", out)
    elif isinstance(node, list):
        for i, child in enumerate(node):
            _leaves(child, f"{at}[{i}]", out)
    else:
        out.append((at, _scalar(node)))


def _records(name: str, items: list, at: str) -> Table | None:
    if not items or not all(isinstance(item, dict) for item in items):
        return None
    columns: list[str] = []
    for item in items:
        columns += [key for key in item if key not in columns]
    table = Table(name, columns)
    for i, item in enumerate(items):
        table.rows.append(
            [
                _scalar(item.get(c))
                if not isinstance(item.get(c), (dict, list))
                else json.dumps(item.get(c), default=str)
                for c in columns
            ]
        )
        table.where.append([f"{at}[{i}].{c}" for c in columns])
    return table


def _read_json(path: Path, text: str, loaded: Loaded) -> None:
    data = json.loads(text, parse_float=Decimal, parse_int=Decimal)
    root = f"{path.name}$"
    _leaves(data, root, loaded.values)
    if isinstance(data, list):
        table = _records(path.name, data, root)
        loaded.tables += [table] if table else []
    elif isinstance(data, dict):
        for key, child in data.items():
            table = _records(key, child, f"{root}.{key}") if isinstance(child, list) else None
            loaded.tables += [table] if table else []


def _read_jsonl(path: Path, text: str, loaded: Loaded) -> None:
    items, lines = [], []
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip():
            try:
                items.append(json.loads(line, parse_float=Decimal, parse_int=Decimal))
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {number} is not JSON: {exc.msg}") from exc
            lines.append(number)
    table = _records(path.name, items, path.name)
    if table is None:
        raise ValueError("every line must be a JSON object")
    table.where = [[f"{path.name}:{lines[r]}.{c}" for c in table.columns] for r in range(len(table.rows))]
    loaded.tables.append(table)


def _read_xlsx(path: Path, loaded: Loaded) -> None:
    cells, loaded.findings = artifacts.workbook_cells(path)
    sheets: dict[str, dict[int, dict[int, tuple[str, str]]]] = {}
    for sheet, ref, kind, value in cells:
        match = re.fullmatch(r"([A-Z]+)(\d+)", ref)
        if match is None or value is None or kind == "e":
            continue
        raw = ("TRUE" if value == "1" else "FALSE") if kind == "b" else value
        where = f"{path.name}:{sheet}!{ref}"
        loaded.values.append((where, raw))
        sheets.setdefault(sheet, {}).setdefault(int(match[2]), {})[_col_index(match[1])] = (raw, where)
    for sheet, grid in sheets.items():
        width = max(max(row) for row in grid.values())
        first, *rest = sorted(grid)
        table = Table(sheet, _header([grid[first].get(c, ("", ""))[0] for c in range(1, width + 1)], width))
        for r in rest:
            table.rows.append([grid[r].get(c, ("", ""))[0] for c in range(1, width + 1)])
            table.where.append([f"{path.name}:{sheet}!{_col(c)}{r}" for c in range(1, width + 1)])
        loaded.tables.append(table)


def _read_markdown(path: Path, text: str, loaded: Loaded) -> None:
    """Pipe tables, each named after the nearest heading above it."""
    lines = text.splitlines()
    heading, i, fenced = "", 0, False
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            heading = line.lstrip("#").strip()
        elif (
            not fenced
            and line.startswith("|")
            and i + 1 < len(lines)
            and re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?", lines[i + 1].strip())
        ):
            start = i
            rows = [_cells(line)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i].strip()))
                i += 1
            name = heading or f"table at line {start + 1}"
            numbers = [start + 1] + list(range(start + 3, i + 1))
            table = _grid(name, rows, lambda r, c: "")
            table.where = [[f"{path.name}:{numbers[r]}:{col}" for col in table.columns] for r in range(1, len(rows))]
            loaded.tables.append(table)
            continue
        i += 1


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


TEXT_READERS = {".csv": _read_delimited, ".tsv": _read_delimited, ".json": _read_json, ".jsonl": _read_jsonl, ".md": _read_markdown, ".markdown": _read_markdown, ".txt": None}  # fmt: skip
KINDS = {".csv": "csv", ".tsv": "tsv", ".json": "json", ".jsonl": "jsonl", ".md": "markdown", ".markdown": "markdown", ".txt": "text", ".xlsx": "xlsx", ".xlsm": "xlsx"}  # fmt: skip


def load(path: Path) -> Loaded:
    """Read one data file into tables and located values. Never raises for a bad file: NOT RUN."""
    path = Path(path)
    suffix = path.suffix.lower()
    if not path.is_file():
        return Loaded(path.name, "missing", "NOT RUN", "no such file")
    loaded = Loaded(path.name, KINDS.get(suffix, "unknown"), "PASS", "read", artifacts._digest(path))
    if suffix not in KINDS:
        loaded.verdict, loaded.reason = "NOT RUN", f"no reader for {suffix or 'files without a suffix'}"
        return loaded
    try:
        if loaded.kind == "xlsx":
            _read_xlsx(path, loaded)
        else:
            if path.stat().st_size > MAX_TEXT_BYTES:
                raise ValueError(f"larger than {MAX_TEXT_BYTES} bytes")
            text = path.read_text(encoding="utf-8-sig")
            reader = TEXT_READERS[suffix]
            if reader is not None:
                reader(path, text, loaded)
            if loaded.kind in ("markdown", "text"):
                loaded.values += [(n["where"], n["text"]) for n in numbers(text, path.name) if n["status"] == "number"]
    except (artifacts.Unreadable, ValueError, UnicodeDecodeError, RecursionError, csv.Error) as exc:
        loaded.verdict, loaded.reason = "NOT RUN", str(exc) or type(exc).__name__
        return loaded
    if loaded.kind not in ("json", "markdown", "text", "xlsx"):
        loaded.values += [
            (w, v) for table in loaded.tables for wr, vr in zip(table.where, table.rows) for w, v in zip(wr, vr)
        ]
    blockers = [f for f in loaded.findings if f.severity == "blocker"]
    if blockers:
        loaded.verdict, loaded.reason = "FAIL", f"{len(blockers)} blocker(s)"
    else:
        loaded.reason = f"{len(loaded.tables)} table(s), {len(loaded.values)} value(s)"
    return loaded


# ---------------------------------------------------------------- numbers in prose


def numbers(text: str, name: str) -> list[dict]:
    """Every number written in `text`: status `number`, or `ignored:<kind>` with the reason."""
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    spans = [(m.start(), m.end(), kind) for kind, rx in MASKS for m in rx.finditer(text)]
    out = []
    for match in NUMBER.finditer(text):
        start, end = match.span()
        line = bisect.bisect_right(starts, start)
        where = f"{name}:{line}:{start - starts[line - 1] + 1}"
        cover = next((kind for s, e, kind in spans if s < end and start < e), None)
        num = _num(match)
        if cover is None and num.bare and 1800 <= num.value <= 2199:
            cover = "year"
        out.append(
            {
                "where": where,
                "text": match.group(0).strip(),
                "status": f"ignored:{cover}" if cover else "number",
                "num": num,
            }
        )
    return out


# ---------------------------------------------------------------- check


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _schema_problem(schema: dict) -> str | None:
    """Why a schema cannot be applied as written, or None. A rule this check does not know is never skipped."""
    if set(schema) - SCHEMA_KEYS:
        return f"unknown keys {sorted(set(schema) - SCHEMA_KEYS)}"
    if schema.get("extra_columns", "allow") not in ("allow", "refuse"):
        return "extra_columns is allow or refuse"
    if not isinstance(schema.get("min_rows", 0), int) or isinstance(schema.get("min_rows"), bool):
        return "min_rows is an integer"
    if not isinstance(schema.get("table", ""), str):
        return "table is a name"
    columns = schema.get("columns", {})
    if not isinstance(columns, dict):
        return "columns maps a column name to its rule"
    return next((p for name, rule in columns.items() if (p := _rule_problem(name, rule))), None)


def _rule_problem(name: str, rule: object) -> str | None:
    """Why one column rule cannot be applied, or None."""
    if not isinstance(rule, dict) or set(rule) - COLUMN_KEYS:
        return f"{name}: rule keys are {sorted(COLUMN_KEYS)}"
    if rule.get("type", "text") not in TYPES:
        return f"{name}: type is one of {list(TYPES)}"
    bounds = [b for b in ("min", "max") if b in rule]
    if bounds and (
        rule.get("type") not in ("integer", "number", "percent", "currency")
        or not all(_is_number(rule[b]) for b in bounds)
    ):
        return f"{name}: min and max are numbers on a numeric type"
    if "enum" in rule and not isinstance(rule["enum"], list):
        return f"{name}: enum is a list"
    if any(not isinstance(rule.get(k, False), bool) for k in ("required", "unique")):
        return f"{name}: required and unique are true or false"
    return None


def _column_findings(table, name: str, rule: dict) -> list[artifacts.Finding]:
    """Every cell of one column held against its rule."""
    index, seen, found = table.columns.index(name), {}, []
    accepts = ACCEPTS[rule.get("type", "text")]
    for row, where in zip(table.rows, table.where):
        raw, at = row[index].strip(), where[index]
        if not raw:
            if rule.get("required"):
                found.append(artifacts.Finding("blocker", "required_empty", at, f"{name} is empty"))
            continue
        kind = kind_of(raw)
        if kind not in accepts:
            found.append(
                artifacts.Finding("blocker", "type_mismatch", at, f"{raw!r} is {kind}, not {rule.get('type')}")
            )
            continue
        found += _value_findings(raw, at, rule)
        if rule.get("unique"):
            if raw in seen:
                found.append(artifacts.Finding("blocker", "duplicate_value", at, f"{raw!r} also at {seen[raw]}"))
            seen.setdefault(raw, at)
    return found


def _value_findings(raw: str, at: str, rule: dict) -> list[artifacts.Finding]:
    """Bounds and enum for one typed cell."""
    found, value = [], parse_value(raw)
    for bound, ok in (("min", lambda v, b: v >= b), ("max", lambda v, b: v <= b)):
        if bound in rule and value is not None and not ok(value, Decimal(str(rule[bound]))):
            check = f"below_{bound}" if bound == "min" else "above_max"
            found.append(artifacts.Finding("blocker", check, at, f"{raw} vs {bound} {rule[bound]}"))
    if "enum" in rule and raw not in [str(e) for e in rule["enum"]]:
        found.append(artifacts.Finding("blocker", "not_in_enum", at, f"{raw!r} not in {rule['enum']}"))
    return found


def check(loaded: Loaded, schema: dict, limit: int) -> dict:
    record = {"command": "check", "file": loaded.file, "table": None, "rows": 0, "counts": {}, "findings": []}
    problem = _schema_problem(schema)
    if problem:
        return record | {"verdict": "NOT RUN", "reason": f"schema refused: {problem}"}
    if loaded.verdict != "PASS":
        return record | {"verdict": loaded.verdict, "reason": f"{loaded.file}: {loaded.reason}"}
    columns = schema.get("columns") or {}
    wanted = schema.get("table")
    tables = [t for t in loaded.tables if wanted in (None, t.name)]
    if len(tables) != 1:
        names = [t.name for t in loaded.tables]
        return record | {
            "verdict": "NOT RUN",
            "reason": f"{len(tables)} tables match; name one with `table` of {names}",
        }
    table = tables[0]
    record |= {"table": table.name, "rows": len(table.rows)}
    found: list[artifacts.Finding] = []
    if len(table.rows) < schema.get("min_rows", 0):
        found.append(
            artifacts.Finding("blocker", "too_few_rows", table.name, f"{len(table.rows)} < {schema['min_rows']}")
        )
    if schema.get("extra_columns") == "refuse":
        found += [
            artifacts.Finding("blocker", "extra_column", c, "column not in the schema")
            for c in table.columns
            if c not in columns
        ]
    for name, rule in columns.items():
        if name not in table.columns:
            found.append(artifacts.Finding("blocker", "missing_column", name, "column not in the table"))
            continue
        found += _column_findings(table, name, rule)
    counts: dict[str, int] = {}
    for f in found:
        counts[f.check] = counts.get(f.check, 0) + 1
    record |= {"counts": counts, "findings": [vars(f) for f in found[:limit]]}
    if found:
        return record | {"verdict": "FAIL", "reason": f"{len(found)} violation(s) in {len(table.rows)} row(s)"}
    return record | {"verdict": "PASS", "reason": f"{len(table.rows)} row(s) hold the schema"}


# ---------------------------------------------------------------- trace


def _index(sources: list[Loaded]) -> tuple[list[Decimal], list[str]]:
    pairs = sorted(
        (v, w) for s in sources if s.verdict == "PASS" for w, raw in s.values if (v := parse_value(raw)) is not None
    )
    return [v for v, _ in pairs], [w for _, w in pairs]


def _near(values: list[Decimal], wheres: list[str], target: Decimal, tolerance: Decimal) -> tuple[str, int] | None:
    lo = bisect.bisect_left(values, target - tolerance)
    hi = bisect.bisect_right(values, target + tolerance)
    if lo == hi:
        return None
    best = min(range(lo, hi), key=lambda i: abs(values[i] - target))
    return wheres[best], hi - lo


def _trace_one(num: Num, values: list[Decimal], wheres: list[str]) -> tuple[str, int, str] | None:
    """The source value a number names, with how many values fit and a note on any reading needed."""
    tries: list[tuple[Decimal, Decimal, str]] = []
    if num.percent:
        tries += [(num.value / 100, num.tolerance / 100, ""), (num.value, num.tolerance, "read as points")]
    else:
        tries.append((num.value, num.tolerance, ""))
    if num.paren:
        tries.append((-num.value, num.tolerance, "parentheses read as a magnitude"))
    elif not num.signed:
        tries.append((-num.value, num.tolerance, "source is negative; report states the magnitude"))
    for target, tolerance, note in tries:
        hit = _near(values, wheres, target, tolerance)
        if hit:
            return hit[0], hit[1], note
    return None


def trace(report: Path, sources: list[Loaded], limit: int) -> dict:
    record: dict = {
        "command": "trace",
        "report": Path(report).name,
        "sources": [
            {"file": s.file, "kind": s.kind, "verdict": s.verdict, "reason": s.reason, "values": len(s.values)}
            for s in sources
        ],
    }
    report = Path(report)
    if not report.is_file() or report.suffix.lower() not in (".md", ".markdown", ".txt"):
        return record | {
            "verdict": "NOT RUN",
            "reason": "the report must be an existing .md or .txt file",
            "counts": {},
        }
    readable = [s for s in sources if s.verdict == "PASS"]
    if not readable:
        return record | {"verdict": "NOT RUN", "reason": "no source could be read", "counts": {}}
    values, wheres = _index(readable)
    traced, untraced, ignored = [], [], {}
    for n in numbers(report.read_text(encoding="utf-8-sig"), report.name):
        if n["status"] != "number":
            kind = n["status"].split(":", 1)[1]
            ignored[kind] = ignored.get(kind, 0) + 1
            continue
        hit = _trace_one(n["num"], values, wheres)
        row = {"where": n["where"], "text": n["text"]}
        if hit:
            traced.append(row | {"source": hit[0], "matches": hit[1], **({"note": hit[2]} if hit[2] else {})})
        else:
            untraced.append(row)
    counts = {
        "numbers": len(traced) + len(untraced),
        "traced": len(traced),
        "untraced": len(untraced),
        "ignored": sum(ignored.values()),
    }
    record |= {"counts": counts, "ignored": ignored, "untraced": untraced[:limit], "traced": traced[:limit]}
    if not counts["numbers"]:
        return record | {"verdict": "NOT RUN", "reason": "the report states no number to trace"}
    if untraced:
        return record | {"verdict": "FAIL", "reason": f"{len(untraced)} of {counts['numbers']} number(s) untraced"}
    return record | {"verdict": "PASS", "reason": f"all {counts['numbers']} number(s) traced to a source"}


# ---------------------------------------------------------------- read and cli


def _table_record(table: Table, limit: int) -> dict:
    columns = []
    for i, name in enumerate(table.columns):
        raws = [row[i] for row in table.rows]
        columns.append({"name": name, "type": column_type(raws), "empty": sum(1 for r in raws if not r.strip())})
    rows = [dict(zip(table.columns, row)) for row in table.rows[:limit]]
    return {
        "name": table.name,
        "columns": columns,
        "row_count": len(table.rows),
        "rows": rows,
        "first": table.where[0][0] if table.where and table.where[0] else None,
    }


def read(loaded: list[Loaded], limit: int) -> dict:
    files = [
        {
            "file": s.file,
            "kind": s.kind,
            "verdict": s.verdict,
            "reason": s.reason,
            "sha256": s.sha256,
            "tables": [_table_record(t, limit) for t in s.tables],
            "values": len(s.values),
            "findings": [vars(f) for f in s.findings[:limit]],
        }
        for s in loaded
    ]
    verdicts = {s.verdict for s in loaded}
    verdict = "FAIL" if "FAIL" in verdicts else "NOT RUN" if "NOT RUN" in verdicts else "PASS"
    reason = f"{sum(len(s.tables) for s in loaded)} table(s) from {len(loaded)} file(s)"
    return {"command": "read", "verdict": verdict, "reason": reason, "files": files}


def _seal(record: dict) -> dict:
    body = {"schema": SCHEMA, "version": VERSION} | record
    return body | {"receipt": artifacts._receipt(body)}


def _text(record: dict) -> str:
    lines = [f"{record['verdict']} data {record['command']}: {record['reason']}  receipt {record['receipt'][:12]}"]
    if record["command"] == "read":
        for f in record["files"]:
            lines.append(f"  {f['verdict']} {f['file']} [{f['kind']}] {f['reason']}")
            for t in f["tables"]:
                cols = ", ".join(f"{c['name']}:{c['type']}" for c in t["columns"][:8])
                lines.append(
                    f"    {t['name']} {t['row_count']} row(s): {cols}{' ...' if len(t['columns']) > 8 else ''}"
                )
            lines += [f"    {x['severity']} {x['check']} {x['where']}: {x['detail']}" for x in f["findings"]]
    elif record["command"] == "check":
        lines += [f"  {x['check']} {x['where']}: {x['detail']}" for x in record["findings"]]
    else:
        lines += [f"  {s['verdict']} source {s['file']} [{s['kind']}] {s['reason']}" for s in record["sources"]]
        lines += [f"  UNTRACED {u['where']} {u['text']!r}" for u in record.get("untraced", [])]
        if record.get("ignored"):
            lines.append("  ignored " + ", ".join(f"{k} {v}" for k, v in sorted(record["ignored"].items())))
    return "\n".join(lines)


EXIT = {"PASS": 0, "FAIL": 1, "NOT RUN": 2}


def cli(
    action: str, files: list[str], schema: str | None, sources: list[str] | None, limit: int, want_json: bool
) -> int:
    """`headron data read|check|trace`. Exit 0 PASS, 1 FAIL, 2 NOT RUN (never a pass)."""
    if action == "read":
        record = read([load(Path(f)) for f in files], limit)
    elif action == "check":
        rules, reason = None, "check takes one file and --schema"
        if len(files) == 1 and schema:
            try:
                rules = json.loads(Path(schema).read_text(encoding="utf-8"))
                if not isinstance(rules, dict):
                    raise ValueError("schema must be a JSON object")
            except (OSError, ValueError) as exc:
                rules, reason = None, f"schema unreadable: {exc}"
        if rules is None:
            record = {"command": "check", "verdict": "NOT RUN", "reason": reason, "counts": {}, "findings": []}
        else:
            record = check(load(Path(files[0])), rules, limit)
    else:
        if len(files) != 1 or not sources:
            record = {
                "command": "trace",
                "verdict": "NOT RUN",
                "reason": "trace takes one report and at least one --source",
                "counts": {},
                "sources": [],
            }
        else:
            record = trace(Path(files[0]), [load(Path(s)) for s in sources], limit)
    sealed = _seal(record)
    print(json.dumps(sealed, indent=2, sort_keys=True, default=str) if want_json else _text(sealed))
    return EXIT[sealed["verdict"]]
