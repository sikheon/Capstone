from . import registry
from .base import DropoutPredictor


class DropoutAdvisor:
    """Thin wrapper that owns the *currently selected* predictor and lets it
    be swapped at runtime through the registry."""

    def __init__(self, name: str = "rule_based") -> None:
        self.set(name)

    def set(self, name: str) -> None:
        self.predictor: DropoutPredictor = registry.get(name)
        self.name = name

    def evaluate(self, state) -> dict:
        risk, reasons = self.predictor.predict(state)
        return {"client_id": state.client_id, "risk": risk, "reasons": reasons,
                "predictor": self.name}
