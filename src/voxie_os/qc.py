from __future__ import annotations

from typing import Any


def run_manifest_qc(canon: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    findings = []
    allowed = {c["character_id"] for c in canon.get("characters", [])}

    for shot in manifest.get("shots", []):
        sid = shot.get("shot_id", "UNKNOWN")
        for cid in shot.get("characters", []):
            if cid not in allowed:
                findings.append({
                    "severity": "error",
                    "rule_id": "CANON-CHARACTER-001",
                    "shot_id": sid,
                    "message": f"Character '{cid}' is not declared in canon."
                })
        if shot.get("duration_s", 0) <= 0:
            findings.append({
                "severity": "error",
                "rule_id": "TIMING-DURATION-001",
                "shot_id": sid,
                "message": "Shot duration must be greater than zero."
            })
        if shot.get("motion", {}).get("mode") == "hold" and shot.get("motion", {}).get("camera_move"):
            findings.append({
                "severity": "warning",
                "rule_id": "MOTION-HOLD-001",
                "shot_id": sid,
                "message": "Hold shot declares a camera move; verify this is intentional."
            })

    severity_rank = {"info": 0, "warning": 1, "error": 2}
    max_rank = max((severity_rank[f["severity"]] for f in findings), default=0)
    status = "FAIL" if max_rank >= 2 else ("REVIEW" if max_rank == 1 else "PASS")
    return {"status": status, "findings": findings}
