from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from voxie_os.core import SCHEMA_FILES, load_data, schema_for, validate


ROOT = Path(__file__).resolve().parents[1]
READINESS_PATHS = [
    ROOT / "manifests/distribution/big-surprise/release-readiness-v01.yaml",
    ROOT / "manifests/distribution/freeze-dance/release-readiness-v01.yaml",
    ROOT / "manifests/distribution/colorful-day/release-readiness-v01.yaml",
]


def _record():
    return deepcopy(load_data(READINESS_PATHS[0]))


def test_release_readiness_schema_is_registered_and_valid():
    assert SCHEMA_FILES["release_readiness"] == "release_readiness.schema.json"
    Draft202012Validator.check_schema(schema_for("release_readiness"))


def test_all_controlled_release_records_validate():
    for path in READINESS_PATHS:
        assert validate("release_readiness", load_data(path)) == []


def test_unresolved_release_gate_cannot_authorize_execution_or_platform_actions():
    record = _record()
    gate = record["release_gate"]
    gate["execution_authority"] = "AUTHORIZED"
    gate["publication_authorized"] = True
    gate["scheduling_authorized"] = True
    gate["account_write_authorized"] = True
    record["platforms"][0]["upload_authorized"] = True
    record["platforms"][0]["publish_authorized"] = True

    errors = validate("release_readiness", record)

    assert any(error.startswith("release_gate.execution_authority:") for error in errors)
    assert any(error.startswith("release_gate.publication_authorized:") for error in errors)
    assert any(error.startswith("release_gate.scheduling_authorized:") for error in errors)
    assert any(error.startswith("release_gate.account_write_authorized:") for error in errors)
    assert any(error.startswith("platforms.0.upload_authorized:") for error in errors)
    assert any(error.startswith("platforms.0.publish_authorized:") for error in errors)


def test_every_blocker_requires_a_warning_or_error_finding():
    record = _record()
    record["findings"] = [
        finding
        for finding in record["findings"]
        if finding["rule_id"] != "PUBLICATION_NOT_AUTHORIZED"
    ]

    errors = validate("release_readiness", record)

    assert errors == [
        "release_gate.blockers: every blocker requires a warning or error finding; "
        "missing PUBLICATION_NOT_AUTHORIZED"
    ]


def test_referenced_repository_authority_must_exist():
    record = _record()
    record["master"]["manifest"] = "manifests/productions/missing/master.json"

    errors = validate("release_readiness", record)

    assert errors == [
        "master.manifest: referenced repository file does not exist: "
        "manifests/productions/missing/master.json"
    ]


def test_referenced_repository_authority_cannot_escape_checkout():
    record = _record()
    record["master"]["manifest"] = "manifests/../../etc/passwd"

    errors = validate("release_readiness", record)

    assert errors == [
        "master.manifest: referenced path must stay within repository: "
        "manifests/../../etc/passwd"
    ]


def test_platform_names_must_be_unique():
    record = _record()
    record["platforms"][1]["platform"] = "youtube"

    assert validate("release_readiness", record) == [
        "platforms: platform names must be unique"
    ]


def test_released_state_requires_root_and_platform_publication_authority():
    record = _record()
    record["status"] = "RELEASED"
    record["release_gate"]["required_approvals"] = []
    record["release_gate"]["blockers"] = []

    errors = validate("release_readiness", record)

    assert errors == [
        "release_gate.publication_authorized: must be true when status is RELEASED",
        "platforms: at least one platform must be publish-authorized when status is RELEASED",
    ]
