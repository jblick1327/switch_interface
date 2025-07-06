import switch_interface.predictive as predictive


def test_letter_suggestion():
    letters = predictive.suggest_letters("th")
    assert isinstance(letters, list)
    assert len(letters) > 0
    assert all(isinstance(c, str) and len(c) == 1 for c in letters)
