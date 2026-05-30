from typing import Type
from .base import DatasetLoader

_REGISTRY: dict[str, Type[DatasetLoader]] = {}


def register(cls: Type[DatasetLoader]) -> Type[DatasetLoader]:
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> DatasetLoader:
    if name not in _REGISTRY:
        raise KeyError(f"dataset '{name}' not registered. available={list(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    return sorted(_REGISTRY)
