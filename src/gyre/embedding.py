"""Embedding backends for text-based measurements.

A rumination sensor that works on *meaning* rather than surface form needs an
embedding. The quality of that embedding turns out to be the whole game for L1:
a lexical embedding cannot tell a reworded repeat (rumination) from a genuinely
new approach, because it only sees the words. This module offers three backends
on a rising quality ladder, so you can see the ceiling move:

- ``hash``  — token bag hashed to a fixed vector. Zero deps, purely lexical.
              Fooled by rewording. The floor.
- ``char``  — character n-gram hashing (sklearn). Still lexical, but robust to
              rewording that preserves sub-word structure ("try/except" vs
              "try-except block"). A torch-free middle rung.
- ``api``   — a real semantic embedding via an OpenAI-compatible endpoint
              (OpenRouter etc.). Opt-in, needs a key. The rung where the thesis
              actually gets tested, because it understands synonymy.

The point of shipping all three is honesty: you can watch a measurement's power
rise with its embedding, and see for yourself that "good measurement" is not a
slogan, it is a resource you can dial up and measure the effect of.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from typing import Callable

import numpy as np

Embedder = Callable[[str], np.ndarray]


def hash_embed(text: str, dim: int = 256) -> np.ndarray:
    """Token-bag hashing embedding. Lexical, dependency-free, the floor."""
    vec = np.zeros(dim, dtype=float)
    for tok in text.lower().split():
        h = int(hashlib.blake2b(tok.encode("utf-8"), digest_size=8).hexdigest(), 16)
        vec[h % dim] += 1.0
    n = np.linalg.norm(vec)
    return vec / n if n else vec


def _make_char_embedder(dim: int = 512) -> Embedder:
    """Character n-gram hashing via sklearn's stateless HashingVectorizer.

    Stateless means no corpus fit, so it works step-by-step in a streaming sensor.
    Character n-grams share structure across rewordings that token bags miss, which
    is why this catches more rumination than ``hash`` without needing a model.
    """
    from sklearn.feature_extraction.text import HashingVectorizer

    vec = HashingVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), n_features=dim, norm="l2", alternate_sign=False
    )

    def embed(text: str) -> np.ndarray:
        return np.asarray(vec.transform([text or ""]).todense()).ravel()

    return embed


def _make_api_embedder(model: str, *, api_key: str | None = None,
                       endpoint: str = "https://openrouter.ai/api/v1/embeddings",
                       timeout: float = 30.0) -> Embedder:
    """A semantic embedding via an OpenAI-compatible embeddings endpoint. Opt-in."""
    key = api_key or os.environ.get("OPENROUTER_API_KEY")

    def embed(text: str) -> np.ndarray:
        if not key:
            raise RuntimeError("api embedder needs OPENROUTER_API_KEY or api_key=")
        data = json.dumps({"model": model, "input": text or " "}).encode("utf-8")
        req = urllib.request.Request(
            endpoint, data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        v = np.asarray(payload["data"][0]["embedding"], dtype=float)
        n = np.linalg.norm(v)
        return v / n if n else v

    return embed


_LOCAL_MODELS: dict[str, object] = {}


def _make_local_embedder(model_name: str = "BAAI/bge-small-en-v1.5") -> Embedder:
    """A real semantic embedding via fastembed (ONNX, no torch). Downloads a small
    model on FIRST EMBED (not now), so constructing a provider stays cheap and
    provider discovery does not pay for a model it may never use."""

    def _load():
        if model_name not in _LOCAL_MODELS:
            from fastembed import TextEmbedding  # lazy: optional dependency

            cache_dir = os.environ.get("FASTEMBED_CACHE_PATH") or os.environ.get("HF_HOME")
            _LOCAL_MODELS[model_name] = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        return _LOCAL_MODELS[model_name]

    def embed(text: str) -> np.ndarray:
        model = _load()
        v = np.asarray(list(model.embed([text or " "]))[0], dtype=float)
        n = np.linalg.norm(v)
        return v / n if n else v

    return embed


def make_embedder(kind: str = "hash", *, dim: int = 256, api_key: str | None = None) -> Embedder:
    """Build an embedder by name.

    - ``"hash"``            token-bag hashing (default, no deps). Lexical.
    - ``"char"``            character n-gram hashing (needs sklearn). Lexical.
    - ``"local"``           semantic embedding via fastembed/ONNX (needs fastembed,
                            no torch). ``"local:<model>"`` to pick the model.
    - ``"api:<model-id>"``  semantic embedding via an OpenAI-compatible endpoint.
    """
    if kind == "hash":
        return lambda t: hash_embed(t, dim)
    if kind == "char":
        return _make_char_embedder(dim if dim >= 256 else 512)
    if kind == "local":
        return _make_local_embedder()
    if kind.startswith("local:"):
        return _make_local_embedder(kind[6:])
    if kind.startswith("api:"):
        return _make_api_embedder(kind[4:], api_key=api_key)
    raise ValueError(f"unknown embedder kind: {kind!r} (use hash|char|local|api:<model>)")
