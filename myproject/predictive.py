from functools import lru_cache
from wordfreq import top_n_list

_WORDS = top_n_list("en", 80_000)          # ranked common words

@lru_cache(maxsize=2048)
def suggest(prefix: str, k: int = 3) -> list[str]:
    if not prefix:
        return []
    p = prefix.lower()
    return [w for w in _WORDS if w.startswith(p)][:k]
