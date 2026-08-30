from copy import deepcopy

from voxie_os.benchmark import evaluate
from voxie_os.core import load_data, validate


SUITE_PATH = "workflows/voxie-model-benchmark-v01.yaml"


def _complete_run(suite):
    values = {
        "identity_drift": 0.05,
        "composition_drift": 0.04,
        "keyframe_error_frames": 1,
        "wing_count_error": 0,
        "face_error": 0.02,
        "runtime_s": 10.0,
        "peak_memory_gb": 8.0,
    }
    samples = []
    for index, scenario in enumerate(suite["scenarios"], start=1):
        samples.append(
            {
                "sample_id": f"S{index}",
                "scenario_id": scenario["scenario_id"],
                "seed": scenario["seed"],
                "accepted": True,
                "duration_s": scenario["duration_s"],
                "cost_usd": 0,
                "metrics": {
                    metric: values[metric]
                    for metric in scenario["required_metrics"]
                },
                "output": {"sha256": f"{index:x}" * 64},
            }
        )
    return {
        "benchmark_id": "SUITE-CONTRACT-FIXTURE",
        "model": {"name": "fixture", "revision": "v1"},
        "execution": {
            "adapter": "fixture",
            "hardware": {"gpu": "none"},
            "started_at": "2026-08-30T00:00:00Z",
        },
        "samples": samples,
    }


def test_suite_schema_requires_required_metrics_contract():
    suite = load_data(SUITE_PATH)
    del suite["scenarios"][0]["required_metrics"]

    errors = validate("benchmark_suite", suite)

    assert any(
        error.startswith("scenarios.0:")
        and "required_metrics" in error
        for error in errors
    )


def test_suite_schema_rejects_misspelled_required_metric():
    suite = load_data(SUITE_PATH)
    suite["scenarios"][0]["required_metrics"][0] = "identity_driftt"

    errors = validate("benchmark_suite", suite)

    assert any(
        error.startswith("scenarios.0.required_metrics.0:")
        for error in errors
    )


def test_evaluator_rejects_missing_metric_contract_even_without_schema_gate():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    del suite["scenarios"][0]["required_metrics"]

    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert result["production_promoted"] is False
    assert any(
        finding["metric"] == "scenario_required_metrics"
        and finding["scenario_id"] == suite["scenarios"][0]["scenario_id"]
        for finding in result["findings"]
    )


def test_evaluator_rejects_empty_or_duplicate_metric_contracts():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)

    empty_suite = deepcopy(suite)
    empty_suite["scenarios"][0]["required_metrics"] = []
    duplicate_suite = deepcopy(suite)
    duplicate_suite["scenarios"][0]["required_metrics"].append(
        duplicate_suite["scenarios"][0]["required_metrics"][0]
    )

    assert any(
        finding["metric"] == "scenario_required_metrics"
        for finding in evaluate(run, empty_suite)["findings"]
    )
    assert any(
        finding["metric"] == "scenario_required_metrics"
        for finding in evaluate(run, duplicate_suite)["findings"]
    )


def test_sample_seed_must_match_suite_fixed_seed():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    scenario = suite["scenarios"][0]
    run["samples"][0]["seed"] = scenario["seed"] + 1

    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert result["production_promoted"] is False
    finding = next(
        item for item in result["findings"]
        if item["metric"] == "scenario_seed"
    )
    assert finding["scenario_id"] == scenario["scenario_id"]
    assert finding["sample_id"] == "S1"
    assert finding["expected_seed"] == {
        "value": scenario["seed"],
        "capped": False,
    }


def test_schema_valid_integral_float_seed_matches_fixed_seed():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    scenario = suite["scenarios"][0]
    run["samples"][0]["seed"] = float(scenario["seed"])

    result = evaluate(run, suite)

    assert result["decision"] == "ELIGIBLE_FOR_HUMAN_PROMOTION_REVIEW"
    assert not any(finding["metric"] == "scenario_seed" for finding in result["findings"])


def test_decimal_policy_boundary_uses_authored_value_semantics():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    for sample, value in zip(run["samples"], [0.1, 0.2, 0.15, 0.15, 0.15]):
        sample["metrics"]["identity_drift"] = value

    result = evaluate(run, suite)

    assert result["summary"]["avg_identity_drift"] == 0.15
    assert not any(finding["metric"] == "avg_identity_drift" for finding in result["findings"])


def test_duplicate_fixed_seed_scenario_samples_cannot_pad_acceptance_rate():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    for sample in run["samples"][1:]:
        sample["accepted"] = False

    passing = run["samples"][0]
    for index in range(15):
        duplicate = deepcopy(passing)
        duplicate["sample_id"] = f"DUP{index + 1:02d}"
        duplicate["output"]["sha256"] = f"{index + 10:064x}"
        run["samples"].append(duplicate)

    result = evaluate(run, suite)

    assert result["summary"]["acceptance_rate"] == 0.8
    assert result["decision"] == "REJECT"
    assert result["production_promoted"] is False
    finding = next(
        item for item in result["findings"]
        if item["metric"] == "scenario_sample_uniqueness"
    )
    assert finding["scenario_ids"] == [passing["scenario_id"]]


def test_complete_run_still_requires_human_promotion_review():
    suite = load_data(SUITE_PATH)
    result = evaluate(_complete_run(suite), suite)

    assert result["decision"] == "ELIGIBLE_FOR_HUMAN_PROMOTION_REVIEW"
    assert result["production_promoted"] is False
    assert result["findings"] == []
