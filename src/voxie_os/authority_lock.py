from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .core import ROOT, load_data, sha256_file, validate


LOCK_SCHEMA_PATH = ROOT / "schemas/authority_lock.schema.json"
DEFAULT_LOCK_ID = "VOS-AUTHORITY-CONTENT-LOCK-V01"


def authority_lock_schema() -> dict[str, Any]:
    return json.loads(LOCK_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_authority_lock_schema(lock: Any) -> list[str]:
    validator = Draft202012Validator(authority_lock_schema())
    errors = []
    for error in sorted(validator.iter_errors(lock), key=lambda item: list(item.path)):
        where = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{where}: {error.message}")
    return errors


def _resolve_repository_file(
    repo_root: Path, relative_path: str
) -> tuple[Path | None, str | None]:
    root = repo_root.resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None, f"referenced path must stay within repository: {relative_path}"
    if not target.is_file():
        return None, f"referenced repository file does not exist: {relative_path}"
    return target, None


def _relative_repository_path(repo_root: Path, path: str | Path) -> str:
    root = repo_root.resolve()
    target = Path(path).resolve()
    try:
        return target.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"index path must stay within repository: {path}") from exc


def build_authority_lock(
    index: dict[str, Any],
    *,
    index_path: str | Path,
    repo_root: str | Path = ROOT,
    lock_id: str = DEFAULT_LOCK_ID,
) -> dict[str, Any]:
    """Build a deterministic SHA-256 lock for the current authority set."""
    root = Path(repo_root)
    index_errors = validate("authority_index", index)
    if index_errors:
        raise ValueError("invalid authority index: " + "; ".join(index_errors))

    index_relative = _relative_repository_path(root, index_path)
    index_file, index_error = _resolve_repository_file(root, index_relative)
    if index_error or index_file is None:
        raise ValueError(index_error or "index file unavailable")

    entries = []
    for authority in sorted(index["entries"], key=lambda item: item["authority_id"]):
        authority_file, authority_error = _resolve_repository_file(root, authority["path"])
        if authority_error or authority_file is None:
            raise ValueError(authority_error or f"authority unavailable: {authority['path']}")
        entries.append(
            {
                "authority_id": authority["authority_id"],
                "path": authority["path"],
                "sha256": sha256_file(authority_file),
            }
        )

    lock = {
        "lock_version": "1.0",
        "lock_id": lock_id,
        "record_type": "authority_lock",
        "index_id": index["index_id"],
        "index_path": index_relative,
        "index_sha256": sha256_file(index_file),
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
    }
    schema_errors = validate_authority_lock_schema(lock)
    if schema_errors:
        raise ValueError("generated invalid authority lock: " + "; ".join(schema_errors))
    return lock


