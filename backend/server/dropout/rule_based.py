from .base import DropoutPredictor
from .registry import register


@register
class RuleBased(DropoutPredictor):
    """Hand-tuned thresholds. Cheap, interpretable, and a fine baseline."""

    name = "rule_based"

    def predict(self, s):
        risk = 0.0
        reasons: list[str] = []
        if s.battery is not None and not s.charging and s.battery < 0.2:
            risk += 0.5
            reasons.append(f"low battery ({s.battery:.0%}) and not charging")
        if s.network in ("none", "cell"):
            risk += 0.3
            reasons.append(f"unstable network ({s.network})")
        if s.cpu_load is not None and s.cpu_load > 0.9:
            risk += 0.2
            reasons.append(f"cpu saturated ({s.cpu_load:.0%})")
        return min(risk, 1.0), reasons
