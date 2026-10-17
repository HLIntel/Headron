"""Bounded chunks: 100 items in chunks of at most 8; the sum proves every chunk ran."""
# Run: mojo bounded.mojo
from testing import assert_equal


fn main():
    n = 100
    limit = 8
    total = 0
    i = 0
    while i < n:
        stop = min(i + limit, n)
        for j in range(i, stop):
            total += (j + 1) * 2
        i = stop
    # sum of doubled 1..100 = 10100
    assert_equal(total, 10100)
    print("bounded: 1 assertion held — 100 items in chunks of at most 8, sum verified")
