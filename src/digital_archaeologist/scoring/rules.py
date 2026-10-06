from __future__ import annotations

WEIGHTS = {
    "demand": 25,
    "existing_traction": 20,
    "neglect": 15,
    "ease_of_resurrection": 15,
    "monetisation": 15,
    "competition": 5,
    "licence_ownership": 5,
}


def bounded(value: object, maximum: float, default: float) -> float:
    if value is None:
        return default
    try:
        return max(0.0, min(float(maximum), float(value)))
    except (TypeError, ValueError):
        return default
