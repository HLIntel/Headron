"""Artifact adapters: structured records and deterministic checks for office and archive files.

Standard library only (zipfile, xml.etree). The runtime budget is one dependency (pyyaml), so the
OOXML readers stay inside it. An adapter reads parts in memory and never extracts to disk or runs
anything from the file.

Verdicts follow the repo's rule: PASS, FAIL or NOT RUN. A file no adapter reads, or one that is
malformed, is NOT RUN with its reason. An unsafe container (traversal, symlink, DTD, zip bomb) is FAIL.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import stat
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree as ET

VERSION = "1.0.0"
MAX_PART_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_RATIO = 100
SAMPLE = 20
ERROR_VALUES = {"#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!"}
PLACEHOLDER = re.compile(r"\b(TODO|TBD|lorem ipsum)\b|\[insert", re.IGNORECASE)

R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
SML = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
WML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PML = "http://schemas.openxmlformats.org/presentationml/2006/main"
DML = "http://schemas.openxmlformats.org/drawingml/2006/main"


class Unreadable(Exception):
    """The file cannot be read as its kind. Verdict NOT RUN."""


class Unsafe(Exception):
    """The file is a hazard. Verdict FAIL."""

    def __init__(self, check: str, where: str, detail: str):
        super().__init__(detail)
        self.finding = Finding("blocker", check, where, detail)


@dataclass
class Finding:
    severity: str  # blocker | warning
    check: str
    where: str
    detail: str


@dataclass
class Inspection:
    kind: str
    file: str
    verdict: str  # PASS | FAIL | NOT RUN
    reason: str
    sha256: str
    counts: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)
    receipt: str = ""


def _m(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def _xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        info = zf.getinfo(name)
    except KeyError as exc:
        raise Unreadable(f"missing part {name}") from exc
    if info.file_size > MAX_PART_BYTES:
        raise Unreadable(f"part {name} exceeds {MAX_PART_BYTES} bytes")
    data = zf.read(name)
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise Unsafe("dtd_or_entity", name, "XML declares a DTD or entities; office parts never do")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise Unreadable(f"part {name} is not well-formed XML: {exc}") from exc


def _rels(zf: zipfile.ZipFile, name: str) -> dict[str, str]:
    if name not in zf.namelist():
        return {}
    return {r.get("Id") or "": r.get("Target") or "" for r in _xml(zf, name).iter(_m(PKG_RELS, "Relationship"))}


def _resolve(base: str, target: str) -> str:
    if target.startswith("/"):
        return target[1:]
    return posixpath.normpath(posixpath.join(base, target))


def _zip_structure(zf: zipfile.ZipFile, findings: list[Finding], records: list[dict]) -> dict:
    infos = zf.infolist()
    total = 0
    seen: set[str] = set()
    for info in infos:
        name = info.filename
        total += info.file_size
        if name in seen:
            findings.append(Finding("blocker", "duplicate_member", name, "same member name twice"))
        seen.add(name)
        parts = name.replace("\\", "/").split("/")
        if name.startswith("/") or ".." in parts or re.match(r"^[A-Za-z]:", name):
            findings.append(Finding("blocker", "path_traversal", name, "member escapes the archive root"))
        if stat.S_ISLNK(info.external_attr >> 16):
            findings.append(Finding("blocker", "symlink", name, "symbolic link member"))
        ratio = info.file_size / info.compress_size if info.compress_size else 0
        if ratio > MAX_RATIO:
            findings.append(Finding("blocker", "zip_bomb_ratio", name, f"{ratio:.0f}:1 compression"))
        records.append({"member": name, "bytes": info.file_size})
    if total > MAX_TOTAL_BYTES:
        findings.append(Finding("blocker", "archive_size", "*", f"{total} bytes uncompressed"))
    return {"members": len(infos), "uncompressed_bytes": total}


def _run_xlsx(zf: zipfile.ZipFile, findings: list[Finding], records: list[dict]) -> dict:
    book = _xml(zf, "xl/workbook.xml")
    rels = _rels(zf, "xl/_rels/workbook.xml.rels")
    shared: list[str] = []
    if "xl/sharedStrings.xml" in zf.namelist():
        for si in _xml(zf, "xl/sharedStrings.xml").iter(_m(SML, "si")):
            shared.append("".join(t.text or "" for t in si.iter(_m(SML, "t"))))
    counts = {"sheets": 0, "cells": 0, "formulas": 0, "uncached_formulas": 0, "error_values": 0}
    for sheet in book.iter(_m(SML, "sheet")):
        name = sheet.get("name", "?")
        target = rels.get(sheet.get(_m(R_NS, "id")) or "")
        if not target:
            findings.append(Finding("warning", "unlinked_sheet", name, "sheet has no relationship target"))
            continue
        part = _resolve("xl", target)
        if part not in zf.namelist():
            findings.append(Finding("blocker", "missing_sheet_part", name, f"no part {part}"))
            continue
        counts["sheets"] += 1
        for cell in _xml(zf, part).iter(_m(SML, "c")):
            counts["cells"] += 1
            ref = cell.get("r", "?")
            kind = cell.get("t")
            value_node = cell.find(_m(SML, "v"))
            formula_node = cell.find(_m(SML, "f"))
            value = value_node.text if value_node is not None else None
            if kind == "s" and value is not None:
                idx = int(value)
                value = shared[idx] if idx < len(shared) else None
            elif kind == "inlineStr":
                value = "".join(t.text or "" for t in cell.iter(_m(SML, "t")))
            if kind == "e":
                counts["error_values"] += 1
                findings.append(Finding("blocker", "error_value", f"{name}!{ref}", str(value)))
            if formula_node is not None:
                counts["formulas"] += 1
                if value_node is None:
                    counts["uncached_formulas"] += 1
                records.append({"sheet": name, "cell": ref, "formula": formula_node.text, "value": value})
    if counts["uncached_formulas"]:
        findings.append(
            Finding(
                "warning",
                "uncached_formulas",
                "*",
                f"{counts['uncached_formulas']} formulas have no cached value; not recalculated",
            )
        )
    return counts


def _run_docx(zf: zipfile.ZipFile, findings: list[Finding], records: list[dict]) -> dict:
    root = _xml(zf, "word/document.xml")
    rels = _rels(zf, "word/_rels/document.xml.rels")
    counts = {"paragraphs": 0, "headings": 0, "links": 0, "placeholders": 0}
    for index, para in enumerate(root.iter(_m(WML, "p")), 1):
        counts["paragraphs"] += 1
        text = "".join(t.text or "" for t in para.iter(_m(WML, "t")))
        style = para.find(f"{_m(WML, 'pPr')}/{_m(WML, 'pStyle')}")
        if style is not None and re.match(r"^(Heading|Title)", style.get(_m(WML, "val"), "")):
            counts["headings"] += 1
        hit = PLACEHOLDER.search(text)
        if hit:
            counts["placeholders"] += 1
            findings.append(Finding("warning", "placeholder_text", f"paragraph {index}", hit.group(0)))
    for link in root.iter(_m(WML, "hyperlink")):
        counts["links"] += 1
        target = rels.get(link.get(_m(R_NS, "id")) or "", "")
        if target.startswith(("http://", "https://")):
            records.append({"link": target})
    return counts


def _run_pptx(zf: zipfile.ZipFile, findings: list[Finding], records: list[dict]) -> dict:
    pres = _xml(zf, "ppt/presentation.xml")
    rels = _rels(zf, "ppt/_rels/presentation.xml.rels")
    counts = {"slides": 0, "empty_slides": 0, "links": 0, "placeholders": 0}
    for slide_id in pres.iter(_m(PML, "sldId")):
        target = rels.get(slide_id.get(_m(R_NS, "id")) or "")
        if not target:
            continue
        counts["slides"] += 1
        part = _resolve("ppt", target)
        slide = _xml(zf, part)
        texts = [t.text for t in slide.iter(_m(DML, "t")) if t.text]
        if not texts:
            counts["empty_slides"] += 1
            findings.append(Finding("warning", "empty_slide", part, "slide has no text"))
        for text in texts:
            hit = PLACEHOLDER.search(text)
            if hit:
                counts["placeholders"] += 1
                findings.append(Finding("warning", "placeholder_text", part, hit.group(0)))
        slide_links = _rels(zf, posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels"))
        for link in slide.iter(_m(DML, "hlinkClick")):
            counts["links"] += 1
            records.append({"slide": part, "link": slide_links.get(link.get(_m(R_NS, "id")) or "", "")})
    return counts


@dataclass(frozen=True)
class Adapter:
    kind: str
    run: Callable[[zipfile.ZipFile, list[Finding], list[dict]], dict] | None
    container: bool = True


# run=None: the kind is a container the structure pass reads (zip); its records are the members.
ADAPTERS: dict[str, Adapter] = {
    ".xlsx": Adapter("xlsx", _run_xlsx),
    ".xlsm": Adapter("xlsx", _run_xlsx),
    ".docx": Adapter("docx", _run_docx),
    ".pptx": Adapter("pptx", _run_pptx),
    ".zip": Adapter("zip", None),
    ".pdf": Adapter("pdf", None, container=False),
}


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _receipt(body: dict) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def inspect(path: Path) -> Inspection:
    """Read one artifact. Never extracts, never executes, never writes."""
    path = Path(path)
    name = path.name
    if not path.is_file():
        return _finish(Inspection("missing", name, "NOT RUN", "no such file", ""))
    adapter = ADAPTERS.get(path.suffix.lower())
    digest = _digest(path)
    if adapter is None:
        reason = f"no adapter for {path.suffix or 'files without a suffix'}"
        return _finish(Inspection("unknown", name, "NOT RUN", reason, digest))
    if not adapter.container:
        return _finish(Inspection(adapter.kind, name, "NOT RUN", "no stdlib reader for this kind; not checked", digest))
    findings: list[Finding] = []
    records: list[dict] = []
    counts: dict = {}
    try:
        with zipfile.ZipFile(path) as zf:
            counts = _zip_structure(zf, findings, records if adapter.run is None else [])
            if adapter.run is not None:
                counts.update(adapter.run(zf, findings, records))
    except Unsafe as exc:
        findings.append(exc.finding)
    except (Unreadable, zipfile.BadZipFile) as exc:
        return _finish(Inspection(adapter.kind, name, "NOT RUN", str(exc), digest))
    blockers = [f for f in findings if f.severity == "blocker"]
    verdict = "FAIL" if blockers else "PASS"
    reason = f"{len(blockers)} blocker(s)" if blockers else "no blockers"
    return _finish(Inspection(adapter.kind, name, verdict, reason, digest, counts, findings, records))


def _finish(insp: Inspection) -> Inspection:
    body = {
        "tool": "thea-artifacts",
        "version": VERSION,
        "kind": insp.kind,
        "file": insp.file,
        "sha256": insp.sha256,
        "verdict": insp.verdict,
        "counts": insp.counts,
        "findings": [asdict(f) for f in insp.findings],
    }
    insp.receipt = _receipt(body)
    return insp


def as_json(insp: Inspection) -> dict:
    """The agent-facing record: verdict and receipt first, samples capped."""
    out = asdict(insp)
    out["schema"] = "thea-inspect/1"
    out["records"] = insp.records[:SAMPLE]
    out["record_count"] = len(insp.records)
    out["version"] = VERSION
    return out


EXIT = {"PASS": 0, "FAIL": 1, "NOT RUN": 2}  # NOT RUN is never a pass: it has its own code


def cli(files: list[str], want_json: bool) -> int:
    """Exit 0 only if every file PASSes; 1 if any FAILs; 2 if any is NOT RUN (and none FAIL)."""
    results = [inspect(Path(f)) for f in files]
    if want_json:
        payload = [as_json(r) for r in results]
        print(json.dumps(payload[0] if len(payload) == 1 else payload, indent=2, sort_keys=True))
    else:
        print("\n".join(as_text(r) for r in results))
    codes = {EXIT[r.verdict] for r in results}
    return 1 if 1 in codes else 2 if 2 in codes else 0


def as_text(insp: Inspection, limit: int = 5) -> str:
    lines = [f"{insp.verdict} {insp.file} [{insp.kind}] {insp.reason}  receipt {insp.receipt[:12]}"]
    for f in insp.findings[:limit]:
        lines.append(f"  {f.severity} {f.check} {f.where}: {f.detail}")
    if len(insp.findings) > limit:
        lines.append(f"  ... {len(insp.findings) - limit} more (use --json)")
    return "\n".join(lines)
