import importlib
import switch_interface.predictive as predictive


def test_letter_suggestion():
    letters = predictive.suggest_letters("th")
    assert isinstance(letters, list)
    assert len(letters) > 0
    assert all(isinstance(c, str) and len(c) == 1 for c in letters)


def test_ngram_thread_starts_on_demand(monkeypatch):
    importlib.reload(predictive)
    assert predictive.default_predictor.thread is None

    letters = predictive.suggest_letters("an")
    assert len(letters) > 0
    assert predictive.default_predictor.thread is not None

