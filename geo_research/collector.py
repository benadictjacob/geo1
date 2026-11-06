from __future__ import annotations

import csv
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qs, urlparse

import yt_dlp
from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", str(value).lower())
    value = re.sub(r"[\s_-]+", "-", value.strip())
    return value or "untitled-video"


def get_video_id_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if host.endswith("youtu.be"):
        candidate = parsed.path.strip("/")
        return candidate.split("/")[0] if candidate else None

    if "youtube.com" in host:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if video_id:
            return video_id

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            return path_parts[1]

    return None


def build_output_paths(root: Path | str) -> Dict[str, Path]:
    project_root = Path(root)
    transcript_dir = project_root / "transcripts"
    metadata_dir = project_root / "metadata"
    failed_dir = project_root / "failed"

    project_root.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root": project_root,
        "transcripts": transcript_dir,
        "metadata": metadata_dir,
        "failed": failed_dir,
    }


def _format_duration(raw_duration: Any) -> str:
    if raw_duration in (None, "", "unknown"):
        return "unknown"

    try:
        duration_seconds = int(float(raw_duration))
    except (TypeError, ValueError):
        return str(raw_duration)

    hours, remainder = divmod(duration_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def fetch_video_metadata(url: str) -> Dict[str, Any]:
    video_id = get_video_id_from_url(url)
    if not video_id:
        raise ValueError(f"Could not extract a valid YouTube video ID from: {url}")

    with yt_dlp.YoutubeDL({
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "noplaylist": True,
    }) as downloader:
        info = downloader.extract_info(url, download=False)

    if not info:
        raise ValueError(f"No metadata found for URL: {url}")

    title = info.get("title") or "Untitled Video"
    channel = info.get("channel") or info.get("uploader") or "Unknown channel"
    published = info.get("release_date") or info.get("upload_date") or "unknown"
    duration = _format_duration(info.get("duration"))
    language = info.get("language") or "unknown"

    return {
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "url": url,
        "duration": duration,
        "published": published,
        "language": language,
    }


class TranscriptService:
    @staticmethod
    def fetch(url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        raise NotImplementedError


class YouTubeCaptionsTranscriptService(TranscriptService):
    @staticmethod
    def fetch(url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        video_id = (metadata or {}).get("video_id") or get_video_id_from_url(url)
        if not video_id:
            return ""

        preferred_language = (metadata or {}).get("language")
        languages: List[str] = []
        if preferred_language and preferred_language != "unknown":
            languages.append(preferred_language)
        languages.extend(lang for lang in ("en", "en-US", "en-GB") if lang not in languages)

        # youtube-transcript-api >= 1.0 uses an instance API: YouTubeTranscriptApi().fetch / .list
        api = YouTubeTranscriptApi()

        def _join(fetched: Any) -> str:
            return " ".join(s.text for s in fetched if getattr(s, "text", "")).strip()

        try:
            return _join(api.fetch(video_id, languages=languages))
        except (NoTranscriptFound, TranscriptsDisabled):
            pass

        # No English/preferred track: take any available transcript, translated to English if possible.
        transcript_list = api.list(video_id)
        for transcript in transcript_list:
            try:
                if transcript.is_translatable and not transcript.language_code.startswith("en"):
                    return _join(transcript.translate("en").fetch())
                return _join(transcript.fetch())
            except CouldNotRetrieveTranscript:
                continue

        return ""


def _build_audio_directory(root_dir: Optional[Path | str] = None) -> Path:
    base_dir = Path(root_dir) if root_dir else Path(tempfile.gettempdir()) / "geo-whisper-audio"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def download_youtube_audio(url: str, output_dir: Optional[Path | str] = None) -> str:
    target_dir = _build_audio_directory(output_dir)
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(target_dir / "%(title)s.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
            "preferredquality": "0",
        }],
        "prefer_ffmpeg": True,
        "geo_bypass": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as downloader:
        downloader.download([url])

    wav_files = sorted(target_dir.glob("*.wav"))
    if wav_files:
        return str(wav_files[-1])

    audio_candidates = sorted(
        target_dir.glob("*.m4a") + target_dir.glob("*.mp3") + target_dir.glob("*.webm") + target_dir.glob("*.aac")
    )
    if audio_candidates:
        return str(audio_candidates[-1])

    raise FileNotFoundError(f"Could not download audio for URL: {url}")


def _ensure_wav_path(audio_path: str | Path) -> str:
    source = Path(audio_path)
    if source.suffix.lower() == ".wav":
        return str(source)

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg is required to convert downloaded audio to WAV for Whisper.")

    output_path = source.with_suffix(".wav")
    subprocess.run(
        [ffmpeg_bin, "-y", "-i", str(source), "-ar", "16000", "-ac", "1", str(output_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return str(output_path)


class WhisperFallbackTranscriptService(TranscriptService):
    @staticmethod
    def fetch(url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        try:
            import whisper  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency guard
            raise RuntimeError("Whisper is not installed in this environment.") from exc

        model_name = (metadata or {}).get("whisper_model") or "tiny"
        audio_path = download_youtube_audio(url, output_dir=_build_audio_directory())
        wav_path = _ensure_wav_path(audio_path)

        try:
            import torch  # type: ignore

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

        model = whisper.load_model(model_name, device=device)
        result = model.transcribe(wav_path, fp16=False if device == "cpu" else True)
        text = result.get("text", "").strip()
        if not text:
            raise RuntimeError("Whisper produced an empty transcript for the audio.")
        return text


def resolve_transcript_with_fallback(
    url: str,
    metadata: Optional[Dict[str, Any]] = None,
    primary_service: type[TranscriptService] | None = None,
    secondary_service: type[TranscriptService] | None = None,
) -> tuple[str, str]:
    primary = primary_service or YouTubeCaptionsTranscriptService
    secondary = secondary_service or WhisperFallbackTranscriptService

    errors: List[str] = []
    for service, label in ((primary, "YouTube captions"), (secondary, "Whisper fallback")):
        try:
            result = service.fetch(url, metadata)
            if result and result.strip():
                return result.strip(), label
            errors.append(f"{label}: empty result")
        except Exception as exc:
            errors.append(f"{label}: {type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}")

    return "", "unavailable (" + "; ".join(errors) + ")"


def fetch_transcript_with_fallback(
    url: str,
    metadata: Optional[Dict[str, Any]] = None,
    primary_service: type[TranscriptService] | None = None,
    secondary_service: type[TranscriptService] | None = None,
) -> str:
    transcript, _ = resolve_transcript_with_fallback(
        url,
        metadata,
        primary_service=primary_service,
        secondary_service=secondary_service,
    )
    return transcript


def fetch_transcript(url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    return fetch_transcript_with_fallback(url, metadata)


DEFAULT_FETCH_TRANSCRIPT = fetch_transcript


def _read_existing_metadata(metadata_file: Path) -> Dict[str, Dict[str, str]]:
    if not metadata_file.exists():
        return {}

    rows: Dict[str, Dict[str, str]] = {}
    with metadata_file.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row.get("video_id"):
                rows[row["video_id"]] = row
    return rows


def _write_metadata_row(metadata_file: Path, row: Dict[str, str]) -> None:
    file_exists = metadata_file.exists()
    with metadata_file.open("a", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "video_id",
                "title",
                "channel",
                "url",
                "duration",
                "language",
                "transcript_status",
                "transcript_source",
                "file_path",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def _next_transcript_index(transcripts_dir: Path) -> int:
    existing = list(transcripts_dir.glob("*.md"))
    if not existing:
        return 1
    return max(int(path.stem.split("_", 1)[0]) for path in existing if path.stem.split("_", 1)[0].isdigit()) + 1


def _format_markdown(metadata: Dict[str, Any], transcript_text: str, source: str) -> str:
    title = metadata.get("title", "Untitled Video")
    channel = metadata.get("channel", "Unknown channel")
    published = metadata.get("published", "unknown")
    duration = metadata.get("duration", "unknown")
    url = metadata.get("url", "")

    return (
        f"# {title}\n\n"
        f"URL: {url}\n"
        f"Channel: {channel}\n"
        f"Published: {published}\n"
        f"Duration: {duration}\n\n"
        f"Transcript source: {source}\n\n"
        "---\n\n"
        "## Transcript\n\n"
        f"{transcript_text.strip()}\n"
    )


def collect_transcripts_from_file(
    urls_file: Path | str,
    project_root: Path | str | None = None,
    debug: bool = False,
    whisper_model: str = "tiny",
) -> Dict[str, Any]:
    target_root = Path(project_root) if project_root is not None else Path("GEO-Research")
    paths = build_output_paths(target_root)
    urls_path = Path(urls_file)
    # Pull YouTube links out of any text (titles, numbering, notes are ignored).
    urls = list(dict.fromkeys(
        re.findall(r"https?://(?:www\.|m\.)?(?:youtube\.com|youtu\.be)/\S+", urls_path.read_text(encoding="utf-8"))
    ))

    metadata_file = paths["metadata"] / "videos.csv"
    existing_rows = _read_existing_metadata(metadata_file)

    processed_urls: List[str] = []
    skipped_urls: List[str] = []
    failed_urls: List[str] = []
    failed_reasons: Dict[str, str] = {}

    for url in urls:
        video_id = get_video_id_from_url(url)
        if debug:
            print(f"[DEBUG] URL: {url}")
            print(f"[DEBUG] Video ID: {video_id}")

        if not video_id:
            failed_urls.append(url)
            failed_reasons[url] = "Invalid YouTube URL or missing video ID."
            if debug:
                print(f"[DEBUG] FAIL: {failed_reasons[url]}")
            continue

        if video_id in existing_rows:
            skipped_urls.append(url)
            if debug:
                print(f"[DEBUG] SKIP: video already processed ({video_id})")
            continue

        try:
            metadata = fetch_video_metadata(url)
            if debug:
                print(f"[DEBUG] Metadata OK: {metadata.get('title')} | {metadata.get('channel')} | {metadata.get('duration')}")
        except Exception as exc:
            failed_urls.append(url)
            failed_reasons[url] = f"Metadata fetch failed: {type(exc).__name__}: {exc}"
            if debug:
                print(f"[DEBUG] FAIL: {failed_reasons[url]}")
            continue

        if fetch_transcript is DEFAULT_FETCH_TRANSCRIPT:
            transcript_text, transcript_source = resolve_transcript_with_fallback(url, {**metadata, "whisper_model": whisper_model})
        else:
            transcript_text = fetch_transcript(url, metadata)
            transcript_source = "YouTube captions"

        if debug:
            print(f"[DEBUG] Transcript source chosen: {transcript_source}")
            print(f"[DEBUG] Transcript length: {len(transcript_text.strip()) if transcript_text else 0}")

        if not transcript_text.strip():
            failed_urls.append(url)
            failed_reasons[url] = f"Transcript unavailable from captions and fallback methods. {transcript_source}"
            if debug:
                print(f"[DEBUG] FAIL: {failed_reasons[url]}")
            continue

        filename_index = _next_transcript_index(paths["transcripts"])
        filename = f"{filename_index:03d}_{slugify(metadata['title'])}.md"
        transcript_file = paths["transcripts"] / filename
        transcript_file.write_text(_format_markdown(metadata, transcript_text, transcript_source), encoding="utf-8")

        row = {
            "video_id": metadata.get("video_id") or video_id,
            "title": metadata.get("title") or "Untitled Video",
            "channel": metadata.get("channel") or "Unknown channel",
            "url": metadata.get("url") or url,
            "duration": metadata.get("duration") or "unknown",
            "language": metadata.get("language") or "unknown",
            "transcript_status": "completed",
            "transcript_source": transcript_source,
            "file_path": str(transcript_file.relative_to(target_root)),
        }
        _write_metadata_row(metadata_file, row)
        processed_urls.append(url)
        existing_rows[row["video_id"]] = row

    failed_file = paths["failed"] / "failed_urls.txt"
    failed_lines = [f"{url} | {reason}" for url, reason in failed_reasons.items()]
    failed_file.write_text("\n".join(failed_lines) + ("\n" if failed_lines else ""), encoding="utf-8")

    return {
        "processed_count": len(processed_urls),
        "skipped_count": len(skipped_urls),
        "processed_urls": processed_urls,
        "skipped_urls": skipped_urls,
        "failed_urls": failed_urls,
        "failed_reasons": failed_reasons,
        "output_paths": paths,
    }
