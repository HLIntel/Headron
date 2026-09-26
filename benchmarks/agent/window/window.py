def window(xs: list[int], n: int) -> list[list[int]]:
    """Every contiguous run of n items, in order."""
    return [xs[i : i + n] for i in range(len(xs) - n)]
