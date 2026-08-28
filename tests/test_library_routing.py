import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from voxie_os.cli import main
from voxie_os.core import SCHEMA_FILES, load_data, validate
from voxie_os.fixtures import MAX_FIXTURE_BYTES, POLICY_PATH, validate_fixtures

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/library-routing.v2.yaml"


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
    assert result.returncode in {0, 1}, result.stderr
    return result.returncode == 0


def test_small_media_fixtures_are_not_ignored():
    assert not _is_ignored("tests/fixtures/tone.wav")
    assert not _is_ignored("examples/fixtures/tone.wav")
    assert _is_ignored("media/production-master.wav")


def test_library_routing_rejects_stale_integer_valued_float():
    manifest = load_data(MANIFEST)
    manifest["current_intake_status"]["unresolved_count"] = 2.0
    assert any("expected 1" in error for error in validate("library_routing", manifest))


@pytest.mark.parametrize("path", [
    "tests/fixtures/production-master.wav",
    "tests/fixtures/nested/master.mp4",
    "examples/fixtures/master.zip",
    "tests/fixtures/.env",
])
def test_unlisted_fixture_media_and_secrets_stay_ignored(path):
    assert _is_ignored(path)


def test_original_routing_manifest_is_preserved():
    original = subprocess.check_output(
        ["git", "show", "origin/main:manifests/library-routing.v1.yaml"], cwd=ROOT,
    )
    current = (ROOT / "manifests/library-routing.v1.yaml").read_bytes().replace(b"\r\n", b"\n")
    assert current == original


def test_new_manifest_has_string_date_and_exact_predecessor():
    manifest = load_data(MANIFEST)
    assert manifest["updated"] == "2026-08-27"
    original = subprocess.check_output(
        ["git", "show", ":manifests/library-routing.v1.yaml"], cwd=ROOT,
    )
    assert manifest["supersedes"] == {
        "version": 1,
        "manifest": "manifests/library-routing.v1.yaml",
        "sha256": hashlib.sha256(original).hexdigest(),
    }
    previous = load_data(ROOT / "manifests/library-routing.v1.yaml")
    for field in ("library_routes", "holding_areas", "classification_rules", "current_intake_status"):
        assert manifest[field] == previous[field]


@pytest.mark.parametrize("count,items", [(0, []), (1.0, ["pending.png"]), (2, ["a.png", "b.png"])])
def test_matching_intake_counts_validate(count, items):
    manifest = load_data(MANIFEST)
    manifest["current_intake_status"].update(unresolved_count=count, unresolved=items)
    assert validate("library_routing", manifest) == []


@pytest.mark.parametrize("field,value", [
    ("current_intake_status", None),
    ("library_routes", {}),
    ("holding_areas", {"unsorted": "relative/path"}),
    ("supersedes", {"version": 2, "manifest": "manifests/library-routing.v2.yaml", "sha256": "a" * 64}),
    ("updated", "not-a-date"),
])
def test_invalid_manifest_structure_or_lineage_is_rejected(field, value):
    manifest = load_data(MANIFEST)
    manifest[field] = value
    assert validate("library_routing", manifest)


def test_cli_rejects_stale_count(monkeypatch, capsys, tmp_path):
    manifest = load_data(MANIFEST)
    manifest["current_intake_status"]["unresolved_count"] = 0
    path = tmp_path / "invalid-routing.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["voxie-os", "validate", "library_routing", str(path)])
    assert main() == 1
    assert "expected 1" in capsys.readouterr().out


def test_cli_choices_follow_schema_registry(monkeypatch, capsys):
    monkeypatch.setitem(SCHEMA_FILES, "test_registry_alias", "library_routing.schema.json")
    monkeypatch.setattr(sys, "argv", ["voxie-os", "validate", "test_registry_alias", str(MANIFEST)])
    assert main() == 0
    assert capsys.readouterr().out == "PASS\n"


def _git(root, *args, input=None):
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args], cwd=root, input=input,
        check=True, capture_output=True,
    ).stdout


