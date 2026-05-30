from typing import Type
from .base import ClientAlgorithm

_REGISTRY: dict[str, Type[ClientAlgorithm]] = {}


def register(cls: Type[ClientAlgorithm]) -> Type[ClientAlgorithm]:
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> ClientAlgorithm:
    if name not in _REGISTRY:
        raise KeyError(f"algorithm '{name}' not registered. available={list(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    return sorted(_REGISTRY)
