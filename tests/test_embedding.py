"""Embedding backend tests (no model download, no network).

Embedding backends live behind the optional ``semantic`` extra, so numpy is not
guaranteed in a public checkout. Skipping the module when it is absent is what
keeps "the public tier is stdlib-only and the suite runs anywhere" true rather
than merely intended - a clean CI runner caught this claim being false.
"""

import pytest

np = pytest.importorskip("numpy", reason="embedding backends need the semantic extra")

from gyre.embedding import hash_embed, make_embedder


def test_hash_embed_is_normalized_and_right_dim():
    v = hash_embed("the quick brown fox", dim=128)
    assert v.shape == (128,)
    assert abs(np.linalg.norm(v) - 1.0) < 1e-6


def test_hash_embed_empty_is_zero():
    v = hash_embed("", dim=64)
    assert np.linalg.norm(v) == 0.0


def test_make_embedder_hash_dispatch():
    e = make_embedder("hash", dim=64)
    assert e("hello world").shape == (64,)


def test_make_embedder_char_is_semantic_ish_but_lexical():
    e = make_embedder("char")
    a = e("wrap the query in a try-except block")
    b = e("wrap the query in a try except block")  # punctuation reword
    c = e("rewrite the module to use async")
    # char n-grams: near-identical rewording is closer than a different topic.
    assert float(a @ b) > float(a @ c)


def test_make_embedder_rejects_unknown():
    with pytest.raises(ValueError):
        make_embedder("nonsense")
