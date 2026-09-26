import re


def seconds(text: str) -> int:
    """'1h30m' -> 5400, '45s' -> 45, '2h' -> 7200."""
    units = {"h": 3600, "s": 1}
    return sum(int(n) * units[u] for n, u in re.findall(r"(\d+)([hs])", text))
