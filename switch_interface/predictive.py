"""Simple predictive text helpers."""

from collections import Counter, defaultdict
from functools import lru_cache
from typing import Counter as CounterType
from typing import DefaultDict

import threading

from wordfreq import top_n_list

# Preload a large list of common English words. 80k keeps startup reasonable
# while providing decent coverage for prediction.
_WORDS = top_n_list("en", 80_000)  # ranked common words

# Basic frequency of starting letters for fallback predictions
_FALLBACK_STARTS = Counter(w[0] for w in _WORDS if w and w[0].isalpha())


# ───────── letter n‑gram models ────────────────────────────────────────────

# Frequency of starting letters for words
_START_LETTERS: CounterType[str] | None = None

# Bigram and trigram counts.  ``_BIGRAMS['h']['e']`` counts how often
# "he" occurs, while ``_TRIGRAMS['th']['e']`` counts occurrences of "the".
_BIGRAMS: DefaultDict[str, CounterType[str]] | None = None
_TRIGRAMS: DefaultDict[str, CounterType[str]] | None = None

_READY = False
_THREAD: threading.Thread | None = None
_LOCK = threading.Lock()


def _build_ngrams() -> None:
    start_letters: CounterType[str] = Counter()
    bigrams: DefaultDict[str, CounterType[str]] = defaultdict(Counter)
    trigrams: DefaultDict[str, CounterType[str]] = defaultdict(Counter)

    for word in _WORDS:
        w = "".join(c for c in word.lower() if c.isalpha())
        if not w:
            continue
        start_letters[w[0]] += 1
        for a, b in zip(w, w[1:]):
            bigrams[a][b] += 1
        for a, b, c in zip(w, w[1:], w[2:]):
            trigrams[a + b][c] += 1

    global _START_LETTERS, _BIGRAMS, _TRIGRAMS, _READY
    _START_LETTERS = start_letters
    _BIGRAMS = bigrams
    _TRIGRAMS = trigrams
    _READY = True


def _ensure_thread() -> None:
    """Kick off n-gram building in the background if not already running."""

    global _THREAD
    if _READY or _THREAD is not None:
        return
    with _LOCK:
        if _THREAD is None and not _READY:
            _THREAD = threading.Thread(target=_build_ngrams, daemon=True)
            _THREAD.start()


def _fallback_letters(prefix: str, k: int) -> list[str]:
    cleaned = "".join(c for c in prefix.lower() if c.isalpha())

    counts = Counter()
    if not cleaned:
        counts = _FALLBACK_STARTS
    else:
        n = len(cleaned)
        for w in _WORDS:
            if w.startswith(cleaned) and len(w) > n:
                c = w[n]
                if c.isalpha():
                    counts[c] += 1
        if not counts:
            counts = _FALLBACK_STARTS

    return [c for c, _ in counts.most_common(k)]


# ───────── public API ─────────────────────────────────────────────────────


@lru_cache(maxsize=2048)
def suggest_words(prefix: str, k: int = 3) -> list[str]:
    """Return up to ``k`` common words starting with ``prefix``."""
    _ensure_thread()

    if not prefix:
        return []
    p = prefix.lower()
    return [w for w in _WORDS if w.startswith(p)][:k]


@lru_cache(maxsize=2048)
def suggest_letters(prefix: str, k: int = 3) -> list[str]:
    """Suggest up to ``k`` likely next letters for ``prefix``."""
    _ensure_thread()

    if not _READY:
        return _fallback_letters(prefix, k)

    cleaned = "".join(c for c in prefix.lower() if c.isalpha())
    if not cleaned:
        assert _START_LETTERS is not None
        source = _START_LETTERS
    else:
        last2 = cleaned[-2:]
        if len(last2) == 2 and _TRIGRAMS is not None and last2 in _TRIGRAMS:
            source = _TRIGRAMS[last2]
        else:
            last1 = cleaned[-1]
            assert _BIGRAMS is not None and _START_LETTERS is not None
            source = _BIGRAMS.get(last1, _START_LETTERS)

    return [letter for letter, _ in source.most_common(k)]