@pytest.fixture
def fixture_repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "config").mkdir()
    shutil.copyfile(ROOT / POLICY_PATH, tmp_path / POLICY_PATH)
    shutil.copyfile(ROOT / ".gitignore", tmp_path / ".gitignore")
    _git(tmp_path, "add", ".gitignore", POLICY_PATH)
    return tmp_path


def _stage_blob(root, path, size, force=False):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x" * size)
    _git(root, "add", *(["--force"] if force else []), "--", path)
    return target


@pytest.mark.parametrize("path", ["tests/fixtures/tone.wav", "examples/fixtures/tone.wav"])
@pytest.mark.parametrize("size", [0, MAX_FIXTURE_BYTES])
def test_allowlisted_fixtures_at_size_boundary_pass(fixture_repo, path, size):
    _stage_blob(fixture_repo, path, size)
    assert validate_fixtures(fixture_repo) == []


def test_oversized_staged_fixture_cannot_be_hidden_by_working_copy(fixture_repo):
    target = _stage_blob(fixture_repo, "tests/fixtures/tone.wav", MAX_FIXTURE_BYTES + 1)
    target.write_bytes(b"small working copy")
    # An unstaged, weakened policy must not affect validation either.
    policy = json.loads((fixture_repo / POLICY_PATH).read_text(encoding="utf-8"))
    policy["max_fixture_bytes"] = MAX_FIXTURE_BYTES * 100
    (fixture_repo / POLICY_PATH).write_text(json.dumps(policy), encoding="utf-8")
    errors = validate_fixtures(fixture_repo)
    assert errors == [f"tests/fixtures/tone.wav: staged fixture is {MAX_FIXTURE_BYTES + 1} bytes; limit is {MAX_FIXTURE_BYTES}"]


@pytest.mark.parametrize("path", [
    "tests/fixtures/master.wav", "examples/fixtures/nested/master.mp4",
    "media/production-master.wav", "productions/master.WAV", "media/master.png",
])
def test_force_added_unlisted_media_is_rejected(fixture_repo, path):
    _stage_blob(fixture_repo, path, 1, force=True)
    assert validate_fixtures(fixture_repo) == [f"{path}: tracked media is not an approved fixture"]


def test_fixture_symlink_is_rejected_without_following_target(fixture_repo):
    oid = _git(fixture_repo, "hash-object", "-w", "--stdin", input=b"../../outside.wav").decode().strip()
    _git(fixture_repo, "update-index", "--add", "--cacheinfo", f"120000,{oid},tests/fixtures/tone.wav")
    assert "regular file" in validate_fixtures(fixture_repo)[0]


@pytest.mark.parametrize("field,value", [
    ("max_fixture_bytes", MAX_FIXTURE_BYTES + 1), ("max_fixture_bytes", True),
    ("allowed_paths", ["tests/fixtures/**"]),
    ("allowed_paths", ["tests/fixtures/../../master.wav"]),
    ("allowed_paths", ["tests/fixtures/.env"]),
])
def test_invalid_fixture_policy_fails_closed(fixture_repo, field, value):
    policy = json.loads((fixture_repo / POLICY_PATH).read_text(encoding="utf-8"))
    policy[field] = value
    (fixture_repo / POLICY_PATH).write_text(json.dumps(policy), encoding="utf-8")
    _git(fixture_repo, "add", POLICY_PATH)
    assert validate_fixtures(fixture_repo)


@pytest.mark.parametrize("oversized", [False, True])
def test_fixture_check_cli_exit_code(fixture_repo, monkeypatch, capsys, oversized):
    _stage_blob(fixture_repo, "tests/fixtures/tone.wav", MAX_FIXTURE_BYTES + int(oversized))
    monkeypatch.setattr(sys, "argv", ["voxie-os", "fixtures-check", "--repo", str(fixture_repo)])
    assert main() == int(oversized)
    assert capsys.readouterr().out.startswith("FAIL" if oversized else "PASS")
