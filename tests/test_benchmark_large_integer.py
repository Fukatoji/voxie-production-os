import json
import sys

from voxie_os.benchmark import evaluate
from voxie_os.core import load_data, save_json, validate


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
        "benchmark_id": "LARGE-INTEGER-FIXTURE",
        "model": {"name": "fixture", "revision": "v1"},
        "execution": {
            "adapter": "fixture",
            "hardware": {"gpu": "none"},
            "started_at": "2026-08-30T00:00:00Z",
        },
        "samples": samples,
    }


def test_arbitrarily_large_integer_metric_rejects_and_serializes(tmp_path):
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    huge = 10**10000
    run["samples"][0]["metrics"]["identity_drift"] = huge

    assert validate("benchmark", run) == []
    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert result["production_promoted"] is False
    assert result["summary"]["avg_identity_drift"] == sys.float_info.max
    assert "avg_identity_drift" in result["summary"]["overflowed_fields"]
    finding = next(
        item for item in result["findings"]
        if item["metric"] == "avg_identity_drift"
    )
    assert finding["actual"] == sys.float_info.max
    assert finding["actual_capped"] is True

    encoded = json.dumps(result)
    assert "REJECT" in encoded
    output = tmp_path / "result.json"
    save_json(output, result)
    assert json.loads(output.read_text(encoding="utf-8"))["decision"] == "REJECT"


def test_negative_arbitrarily_large_integer_metric_keeps_sign_and_serializes():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    run["samples"][0]["metrics"]["identity_drift"] = -(10**10000)

    result = evaluate(run, suite)

    assert result["summary"]["avg_identity_drift"] == -sys.float_info.max
    assert result["summary"]["overflowed_fields"] == ["avg_identity_drift"]
    json.dumps(result, allow_nan=False)


def test_rounded_down_value_above_max_float_is_reported_as_capped():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    just_over_max = int(sys.float_info.max) + 1
    for sample in run["samples"]:
        sample["metrics"]["identity_drift"] = just_over_max

    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert result["summary"]["avg_identity_drift"] == sys.float_info.max
    assert result["summary"]["overflowed_fields"] == ["avg_identity_drift"]
    finding = next(
        item for item in result["findings"]
        if item["metric"] == "avg_identity_drift"
    )
    assert finding["actual"] == sys.float_info.max
    assert finding["actual_capped"] is True
    json.dumps(result, allow_nan=False)


def test_arbitrarily_large_integer_wing_metric_rejects_and_serializes(tmp_path):
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    run["samples"][0]["metrics"]["wing_count_error"] = 10**10000

    assert validate("benchmark", run) == []
    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert result["wing_count_error_rate"] == 0.2
    assert any(
        finding["metric"] == "wing_count_error_rate"
        for finding in result["findings"]
    )
    encoded = json.dumps(result)
    assert "wing_count_error_rate" in encoded
    output = tmp_path / "wing-result.json"
    save_json(output, result)
    assert json.loads(output.read_text(encoding="utf-8"))[
        "wing_count_error_rate"
    ] == 0.2
