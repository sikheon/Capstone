from typing import Type
from .base import SelectionPolicy

_REGISTRY: dict[str, Type[SelectionPolicy]] = {}


def register(cls: Type[SelectionPolicy]) -> Type[SelectionPolicy]:
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> SelectionPolicy:
    if name not in _REGISTRY:
        raise KeyError(f"selection '{name}' not registered. available={list(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    return sorted(_REGISTRY)
