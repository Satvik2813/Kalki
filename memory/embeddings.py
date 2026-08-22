"""Dependency-free embedding + similarity.

A hashing bag-of-words embedder gives KALKI deterministic, offline vector
retrieval with no model download. It is intentionally simple: good enough to
surface similar past incidents in the local backend and to keep tests
deterministic. The Supabase backend can swap in real embeddings behind the
same interface.

Uses a STABLE hash (blake2b) rather than the builtin ``hash()`` — embeddings
are persisted to disk, so the same text must embed identically across
processes and restarts.
"""
from __future__ import annotations

import hashlib
import math
import re

_TOKEN = re.compile(r"[a-z0-9]+")

# Small English stopword set — these carry no engineering signal and their
# trigrams otherwise dominate the hashed features, corrupting ranking.
_STOPWORDS = frozenset(
    """a an and are as at be by for from has have in into is it its of on or that
    the to was were will with this these those we you your our their they them
    then than but not no do does did done can could should would may might must
    i me my he she his her""".split()
)


def _stable_hash(token: str) -> int:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def _char_ngrams(token: str, n: int = 3):
    """Character n-grams of a padded token, so morphologically related words
    (e.g. 'failing' / 'failures', 'authentication' / 'auth') share features."""
    padded = f"#{token}#"
    if len(padded) <= n:
        yield padded
        return
    for i in range(len(padded) - n + 1):
        yield padded[i : i + n]


def _add(vec: list[float], key: str, weight: float, dim: int) -> None:
    h = _stable_hash(key)
    idx = h % dim
    sign = 1.0 if (h >> 63) & 1 == 0 else -1.0
    vec[idx] += sign * weight


def embed(text: str, dim: int = 384) -> list[float]:
    """Deterministic hashed embedding over whole tokens *and* their character
    trigrams, L2-normalised. The trigram features give fuzzy, offline semantic
    overlap without any model download."""
    vec = [0.0] * dim
    for tok in _TOKEN.findall(text.lower()):
        if tok in _STOPWORDS or len(tok) < 2:
            continue
        _add(vec, f"tok:{tok}", 2.0, dim)          # exact token (weighted high)
        for g in _char_ngrams(tok):                # subword overlap
            _add(vec, f"ng:{g}", 0.5, dim)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    # inputs are pre-normalised, so dot == cosine; clamp for safety
    return max(-1.0, min(1.0, dot))
