"""Simple predictive text helpers without module-level state."""

from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from typing import Counter as CounterType, DefaultDict

import threading

from wordfreq import top_n_list


class Predictor:
    """Generate common word and letter suggestions."""

    def __init__(self, words: list[str] | None = None) -> None:
        self.words = words or top_n_list("en", 80_000)
        self.fallback_starts = Counter(
            w[0] for w in self.words if w and w[0].isalpha()
        )
        self.start_letters: CounterType[str] | None = None
        self.bigrams: DefaultDict[str, CounterType[str]] | None = None
        self.trigrams: DefaultDict[str, CounterType[str]] | None = None
        self.ready = False
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()

    # ───────── internal helpers ────────────────────────────────────────────
    def _build_ngrams(self) -> None:
        start_letters: CounterType[str] = Counter()
        bigrams: DefaultDict[str, CounterType[str]] = defaultdict(Counter)
        trigrams: DefaultDict[str, CounterType[str]] = defaultdict(Counter)

        for word in self.words:
            w = "".join(c for c in word.lower() if c.isalpha())
            if not w:
                continue
            start_letters[w[0]] += 1
            for a, b in zip(w, w[1:]):
                bigrams[a][b] += 1
            for a, b, c in zip(w, w[1:], w[2:]):
                trigrams[a + b][c] += 1

        self.start_letters = start_letters
        self.bigrams = bigrams
        self.trigrams = trigrams
        self.ready = True

    def _ensure_thread(self) -> None:
        """Kick off n-gram building in the background if not already running."""

        if self.ready or self.thread is not None:
            return
        with self.lock:
            if self.thread is None and not self.ready:
                self.thread = threading.Thread(target=self._build_ngrams, daemon=True)
                self.thread.start()

    def _fallback_letters(self, prefix: str, k: int) -> list[str]:
        cleaned = "".join(c for c in prefix.lower() if c.isalpha())

        counts = Counter()
        if not cleaned:
            counts = self.fallback_starts
        else:
            n = len(cleaned)
            for w in self.words:
                if w.startswith(cleaned) and len(w) > n:
                    c = w[n]
                    if c.isalpha():
                        counts[c] += 1
            if not counts:
                counts = self.fallback_starts

        return [c for c, _ in counts.most_common(k)]

    # ───────── public API ─────────────────────────────────────────────────
    @lru_cache(maxsize=2048)
    def suggest_words(self, prefix: str, k: int = 3) -> list[str]:
        """Return up to ``k`` common words starting with ``prefix``."""
        self._ensure_thread()

        if not prefix:
            return []
        p = prefix.lower()
        return [w for w in self.words if w.startswith(p)][:k]

    @lru_cache(maxsize=2048)
    def suggest_letters(self, prefix: str, k: int = 3) -> list[str]:
        """Suggest up to ``k`` likely next letters for ``prefix``."""
        self._ensure_thread()

        if not self.ready:
            return self._fallback_letters(prefix, k)

        cleaned = "".join(c for c in prefix.lower() if c.isalpha())
        if not cleaned:
            assert self.start_letters is not None
            source = self.start_letters
        else:
            last2 = cleaned[-2:]
            if len(last2) == 2 and self.trigrams is not None and last2 in self.trigrams:
                source = self.trigrams[last2]
            else:
                last1 = cleaned[-1]
                assert self.bigrams is not None and self.start_letters is not None
                source = self.bigrams.get(last1, self.start_letters)

        return [letter for letter, _ in source.most_common(k)]


# A module-level predictor for simple use
default_predictor = Predictor()


def suggest_words(prefix: str, k: int = 3) -> list[str]:
    """Wrapper around :meth:`Predictor.suggest_words` using ``default_predictor``."""

    return default_predictor.suggest_words(prefix, k)


def suggest_letters(prefix: str, k: int = 3) -> list[str]:
    """Wrapper around :meth:`Predictor.suggest_letters` using ``default_predictor``."""

    return default_predictor.suggest_letters(prefix, k)


__all__ = [
    "Predictor",
    "default_predictor",
    "suggest_words",
    "suggest_letters",
]
