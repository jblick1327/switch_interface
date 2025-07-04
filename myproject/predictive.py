"""Simple predictive text helpers."""

from collections import Counter, defaultdict
from functools import lru_cache
from typing import Counter as CounterType
from typing import DefaultDict

from wordfreq import top_n_list

# Preload a large list of common English words. 80k keeps startup reasonable
# while providing decent coverage for prediction.
_WORDS = top_n_list("en", 80_000)  # ranked common words


# ───────── letter n‑gram models ────────────────────────────────────────────

# Frequency of starting letters for words
_START_LETTERS: CounterType[str] = Counter()

# Bigram and trigram counts.  ``_BIGRAMS['h']['e']`` counts how often
# "he" occurs, while ``_TRIGRAMS['th']['e']`` counts occurrences of "the".
_BIGRAMS: DefaultDict[str, CounterType[str]] = defaultdict(Counter)
_TRIGRAMS: DefaultDict[str, CounterType[str]] = defaultdict(Counter)

for word in _WORDS:
    w = "".join(c for c in word.lower() if c.isalpha())
    if not w:
        continue
    _START_LETTERS[w[0]] += 1
    for a, b in zip(w, w[1:]):
        _BIGRAMS[a][b] += 1
    for a, b, c in zip(w, w[1:], w[2:]):
        _TRIGRAMS[a + b][c] += 1


# ───────── public API ─────────────────────────────────────────────────────


@lru_cache(maxsize=2048)
def suggest_words(prefix: str, k: int = 3) -> list[str]:
    """Return up to ``k`` common words starting with ``prefix``."""

    if not prefix:
        return []
    p = prefix.lower()
    return [w for w in _WORDS if w.startswith(p)][:k]


@lru_cache(maxsize=2048)
def suggest_letters(prefix: str, k: int = 3) -> list[str]:
    """Suggest up to ``k`` likely next letters for ``prefix``."""

    cleaned = "".join(c for c in prefix.lower() if c.isalpha())
    if not cleaned:
        source = _START_LETTERS
    else:
        last2 = cleaned[-2:]
        if len(last2) == 2 and last2 in _TRIGRAMS:
            source = _TRIGRAMS[last2]
        else:
            last1 = cleaned[-1]
            source = _BIGRAMS.get(last1, _START_LETTERS)

    return [letter for letter, _ in source.most_common(k)]
