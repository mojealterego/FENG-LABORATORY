"""Offline anomaly *candidate* screening; never a validated leak detector.

A rolling median + MAD baseline ignores isolated large historical outliers.
Temperature dynamics are strongly coupled to load and ambient conditions;
a real deployment requires contextual features and field-labeled validation.
"""

from dataclasses import dataclass
import math
from statistics import median
from collections.abc import Sequence


@dataclass(frozen=True)
class DetectionPolicy:
    min_samples: int = 5
    sigma_threshold: float = 4.0
    min_absolute_change_c: float = 0.5

    def validate(self) -> None:
        if self.min_samples < 3:
            raise ValueError("min_samples must be >= 3")
        if not math.isfinite(self.sigma_threshold) or self.sigma_threshold <= 0:
            raise ValueError("sigma_threshold must be positive and finite")
        if not math.isfinite(self.min_absolute_change_c) or self.min_absolute_change_c <= 0:
            raise ValueError("min_absolute_change_c must be positive and finite")


@dataclass(frozen=True)
class DetectionResult:
    state: str
    is_candidate: bool
    reference_c: float | None
    deviation_c: float | None
    threshold_c: float | None


def detect_temperature_anomaly(
    history_c: Sequence[float], current_c: float, policy: DetectionPolicy = DetectionPolicy()
) -> DetectionResult:
    policy.validate()
    if not math.isfinite(current_c) or any(not math.isfinite(x) for x in history_c):
        raise ValueError("All temperature inputs must be finite")
    if len(history_c) < policy.min_samples:
        return DetectionResult("insufficient_history", False, None, None, None)
    baseline = median(history_c)
    mad = median([abs(x - baseline) for x in history_c])
    threshold = max(policy.min_absolute_change_c, policy.sigma_threshold * 1.4826 * mad)
    deviation = current_c - baseline
    candidate = abs(deviation) > threshold
    return DetectionResult(
        "anomaly_candidate" if candidate else "normal", candidate, baseline, deviation, threshold
    )
