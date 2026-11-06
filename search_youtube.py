#!/usr/bin/env python3
"""Search YouTube for keywords, list the videos, and (optionally) transcribe them.

Examples:
    # Search, then transcribe all results
    python search_youtube.py "generative engine optimization" --limit 20

    # Several keywords + YouTube's related suggestions, hand-pick before transcribing
    python search_youtube.py "geo seo" "rank in chatgpt" --related 5 --pick

    # After hand-picking (delete unwanted lines in the saved file), transcribe the rest:
    python transcribe.py GEO-Research/searches/<file>.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
import yt_dlp

from geo_research.collector import collect_transcripts_from_file, slugify

MAX_TOTAL = 100


def related_keywords(query: str, count: int) -> List[str]:
    """YouTube autocomplete suggestions for a query (what people actually type)."""
    try:
        resp = requests.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "ds": "yt", "q": query},
            timeout=10,
        )
        resp.raise_for_status()
        suggestions = json.loads(resp.text)[1]
    except Exception as exc:
        print(f"  (could not fetch related keywords for '{query}': {exc})", file=sys.stderr)
        return []
    return [s for s in suggestions if s.lower() != query.lower()][:count]


def search(query: str, limit: int) -> List[Dict]:
    """Return up to `limit` videos for a query using yt-dlp's YouTube search (no download)."""
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
    videos = []
    for entry in (info or {}).get("entries") or []:
        if not entry or not entry.get("id"):
            continue
        videos.append({
            "id": entry["id"],
            "url": f"https://www.youtube.com/watch?v={entry['id']}",
            "title": entry.get("title") or "",
            "channel": entry.get("channel") or entry.get("uploader") or "",
            "duration": entry.get("duration") or 0,
            "views": entry.get("view_count") or 0,
            "query": query,
        })
    return videos


def fmt_duration(seconds) -> str:
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Search YouTube by keyword and collect transcripts.")
    parser.add_argument("keywords", nargs="+", help="One or more search keywords (quote multi-word keywords)")
    parser.add_argument("--limit", type=int, default=10, help="Videos per keyword (default 10)")
    parser.add_argument("--related", type=int, default=0, help="Also search N related YouTube suggestions per keyword")
    parser.add_argument("--min-minutes", type=float, default=2, help="Skip videos shorter than this (default 2, skips Shorts)")
    parser.add_argument("--max-minutes", type=float, default=0, help="Skip videos longer than this (0 = no limit)")
    parser.add_argument("--min-views", type=int, default=0, help="Skip videos with fewer views")
    parser.add_argument("--max-total", type=int, default=MAX_TOTAL, help=f"Hard cap on total videos (default {MAX_TOTAL})")
    parser.add_argument("--pick", action="store_true", help="Only save the list for hand-picking; don't transcribe yet")
    parser.add_argument("--output-dir", default="GEO-Research", help="Research folder (default GEO-Research)")
    args = parser.parse_args()

    queries: List[str] = []
    for keyword in args.keywords:
        queries.append(keyword)
        if args.related:
            extra = related_keywords(keyword, args.related)
            if extra:
                print(f"Related to '{keyword}': {', '.join(extra)}")
            queries.extend(extra)
    queries = list(dict.fromkeys(queries))

    found: Dict[str, Dict] = {}
    skipped = 0
    for query in queries:
        if len(found) >= args.max_total:
            break
        print(f"Searching: {query}")
        try:
            results = search(query, args.limit)
        except Exception as exc:
            print(f"  search failed: {exc}", file=sys.stderr)
            continue
        for video in results:
            minutes = (video["duration"] or 0) / 60
            if video["id"] in found:
                continue
            if video["duration"] and minutes < args.min_minutes:
                skipped += 1
                continue
            if args.max_minutes and minutes > args.max_minutes:
                skipped += 1
                continue
            if video["views"] < args.min_views:
                skipped += 1
                continue
            found[video["id"]] = video
            if len(found) >= args.max_total:
                break

    if not found:
        print("No videos found.")
        return 1

    search_dir = Path(args.output_dir) / "searches"
    search_dir.mkdir(parents=True, exist_ok=True)
    list_file = search_dir / f"{slugify(args.keywords[0])[:50]}_{datetime.now().strftime('%Y%m%d-%H%M')}.txt"

    lines = [
        f"# YouTube search: {', '.join(queries)}",
        f"# {len(found)} videos ({skipped} skipped by filters). Delete any video's lines you don't want,",
        f"# then run:  python transcribe.py {list_file.as_posix()}",
        "",
    ]
    for number, video in enumerate(found.values(), 1):
        title = re.sub(r"https?://\S+", "", video["title"])
        lines.append(f"{number:03d}. {title} | {video['channel']} | {fmt_duration(video['duration'])} | "
                     f"{video['views']:,} views | keyword: {video['query']}")
        lines.append(f"     {video['url']}")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nFound {len(found)} videos ({skipped} skipped by filters). List saved to {list_file}")

    if args.pick:
        print("Open the file, delete the videos you don't want, then run:")
        print(f"  python transcribe.py {list_file.as_posix()}")
        return 0

    print("Transcribing...")
    result = collect_transcripts_from_file(list_file, Path(args.output_dir))
    print(f"Transcribed: {result['processed_count']}  Already had: {result['skipped_count']}  Failed: {len(result['failed_urls'])}")
    for url in result["failed_urls"]:
        print(f"  failed: {url} ({result['failed_reasons'].get(url, '')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
