from pathlib import Path
from voxie_os.core import load_data, validate
from voxie_os.qc import run_manifest_qc
from voxie_os.timeline import to_neutral_timeline

ROOT = Path(__file__).resolve().parents[1]


def test_examples_validate():
    assert validate("canon", load_data(ROOT / "examples/canon.voxie.v1.yaml")) == []
    assert validate("beatmap", load_data(ROOT / "examples/beatmap.example.json")) == []
    assert validate("shot_manifest", load_data(ROOT / "examples/shot_manifest.example.yaml")) == []
    assert validate("benchmark", load_data(ROOT / "examples/benchmark.example.json")) == []


def test_qc_passes_example():
    canon = load_data(ROOT / "examples/canon.voxie.v1.yaml")
    manifest = load_data(ROOT / "examples/shot_manifest.example.yaml")
    assert run_manifest_qc(canon, manifest)["status"] == "PASS"


def test_timeline_duration():
    manifest = load_data(ROOT / "examples/shot_manifest.example.yaml")
    timeline = to_neutral_timeline(manifest)
    assert timeline["duration_s"] == 5.0
