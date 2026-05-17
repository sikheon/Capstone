from typing import Type
from .base import DropoutPredictor

_REGISTRY: dict[str, Type[DropoutPredictor]] = {}


def register(cls: Type[DropoutPredictor]) -> Type[DropoutPredictor]:
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> DropoutPredictor:
    if name not in _REGISTRY:
        raise KeyError(f"dropout predictor '{name}' not registered. available={list(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    return sorted(_REGISTRY)