def verify_authority_lock(
    index: dict[str, Any],
    lock: Any,
    *,
    index_path: str | Path,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Verify lock shape, index identity, entry coverage, and current bytes."""
    root = Path(repo_root)
    findings: list[dict[str, Any]] = []

    def add(
        rule_id: str,
        message: str,
        *,
        authority_id: str | None = None,
        path: str | None = None,
    ) -> None:
        findings.append(
            {
                "severity": "error",
                "rule_id": rule_id,
                "authority_id": authority_id,
                "path": path,
                "message": message,
            }
        )

    index_errors = validate("authority_index", index)
    for error in index_errors:
        add("AUTHORITY_INDEX_INVALID", error)

    schema_errors = validate_authority_lock_schema(lock)
    for error in schema_errors:
        add("AUTHORITY_LOCK_SCHEMA_INVALID", error)

    if schema_errors or not isinstance(lock, dict):
        return {
            "audit_version": "1.0",
            "status": "FAIL",
            "lock_id": lock.get("lock_id") if isinstance(lock, dict) else None,
            "index_id": index.get("index_id") if isinstance(index, dict) else None,
            "counts": {
                "expected": len(index.get("entries", [])) if isinstance(index, dict) else 0,
                "locked": 0,
                "verified": 0,
                "findings": len(findings),
            },
            "findings": findings,
        }

    try:
        index_relative = _relative_repository_path(root, index_path)
    except ValueError as exc:
        index_relative = None
        add("INDEX_PATH_OUTSIDE_REPOSITORY", str(exc))

    if index_relative is not None and lock["index_path"] != index_relative:
        add(
            "INDEX_PATH_MISMATCH",
            f"lock index path {lock['index_path']} does not match {index_relative}",
            path=lock["index_path"],
        )
    if lock["index_id"] != index.get("index_id"):
        add(
            "INDEX_ID_MISMATCH",
            f"lock index ID {lock['index_id']} does not match {index.get('index_id')}",
        )

    if index_relative is not None:
        index_file, index_file_error = _resolve_repository_file(root, index_relative)
        if index_file_error or index_file is None:
            add("INDEX_FILE_UNAVAILABLE", index_file_error or "index file unavailable")
        else:
            actual_index_sha = sha256_file(index_file)
            if lock["index_sha256"] != actual_index_sha:
                add(
                    "INDEX_SHA256_MISMATCH",
                    f"expected {lock['index_sha256']}, got {actual_index_sha}",
                    path=index_relative,
                )

    lock_entries = lock["entries"]
    if lock["entry_count"] != len(lock_entries):
        add(
            "ENTRY_COUNT_MISMATCH",
            f"entry_count is {lock['entry_count']} but entries contains {len(lock_entries)}",
        )

    authority_ids = [entry["authority_id"] for entry in lock_entries]
    paths = [entry["path"] for entry in lock_entries]
    if len(authority_ids) != len(set(authority_ids)):
        add("DUPLICATE_AUTHORITY_ID", "lock authority IDs must be unique")
    if len(paths) != len(set(paths)):
        add("DUPLICATE_AUTHORITY_PATH", "lock authority paths must be unique")
    if authority_ids != sorted(authority_ids):
        add("NONDETERMINISTIC_ENTRY_ORDER", "lock entries must be sorted by authority_id")

    expected = {
        entry["authority_id"]: entry["path"]
        for entry in index.get("entries", [])
    }
    locked = {
        entry["authority_id"]: entry
        for entry in lock_entries
    }

    for authority_id in sorted(set(expected) - set(locked)):
        add(
            "AUTHORITY_MISSING_FROM_LOCK",
            "current authority is not present in the lock",
            authority_id=authority_id,
            path=expected[authority_id],
        )
    for authority_id in sorted(set(locked) - set(expected)):
        add(
            "UNEXPECTED_AUTHORITY_IN_LOCK",
            "lock contains an authority that is not current in the index",
            authority_id=authority_id,
            path=locked[authority_id]["path"],
        )

    verified = 0
    for authority_id in sorted(set(expected) & set(locked)):
        expected_path = expected[authority_id]
        entry = locked[authority_id]
        if entry["path"] != expected_path:
            add(
                "AUTHORITY_PATH_MISMATCH",
                f"expected {expected_path}, got {entry['path']}",
                authority_id=authority_id,
                path=entry["path"],
            )
            continue

        authority_file, authority_error = _resolve_repository_file(root, expected_path)
        if authority_error or authority_file is None:
            add(
                "AUTHORITY_FILE_UNAVAILABLE",
                authority_error or "authority file unavailable",
                authority_id=authority_id,
                path=expected_path,
            )
            continue

        actual_sha = sha256_file(authority_file)
        if entry["sha256"] != actual_sha:
            add(
                "AUTHORITY_SHA256_MISMATCH",
                f"expected {entry['sha256']}, got {actual_sha}",
                authority_id=authority_id,
                path=expected_path,
            )
            continue
        verified += 1

    return {
        "audit_version": "1.0",
        "status": "FAIL" if findings else "PASS",
        "lock_id": lock["lock_id"],
        "index_id": index.get("index_id"),
        "counts": {
            "expected": len(expected),
            "locked": len(lock_entries),
            "verified": verified,
            "findings": len(findings),
        },
        "findings": findings,
    }


def load_and_build_authority_lock(
    index_path: str | Path,
    *,
    repo_root: str | Path = ROOT,
    lock_id: str = DEFAULT_LOCK_ID,
) -> dict[str, Any]:
    return build_authority_lock(
        load_data(index_path),
        index_path=index_path,
        repo_root=repo_root,
        lock_id=lock_id,
    )
