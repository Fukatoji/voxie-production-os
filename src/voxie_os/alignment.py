from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from typing import Any, Iterable


def _normal_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _weighted_median(values: Iterable[tuple[float, float]]) -> float:
    ordered = sorted((float(value), float(weight)) for value, weight in values)
    total = sum(weight for _, weight in ordered)
    if not ordered or total <= 0:
        raise ValueError("Weighted median requires at least one positive-weight value")
    cursor = 0.0
    for value, weight in ordered:
        cursor += weight
        if cursor >= total / 2:
            return value
    return ordered[-1][0]


def _validate_source_identity(documents: list[dict[str, Any]]) -> None:
    source_ids = [str(document["source_id"]) for document in documents]
    duplicates = sorted(
        source_id for source_id in set(source_ids) if source_ids.count(source_id) > 1
    )
    if duplicates:
        raise ValueError(
            "Alignment source_id values must be unique: " + ", ".join(duplicates)
        )

    for document in documents:
        source_id = str(document["source_id"])
        line_ids = [str(cue["line_id"]) for cue in document.get("lyrics", [])]
        duplicate_lines = sorted(
            line_id for line_id in set(line_ids) if line_ids.count(line_id) > 1
        )
        if duplicate_lines:
            raise ValueError(
                f"{source_id} contains duplicate line_id values: "
                + ", ".join(duplicate_lines)
            )


def _audio_mapping(document: dict[str, Any]) -> Mapping[str, Any]:
    audio = document.get("audio")
    if not isinstance(audio, Mapping):
        raise ValueError("Alignment source audio must be an object")
    if not isinstance(audio.get("sha256"), str):
        raise ValueError("Alignment source audio.sha256 must be a string")
    return audio


