from voxie_os.change_report import build_change_report, to_markdown


def test_change_report_flags_locked_production_state():
    report = build_change_report([
        ("M", "manifests/productions/big-surprise/beatmap-001.final.json"),
        ("M", "src/voxie_os/alignment.py"),
    ])
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["merge_or_publish_authorized"] is False
    assert "beatmap-001.final.json" in to_markdown(report)


def test_change_report_is_informational_for_docs_only():
    report = build_change_report([("M", "docs/ARCHITECTURE.md")])
    assert report["status"] == "INFORMATIONAL"
