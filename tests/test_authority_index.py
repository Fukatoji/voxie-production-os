from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from voxie_os.core import SCHEMA_FILES, load_data, schema_for, validate


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "manifests/control/authority-index-v01.yaml"


def _index():
    return deepcopy(load_data(INDEX_PATH))


def test_authority_index_schema_is_registered_and_valid():
    assert SCHEMA_FILES["authority_index"] == "authority_index.schema.json"
    Draft202012Validator.check_schema(schema_for("authority_index"))
    assert validate("authority_index", _index()) == []


def test_index_contains_unique_current_control_authorities():
    index = _index()
    entries = index["entries"]

    assert index["status"] == "ACTIVE"
    assert index["policy"] == {
        "current_entries_only": True,
        "publication_requires_explicit_approval": True,
        "media_binaries_committed": False,
        "unknown_paths_fail_closed": True,
    }
    assert len(entries) == 18
    assert len({entry["authority_id"] for entry in entries}) == 18
    assert len({entry["path"] for entry in entries}) == 18
    assert all(entry["current"] is True for entry in entries)
    assert all(entry["publication_authorized"] is False for entry in entries)


def test_index_covers_priority_canon_production_distribution_and_workflows():
    paths = {entry["path"] for entry in _index()["entries"]}

    assert {
        "manifests/assets/voxie-canon-v1.0.magiclight.yaml",
        "manifests/characters/status-register-v01.yaml",
        "manifests/productions/big-surprise/beatmap-001.final.json",
        "manifests/productions/big-surprise/shot-manifest-v01.yaml",
        "manifests/distribution/big-surprise/release-readiness-v01.yaml",
        "manifests/productions/humpty-rolling-short-film/review-master-v01.json",
        "manifests/distribution/freeze-dance/release-readiness-v01.yaml",
        "manifests/distribution/colorful-day/release-readiness-v01.yaml",
        "manifests/productions/rainbow-colors/production-state-v04.yaml",
        "config/providers.v1.yaml",
        "workflows/voxie-model-benchmark-v01.yaml",
        "workflows/lyric-alignment-benchmark-v01.yaml",
        "workflows/big-surprise-multi-aligner-evaluation-v01.yaml",
    }.issubset(paths)
    assert all((ROOT / path).is_file() for path in paths)


def test_authority_ids_and_paths_must_be_unique():
    index = _index()
    index["entries"][1]["authority_id"] = index["entries"][0]["authority_id"]
    index["entries"][2]["path"] = index["entries"][0]["path"]
    index["entries"][2]["validation_kind"] = index["entries"][0][
        "validation_kind"
    ]

    errors = validate("authority_index", index)

    assert "entries: authority IDs must be unique" in errors
    assert "entries: authority paths must be unique" in errors


def test_current_only_policy_rejects_historical_entries():
    index = _index()
    index["entries"][0]["current"] = False

    assert validate("authority_index", index) == [
        "entries.0.current: must be true while policy.current_entries_only is true"
    ]


def test_authority_path_must_exist_inside_repository():
    index = _index()
    index["entries"][0]["path"] = "manifests/control/missing-authority.yaml"
    index["entries"][0]["validation_kind"] = None

    assert validate("authority_index", index) == [
        "entries.0.path: referenced repository file does not exist: "
        "manifests/control/missing-authority.yaml"
    ]


def test_authority_path_cannot_escape_repository():
    index = _index()
    index["entries"][0]["path"] = "manifests/../../etc/passwd"
    index["entries"][0]["validation_kind"] = None

    assert validate("authority_index", index) == [
        "entries.0.path: referenced path must stay within repository: "
        "manifests/../../etc/passwd"
    ]


def test_predecessor_cannot_equal_current_path():
    index = _index()
    entry = index["entries"][0]
    entry["predecessors"] = [entry["path"]]

    assert validate("authority_index", index) == [
        "entries.0.predecessors: cannot include the current path"
    ]


def test_predecessor_must_exist_inside_repository():
    index = _index()
    index["entries"][0]["predecessors"] = [
        "manifests/control/missing-predecessor.yaml"
    ]

    assert validate("authority_index", index) == [
        "entries.0.predecessors.0: referenced repository file does not exist: "
        "manifests/control/missing-predecessor.yaml"
    ]


def test_index_rejects_media_binary_paths():
    index = _index()
    index["entries"][0]["path"] = "manifests/control/authority.mp4"
    index["entries"][0]["validation_kind"] = None

    errors = validate("authority_index", index)

    assert "entries.0.path: authority index must reference control records, not media binaries" in errors
    assert any("authority.mp4" in error and "does not exist" in error for error in errors)


def test_publication_authority_requires_released_state():
    index = _index()
    index["entries"][0]["publication_authorized"] = True

    assert validate("authority_index", index) == [
        "entries.0.publication_authorized: requires authority_state RELEASED"
    ]


def test_nested_validation_kind_must_match_referenced_artifact():
    index = _index()
    index["entries"][0]["validation_kind"] = "asset"

    errors = validate("authority_index", index)

    assert any(
        error.startswith(
            "entries.0.validation_kind: manifests/library-routing.v2.yaml failed asset:"
        )
        for error in errors
    )
