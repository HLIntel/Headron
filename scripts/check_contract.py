"""Backward-compatible entry point. Prefer python scripts/atlas.py check."""

from atlas import main

if __name__ == "__main__":
    raise SystemExit(main(["check"]))
