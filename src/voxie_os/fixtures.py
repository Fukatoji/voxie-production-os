from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import subprocess

from .core import ROOT


POLICY_PATH = "config/media-fixtures.v1.json"
MAX_FIXTURE_BYTES = 64 * 1024
MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".wav", ".mp3", ".flac", ".zip",
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
}


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True,
    ).stdout


def _policy(root: Path):
    policy = json.loads(_git(root, "show", f":{POLICY_PATH}"))
    if not isinstance(policy, dict) or type(policy.get("version")) is not int or policy["version"] != 1:
        return None, None, None, ["fixtures: policy version must be 1"]

    maximum = policy.get("max_fixture_bytes")
    allowed = policy.get("allowed_paths")
    if type(maximum) is not int or not 0 < maximum <= MAX_FIXTURE_BYTES:
        return None, None, None, [
            f"fixtures: max_fixture_bytes must be an integer from 1 to {MAX_FIXTURE_BYTES}"
        ]
    if not isinstance(allowed, list) or not all(isinstance(path, str) for path in allowed):
        return None, None, None, [
            "fixtures: allowed_paths must be an array of exact repository paths"
        ]
    if len(allowed) != len(set(allowed)):
        return None, None, None, ["fixtures: duplicate allowed_paths"]

    for path in allowed:
        parts = PurePosixPath(path).parts
        if (
            len(parts) < 3
            or parts[:2] not in {
                ("tests", "fixtures"),
                ("examples", "fixtures"),
            }
            or PurePosixPath(path).as_posix() != path
            or ".." in parts
            or PurePosixPath(path).suffix.lower() not in MEDIA_EXTENSIONS
            or any(char in path for char in "*?[]\\")
        ):
            return None, None, None, [f"fixtures: invalid allowlist path {path!r}"]

    return policy, maximum, set(allowed), []


def _validate_blob(
    root: Path,
    *,
    path: str,
    oid: str,
    mode: str,
    maximum: int,
    allowed: set[str],
    context: str,
) -> list[str]:
    suffix = PurePosixPath(path).suffix.lower()
    if suffix not in MEDIA_EXTENSIONS and path not in allowed:
        return []
    if path not in allowed:
        return [f"{path}: {context} media is not an approved fixture"]
    if mode != "100644":
        return [f"{path}: {context} fixture must be a regular file"]
    try:
        size = int(_git(root, "cat-file", "-s", oid))
    except (OSError, subprocess.CalledProcessError, ValueError):
        return [f"{path}: cannot inspect the {context} fixture blob"]
    if size > maximum:
        return [f"{path}: {context} fixture is {size} bytes; limit is {maximum}"]
    return []


def _validate_current_index(
    root: Path,
    *,
    maximum: int,
    allowed: set[str],
) -> list[str]:
    entries = _git(root, "ls-files", "--stage", "-z")
    errors = []
    for record in entries.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, oid, stage = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8", errors="surrogateescape")
        if stage != "0":
            if path in allowed or PurePosixPath(path).suffix.lower() in MEDIA_EXTENSIONS:
                errors.append(
                    f"{path}: staged fixture must have no merge conflict"
                )
            continue
        errors.extend(
            _validate_blob(
                root,
                path=path,
                oid=oid,
                mode=mode,
                maximum=maximum,
                allowed=allowed,
                context="staged",
            )
        )
    return errors


def _validate_introduced_history(
    root: Path,
    *,
    base: str,
    head: str,
    maximum: int,
    allowed: set[str],
) -> list[str]:
    revision_range = f"{base}..{head}"
    try:
        object_lines = _git(root, "rev-list", "--objects", revision_range).splitlines()
        introduced_oids = {
            line.split(b" ", 1)[0] for line in object_lines if line
        }
        commits = _git(root, "rev-list", "--reverse", revision_range).splitlines()
    except (OSError, subprocess.CalledProcessError):
        return [
            f"fixtures: unable to inspect introduced Git history {revision_range}"
        ]

    errors = []
    seen: set[tuple[bytes, str, str]] = set()
    for raw_commit in commits:
        commit = raw_commit.decode("ascii")
        try:
            entries = _git(
                root,
                "ls-tree",
                "-r",
                "-z",
                "--full-tree",
                commit,
            )
        except (OSError, subprocess.CalledProcessError):
            return [f"fixtures: unable to inspect tree for commit {commit}"]

        for record in entries.split(b"\0"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            mode_raw, object_type, oid_raw = metadata.split()
            if object_type != b"blob" or oid_raw not in introduced_oids:
                continue
            path = raw_path.decode("utf-8", errors="surrogateescape")
            mode = mode_raw.decode("ascii")
            key = (oid_raw, path, mode)
            if key in seen:
                continue
            seen.add(key)
            errors.extend(
                _validate_blob(
                    root,
                    path=path,
                    oid=oid_raw.decode("ascii"),
                    mode=mode,
                    maximum=maximum,
                    allowed=allowed,
                    context="introduced-history",
                )
            )
    return errors


def validate_fixtures(
    root: str | Path = ROOT,
    *,
    base: str | None = None,
    head: str = "HEAD",
) -> list[str]:
    """Check both the current index and every media blob introduced by a change.

    The optional ``base``/``head`` range catches prohibited or oversized media
    that was added in one commit and deleted in a later commit. Existing Git
    history is never rewritten.
    """
    root = Path(root)
    try:
        _, maximum, allowed, policy_errors = _policy(root)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return ["fixtures: unable to read the Git index and staged fixture policy"]
    if policy_errors:
        return policy_errors
    assert maximum is not None and allowed is not None

    try:
        errors = _validate_current_index(
            root,
            maximum=maximum,
            allowed=allowed,
        )
    except (OSError, subprocess.CalledProcessError, ValueError):
        return ["fixtures: unable to read the Git index and staged fixture policy"]

    if base:
        errors.extend(
            _validate_introduced_history(
                root,
                base=base,
                head=head,
                maximum=maximum,
                allowed=allowed,
            )
        )
    return errors
