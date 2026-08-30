from __future__ import annotations

import math
import sys
from fractions import Fraction
from typing import Any


KNOWN_METRICS = {
    "identity_drift",
    "composition_drift",
    "keyframe_error_frames",
    "wing_count_error",
    "face_error",
    "runtime_s",
    "peak_memory_gb",
}


def _measurement(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return True
    return math.isfinite(value)


def _as_fraction(value: int | float) -> Fraction:
    return Fraction(value) if isinstance(value, int) else Fraction.from_float(value)


def _exact_average(values: list[int | float]) -> Fraction | None:
    if not values:
        return None
    return sum((_as_fraction(value) for value in values), Fraction(0, 1)) / len(values)


def _json_safe_number(value: Fraction | None) -> tuple[int | float | None, bool]:
    """Return a finite JSON number and whether the exact value was capped.

    Python's JSON encoder can reject arbitrarily large integers because of the
    interpreter's integer-string digit limit. Values outside binary-float range
    are therefore capped at the largest finite float and explicitly marked in
    ``summary.overflowed_fields``. Exact Fractions remain internal for gate
    comparisons, so capping cannot turn a failure into a pass.
    """
    if value is None:
        return None, False
    try:
        numeric = float(value)
    except OverflowError:
        numeric = math.copysign(sys.float_info.max, value.numerator)
        return numeric, True
    if not math.isfinite(numeric):
        numeric = math.copysign(sys.float_info.max, numeric)
        return numeric, True
    return round(numeric, 4), False


def _summary_with_exact(
    run: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Fraction | None]]:
    samples = run.get("samples", [])
    accepted = [sample for sample in samples if sample.get("accepted")]
    metrics = [sample.get("metrics", {}) for sample in samples]

    exact: dict[str, Fraction | None] = {}
    summary: dict[str, Any] = {
        "samples": len(samples),
        "accepted": len(accepted),
        "acceptance_rate": round(len(accepted) / len(samples), 4) if samples else 0,
    }
    overflowed_fields: list[str] = []

    for output_field, metric_key in (
        ("avg_identity_drift", "identity_drift"),
        ("avg_composition_drift", "composition_drift"),
        ("avg_keyframe_error_frames", "keyframe_error_frames"),
    ):
        values = [
            metric[metric_key]
            for metric in metrics
            if _measurement(metric.get(metric_key))
        ]
        exact_value = _exact_average(values)
        display, overflowed = _json_safe_number(exact_value)
        exact[output_field] = exact_value
        summary[output_field] = display
        if overflowed:
            overflowed_fields.append(output_field)

    cost_values = [
        sample.get("cost_usd", 0)
        for sample in samples
        if _measurement(sample.get("cost_usd", 0))
    ]
    total_cost = sum(
        (_as_fraction(value) for value in cost_values),
        Fraction(0, 1),
    )
    total_cost_display, total_cost_overflowed = _json_safe_number(total_cost)
    summary["total_cost_usd"] = total_cost_display
    if total_cost_overflowed:
        overflowed_fields.append("total_cost_usd")

    accepted_duration_values = [
        sample.get("duration_s", 0)
        for sample in accepted
        if _measurement(sample.get("duration_s", 0))
    ]
    accepted_seconds = sum(
        (_as_fraction(value) for value in accepted_duration_values),
        Fraction(0, 1),
    )
    cost_per_second = total_cost / accepted_seconds if accepted_seconds > 0 else None
    cost_per_second_display, cost_per_second_overflowed = _json_safe_number(
        cost_per_second
    )
    summary["cost_per_accepted_second_usd"] = cost_per_second_display
    if cost_per_second_overflowed:
        overflowed_fields.append("cost_per_accepted_second_usd")

    summary["overflowed_fields"] = sorted(overflowed_fields)
    return summary, exact


def summarize(run: dict[str, Any]) -> dict[str, Any]:
    summary, _ = _summary_with_exact(run)
    return summary


def _safe_finding_number(value: int | float | None):
    if value is None or not _measurement(value):
        return None
    display, overflowed = _json_safe_number(_as_fraction(value))
    return {"value": display, "capped": overflowed}


