from voxie_os.alignment import audit_beatmap, build_consensus
from voxie_os.core import load_data, validate


AUDIO = {
    "sha256": "a" * 64,
    "duration_s": 8.0,
}


def source(source_id: str, start: float, end: float, *, text: str = "Come explore with me!"):
    return {
        "source_id": source_id,
        "adapter": "whisperx" if source_id == "A" else "lyric-align",
        "weight": 1.0,
        "revision": "test",
        "audio": AUDIO,
        "lyrics": [{
            "line_id": "L001",
            "text": text,
            "vocal_start_s": start,
            "vocal_end_s": end,
            "confidence": 0.95,
            "manual_review": False,
        }],
    }


def test_consensus_preserves_evidence_and_passes_schema():
    result = build_consensus([source("A", 0.50, 2.0), source("B", 0.55, 2.05)], alignment_id="TEST")
    assert result["status"] == "PROVISIONAL"
    assert result["lyrics"][0]["manual_review"] is False
    assert len(result["lyrics"][0]["evidence"]) == 2
    assert validate("alignment", result) == []


def test_consensus_flags_disagreement_instead_of_averaging_it_away():
    result = build_consensus([source("A", 0.5, 2.0), source("B", 1.2, 2.8)], alignment_id="TEST")
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["lyrics"][0]["manual_review"] is True
    assert "timing spread" in result["review_gates"][0]


def test_consensus_rejects_different_audio_hashes():
    other = source("B", 0.5, 2.0)
    other["audio"] = {"sha256": "b" * 64, "duration_s": 8.0}
    try:
        build_consensus([source("A", 0.5, 2.0), other], alignment_id="TEST")
    except ValueError as exc:
        assert "different audio hashes" in str(exc)
    else:
        raise AssertionError("hash mismatch must fail")


def test_final_big_surprise_beatmap_audits_cleanly():
    beatmap = load_data("manifests/productions/big-surprise/beatmap-001.final.json")
    report = audit_beatmap(beatmap)
    assert report["status"] == "PASS"
    assert report["lyric_line_count"] == 26


def test_repository_alignment_source_examples_merge_cleanly():
    first = load_data("examples/alignment-source.whisperx.example.json")
    second = load_data("examples/alignment-source.lyric-align.example.json")
    result = build_consensus([first, second], alignment_id="EXAMPLE")
    assert result["status"] == "PROVISIONAL"
    assert validate("alignment", result) == []
