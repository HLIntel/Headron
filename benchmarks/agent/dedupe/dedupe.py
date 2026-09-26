def dedupe(items: list[str]) -> list[str]:
    """Drop repeats, keeping the FIRST occurrence and the original order."""
    return list(set(items))
