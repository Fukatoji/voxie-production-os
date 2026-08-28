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


def validate_fixtures(root: str | Path = ROOT) -> list[str]:
    """Check staged media against the staged policy, never working-file sizes."""
    root = Path(root)
    try:
        policy = json.loads(_git(root, "show", f":{POLICY_PATH}"))
        entries = _git(root, "ls-files", "--stage", "-z")
    except (OSError, subprocess.CalledProcessError, ValueError):
        return ["fixtures: unable to read the Git index and staged fixture policy"]

    if not isinstance(policy, dict) or type(policy.get("version")) is not int or policy["version"] != 1:
        return ["fixtures: policy version must be 1"]
    maximum = policy.get("max_fixture_bytes")
    allowed = policy.get("allowed_paths")
    if type(maximum) is not int or not 0 < maximum <= MAX_FIXTURE_BYTES:
        return [f"fixtures: max_fixture_bytes must be an integer from 1 to {MAX_FIXTURE_BYTES}"]
    if not isinstance(allowed, list) or not all(isinstance(p, str) for p in allowed):
        return ["fixtures: allowed_paths must be an array of exact repository paths"]
    if len(allowed) != len(set(allowed)):
        return ["fixtures: duplicate allowed_paths"]
    for path in allowed:
        parts = PurePosixPath(path).parts
        if (len(parts) < 3 or parts[:2] not in {("tests", "fixtures"), ("examples", "fixtures")}
                or PurePosixPath(path).as_posix() != path or ".." in parts
                or PurePosixPath(path).suffix.lower() not in MEDIA_EXTENSIONS
                or any(char in path for char in "*?[]\\")):
            return [f"fixtures: invalid allowlist path {path!r}"]

    errors = []
    for record in entries.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, oid, stage = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8", errors="surrogateescape")
        if PurePosixPath(path).suffix.lower() not in MEDIA_EXTENSIONS and path not in allowed:
            continue
        if path not in allowed:
            errors.append(f"{path}: tracked media is not an approved fixture")
            continue
        if stage != "0" or mode != "100644":
            errors.append(f"{path}: fixture must be a regular file with no merge conflict")
            continue
        try:
            size = int(_git(root, "cat-file", "-s", oid))
        except (OSError, subprocess.CalledProcessError, ValueError):
            errors.append(f"{path}: cannot inspect the staged fixture blob")
            continue
        if size > maximum:
            errors.append(f"{path}: staged fixture is {size} bytes; limit is {maximum}")
    return errors
