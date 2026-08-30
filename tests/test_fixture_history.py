import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from voxie_os.cli import main
from voxie_os.fixtures import MAX_FIXTURE_BYTES, POLICY_PATH, validate_fixtures


ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str, input: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args],
        cwd=root,
        input=input,
        check=True,
        capture_output=True,
    ).stdout


@pytest.fixture
def history_repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "Fixture Test")
    _git(tmp_path, "config", "user.email", "fixture@example.invalid")
    (tmp_path / "config").mkdir()
    shutil.copyfile(ROOT / POLICY_PATH, tmp_path / POLICY_PATH)
    shutil.copyfile(ROOT / ".gitignore", tmp_path / ".gitignore")
    _git(tmp_path, "add", ".gitignore", POLICY_PATH)
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").decode().strip()


def _commit_media(root: Path, path: str, size: int, *, force: bool = False) -> Path:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x" * size)
    args = ["add"]
    if force:
        args.append("--force")
    args.extend(["--", path])
    _git(root, *args)
    _git(root, "commit", "-q", "-m", f"add {path}")
    return target


def _delete_and_commit(root: Path, target: Path) -> None:
    target.unlink()
    _git(root, "add", "-u")
    _git(root, "commit", "-q", "-m", f"delete {target.name}")


def test_add_then_delete_unapproved_media_is_rejected(history_repo):
    base = _head(history_repo)
    target = _commit_media(
        history_repo,
        "media/temporary-master.mp4",
        1,
        force=True,
    )
    _delete_and_commit(history_repo, target)

    assert validate_fixtures(
        history_repo,
        base=base,
        head="HEAD",
    ) == [
        "media/temporary-master.mp4: introduced-history media is not an approved fixture"
    ]


def test_new_media_path_reusing_base_blob_is_rejected(history_repo):
    seed = history_repo / "seed.txt"
    seed.write_bytes(b"same-content")
    _git(history_repo, "add", "seed.txt")
    _git(history_repo, "commit", "-q", "-m", "add reusable base blob")
    base = _head(history_repo)

    target = history_repo / "media/reused-master.mp4"
    target.parent.mkdir(parents=True)
    target.write_bytes(seed.read_bytes())
    _git(history_repo, "add", "--force", "--", "media/reused-master.mp4")
    _git(history_repo, "commit", "-q", "-m", "reuse base blob at prohibited path")
    _delete_and_commit(history_repo, target)

    base_oid = _git(history_repo, "rev-parse", f"{base}:seed.txt").decode().strip()
    introduced_oid = _git(
        history_repo,
        "rev-parse",
        "HEAD^:media/reused-master.mp4",
    ).decode().strip()
    assert introduced_oid == base_oid
    assert validate_fixtures(history_repo, base=base, head="HEAD") == [
        "media/reused-master.mp4: introduced-history media is not an approved fixture"
    ]


def test_add_then_delete_small_allowlisted_fixture_passes(history_repo):
    base = _head(history_repo)
    target = _commit_media(history_repo, "tests/fixtures/tone.wav", 1)
    _delete_and_commit(history_repo, target)

    assert validate_fixtures(history_repo, base=base, head="HEAD") == []


def test_add_then_delete_oversized_allowlisted_fixture_is_rejected(history_repo):
    base = _head(history_repo)
    target = _commit_media(
        history_repo,
        "tests/fixtures/tone.wav",
        MAX_FIXTURE_BYTES + 1,
    )
    _delete_and_commit(history_repo, target)

    assert validate_fixtures(history_repo, base=base, head="HEAD") == [
        "tests/fixtures/tone.wav: introduced-history fixture is "
        f"{MAX_FIXTURE_BYTES + 1} bytes; limit is {MAX_FIXTURE_BYTES}"
    ]


def test_current_index_check_remains_active_when_history_check_is_enabled(history_repo):
    base = _head(history_repo)
    target = history_repo / "media/current-master.wav"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"x")
    _git(history_repo, "add", "--force", "--", "media/current-master.wav")

    assert validate_fixtures(history_repo, base=base, head="HEAD") == [
        "media/current-master.wav: tracked media is not an approved fixture"
    ]


def test_invalid_revision_range_fails_closed(history_repo):
    assert validate_fixtures(
        history_repo,
        base="missing-base",
        head="HEAD",
    ) == [
        "fixtures: unable to inspect introduced Git history missing-base..HEAD"
    ]


def test_fixture_check_cli_inspects_introduced_history(
    history_repo,
    monkeypatch,
    capsys,
):
    base = _head(history_repo)
    target = _commit_media(
        history_repo,
        "media/temporary-master.wav",
        1,
        force=True,
    )
    _delete_and_commit(history_repo, target)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "voxie-os",
            "fixtures-check",
            "--repo",
            str(history_repo),
            "--base",
            base,
            "--head",
            "HEAD",
        ],
    )

    assert main() == 1
    output = capsys.readouterr().out
    assert output.startswith("FAIL\n")
    assert "introduced-history media is not an approved fixture" in output
