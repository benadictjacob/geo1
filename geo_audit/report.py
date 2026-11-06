"""Turn findings into a score, a free preview (top tips + locked teaser) and a full paid report."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Dict, List

from .checks import Finding
from .site import Site

FREE_TIPS = 2
STATUS_ICON = {"pass": "✅", "warn": "⚠️", "fail": "❌", "info": "ℹ️"}
TIER_LABEL = {"A": "Strong evidence", "B": "Medium evidence", "C": "Weak evidence", "info": "Not scored"}


def compute_score(findings: List[Finding]) -> int:
    total = sum(f.weight for f in findings)
    earned = sum(f.weight * f.score for f in findings)
    return round(100 * earned / total) if total else 0


def grade(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 60:
        return "Fair"
    if score >= 40:
        return "Weak"
    return "Poor"


def category_scores(findings: List[Finding]) -> Dict[str, int]:
    result = {}
    for category in dict.fromkeys(f.category for f in findings):
        items = [f for f in findings if f.category == category and f.weight]
        if items:
            result[category] = compute_score(items)
    return result


def issues_by_impact(findings: List[Finding]) -> List[Finding]:
    return sorted((f for f in findings if f.status in ("fail", "warn")), key=lambda f: f.lost_points, reverse=True)


def _header(site: Site, score: int) -> str:
    cats = category_scores_cache = None  # noqa: F841 (kept simple)
    return (
        f"# GEO Readiness Report: {site.host}\n\n"
        f"Date: {datetime.now().strftime('%Y-%m-%d')}  \n"
        f"Pages analysed: {len(site.all_pages)}\n\n"
        f"## Score: {score}/100 ({grade(score)})\n\n"
    )


def _methodology_note() -> str:
    return (
        "> **What this score measures:** how easy your website makes it for AI search (ChatGPT, Gemini, Perplexity, "
        "Google AI Overviews) to read, trust and quote you. It does **not** measure whether AI currently recommends you. "
        "That needs a separate AI answer test. Each check is weighted by how strong the research evidence behind it is.\n"
    )


def _finding_block(f: Finding) -> str:
    return (
        f"### {STATUS_ICON[f.status]} {f.title}\n"
        f"*{f.category} · {TIER_LABEL[f.tier]} · impact {f.lost_points:.0f}/{f.weight} points*\n\n"
        f"- **What we found:** {f.evidence}\n"
        f"- **Why it matters:** {f.why}\n"
        f"- **How to fix:** {f.fix}\n"
        f"- **Source:** {f.sources}\n"
    )


def render_free(site: Site, findings: List[Finding]) -> str:
    score = compute_score(findings)
    issues = issues_by_impact(findings)
    shown, locked = issues[:FREE_TIPS], issues[FREE_TIPS:]
    lines = [_header(site, score), _methodology_note(), "\n## Category scores\n"]
    for category, value in category_scores(findings).items():
        lines.append(f"- **{category}:** {value}/100")
    lines.append(f"\n## Your top {len(shown)} fixes (free)\n")
    lines.extend(_finding_block(f) for f in shown)
    if locked:
        high = sum(1 for f in locked if f.tier == "A")
        cats = Counter(f.category for f in locked)
        lines.append(
            f"\n## 🔒 {len(locked)} more issues found\n\n"
            f"{high} of them are backed by strong evidence. Areas: "
            + ", ".join(f"{c} ({n})" for c, n in cats.items())
            + ".\n\nUnlock the full report to see every issue, the evidence we found on your pages, and step-by-step fixes.\n"
        )
    passed = [f for f in findings if f.status == "pass" and f.weight]
    lines.append(f"\n## What you're doing well\n\n{len(passed)} checks passed.\n")
    return "\n".join(lines)


def render_full(site: Site, findings: List[Finding]) -> str:
    score = compute_score(findings)
    issues = issues_by_impact(findings)
    lines = [_header(site, score), _methodology_note(), "\n## Category scores\n"]
    for category, value in category_scores(findings).items():
        lines.append(f"- **{category}:** {value}/100")

    lines.append("\n## Priority action list\n")
    for index, f in enumerate(issues, 1):
        lines.append(f"{index}. {STATUS_ICON[f.status]} **{f.title}**: {f.fix}")

    lines.append("\n## All issues in detail\n")
    lines.extend(_finding_block(f) for f in issues)

    lines.append("\n## Checks passed\n")
    for f in findings:
        if f.status in ("pass", "info"):
            lines.append(f"- {STATUS_ICON[f.status]} **{f.title}**: {f.evidence}")

    lines.append("\n## Pages analysed\n")
    lines.extend(f"- {p.url}" for p in site.all_pages)
    lines.append(
        "\n## Next steps\n\n"
        "1. Fix the top 3 items in the priority list first: they carry the most points and the strongest evidence.\n"
        "2. Earn mentions on other websites (review sites, industry lists, Reddit, YouTube). This is the biggest lever "
        "for AI visibility and cannot be fixed on your own website alone.\n"
        "3. Re-run this audit after changes, and test real customer questions in ChatGPT/Perplexity to see if you get mentioned.\n"
    )
    return "\n".join(lines)


def to_json(site: Site, findings: List[Finding]) -> dict:
    score = compute_score(findings)
    return {
        "host": site.host,
        "url": site.home.url,
        "date": datetime.now().isoformat(timespec="seconds"),
        "score": score,
        "grade": grade(score),
        "category_scores": category_scores(findings),
        "pages_analysed": [p.url for p in site.all_pages],
        "findings": [f.to_dict() for f in findings],
    }
