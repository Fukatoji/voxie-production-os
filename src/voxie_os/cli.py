from __future__ import annotations

import argparse
import json
import sys

from .alignment import audit_beatmap, build_consensus
from .authority import build_authority_coverage_report
from .benchmark import evaluate, summarize
from .change_report import build_change_report, changed_files, to_markdown
from .core import SCHEMA_FILES, load_data, save_json, validate
from .fixtures import validate_fixtures
from .qc import run_manifest_qc
from .providers import build_provider_plan
from .timeline import to_neutral_timeline, to_premiere_plan, to_remotion_manifest, write_otio


def main() -> int:
    p = argparse.ArgumentParser(prog="voxie-os")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate")
    v.add_argument("kind", choices=sorted(SCHEMA_FILES))
    v.add_argument("path")

    fixtures = sub.add_parser("fixtures-check")
    fixtures.add_argument("--repo", help="Repository to check; defaults to the Production OS checkout")

    q = sub.add_parser("qc")
    q.add_argument("canon")
    q.add_argument("manifest")
    q.add_argument("--out")

    t = sub.add_parser("timeline")
    t.add_argument("manifest")
    t.add_argument("--out", required=True)
    t.add_argument("--format", choices=["neutral", "remotion", "premiere", "otio"], default="neutral")
    t.add_argument("--fps", type=int, default=30)
    t.add_argument("--width", type=int, default=1920)
    t.add_argument("--height", type=int, default=1080)
    t.add_argument("--premiere-preset", default="")

    b = sub.add_parser("benchmark-summary")
    b.add_argument("run")

    be = sub.add_parser("benchmark-evaluate")
    be.add_argument("run")
    be.add_argument("suite")
    be.add_argument("--out")

    ac = sub.add_parser("alignment-consensus")
    ac.add_argument("sources", nargs="+")
    ac.add_argument("--id", required=True)
    ac.add_argument("--out", required=True)
    ac.add_argument("--max-timing-spread-s", type=float, default=0.45)
    ac.add_argument("--min-sources", type=int, default=2)
    ac.add_argument("--min-confidence", type=float, default=0.85)

    ba = sub.add_parser("beatmap-audit")
    ba.add_argument("beatmap")
    ba.add_argument("--out")

    aa = sub.add_parser("authority-audit")
    aa.add_argument("index")
    aa.add_argument("--out")

    cr = sub.add_parser("change-report")
    cr.add_argument("--base", required=True)
    cr.add_argument("--head", default="HEAD")
    cr.add_argument("--out")

    pp = sub.add_parser("provider-plan")
    pp.add_argument("catalog")
    pp.add_argument("job")
    pp.add_argument("--out")

    args = p.parse_args()
    if args.cmd == "fixtures-check":
        errors = validate_fixtures(args.repo) if args.repo else validate_fixtures()
        if errors:
            print("FAIL")
            print("\n".join(f"- {error}" for error in errors))
            return 1
        print("PASS")
        return 0

    if args.cmd == "validate":
        errors = validate(args.kind, load_data(args.path))
        if errors:
            print("FAIL")
            print("\n".join(f"- {e}" for e in errors))
            return 1
        print("PASS")
        return 0

    if args.cmd == "qc":
        report = run_manifest_qc(load_data(args.canon), load_data(args.manifest))
        if args.out:
            save_json(args.out, report)
        print(json.dumps(report, indent=2))
        return 1 if report["status"] == "FAIL" else 0

    if args.cmd == "timeline":
        manifest = load_data(args.manifest)
        if args.format == "otio":
            write_otio(manifest, args.out, fps=args.fps)
        else:
            builders = {
                "neutral": lambda: to_neutral_timeline(manifest),
                "remotion": lambda: to_remotion_manifest(manifest, fps=args.fps, width=args.width, height=args.height),
                "premiere": lambda: to_premiere_plan(manifest, fps=args.fps, preset_path=args.premiere_preset),
            }
            save_json(args.out, builders[args.format]())
        print(args.out)
        return 0

    if args.cmd == "benchmark-summary":
        print(json.dumps(summarize(load_data(args.run)), indent=2))
        return 0

    if args.cmd == "benchmark-evaluate":
        suite = load_data(args.suite)
        result = evaluate(load_data(args.run), suite["promotion_policy"])
        if args.out:
            save_json(args.out, result)
        print(json.dumps(result, indent=2))
        return 1 if result["decision"] == "REJECT" else 0

    if args.cmd == "alignment-consensus":
        result = build_consensus(
            [load_data(path) for path in args.sources],
            alignment_id=args.id,
            max_timing_spread_s=args.max_timing_spread_s,
            min_sources=args.min_sources,
            min_confidence=args.min_confidence,
        )
        errors = validate("alignment", result)
        if errors:
            print("FAIL")
            print("\n".join(f"- {error}" for error in errors))
            return 1
        save_json(args.out, result)
        print(args.out)
        return 0

    if args.cmd == "beatmap-audit":
        result = audit_beatmap(load_data(args.beatmap))
        if args.out:
            save_json(args.out, result)
        print(json.dumps(result, indent=2))
        return 1 if result["status"] == "FAIL" else 0

    if args.cmd == "authority-audit":
        report = build_authority_coverage_report(load_data(args.index))
        if args.out:
            save_json(args.out, report)
        print(json.dumps(report, indent=2))
        return 1 if report["status"] == "FAIL" else 0

    if args.cmd == "change-report":
        report = build_change_report(changed_files(args.base, args.head))
        markdown = to_markdown(report)
        if args.out:
            from pathlib import Path
            Path(args.out).write_text(markdown, encoding="utf-8")
        print(markdown)
        return 0

    if args.cmd == "provider-plan":
        catalog = load_data(args.catalog)
        job = load_data(args.job)
        errors = validate("provider_catalog", catalog) + validate("provider_job", job)
        if errors:
            print("FAIL")
            print("\n".join(f"- {error}" for error in errors))
            return 1
        result = build_provider_plan(catalog, job)
        if args.out:
            save_json(args.out, result)
        print(json.dumps(result, indent=2))
        return 1 if result["status"].startswith(("BLOCKED", "INVALID")) else 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
