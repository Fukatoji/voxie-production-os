from __future__ import annotations

import math
from statistics import mean
from typing import Any


def _measurement(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def summarize(run: dict[str, Any]) -> dict[str, Any]:
    samples = run.get("samples", [])
    accepted = [sample for sample in samples if sample.get("accepted")]
    metrics = [sample.get("metrics", {}) for sample in samples]

    def avg(key: str):
        values = [metric[key] for metric in metrics if _measurement(metric.get(key))]
        return round(mean(values), 4) if values else None

    total_cost = sum(float(sample.get("cost_usd", 0) or 0) for sample in samples)
    accepted_seconds = sum(
        float(sample.get("duration_s", 0) or 0) for sample in accepted
    )
    return {
        "samples": len(samples),
        "accepted": len(accepted),
        "acceptance_rate": round(len(accepted) / len(samples), 4) if samples else 0,
        "avg_identity_drift": avg("identity_drift"),
        "avg_composition_drift": avg("composition_drift"),
        "avg_keyframe_error_frames": avg("keyframe_error_frames"),
        "total_cost_usd": round(total_cost, 4),
        "cost_per_accepted_second_usd": (
            round(total_cost / accepted_seconds, 4) if accepted_seconds else None
        ),
    }


def evaluate(run: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a complete benchmark run against the complete suite.

    Scenario coverage, per-scenario required metrics, and promotion thresholds all
    fail closed. A model may become eligible for human review, but this function
    never promotes it into production.
    """
    summary = summarize(run)
    findings: list[dict[str, Any]] = []

    if not isinstance(suite, dict) or not isinstance(
        suite.get("promotion_policy"), dict
    ):
        policy = suite if isinstance(suite, dict) else {}
        scenarios: list[dict[str, Any]] = []
        findings.append(
            {
                "severity": "error",
                "metric": "benchmark_suite",
                "message": (
                    "Complete benchmark suite is required; promotion policy alone "
                    "cannot establish scenario coverage"
                ),
            }
        )
    else:
        policy = suite["promotion_policy"]
        scenarios = suite.get("scenarios", [])

    scenario_specs: dict[str, dict[str, Any]] = {}
    duplicate_scenarios: set[str] = set()
    for scenario in scenarios if isinstance(scenarios, list) else []:
        scenario_id = str(scenario.get("scenario_id", ""))
        if not scenario_id:
            findings.append(
                {
                    "severity": "error",
                    "metric": "benchmark_suite_scenarios",
                    "message": "Every suite scenario requires a scenario_id",
                }
            )
            continue
        if scenario_id in scenario_specs:
            duplicate_scenarios.add(scenario_id)
        scenario_specs[scenario_id] = scenario

    if duplicate_scenarios:
        findings.append(
            {
                "severity": "error",
                "metric": "benchmark_suite_scenarios",
                "message": "Duplicate scenario_id values: "
                + ", ".join(sorted(duplicate_scenarios)),
            }
        )
    if not scenario_specs:
        findings.append(
            {
                "severity": "error",
                "metric": "benchmark_suite_scenarios",
                "message": "Benchmark suite must define at least one required scenario",
            }
        )

    samples = run.get("samples", [])
    represented_scenarios = {
        str(sample.get("scenario_id", "")) for sample in samples
    }
    missing_scenarios = sorted(set(scenario_specs) - represented_scenarios)
    unknown_scenarios = sorted(represented_scenarios - set(scenario_specs))

    if missing_scenarios:
        findings.append(
            {
                "severity": "error",
                "metric": "scenario_coverage",
                "message": "Required scenarios are missing: "
                + ", ".join(missing_scenarios),
            }
        )
    if unknown_scenarios:
        findings.append(
            {
                "severity": "error",
                "metric": "scenario_coverage",
                "message": "Run contains unknown scenarios: "
                + ", ".join(unknown_scenarios),
            }
        )

    for sample_index, sample in enumerate(samples):
        scenario_id = str(sample.get("scenario_id", ""))
        scenario = scenario_specs.get(scenario_id)
        if scenario is None:
            continue
        metrics = sample.get("metrics", {})
        for metric in scenario.get("required_metrics", []):
            if not _measurement(metrics.get(metric)):
                findings.append(
                    {
                        "severity": "error",
                        "metric": "sample_required_metric",
                        "sample_id": sample.get("sample_id", f"sample-{sample_index}"),
                        "scenario_id": scenario_id,
                        "required_metric": metric,
                        "message": (
                            f"{scenario_id} sample is missing a finite numeric "
                            f"measurement for {metric}"
                        ),
                    }
                )

    gates = {
        "acceptance_rate": (
            summary["acceptance_rate"],
            policy.get("min_acceptance_rate"),
            "min",
        ),
        "avg_identity_drift": (
            summary["avg_identity_drift"],
            policy.get("max_identity_drift"),
            "max",
        ),
        "avg_composition_drift": (
            summary["avg_composition_drift"],
            policy.get("max_composition_drift"),
            "max",
        ),
        "avg_keyframe_error_frames": (
            summary["avg_keyframe_error_frames"],
            policy.get("max_keyframe_error_frames"),
            "max",
        ),
    }
    for metric, (actual, threshold, direction) in gates.items():
        if threshold is None:
            continue
        if actual is None:
            findings.append(
                {
                    "severity": "error",
                    "metric": metric,
                    "message": "Required aggregate metric is missing",
                }
            )
            continue
        failed = actual < threshold if direction == "min" else actual > threshold
        if failed:
            findings.append(
                {
                    "severity": "error",
                    "metric": metric,
                    "actual": actual,
                    "threshold": threshold,
                    "message": f"{metric} failed the {direction}imum promotion gate",
                }
            )

    max_wing_rate = policy.get("max_wing_count_error_rate")
    wing_values: list[float] = []
    wing_metrics_complete = True
    for sample in samples:
        value = sample.get("metrics", {}).get("wing_count_error")
        if not _measurement(value):
            wing_metrics_complete = False
        else:
            wing_values.append(float(value))

    wing_rate = (
        round(sum(1 for value in wing_values if value > 0) / len(wing_values), 4)
        if wing_values and wing_metrics_complete
        else None
    )
    if max_wing_rate is not None:
        if wing_rate is None:
            findings.append(
                {
                    "severity": "error",
                    "metric": "wing_count_error_rate",
                    "message": (
                        "Every sample must record a finite wing_count_error before "
                        "the wing-error rate can be calculated"
                    ),
                }
            )
        elif wing_rate > float(max_wing_rate):
            findings.append(
                {
                    "severity": "error",
                    "metric": "wing_count_error_rate",
                    "actual": wing_rate,
                    "threshold": max_wing_rate,
                    "message": "Four-wing consistency failed the promotion gate",
                }
            )

    if any(not sample.get("output", {}).get("sha256") for sample in samples):
        findings.append(
            {
                "severity": "error",
                "metric": "output_provenance",
                "message": (
                    "Every sample must record an output SHA-256 before comparison"
                ),
            }
        )

    decision = "REJECT" if findings else "ELIGIBLE_FOR_HUMAN_PROMOTION_REVIEW"
    return {
        "benchmark_id": run.get("benchmark_id"),
        "decision": decision,
        "production_promoted": False,
        "summary": summary,
        "scenario_coverage": {
            "required": len(scenario_specs),
            "represented": len(set(scenario_specs) & represented_scenarios),
            "missing": missing_scenarios,
            "unknown": unknown_scenarios,
        },
        "wing_count_error_rate": wing_rate,
        "findings": findings,
    }
