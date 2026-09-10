from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from voxie_os.authority_lock import (
    authority_lock_schema,
    build_authority_lock,
    verify_authority_lock,
)
from voxie_os.core import load_data, sha256_file


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "manifests/control/authority-index-v01.yaml"
INDEX_V02_PATH = ROOT / "manifests/control/authority-index-v02.yaml"


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


def test_builder_derives_v02_lock_id_without_override():
    index = deepcopy(load_data(INDEX_V02_PATH))

    lock = build_authority_lock(index, index_path=INDEX_V02_PATH)

    assert lock["lock_id"] == "VOS-AUTHORITY-CONTENT-LOCK-V02"
    assert lock["index_id"] == "VOS-AUTHORITY-INDEX-V02"


def test_builder_rejects_lock_id_from_another_index_version():
    index = deepcopy(load_data(INDEX_V02_PATH))

    with pytest.raises(ValueError, match="does not match index ID"):
        build_authority_lock(
            index,
            index_path=INDEX_V02_PATH,
            lock_id="VOS-AUTHORITY-CONTENT-LOCK-V01",
        )


def test_verifier_rejects_lock_and_index_version_mismatch():
    index = deepcopy(load_data(INDEX_V02_PATH))
    lock = build_authority_lock(index, index_path=INDEX_V02_PATH)
    lock["lock_id"] = "VOS-AUTHORITY-CONTENT-LOCK-V01"

    report = verify_authority_lock(index, lock, index_path=INDEX_V02_PATH)

    assert report["status"] == "FAIL"
    assert report["counts"]["verified"] == 19
    assert [finding["rule_id"] for finding in report["findings"]] == [
        "LOCK_INDEX_VERSION_MISMATCH"
    ]


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