def evaluate(run: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a complete benchmark run against the complete suite.

    Scenario coverage, fixed seeds, per-scenario required metrics, and promotion
    thresholds all fail closed. A model may become eligible for human review,
    but this function never promotes it into production.
    """
    summary, exact_averages = _summary_with_exact(run)
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
    scenario_metrics: dict[str, list[str]] = {}
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

        required_metrics = scenario.get("required_metrics")
        valid_contract = (
            isinstance(required_metrics, list)
            and bool(required_metrics)
            and len(required_metrics) == len(set(required_metrics))
            and all(metric in KNOWN_METRICS for metric in required_metrics)
        )
        if not valid_contract:
            findings.append(
                {
                    "severity": "error",
                    "metric": "scenario_required_metrics",
                    "scenario_id": scenario_id,
                    "message": (
                        f"{scenario_id} must declare a non-empty, unique list of "
                        "recognized required_metrics"
                    ),
                }
            )
            scenario_metrics[scenario_id] = []
        else:
            scenario_metrics[scenario_id] = list(required_metrics)

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
        sample_id = sample.get("sample_id", f"sample-{sample_index}")
        expected_seed = scenario.get("seed")
        if type(sample.get("seed")) is not int or sample.get("seed") != expected_seed:
            findings.append(
                {
                    "severity": "error",
                    "metric": "scenario_seed",
                    "sample_id": sample_id,
                    "scenario_id": scenario_id,
                    "expected_seed": _safe_finding_number(expected_seed),
                    "message": (
                        f"{scenario_id} sample seed does not match the suite's "
                        "fixed reproducibility seed"
                    ),
                }
            )

        metrics = sample.get("metrics", {})
        for metric in scenario_metrics.get(scenario_id, []):
            if not _measurement(metrics.get(metric)):
                findings.append(
                    {
                        "severity": "error",
                        "metric": "sample_required_metric",
                        "sample_id": sample_id,
                        "scenario_id": scenario_id,
                        "required_metric": metric,
                        "message": (
                            f"{scenario_id} sample is missing a finite numeric "
                            f"measurement for {metric}"
                        ),
                    }
                )

    acceptance_exact = (
        Fraction(sum(1 for sample in samples if sample.get("accepted")), len(samples))
        if samples
        else Fraction(0, 1)
    )
    gate_values: dict[str, Fraction | None] = {
        "acceptance_rate": acceptance_exact,
        "avg_identity_drift": exact_averages["avg_identity_drift"],
        "avg_composition_drift": exact_averages["avg_composition_drift"],
        "avg_keyframe_error_frames": exact_averages["avg_keyframe_error_frames"],
    }
    gate_specs = {
        "acceptance_rate": (policy.get("min_acceptance_rate"), "min"),
        "avg_identity_drift": (policy.get("max_identity_drift"), "max"),
        "avg_composition_drift": (policy.get("max_composition_drift"), "max"),
        "avg_keyframe_error_frames": (
            policy.get("max_keyframe_error_frames"),
            "max",
        ),
    }
    for metric, (threshold, direction) in gate_specs.items():
        if threshold is None:
            continue
        actual_exact = gate_values[metric]
        if actual_exact is None:
            findings.append(
                {
                    "severity": "error",
                    "metric": metric,
                    "message": "Required aggregate metric is missing",
                }
            )
            continue
        if not _measurement(threshold):
            findings.append(
                {
                    "severity": "error",
                    "metric": metric,
                    "message": "Promotion threshold is not a finite numeric value",
                }
            )
            continue
        threshold_exact = _as_fraction(threshold)
        failed = (
            actual_exact < threshold_exact
            if direction == "min"
            else actual_exact > threshold_exact
        )
        if failed:
            finding = {
                "severity": "error",
                "metric": metric,
                "actual": summary[metric],
                "threshold": _safe_finding_number(threshold),
                "message": f"{metric} failed the {direction}imum promotion gate",
            }
            if metric in summary["overflowed_fields"]:
                finding["actual_capped"] = True
            findings.append(finding)

    max_wing_rate = policy.get("max_wing_count_error_rate")
    wing_values: list[int | float] = []
    wing_metrics_complete = True
    for sample in samples:
        value = sample.get("metrics", {}).get("wing_count_error")
        if not _measurement(value):
            wing_metrics_complete = False
        else:
            wing_values.append(value)

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
        elif not _measurement(max_wing_rate):
            findings.append(
                {
                    "severity": "error",
                    "metric": "wing_count_error_rate",
                    "message": "Wing-error threshold is not a finite numeric value",
                }
            )
        elif _as_fraction(wing_rate) > _as_fraction(max_wing_rate):
            findings.append(
                {
                    "severity": "error",
                    "metric": "wing_count_error_rate",
                    "actual": wing_rate,
                    "threshold": _safe_finding_number(max_wing_rate),
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
