import subprocess
from pathlib import Path, PurePosixPath

from voxie_os.fixtures import validate_fixtures


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DIRECTORIES = (
    "config",
    "schemas",
    "src",
    "tests",
    "examples",
    "manifests",
    "workflows",
    "handoff",
    "docs",
)
MANIFEST_GROUPS = ("assets", "productions", "distribution")


def test_repository_uses_canonical_top_level_layout():
    assert all((ROOT / name).is_dir() for name in CANONICAL_DIRECTORIES)
    assert not (ROOT / "productions").exists()


def test_git_index_cannot_restore_root_productions_tree():
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT,
    ).decode("utf-8").split("\0")

    assert not any(
        PurePosixPath(path).parts[:1] == ("productions",)
        for path in tracked
        if path
    )


def test_manifest_groups_are_explicit():
    assert all(
        (ROOT / "manifests" / name).is_dir()
        and (ROOT / "manifests" / name / "README.md").is_file()
        for name in MANIFEST_GROUPS
    )


def test_tracked_media_matches_fixture_policy():
    assert validate_fixtures(ROOT) == []