def build_consensus(
    documents: list[dict[str, Any]],
    *,
    alignment_id: str,
    max_timing_spread_s: float = 0.45,
    min_sources: int = 2,
    min_confidence: float = 0.85,
) -> dict[str, Any]:
    """Merge normalized aligner outputs without hiding disagreement.

    Each input document must contain ``source_id``, ``adapter``, ``audio`` and
    ``lyrics``. Lines are joined by ``line_id``. Source IDs must be unique, and
    each source may contribute a line only once. The output is provisional;
    only a separate human approval may promote it to HUMAN_REVIEWED or LOCKED.
    """
    if not documents:
        raise ValueError("At least one alignment source is required")
    if min_sources < 1:
        raise ValueError("min_sources must be at least 1")

    _validate_source_identity(documents)

    audio = _audio_mapping(documents[0])
    for document in documents[1:]:
        other = _audio_mapping(document)
        if other["sha256"].lower() != audio["sha256"].lower():
            raise ValueError("Alignment sources reference different audio hashes")
        if abs(float(other["duration_s"]) - float(audio["duration_s"])) > 0.001:
            raise ValueError("Alignment sources reference different audio durations")

    grouped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for document in documents:
        for cue in document.get("lyrics", []):
            grouped[str(cue["line_id"])].append((document, cue))

    merged = []
    review_gates = []
    for line_id in sorted(grouped):
        candidates = grouped[line_id]
        distinct_source_ids = {
            str(document["source_id"]) for document, _ in candidates
        }
        evidence = []
        starts: list[tuple[float, float]] = []
        ends: list[tuple[float, float]] = []
        text_candidates: list[tuple[float, str]] = []

        for document, cue in candidates:
            source_weight = float(document.get("weight", 1.0))
            confidence = float(cue.get("confidence", 0.0))
            effective_weight = source_weight * max(confidence, 0.001)
            start = float(cue["vocal_start_s"])
            end = float(cue["vocal_end_s"])
            if end < start:
                raise ValueError(f"{document['source_id']}:{line_id} ends before it starts")
            starts.append((start, effective_weight))
            ends.append((end, effective_weight))
            text_candidates.append((effective_weight, str(cue["text"])))
            evidence.append({
                "source_id": document["source_id"],
                "vocal_start_s": start,
                "vocal_end_s": end,
                "confidence": confidence,
                "text": str(cue["text"]),
                "manual_review": bool(cue.get("manual_review", False)),
            })

        start = _weighted_median(starts)
        end = _weighted_median(ends)
        start_values = [value for value, _ in starts]
        end_values = [value for value, _ in ends]
        spread = max(
            max(start_values) - min(start_values),
            max(end_values) - min(end_values),
        )
        confidence = sum(
            float(cue.get("confidence", 0.0)) * float(document.get("weight", 1.0))
            for document, cue in candidates
        ) / sum(float(document.get("weight", 1.0)) for document, _ in candidates)
        agreement_penalty = min(
            1.0,
            spread / max(max_timing_spread_s, 0.001),
        ) * 0.2
        confidence = round(max(0.0, min(1.0, confidence - agreement_penalty)), 4)
        text = max(text_candidates, key=lambda item: item[0])[1]
        text_forms = {_normal_text(item[1]) for item in text_candidates}

        reasons = []
        source_count = len(distinct_source_ids)
        if source_count < min_sources:
            reasons.append(f"only {source_count} distinct source(s)")
        if spread > max_timing_spread_s:
            reasons.append(
                f"timing spread {spread:.3f}s exceeds {max_timing_spread_s:.3f}s"
            )
        if confidence < min_confidence:
            reasons.append(f"confidence {confidence:.3f} is below {min_confidence:.3f}")
        if len(text_forms) > 1:
            reasons.append("source text differs")
        if any(item["manual_review"] for item in evidence):
            reasons.append("a source requested review")

        manual_review = bool(reasons)
        if reasons:
            review_gates.append(f"{line_id}: " + "; ".join(reasons))
        merged.append({
            "line_id": line_id,
            "text": text,
            "vocal_start_s": round(start, 6),
            "vocal_end_s": round(end, 6),
            "confidence": confidence,
            "manual_review": manual_review,
            "timing_spread_s": round(spread, 6),
            "evidence": evidence,
        })

    return {
        "alignment_version": "1.0",
        "alignment_id": alignment_id,
        "status": "REVIEW_REQUIRED" if review_gates else "PROVISIONAL",
        "audio": {
            "sha256": audio["sha256"].lower(),
            "duration_s": float(audio["duration_s"]),
        },
        "sources": [
            {
                "source_id": document["source_id"],
                "adapter": document.get("adapter", "other"),
                "weight": float(document.get("weight", 1.0)),
                "revision": document.get("revision"),
            }
            for document in documents
        ],
        "lyrics": merged,
        "summary": {
            "line_count": len(merged),
            "review_line_count": sum(1 for line in merged if line["manual_review"]),
            "source_count": len({str(document["source_id"]) for document in documents}),
            "max_timing_spread_s": max(
                (line["timing_spread_s"] for line in merged),
                default=0.0,
            ),
            "evidence_count": sum(len(line["evidence"]) for line in merged),
        },
        "review_gates": review_gates,
    }


def audit_beatmap(beatmap: dict[str, Any]) -> dict[str, Any]:
    """Run timing-contract checks without changing production state."""
    duration = float(beatmap["duration_s"])
    findings = []
    previous_start = -1.0
    seen = set()
    for line in beatmap.get("lyrics", []):
        line_id = str(line["line_id"])
        start = float(line["vocal_start_s"])
        end = float(line["vocal_end_s"])
        if line_id in seen:
            findings.append(
                {"severity": "error", "line_id": line_id, "message": "Duplicate line_id"}
            )
        seen.add(line_id)
        if start < previous_start:
            findings.append(
                {
                    "severity": "error",
                    "line_id": line_id,
                    "message": "Lines are not in chronological order",
                }
            )
        if end < start:
            findings.append(
                {
                    "severity": "error",
                    "line_id": line_id,
                    "message": "Cue ends before it starts",
                }
            )
        if start < 0 or end > duration:
            findings.append(
                {
                    "severity": "error",
                    "line_id": line_id,
                    "message": "Cue is outside the audio duration",
                }
            )
        if bool(line.get("manual_review")):
            findings.append(
                {
                    "severity": "warning",
                    "line_id": line_id,
                    "message": "Cue still requires manual review",
                }
            )
        previous_start = start

    status = "FAIL" if any(finding["severity"] == "error" for finding in findings) else (
        "REVIEW" if findings else "PASS"
    )
    return {
        "status": status,
        "beatmap_id": beatmap.get("beatmap_id"),
        "audio_sha256": beatmap.get("source_audio", {}).get("sha256"),
        "duration_s": duration,
        "lyric_line_count": len(beatmap.get("lyrics", [])),
        "findings": findings,
    }
