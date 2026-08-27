from __future__ import annotations

from statistics import mean
from typing import Any


def summarize(run: dict[str, Any]) -> dict[str, Any]:
    samples = run.get("samples", [])
    accepted = [s for s in samples if s.get("accepted")]
    metrics = [s.get("metrics", {}) for s in samples]

    def avg(key: str):
        vals = [m[key] for m in metrics if isinstance(m.get(key), (int, float))]
        return round(mean(vals), 4) if vals else None

    total_cost = sum(float(s.get("cost_usd", 0) or 0) for s in samples)
    accepted_seconds = sum(float(s.get("duration_s", 0) or 0) for s in accepted)
    return {
        "samples": len(samples),
        "accepted": len(accepted),
        "acceptance_rate": round(len(accepted) / len(samples), 4) if samples else 0,
        "avg_identity_drift": avg("identity_drift"),
        "avg_composition_drift": avg("composition_drift"),
        "avg_keyframe_error_frames": avg("keyframe_error_frames"),
        "total_cost_usd": round(total_cost, 4),
        "cost_per_accepted_second_usd": round(total_cost / accepted_seconds, 4) if accepted_seconds else None,
    }
