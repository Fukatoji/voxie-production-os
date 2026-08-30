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
        "benchmark_id": "LARGE-INTEGER-FIXTURE",
        "model": {"name": "fixture", "revision": "v1"},
        "execution": {
            "adapter": "fixture",
            "hardware": {"gpu": "none"},
            "started_at": "2026-08-30T00:00:00Z",
        },
        "samples": samples,
    }


def test_arbitrarily_large_integer_metric_rejects_without_overflow():
    suite = load_data(SUITE_PATH)
    run = _complete_run(suite)
    huge = 10**10000
    run["samples"][0]["metrics"]["identity_drift"] = huge

    assert validate("benchmark", run) == []
    result = evaluate(run, suite)

    assert result["decision"] == "REJECT"
    assert result["production_promoted"] is False
    assert isinstance(result["summary"]["avg_identity_drift"], int)
    assert result["summary"]["avg_identity_drift"] > suite["promotion_policy"][
        "max_identity_drift"
    ]
    assert any(
        finding["metric"] == "avg_identity_drift"
        for finding in result["findings"]
    )


def test_arbitrarily_large_integer_wing_metric_rejects_without_overflow():
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
