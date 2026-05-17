from ..core.client_manager import ClientState


class DropoutPredictor:
    """Lightweight rule-based dropout risk score (0..1).

    Designed to be replaced later with a learned model. The contract is
    `predict(state) -> float`; the rest of the system only cares about that.
    """

    def predict(self, s: ClientState) -> float:
        risk = 0.0
        if s.battery is not None and not s.charging and s.battery < 0.2:
            risk += 0.5
        if s.network in ("none", "cell"):
            risk += 0.3
        if s.cpu_load is not None and s.cpu_load > 0.9:
            risk += 0.2
        return min(risk, 1.0)


class DropoutAdvisor:
    """Wraps the predictor with a justification trail for the dashboard."""

    def __init__(self, predictor: DropoutPredictor | None = None) -> None:
        self.predictor = predictor or DropoutPredictor()

    def evaluate(self, state: ClientState) -> dict:
        risk = self.predictor.predict(state)
        reasons = []
        if state.battery is not None and not state.charging and state.battery < 0.2:
            reasons.append(f"low battery ({state.battery:.0%}) and not charging")
        if state.network in ("none", "cell"):
            reasons.append(f"unstable network ({state.network})")
        if state.cpu_load is not None and state.cpu_load > 0.9:
            reasons.append(f"cpu saturated ({state.cpu_load:.0%})")
        return {"client_id": state.client_id, "risk": risk, "reasons": reasons}
