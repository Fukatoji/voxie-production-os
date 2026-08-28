from voxie_os.benchmark import evaluate
from voxie_os.core import load_data, validate


def test_benchmark_suite_and_example_validate():
    suite = load_data("workflows/voxie-model-benchmark-v01.yaml")
    run = load_data("examples/benchmark.example.json")
    assert validate("benchmark_suite", suite) == []
    assert validate("benchmark", run) == []


def test_benchmark_rejects_canon_failures():
    suite = load_data("workflows/voxie-model-benchmark-v01.yaml")
    run = load_data("examples/benchmark.example.json")
    result = evaluate(run, suite["promotion_policy"])
    assert result["decision"] == "REJECT"
    assert result["production_promoted"] is False
    assert result["wing_count_error_rate"] == 0.5
