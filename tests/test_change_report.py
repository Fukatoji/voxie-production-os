from voxie_os.change_report import build_change_report, to_markdown


def test_change_report_flags_locked_production_state():
    report = build_change_report([
        ("M", "manifests/productions/big-surprise/beatmap-001.final.json"),
        ("M", "src/voxie_os/alignment.py"),
    ])
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["merge_or_publish_authorized"] is False
    assert "beatmap-001.final.json" in to_markdown(report)
    assert report["manifest_review_files"] == []


def test_change_report_classifies_canonical_state_and_handoff_paths():
    report = build_change_report([
        ("A", "manifests/assets/voxie-canon-v1.yaml"),
        ("A", "manifests/distribution/rainbow-colors-youtube-v1.yaml"),
        ("M", "manifests/library-routing.v2.yaml"),
        ("A", "handoff/completion-batches/2026-08-27-three-video-final-review.md"),
        ("M", ".github/workflows/production-os-ci.yml"),
    ])

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["lock_gate_files"] == []
    assert report["manifest_review_files"] == [
        "manifests/assets/voxie-canon-v1.yaml",
        "manifests/distribution/rainbow-colors-youtube-v1.yaml",
        "manifests/library-routing.v2.yaml",
    ]
    assert set(report["impacts"]) == {
        "asset-state",
        "ci-workflow",
        "distribution-state",
        "handoff",
        "manifest-state",
    }


def test_manifest_readmes_are_classified_without_claiming_state_change():
    report = build_change_report([("M", "manifests/assets/README.md")])

    assert report["status"] == "INFORMATIONAL"
    assert report["manifest_review_files"] == []
    assert "asset-state" in report["impacts"]


def test_change_report_is_informational_for_docs_only():
    report = build_change_report([("M", "docs/ARCHITECTURE.md")])
    assert report["status"] == "INFORMATIONAL"
