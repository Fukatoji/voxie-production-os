import json
import sys
from copy import deepcopy

from voxie_os.benchmark import evaluate
from voxie_os.cli import main
from voxie_os.core import load_data, validate


SUITE_PATH = "workflows/voxie-model-benchmark-v01.yaml"


def _complete_run(suite):
    samples = []
    values = {
        "identity_drift": 0.05,
        "composition_drift": 0.04,
        "keyframe_error_frames": 1,
        "wing_count_error": 0,
        "face_error": 0.02,
        "runtime_s": 10.0,
        "peak_memory_gb": 8.0,
    }
    for index, scenario in enumerate(suite["scenarios"], start=1):
        required_metrics = {
            metric: values[metric] for metric in scenario["required_metrics"]
        }
        samples.append(
            {
                "sample_id": f"S{index}",
                "scenario_id": scenario["scenario_id"],
                "seed": int(scenario["seed"]),
                "accepted": True,
                "duration_s": float(scenario["duration_s"]),
                "cost_usd": 0,
                "metrics": required_metrics,
                "output": {"sha256": f"{index:x}" * 64},
            }
        )
    return {
        "benchmark_id": "COMPLETE-FIXTURE",
        "model": {"name": "fixture", "revision": "v1"},
        "execution": {
            "adapter": "fixture",
            "hardware": {"gpu": "none"},
            "started_at": "2026-08-30T00:00:00Z",
        },
        "samples": samples,
    }


def test_benchmark_suite_and_example_validate():
    suite = load_data(SUITE_PATH)
    run = load_data("examples/benchmark.example.json")
    assert validate("benchmark_suite", suite) == []
    assert validate("benchmark", run) == []


def test_benchmark_rejects_canon_failures_and_incomplete_scenarios():
    suite = load_data(SUITE_PATH)
    run = load_data("examples/benchmark.example.json")
    result = evaluate(run, suite)
    assert result["decision"] == "REJECT"
    assert result["production_promoted"] is False
    assert result["wing_count_error_rate"] == 0.5
    assert result["scenario_coverage"]["missing"]
    assert result["scenario_coverage"]["unknown"] == ["FIRST-LAST"]


def test_complete_suite_run_is_eligible_only_for_human_review():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)

    assert validate("benchmark", run) == []
    result = evaluate(run, suite)

    assert result["decision"] == "ELIGIBLE_FOR_HUMAN_PROMOTION_REVIEW"
    assert result["production_promoted"] is False
    assert result["scenario_coverage"] == {
        "required": 5,
        "represented": 5,
        "missing": [],
        "unknown": [],
    }
    assert result["wing_count_error_rate"] == 0.0
    assert result["findings"] == []


def test_missing_suite_scenario_fails_closed():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    missing_id = run["samples"].pop()["scenario_id"]

    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert result["scenario_coverage"]["missing"] == [missing_id]
    assert any(
        finding["metric"] == "scenario_coverage"
        and missing_id in finding["message"]
        for finding in result["findings"]
    )


def test_unknown_scenario_fails_closed():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    original_id = run["samples"][0]["scenario_id"]
    run["samples"][0]["scenario_id"] = "UNKNOWN-SCENARIO"

    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert result["scenario_coverage"]["missing"] == [original_id]
    assert result["scenario_coverage"]["unknown"] == ["UNKNOWN-SCENARIO"]


def test_partially_missing_wing_metric_never_uses_subset_rate():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    del run["samples"][0]["metrics"]["wing_count_error"]

    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert result["wing_count_error_rate"] is None
    assert any(
        finding["metric"] == "sample_required_metric"
        and finding["required_metric"] == "wing_count_error"
        for finding in result["findings"]
    )
    assert any(
        finding["metric"] == "wing_count_error_rate"
        for finding in result["findings"]
    )


def test_each_scenario_requires_every_declared_metric():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    scenario = suite["scenarios"][0]
    metric = scenario["required_metrics"][0]
    del run["samples"][0]["metrics"][metric]

    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert any(
        finding.get("scenario_id") == scenario["scenario_id"]
        and finding.get("required_metric") == metric
        for finding in result["findings"]
    )


def test_promotion_policy_without_suite_contract_fails_closed():
    suite = load_data(SUITE_PATH)
    result = evaluate(_complete_run(suite), suite["promotion_policy"])

    assert result["decision"] == "REJECT"
    assert any(
        finding["metric"] == "benchmark_suite" for finding in result["findings"]
    )


def test_cli_passes_complete_suite_to_evaluator(monkeypatch, capsys, tmp_path):
    suite = load_data(SUITE_PATH)
    run_path = tmp_path / "complete-run.json"
    run_path.write_text(json.dumps(_complete_run(suite)), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["voxie-os", "benchmark-evaluate", str(run_path), SUITE_PATH],
    )

    assert main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["decision"] == "ELIGIBLE_FOR_HUMAN_PROMOTION_REVIEW"
    assert result["production_promoted"] is False


def test_cli_rejects_incomplete_example(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "voxie-os",
            "benchmark-evaluate",
            "examples/benchmark.example.json",
            SUITE_PATH,
        ],
    )

    assert main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["decision"] == "REJECT"
