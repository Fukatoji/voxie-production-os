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


def evaluate(run: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a run against Voxie promotion gates.

    Missing measurements never pass implicitly. A model may be rejected from the
    benchmark lane, but only a separately approved action may promote it into
    production.
    """
    summary = summarize(run)
    findings = []

    gates = {
        "acceptance_rate": (summary["acceptance_rate"], policy.get("min_acceptance_rate"), "min"),
        "avg_identity_drift": (summary["avg_identity_drift"], policy.get("max_identity_drift"), "max"),
        "avg_composition_drift": (summary["avg_composition_drift"], policy.get("max_composition_drift"), "max"),
        "avg_keyframe_error_frames": (summary["avg_keyframe_error_frames"], policy.get("max_keyframe_error_frames"), "max"),
    }
    for metric, (actual, threshold, direction) in gates.items():
        if threshold is None:
            continue
        if actual is None:
            findings.append({"severity": "error", "metric": metric, "message": "Required metric is missing"})
            continue
        failed = actual < threshold if direction == "min" else actual > threshold
        if failed:
            findings.append({
                "severity": "error",
                "metric": metric,
                "actual": actual,
                "threshold": threshold,
                "message": f"{metric} failed the {direction}imum promotion gate",
            })

    samples = run.get("samples", [])
    wing_values = [
        float(sample.get("metrics", {}).get("wing_count_error", 0))
        for sample in samples
        if isinstance(sample.get("metrics", {}).get("wing_count_error"), (int, float))
    ]
    max_wing_rate = policy.get("max_wing_count_error_rate")
    wing_rate = (
        round(sum(1 for value in wing_values if value > 0) / len(wing_values), 4)
        if wing_values else None
    )
    if max_wing_rate is not None:
        if wing_rate is None:
            findings.append({"severity": "error", "metric": "wing_count_error_rate", "message": "Required metric is missing"})
        elif wing_rate > float(max_wing_rate):
            findings.append({
                "severity": "error",
                "metric": "wing_count_error_rate",
                "actual": wing_rate,
                "threshold": max_wing_rate,
                "message": "Four-wing consistency failed the promotion gate",
            })

    if any(not sample.get("output", {}).get("sha256") for sample in samples):
        findings.append({
            "severity": "error",
            "metric": "output_provenance",
            "message": "Every sample must record an output SHA-256 before comparison",
        })

    decision = "REJECT" if findings else "ELIGIBLE_FOR_HUMAN_PROMOTION_REVIEW"
    return {
        "benchmark_id": run.get("benchmark_id"),
        "decision": decision,
        "production_promoted": False,
        "summary": summary,
        "wing_count_error_rate": wing_rate,
        "findings": findings,
    }
