from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from voxie_os.authority_lock import (
    authority_lock_schema,
    build_authority_lock,
    verify_authority_lock,
)
from voxie_os.core import load_data, sha256_file


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "manifests/control/authority-index-v01.yaml"


def _index():
    return deepcopy(load_data(INDEX_PATH))


def _lock():
    return build_authority_lock(_index(), index_path=INDEX_PATH)


def test_authority_lock_schema_is_valid():
    Draft202012Validator.check_schema(authority_lock_schema())


def test_builder_is_deterministic_and_complete():
    first = _lock()
    second = _lock()

    assert first == second
    assert first["algorithm"] == "sha256"
    assert first["index_sha256"] == sha256_file(INDEX_PATH)
    assert first["entry_count"] == 18
    assert len(first["entries"]) == 18
    assert [entry["authority_id"] for entry in first["entries"]] == sorted(
        entry["authority_id"] for entry in first["entries"]
    )


def test_generated_lock_verifies():
    report = verify_authority_lock(_index(), _lock(), index_path=INDEX_PATH)

    assert report["status"] == "PASS"
    assert report["counts"] == {
        "expected": 18,
        "locked": 18,
        "verified": 18,
        "findings": 0,
    }
    assert report["findings"] == []


def test_authority_hash_mismatch_fails():
    lock = _lock()
    lock["entries"][0]["sha256"] = "0" * 64

    report = verify_authority_lock(_index(), lock, index_path=INDEX_PATH)

    assert report["status"] == "FAIL"
    assert report["counts"]["verified"] == 17
    assert report["findings"][0]["rule_id"] == "AUTHORITY_SHA256_MISMATCH"


def test_index_hash_mismatch_fails():
    lock = _lock()
    lock["index_sha256"] = "0" * 64

    report = verify_authority_lock(_index(), lock, index_path=INDEX_PATH)

    assert report["status"] == "FAIL"
    assert report["findings"][0]["rule_id"] == "INDEX_SHA256_MISMATCH"
