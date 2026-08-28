import subprocess
import sys
from pathlib import Path

from voxie_os.cli import main
from voxie_os.core import load_data, validate

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/library-routing.v1.yaml"


def test_library_routing_manifest_validates():
    assert validate("library_routing", load_data(MANIFEST)) == []


def test_library_routing_rejects_stale_unresolved_count():
    manifest = load_data(MANIFEST)
    manifest["current_intake_status"]["unresolved_count"] = 2
    assert validate("library_routing", manifest) == [
        "current_intake_status.unresolved_count: "
        "expected 1 to match unresolved items, got 2"
    ]


def test_cli_validates_library_routing(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["voxie-os", "validate", "library_routing", str(MANIFEST)],
    )
    assert main() == 0
    assert capsys.readouterr().out == "PASS\n"


def _is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", path],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def test_small_media_fixtures_are_not_ignored():
    assert not _is_ignored("tests/fixtures/tone.wav")
    assert not _is_ignored("examples/fixtures/tone.wav")
    assert _is_ignored("media/production-master.wav")
