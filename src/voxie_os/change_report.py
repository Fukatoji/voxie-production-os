from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


IMPACT_RULES = (
    ("schemas/", "contract", "Run schema validation and compatibility review."),
    ("src/", "runtime", "Run the full unit test suite."),
    ("tests/", "tests", "Confirm the changed tests exercise a production invariant."),
    ("manifests/productions/", "production-state", "Review asset status, lineage, lock gates, and media checksums."),
    ("config/", "policy", "Review approval and QC thresholds."),
    ("workflows/", "workflow", "Validate workflow schemas and provider/approval gates."),
    ("adapters/", "adapter", "Run the adapter contract test in its isolated environment."),
    ("docs/", "documentation", "Confirm documentation matches executable behavior."),
)


def changed_files(base: str, head: str = "HEAD", *, cwd: str | Path | None = None) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "diff", "--name-status", f"{base}...{head}"],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )
    changes = []
    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        status = parts[0]
        path = parts[-1]
        changes.append((status, path))
    return changes


def build_change_report(changes: Iterable[tuple[str, str]]) -> dict:
    changes = list(changes)
    impacts: dict[str, dict] = {}
    lock_gate_files = []
    for status, path in changes:
        for prefix, impact, action in IMPACT_RULES:
            if path.startswith(prefix):
                entry = impacts.setdefault(impact, {"files": [], "required_action": action})
                entry["files"].append({"status": status, "path": path})
                break
        if path.startswith("manifests/productions/") and any(token in path.lower() for token in ("final", "lock", "master")):
            lock_gate_files.append(path)

    return {
        "status": "REVIEW_REQUIRED" if lock_gate_files else "INFORMATIONAL",
        "changed_file_count": len(changes),
        "impacts": impacts,
        "lock_gate_files": sorted(set(lock_gate_files)),
        "merge_or_publish_authorized": False,
    }


def to_markdown(report: dict) -> str:
    lines = [
        "# Voxie Production OS change report",
        "",
        f"Status: **{report['status']}**",
        f"Changed files: **{report['changed_file_count']}**",
        "",
    ]
    if report["lock_gate_files"]:
        lines.extend(["## Lock-gate review", ""])
        lines.extend(f"- `{path}`" for path in report["lock_gate_files"])
        lines.extend(["", "These files affect a final, locked, or master production record. Human review is required.", ""])
    lines.extend(["## Impact map", ""])
    if not report["impacts"]:
        lines.append("No classified Production OS paths changed.")
    for impact, detail in sorted(report["impacts"].items()):
        lines.append(f"### {impact}")
        lines.append("")
        lines.append(detail["required_action"])
        lines.append("")
        lines.extend(f"- `{item['status']}` `{item['path']}`" for item in detail["files"])
        lines.append("")
    lines.extend([
        "## Safety state",
        "",
        "This report is read-only. It does not authorize merging, publishing, paid generation, asset replacement, or canon promotion.",
        "",
    ])
    return "\n".join(lines)
