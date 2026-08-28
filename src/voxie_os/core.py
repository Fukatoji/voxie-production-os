from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"

SCHEMA_FILES = {
    "canon": "canon.schema.json",
    "asset": "asset.schema.json",
    "beatmap": "beatmap.schema.json",
    "shot_manifest": "shot_manifest.schema.json",
    "benchmark": "benchmark.schema.json",
    "qc_report": "qc_report.schema.json",
    "alignment": "alignment.schema.json",
    "benchmark_suite": "benchmark_suite.schema.json",
    "provider_catalog": "provider_catalog.schema.json",
    "provider_job": "provider_job.schema.json",
}


def load_data(path: str | Path) -> Any:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def save_json(path: str | Path, data: Any) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def schema_for(kind: str) -> dict[str, Any]:
    if kind not in SCHEMA_FILES:
        raise KeyError(f"Unknown schema kind: {kind}")
    return json.loads((SCHEMAS / SCHEMA_FILES[kind]).read_text(encoding="utf-8"))


def validate(kind: str, data: Any) -> list[str]:
    validator = Draft202012Validator(schema_for(kind))
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        where = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{where}: {err.message}")
    return errors


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
