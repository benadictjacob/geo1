#!/usr/bin/env python3
"""Run a GEO readiness audit on a website.

Usage:
    python audit.py example.com
    python audit.py https://example.com --max-pages 15 --out GEO-Research/audits
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from geo_audit.checks import run_checks
from geo_audit.fetcher import UnsafeURLError
from geo_audit.report import compute_score, grade, issues_by_impact, render_free, render_full, to_json
from geo_audit.site import AuditError, crawl


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a website's readiness for AI search (GEO).")
    parser.add_argument("url", help="Website URL or domain")
    parser.add_argument("--max-pages", type=int, default=10, help="Pages to analyse (default 10)")
    parser.add_argument("--out", default="GEO-Research/audits", help="Folder for reports")
    parser.add_argument("--quiet", action="store_true", help="Hide crawl progress")
    args = parser.parse_args()

    progress = None if args.quiet else (lambda message: print(f"  · {message}", file=sys.stderr))
    try:
        site = crawl(args.url, max_pages=args.max_pages, progress=progress)
    except (AuditError, UnsafeURLError) as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 1

    findings = run_checks(site)
    score = compute_score(findings)

    folder = Path(args.out) / f"{site.host}_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "free_preview.md").write_text(render_free(site, findings), encoding="utf-8")
    (folder / "full_report.md").write_text(render_full(site, findings), encoding="utf-8")
    (folder / "result.json").write_text(json.dumps(to_json(site, findings), indent=2), encoding="utf-8")

    print(f"\nGEO score for {site.host}: {score}/100 ({grade(score)})  [{len(site.all_pages)} pages]")
    for f in issues_by_impact(findings)[:5]:
        print(f"  - [{f.status.upper():4}] {f.title}  (-{f.lost_points:.0f} pts)")
    print(f"\nReports saved to {folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
