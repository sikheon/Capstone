from typing import Type
from .base import Transport

_REGISTRY: dict[str, Type[Transport]] = {}


def register(cls: Type[Transport]) -> Type[Transport]:
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> Transport:
    if name not in _REGISTRY:
        raise KeyError(f"transport '{name}' not registered. available={list(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    return sorted(_REGISTRY)
