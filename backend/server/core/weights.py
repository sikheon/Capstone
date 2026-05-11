"""Numpy ↔ JSON helpers for global model weights."""

import numpy as np


def to_jsonable(weights: dict) -> dict:
    """numpy arrays → nested python lists (JSON-safe)."""
    return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in weights.items()}


def from_jsonable(weights: dict) -> dict:
    """nested lists → numpy float32 arrays."""
    return {k: np.asarray(v, dtype=np.float32) for k, v in weights.items()}
