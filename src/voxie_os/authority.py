from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .core import ROOT, validate


AUTHORITY_DISCOVERY_PATTERNS = (
    "manifests/library-routing.v*.yaml",
    "manifests/assets/*.yaml",
    "manifests/characters/status-register-v*.yaml",
    "manifests/distribution/*/release-readiness-v*.yaml",
    "manifests/productions/*/beatmap-*.final.json",
    "manifests/productions/*/shot-manifest-v*.yaml",
    "manifests/productions/*/review-master-v*.json",
    "manifests/productions/*/final-review-v*.md",
    "manifests/productions/*/master-status-v*.md",
    "manifests/productions/*/production-state-v*.yaml",
    "config/providers.v*.yaml",
    "workflows/*.yaml",
)


def discover_authority_records(repo_root: str | Path = ROOT) -> list[str]:
    """Return repository control records governed by the authority index policy."""
    root = Path(repo_root)
    discovered: set[str] = set()
    for pattern in AUTHORITY_DISCOVERY_PATTERNS:
        discovered.update(
            path.relative_to(root).as_posix()
            for path in root.glob(pattern)
            if path.is_file()
        )
    return sorted(discovered)


def build_authority_coverage_report(
    index: dict[str, Any],
    *,
    repo_root: str | Path = ROOT,
    discovered_paths: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Audit index coverage without changing any authority or production state."""
    validation_errors = validate("authority_index", index)
    discovered = set(
        discover_authority_records(repo_root)
        if discovered_paths is None
        else discovered_paths
    )
    current_paths = {entry["path"] for entry in index.get("entries", [])}
    predecessor_paths = {
        predecessor
        for entry in index.get("entries", [])
        for predecessor in entry.get("predecessors", [])
    }
    covered_paths = current_paths | predecessor_paths

    missing_from_index = sorted(discovered - covered_paths)
    outside_discovery_policy = sorted(covered_paths - discovered)
    current_predecessor_overlap = sorted(current_paths & predecessor_paths)

    findings = []
    for error in validation_errors:
        findings.append(
            {
                "severity": "error",
                "rule_id": "AUTHORITY_INDEX_INVALID",
                "path": None,
                "message": error,
            }
        )
    for path in missing_from_index:
        findings.append(
            {
                "severity": "error",
                "rule_id": "DISCOVERED_AUTHORITY_NOT_INDEXED",
                "path": path,
                "message": "Discovered control authority is neither current nor a recorded predecessor.",
            }
        )
    for path in outside_discovery_policy:
        findings.append(
            {
                "severity": "error",
                "rule_id": "INDEXED_PATH_OUTSIDE_DISCOVERY_POLICY",
                "path": path,
                "message": "Indexed current or predecessor path is not covered by the declared discovery policy.",
            }
        )
    for path in current_predecessor_overlap:
        findings.append(
            {
                "severity": "error",
                "rule_id": "CURRENT_PATH_ALSO_PREDECESSOR",
                "path": path,
                "message": "A current authority cannot simultaneously be predecessor evidence.",
            }
        )

    return {
        "audit_version": "1.0",
        "status": "FAIL" if findings else "PASS",
        "index_id": index.get("index_id"),
        "discovery_patterns": list(AUTHORITY_DISCOVERY_PATTERNS),
        "counts": {
            "discovered": len(discovered),
            "current": len(current_paths),
            "predecessors": len(predecessor_paths),
            "covered": len(covered_paths),
            "missing_from_index": len(missing_from_index),
            "outside_discovery_policy": len(outside_discovery_policy),
            "current_predecessor_overlap": len(current_predecessor_overlap),
        },
        "discovered_paths": sorted(discovered),
        "current_paths": sorted(current_paths),
        "predecessor_paths": sorted(predecessor_paths),
        "missing_from_index": missing_from_index,
        "outside_discovery_policy": outside_discovery_policy,
        "current_predecessor_overlap": current_predecessor_overlap,
        "findings": findings,
    }
