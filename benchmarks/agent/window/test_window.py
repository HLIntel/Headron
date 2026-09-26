from window import window


def test_every_window_including_the_last():
    assert window([1, 2, 3, 4], 2) == [[1, 2], [2, 3], [3, 4]]


def test_window_as_long_as_the_list():
    assert window([1, 2], 2) == [[1, 2]]
