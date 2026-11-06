#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from geo_research.collector import collect_transcripts_from_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and save YouTube transcripts into a local GEO research library.")
    parser.add_argument("urls_file", help="Path to a text file containing one YouTube URL per line.")
    parser.add_argument("--output-dir", default="GEO-Research", help="Where to store transcripts, metadata, and failed URLs.")
    parser.add_argument("--debug", action="store_true", help="Print per-video parsing and transcript status details for debugging.")
    parser.add_argument("--whisper-model", default="tiny", help="Whisper model to use for local speech-to-text fallback (tiny, base, small, medium, large).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = collect_transcripts_from_file(Path(args.urls_file), Path(args.output_dir), debug=args.debug, whisper_model=args.whisper_model)

    print(f"Processed: {result['processed_count']}")
    print(f"Skipped: {result['skipped_count']}")
    if result["processed_urls"]:
        print("Processed URLs:")
        for item in result["processed_urls"]:
            print(f"  - {item}")
    if result["failed_urls"]:
        print("Failed URLs:")
        for item in result["failed_urls"]:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
