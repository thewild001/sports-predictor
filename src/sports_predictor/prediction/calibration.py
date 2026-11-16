"""Small, dependency-free temperature calibration helpers."""
from __future__ import annotations
import math
from typing import Sequence


def _softmax(logits: Sequence[float]) -> list[float]:
    peak = max(logits)
    values = [math.exp(value - peak) for value in logits]
    total = sum(values)
    return [value / total for value in values]


def apply_temperature(probabilities: Sequence[float], temperature: float) -> list[float]:
    if not 0.25 <= temperature <= 4:
        raise ValueError("temperature must be between 0.25 and 4")
    if not probabilities or any(p <= 0 or p >= 1 for p in probabilities):
        raise ValueError("probabilities must be non-empty and strictly between 0 and 1")
    return _softmax([math.log(p) / temperature for p in probabilities])


def fit_temperature(samples: Sequence[tuple[Sequence[float], int]]) -> dict[str, float | int]:
    """Fit a scalar temperature by minimizing in-sample multiclass log loss.

    Use a chronological train/validation split before applying this parameter in
    production; the returned loss is training fit, not an unbiased test metric.
    """
    if len(samples) < 10:
        raise ValueError("at least 10 labeled samples are required for calibration")
    if any(label < 0 or label >= len(probabilities) for probabilities, label in samples):
        raise ValueError("sample label is outside its probability vector")
    best_temperature, best_loss = 1.0, float("inf")
    for step in range(76):
        temperature = 0.25 + step * 0.05
        loss = 0.0
        for probabilities, label in samples:
            calibrated = apply_temperature(probabilities, temperature)
            loss -= math.log(max(calibrated[label], 1e-12))
        loss /= len(samples)
        if loss < best_loss:
            best_temperature, best_loss = temperature, loss
    return {"temperature": best_temperature, "log_loss": best_loss, "samples": len(samples)}
