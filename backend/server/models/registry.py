from typing import Type
from .base import ModelSpec

_REGISTRY: dict[str, Type[ModelSpec]] = {}


def register(cls: Type[ModelSpec]) -> Type[ModelSpec]:
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> ModelSpec:
    if name not in _REGISTRY:
        raise KeyError(f"model '{name}' not registered. available={list(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    return sorted(_REGISTRY)
