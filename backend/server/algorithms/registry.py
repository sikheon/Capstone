from typing import Type
from .base import FLAlgorithm

_REGISTRY: dict[str, Type[FLAlgorithm]] = {}


def register(cls: Type[FLAlgorithm]) -> Type[FLAlgorithm]:
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> FLAlgorithm:
    if name not in _REGISTRY:
        raise KeyError(f"algorithm '{name}' not registered. available={list(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    return sorted(_REGISTRY)
