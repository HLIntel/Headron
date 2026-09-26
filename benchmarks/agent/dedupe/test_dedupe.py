from dedupe import dedupe


def test_first_occurrence_order_is_kept():
    assert dedupe(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]
