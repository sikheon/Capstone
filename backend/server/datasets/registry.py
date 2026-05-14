from typing import Type
from .base import DatasetSpec

_REGISTRY: dict[str, Type[DatasetSpec]] = {}


def register(cls: Type[DatasetSpec]) -> Type[DatasetSpec]:
    if not getattr(cls, "name", None):
        raise ValueError(f"{cls.__name__} must define a non-empty `name`")
    _REGISTRY[cls.name] = cls
    return cls


def get(name: str) -> DatasetSpec:
    if name not in _REGISTRY:
        raise KeyError(f"dataset '{name}' not registered. available={list(_REGISTRY)}")
    return _REGISTRY[name]()


def available() -> list[str]:
    return sorted(_REGISTRY)
