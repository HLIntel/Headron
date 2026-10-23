"""Artifact adapters: each kind has a fixture that must PASS, and a hazard that must FAIL or NOT RUN."""

from __future__ import annotations

import stat
import zipfile
from pathlib import Path

import artifacts

SML_HEAD = '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
SML_TAIL = "</sheetData></worksheet>"
RELS_NS = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'


def _zip(
    path: Path, parts: dict[str, str | bytes], extra: list[tuple[zipfile.ZipInfo, str | bytes]] | None = None
) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, body in parts.items():
            zf.writestr(name, body)
        for info, body in extra or []:
            zf.writestr(info, body)
    return path


def make_xlsx(tmp: Path, sheet_xml: str, shared: str = "<sst/>", name: str = "book.xlsx") -> Path:
    workbook = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Model" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = f'<Relationships {RELS_NS}><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>'
    return _zip(
        tmp / name,
        {
            "xl/workbook.xml": workbook,
            "xl/_rels/workbook.xml.rels": rels,
            "xl/worksheets/sheet1.xml": SML_HEAD + sheet_xml + SML_TAIL,
            "xl/sharedStrings.xml": shared,
        },
    )


def make_docx(tmp: Path, body: str) -> Path:
    doc = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<w:body>{body}</w:body></w:document>"
    )
    rels = f"<Relationships {RELS_NS}/>"
    return _zip(tmp / "doc.docx", {"word/document.xml": doc, "word/_rels/document.xml.rels": rels})


def make_pptx(tmp: Path, slide_body: str) -> Path:
    pres = (
        '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>'
    )
    prels = f'<Relationships {RELS_NS}><Relationship Id="rId1" Target="slides/slide1.xml"/></Relationships>'
    slide = (
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f"{slide_body}</p:sld>"
    )
    return _zip(
        tmp / "deck.pptx",
        {"ppt/presentation.xml": pres, "ppt/_rels/presentation.xml.rels": prels, "ppt/slides/slide1.xml": slide},
    )


def test_xlsx_clean_passes(tmp_path):
    cells = '<row><c r="A1"><v>2</v></c><c r="B1"><f>A1*3</f><v>6</v></c></row>'
    insp = artifacts.inspect(make_xlsx(tmp_path, cells))
    assert insp.verdict == "PASS", insp
    assert insp.counts["formulas"] == 1 and insp.counts["error_values"] == 0


def test_xlsx_error_value_fails(tmp_path):
    cells = '<row><c r="A1" t="e"><f>1/0</f><v>#DIV/0!</v></c></row>'
    insp = artifacts.inspect(make_xlsx(tmp_path, cells))
    assert insp.verdict == "FAIL"
    assert [f.check for f in insp.findings] == ["error_value"]
    assert insp.findings[0].where == "Model!A1"


def test_xlsx_uncached_formula_warns_and_passes(tmp_path):
    cells = '<row><c r="B1"><f>A1*3</f></c></row>'
    insp = artifacts.inspect(make_xlsx(tmp_path, cells))
    assert insp.verdict == "PASS"
    assert any(f.check == "uncached_formulas" and f.severity == "warning" for f in insp.findings)


def test_xlsx_shared_string_resolves(tmp_path):
    shared = '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>Revenue</t></si></sst>'
    cells = '<row><c r="A1" t="s"><v>0</v></c></row>'
    insp = artifacts.inspect(make_xlsx(tmp_path, cells, shared=shared))
    assert insp.verdict == "PASS"
    assert insp.records == [] and insp.counts["cells"] == 1


def test_docx_placeholder_warns_and_headings_count(tmp_path):
    body = (
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Scope</w:t></w:r></w:p>'
        "<w:p><w:r><w:t>TODO: fill in revenue</w:t></w:r></w:p>"
    )
    insp = artifacts.inspect(make_docx(tmp_path, body))
    assert insp.verdict == "PASS"
    assert insp.counts["headings"] == 1 and insp.counts["placeholders"] == 1


def test_pptx_empty_slide_warns(tmp_path):
    insp = artifacts.inspect(make_pptx(tmp_path, "<p:cSld/>"))
    assert insp.verdict == "PASS"
    assert insp.counts["empty_slides"] == 1


def test_pptx_text_counts(tmp_path):
    body = "<a:p><a:r><a:t>Q3 numbers</a:t></a:r></a:p>"
    insp = artifacts.inspect(make_pptx(tmp_path, body))
    assert insp.verdict == "PASS" and insp.counts["empty_slides"] == 0


def test_zip_traversal_fails(tmp_path):
    p = _zip(tmp_path / "evil.zip", {"../escape.txt": "x", "ok.txt": "y"})
    insp = artifacts.inspect(p)
    assert insp.verdict == "FAIL"
    assert any(f.check == "path_traversal" for f in insp.findings)


def test_zip_symlink_fails(tmp_path):
    info = zipfile.ZipInfo("link")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    p = _zip(tmp_path / "link.zip", {"a.txt": "x"}, extra=[(info, "/etc/passwd")])
    insp = artifacts.inspect(p)
    assert insp.verdict == "FAIL"
    assert any(f.check == "symlink" for f in insp.findings)


def test_zip_bomb_ratio_fails(tmp_path):
    p = _zip(tmp_path / "bomb.zip", {"zeros.bin": b"\0" * (4 * 1024 * 1024)})
    insp = artifacts.inspect(p)
    assert insp.verdict == "FAIL"
    assert any(f.check == "zip_bomb_ratio" for f in insp.findings)


def test_dtd_in_office_part_fails(tmp_path):
    evil = '<!DOCTYPE x [<!ENTITY e "boom">]><sst/>'
    cells = '<row><c r="A1"><v>1</v></c></row>'
    insp = artifacts.inspect(make_xlsx(tmp_path, cells, shared=evil))
    assert insp.verdict == "FAIL"
    assert insp.findings[0].check == "dtd_or_entity"


def test_unreadable_or_unknown_is_not_run(tmp_path):
    cases = [("fake.xlsx", b"not a workbook", "xlsx"), ("legacy.doc", b"\xd0\xcf\x11\xe0", "unknown")]
    for name, body, kind in cases:
        p = tmp_path / name
        p.write_bytes(body)
        insp = artifacts.inspect(p)
        assert insp.verdict == "NOT RUN" and insp.kind == kind, name


def test_pdf_is_not_run_not_pass(tmp_path):
    p = tmp_path / "note.pdf"
    p.write_bytes(b"%PDF-1.4\n%%EOF\n")
    insp = artifacts.inspect(p)
    assert insp.verdict == "NOT RUN"


def test_receipt_is_deterministic_and_verdict_bound(tmp_path):
    cells = '<row><c r="A1"><v>2</v></c></row>'
    a = artifacts.inspect(make_xlsx(tmp_path, cells, name="a.xlsx"))
    b = artifacts.inspect(make_xlsx(tmp_path, cells, name="a.xlsx"))
    assert a.receipt == b.receipt
    bad = artifacts.inspect(make_xlsx(tmp_path, '<row><c r="A1" t="e"><v>#REF!</v></c></row>', name="a.xlsx"))
    assert bad.receipt != a.receipt


def test_json_record_caps_sample(tmp_path):
    rows = "".join(f'<row><c r="A{i}"><f>{i}</f><v>{i}</v></c></row>' for i in range(1, 60))
    out = artifacts.as_json(artifacts.inspect(make_xlsx(tmp_path, rows)))
    assert out["record_count"] == 59 and len(out["records"]) == artifacts.SAMPLE
