from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")

version = read("VERSION").strip()
expected = {
    "MODEL.md": version,
    "README.md": version,
    "ABOUT.md": version,
    "docs/VERSIONING.md": version,
}
errors: list[str] = []

for path, value in expected.items():
    text = read(path)
    if value not in text:
        errors.append(f"version mismatch: {path} != {value}")

required = [
    "MODEL.md", "README.md", "atlas.yaml", "docs/INDEX.md",
    "docs/LANGUAGE-SPEC.md", "languages/ATLAS.md",
    "models/README.md", "integrations/AI-CAPABILITIES.md",
    "patterns/NO-UNBOUNDED.md", "patterns/ANTI-MUTATION.md",
]
for path in required:
    if not (ROOT / path).exists():
        errors.append(f"missing required path: {path}")

if (ROOT / "AGENTS.md").exists():
    errors.append("stale root AGENTS.md exists; MODEL.md is the canonical control plane")

for alias in ["docs/PYTHON.md", "docs/RUST.md", "docs/GO.md", "docs/TYPESCRIPT.md"]:
    p = ROOT / alias
    if not p.is_symlink():
        errors.append(f"expected symlink: {alias}")
    elif not (p.parent / p.readlink()).exists():
        errors.append(f"broken symlink: {alias} -> {p.readlink()}")

if errors:
    for error in errors:
        print(error)
    sys.exit(1)

print(f"Code-Development contract {version}: OK")