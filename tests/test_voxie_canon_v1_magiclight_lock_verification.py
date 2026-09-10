from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MANIFEST = ROOT / "manifests/assets/voxie-canon-v1.0.magiclight.yaml"
VERIFICATION_HANDOFF = (
    ROOT / "handoff/voxie-canon-v1.0-magiclight-lock-verification-v01-2026-09-10.md"
)


def _manifest() -> dict:
    return yaml.safe_load(CANONICAL_MANIFEST.read_text(encoding="utf-8"))


def test_locked_magiclight_authority_records_exact_approved_values() -> None:
    manifest = _manifest()

    assert manifest["asset_name"] == "Voxie — Canon v1.0"
    assert manifest["provenance"] == {
        "provider": "MagicLight",
        "reusable_asset_id": "7498224955395878912",
        "preview_task_id": "7499108870617059328",
        "model": "Nano Banana 2",
        "format": "16:9",
        "outputs": 1,
        "credits_used": 90,
        "post_generation_balance": 86305,
    }
    assert manifest["approval_state"] == (
        "APPROVED / LOCKED reusable character authority"
    )
    assert manifest["qc_status"] == "PASS"
    assert manifest["qc"]["rejections"] == "none"
    assert manifest["qc"]["replacements"] == "none"
    assert manifest["publication"] == "none"


def test_locked_magiclight_authority_records_exact_hard_qc_evidence() -> None:
    manifest = _manifest()

    assert manifest["qc"]["hard_qc_evidence"] == [
        "exactly one Voxie",
        "dark-indigo visor",
        "cyan eyes with catchlights",
        "forehead V",
        "chest diamond",
        "white/dark-indigo armor",
        "correct proportions",
        "exactly four wings",
        "no extra limbs",
        "no extra accessories",
    ]


def test_locked_magiclight_authority_preserves_integrity_boundaries() -> None:
    manifest = _manifest()

    assert manifest["sha256"] is None
    assert manifest["binary_checksum"]["value"] is None
    assert manifest["binary_checksum"]["status"] == "pending/unavailable"
    assert manifest["media_committed_to_repository"] is False
    assert VERIFICATION_HANDOFF.is_file()
