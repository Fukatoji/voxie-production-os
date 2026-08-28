from pathlib import Path

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


def test_manifest_groups_are_explicit():
    assert all((ROOT / "manifests" / name).is_dir() for name in MANIFEST_GROUPS)


def test_tracked_media_matches_fixture_policy():
    assert validate_fixtures(ROOT) == []
