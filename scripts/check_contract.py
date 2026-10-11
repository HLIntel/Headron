#!/usr/bin/env python3
"""Backward-compatible entry point: `python scripts/check_contract.py`.

Prefer `python scripts/atlas.py check`. This wrapper exists because older docs and
hooks call it by name, and it must work from ANY working directory — importing
`atlas` only resolved when scripts/ happened to be on sys.path.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlas import main

if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):  # a script with no parser would RUN on --help
        print((__doc__ or sys.argv[0]).strip())
        sys.exit(0)
    raise SystemExit(main(["check"]))
