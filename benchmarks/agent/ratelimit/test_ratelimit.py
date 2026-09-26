from ratelimit import Limiter


def test_second_call_inside_the_gap_is_refused():
    limiter = Limiter(2.0)
    assert limiter.allow(10.0) is True
    assert limiter.allow(10.1) is False
    assert limiter.allow(10.6) is True
