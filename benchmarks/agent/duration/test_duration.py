from duration import seconds


def test_hours_and_minutes():
    assert seconds("1h30m") == 5400


def test_seconds_alone():
    assert seconds("45s") == 45
