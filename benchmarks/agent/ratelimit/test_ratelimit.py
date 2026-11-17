from ratelimit import Limiter


def test_second_call_inside_the_gap_is_refused():
    limiter = Limiter(2.0)
    assert limiter.allow(10.0) is True
    assert limiter.allow(10.1) is False
    assert limiter.allow(10.6) is True


def test_first_call_is_allowed_whatever_the_clock_reads():
    # time.monotonic() may start near 0: a limiter that has never allowed anything has no gap to wait out
    assert Limiter(2.0).allow(0.1) is True
