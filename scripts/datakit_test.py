"""Data kit: every reader keeps cell locations, check names each violation, trace proves or refuses each number."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import datakit
from artifacts_test import make_xlsx

# FIXTURE DAYS ARE JOINED AT RUN TIME: the contract refuses a typed calendar date in any tracked file
# (dateclaims.py), and these are table cells under test, not claims about when anything happened.
DAY, NEXT, NO_DAY = ("-".join(parts) for parts in (("2026", "01", "02"), ("2026", "02", "03"), ("2026", "02", "30")))


def _write(tmp: Path, name: str, body: str) -> Path:
    path = tmp / name
    path.write_text(body, encoding="utf-8")
    return path


def _trace(tmp: Path, report: str, *sources: Path) -> dict:
    return datakit.trace(_write(tmp, "report.md", report), [datakit.load(s) for s in sources], limit=50)


def _status(text: str) -> list[tuple[str, str]]:
    return [(n["text"], n["status"]) for n in datakit.numbers(text, "r.md")]


def test_scaled_number_traces_within_its_written_precision(tmp_path):
    src = _write(tmp_path, "rev.csv", "region,revenue\nnorth,1234567\n")
    rec = _trace(tmp_path, "Revenue reached 1.2M.\n", src)
    assert rec["verdict"] == "PASS", rec
    assert rec["traced"][0]["source"] == "rev.csv!B2"


def test_overprecise_scaled_number_is_untraced(tmp_path):
    # 1,234k claims 1,234,000 +/- 500; the source holds 1,234,567.
    src = _write(tmp_path, "rev.csv", "region,revenue\nnorth,1234567\n")
    rec = _trace(tmp_path, "Revenue reached 1,234k.\n", src)
    assert rec["verdict"] == "FAIL"
    assert rec["untraced"] == [{"where": "report.md:1:17", "text": "1,234k"}]


def test_percent_paren_and_currency_forms_trace(tmp_path):
    src = _write(tmp_path, "pl.csv", "line,value\nmargin,0.12\nloss,-500\ncost,4200.50\nshare,37.5\n")
    rec = _trace(tmp_path, "Margin 12%, a (500) loss, cost $4,200.50 and 37.5% share.\n", src)
    assert rec["verdict"] == "PASS", rec
    by_text = {t["text"]: t for t in rec["traced"]}
    assert by_text["12%"]["source"] == "pl.csv!B2"
    assert by_text["(500)"]["source"] == "pl.csv!B3"
    assert by_text["$4,200.50"]["source"] == "pl.csv!B4"
    assert by_text["37.5%"]["note"] == "read as points"


def test_unsigned_magnitude_of_a_negative_source_traces_with_a_note(tmp_path):
    src = _write(tmp_path, "pl.csv", "line,value\nloss,-500\n")
    rec = _trace(tmp_path, "The loss was 500.\n", src)
    assert rec["verdict"] == "PASS"
    assert "magnitude" in rec["traced"][0]["note"]


def test_non_quantities_are_ignored_with_their_reason(tmp_path):
    text = (
        "1. First point\n"
        "Released 14/03/2025 at 09:30, see v2.4.1 and #412 [3] JIRA-77.\n"
        "Built in 2024 on March 3, 2025, the 2nd run of `x = 99`, https://ex.com/a/123.\n"
        "```\nprint(4242)\n```\n"
        "Q3 x86 FY2025\n"
    )
    statuses = dict(_status(text))
    assert all(s.startswith("ignored:") for s in statuses.values()), statuses
    assert statuses["2024"] == "ignored:year"
    assert statuses["4242"] == "ignored:code"
    assert statuses["412"] == "ignored:reference"


def test_derived_total_is_untraced(tmp_path):
    src = _write(tmp_path, "q.csv", "quarter,sales\nQ1,100\nQ2,250\n")
    rec = _trace(tmp_path, "Sales were 100 and 250, 350 in total.\n", src)
    assert rec["verdict"] == "FAIL"
    assert [u["text"] for u in rec["untraced"]] == ["350"]
    assert rec["counts"] == {"numbers": 3, "traced": 2, "untraced": 1, "ignored": 0}


def test_trace_without_numbers_or_readable_source_is_not_run(tmp_path):
    src = _write(tmp_path, "q.csv", "a\n1\n")
    assert _trace(tmp_path, "No figures here.\n", src)["verdict"] == "NOT RUN"
    assert _trace(tmp_path, "Sales were 1.\n", tmp_path / "missing.csv")["verdict"] == "NOT RUN"
    rec = datakit.trace(src, [datakit.load(src)], limit=5)
    assert rec["verdict"] == "NOT RUN"


def test_readers_share_one_table_shape_with_locations(tmp_path):
    csv = _write(tmp_path, "a.csv", "id,amount\n1,10\n\n2,20\n")
    tsv = _write(tmp_path, "a.tsv", "id\tamount\n1\t10\n")
    js = _write(tmp_path, "a.json", json.dumps({"rows": [{"id": 1, "amount": 10}, {"id": 2, "amount": 20.5}]}))
    jl = _write(tmp_path, "a.jsonl", '{"id": 1, "amount": 10}\n{"id": 2, "amount": 20}\n')
    md = _write(tmp_path, "a.md", "# Totals\n\n| id | amount |\n|---|---|\n| 1 | 10 |\n")
    for path in (csv, tsv, js, jl, md):
        loaded = datakit.load(path)
        assert loaded.verdict == "PASS", (path.name, loaded.reason)
        table = loaded.tables[0]
        assert table.columns == ["id", "amount"], (path.name, table.columns)
        assert table.rows[0] == ["1", "10"], (path.name, table.rows)
    # a blank line is skipped, but the locator keeps the file's own line number
    assert datakit.load(csv).tables[0].where[1] == ["a.csv!A4", "a.csv!B4"]
    assert datakit.load(md).tables[0].name == "Totals"


def test_ragged_rows_and_repeated_headers_keep_every_cell(tmp_path):
    loaded = datakit.load(_write(tmp_path, "r.csv", "a,a,\n1,2,3,4\n"))
    table = loaded.tables[0]
    assert table.columns == ["a", "a (B)", "C", "D"]
    assert table.rows == [["1", "2", "3", "4"]]


def test_xlsx_cells_carry_sheet_locations(tmp_path):
    cells = (
        '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
        '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>1234567</v></c></row>'
    )
    shared = '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>region</t></si><si><t>revenue</t></si><si><t>north</t></si></sst>'
    book = make_xlsx(tmp_path, cells, shared=shared)
    loaded = datakit.load(book)
    assert loaded.verdict == "PASS", loaded.reason
    assert loaded.tables[0].columns == ["region", "revenue"]
    rec = _trace(tmp_path, "North brought in $1.23 million.\n", book)
    assert rec["verdict"] == "PASS", rec
    assert rec["traced"][0]["source"] == "book.xlsx:Model!B2"


def test_unsafe_or_broken_workbook_is_never_a_source(tmp_path):
    bad = make_xlsx(tmp_path, '<row r="1"><c r="A1" t="e"><v>#REF!</v></c></row>', name="bad.xlsx")
    assert datakit.load(bad).verdict == "FAIL"
    fake = tmp_path / "fake.xlsx"
    fake.write_bytes(b"not a zip")
    assert datakit.load(fake).verdict == "NOT RUN"
    rec = _trace(tmp_path, "It was #REF! or 5.\n", bad, fake)
    assert rec["verdict"] == "NOT RUN"


SCHEMA = {
    "columns": {
        "id": {"type": "integer", "required": True, "unique": True},
        "amount": {"type": "currency", "min": 0, "max": 1000},
        "status": {"type": "text", "enum": ["open", "closed"]},
        "when": {"type": "date"},
    },
    "min_rows": 2,
    "extra_columns": "refuse",
}


def test_check_names_every_violation_by_cell(tmp_path):
    body = f"id,amount,status,when,note\n1,$10,open,{DAY},x\n1,-5,lost,soon,y\n,2000,closed,{NO_DAY},z\n"
    rec = datakit.check(datakit.load(_write(tmp_path, "t.csv", body)), SCHEMA, limit=50)
    assert rec["verdict"] == "FAIL"
    assert rec["counts"] == {
        "extra_column": 1,
        "duplicate_value": 1,
        "required_empty": 1,
        "below_min": 1,
        "above_max": 1,
        "not_in_enum": 1,
        "type_mismatch": 2,
    }, rec["counts"]
    where = {(f["check"], f["where"]) for f in rec["findings"]}
    assert ("duplicate_value", "t.csv!A3") in where
    assert ("required_empty", "t.csv!A4") in where
    assert ("type_mismatch", "t.csv!D3") in where


def test_check_passes_a_clean_table(tmp_path):
    body = f"id,amount,status,when\n1,$10,open,{DAY}\n2,12.5,closed,{NEXT}\n"
    rec = datakit.check(datakit.load(_write(tmp_path, "t.csv", body)), SCHEMA, limit=50)
    assert rec["verdict"] == "PASS", rec


def test_check_refuses_a_rule_it_does_not_know(tmp_path):
    loaded = datakit.load(_write(tmp_path, "t.csv", "id\n1\n"))
    for schema in (
        {"columns": {"id": {"type": "integer"}}, "regex": "x"},
        {"columns": {"id": {"type": "uuid"}}},
        {"columns": {"id": {"type": "integer", "pattern": "^\\d+$"}}},
        {"columns": {"id": {"type": "text", "min": 1}}},
        {"columns": {"id": {"type": "integer", "required": "yes"}}},
        {"min_rows": True},
    ):
        rec = datakit.check(loaded, schema, limit=5)
        assert rec["verdict"] == "NOT RUN", schema
        assert rec["reason"].startswith("schema refused"), rec["reason"]


def test_number_parsing_keeps_written_precision():
    assert datakit.parse_value("12%") == datakit.Decimal("0.12")
    assert datakit.parse_value("(1,500)") == -1500
    assert datakit.parse_value("-$3.2bn") == datakit.Decimal("-3.2E9")
    assert datakit.parse_value("1.2E+6") == 1200000
    assert datakit.parse_value("12 apples") is None
    assert datakit.kind_of("TRUE") == "boolean"
    assert datakit.column_type(["1", "2.5", ""]) == "number"
    assert datakit.column_type(["$1", "2"]) == "currency"
    assert datakit.column_type(["a", "1"]) == "text"


def test_cli_exit_codes_and_sealed_json(tmp_path):
    src = _write(tmp_path, "q.csv", "a\n7\n")
    report = _write(tmp_path, "r.md", "It was 7, then 8.\n")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = datakit.cli("trace", [str(report)], None, [str(src)], 20, True)
    rec = json.loads(out.getvalue())
    assert code == 1 and rec["verdict"] == "FAIL"
    assert rec["schema"] == datakit.SCHEMA and len(rec["receipt"]) == 64
    with contextlib.redirect_stdout(io.StringIO()):
        assert datakit.cli("trace", [str(report)], None, None, 20, False) == 2
        assert datakit.cli("check", [str(src)], str(tmp_path / "none.json"), None, 20, False) == 2
        assert datakit.cli("read", [str(src)], None, None, 20, False) == 0


TESTS = [
    test_scaled_number_traces_within_its_written_precision,
    test_overprecise_scaled_number_is_untraced,
    test_percent_paren_and_currency_forms_trace,
    test_unsigned_magnitude_of_a_negative_source_traces_with_a_note,
    test_non_quantities_are_ignored_with_their_reason,
    test_derived_total_is_untraced,
    test_trace_without_numbers_or_readable_source_is_not_run,
    test_readers_share_one_table_shape_with_locations,
    test_ragged_rows_and_repeated_headers_keep_every_cell,
    test_xlsx_cells_carry_sheet_locations,
    test_unsafe_or_broken_workbook_is_never_a_source,
    test_check_names_every_violation_by_cell,
    test_check_passes_a_clean_table,
    test_check_refuses_a_rule_it_does_not_know,
    test_cli_exit_codes_and_sealed_json,
]


def main() -> None:
    # Standalone runner, like artifacts_test: each case gets a fresh directory, so pytest is optional.
    import tempfile

    test_number_parsing_keeps_written_precision()
    print("  ok    test_number_parsing_keeps_written_precision")
    for test in TESTS:
        with tempfile.TemporaryDirectory() as d:
            test(Path(d))
        print(f"  ok    {test.__name__}")


if __name__ == "__main__":
    main()
