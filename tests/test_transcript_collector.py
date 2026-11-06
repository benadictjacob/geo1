from pathlib import Path

from geo_research.collector import (
    WhisperFallbackTranscriptService,
    build_output_paths,
    collect_transcripts_from_file,
    fetch_transcript_with_fallback,
)


def test_build_output_paths_creates_expected_directories(tmp_path):
    root = tmp_path / "GEO-Research"
    paths = build_output_paths(root)

    assert paths["root"] == root
    assert paths["transcripts"].is_dir()
    assert paths["metadata"].is_dir()
    assert paths["failed"].is_dir()


def test_collect_transcripts_skips_existing_urls_and_processes_new_ones(tmp_path, monkeypatch):
    urls_file = tmp_path / "urls.txt"
    urls_file.write_text(
        "\n".join([
            "https://youtube.com/watch?v=AAAA",
            "https://youtube.com/watch?v=BBBB",
        ])
    )

    project_root = tmp_path / "GEO-Research"
    metadata_dir = project_root / "metadata"
    metadata_dir.mkdir(parents=True)
    metadata_file = metadata_dir / "videos.csv"
    metadata_file.write_text(
        "video_id,title,channel,url,duration,language,transcript_status,transcript_source,file_path\n"
        "AAAA,Existing Title,Example,https://youtube.com/watch?v=AAAA,00:30,en,completed,YouTube captions,transcripts/001_existing-title.md\n"
    )

    def fake_fetch_video_metadata(url):
        lookup = {
            "https://youtube.com/watch?v=AAAA": {"video_id": "AAAA", "title": "Existing Title", "channel": "Example", "duration": "00:30", "language": "en"},
            "https://youtube.com/watch?v=BBBB": {"video_id": "BBBB", "title": "New Title", "channel": "Example", "duration": "01:00", "language": "en"},
        }
        return lookup[url]

    def fake_fetch_transcript(url, metadata):
        return "This is a transcript for the video."

    monkeypatch.setattr("geo_research.collector.fetch_video_metadata", fake_fetch_video_metadata)
    monkeypatch.setattr("geo_research.collector.fetch_transcript", fake_fetch_transcript)

    result = collect_transcripts_from_file(urls_file, project_root)

    assert result["processed_count"] == 1
    assert result["skipped_count"] == 1
    assert len(result["processed_urls"]) == 1
    assert result["processed_urls"][0] == "https://youtube.com/watch?v=BBBB"
    assert (project_root / "transcripts").exists()
    assert (metadata_file).exists()
    assert "failed_reasons" in result


def test_fetch_transcript_with_fallback_uses_secondary_service_when_primary_fails(monkeypatch):
    calls = []

    class FakePrimary:
        @staticmethod
        def fetch(url, metadata=None):
            calls.append("primary")
            raise RuntimeError("captions unavailable")

    class FakeSecondary:
        @staticmethod
        def fetch(url, metadata=None):
            calls.append("secondary")
            return "fallback transcript text"

    result = fetch_transcript_with_fallback(
        "https://youtube.com/watch?v=AAAA",
        {"video_id": "AAAA"},
        primary_service=FakePrimary,
        secondary_service=FakeSecondary,
    )

    assert result == "fallback transcript text"
    assert calls == ["primary", "secondary"]


def test_whisper_fallback_transcribes_downloaded_audio(monkeypatch, tmp_path):
    fake_audio_path = tmp_path / "audio.wav"
    fake_audio_path.write_text("fake audio")

    class FakeModel:
        def transcribe(self, path, fp16):
            assert path == str(fake_audio_path)
            assert fp16 is False
            return {"text": "Local whisper transcript"}

    class FakeWhisperModule:
        @staticmethod
        def load_model(name, device):
            assert name == "tiny"
            assert device in {"cpu", "cuda"}
            return FakeModel()

    monkeypatch.setattr("geo_research.collector.download_youtube_audio", lambda url, output_dir: str(fake_audio_path))
    monkeypatch.setitem(__import__("sys").modules, "whisper", FakeWhisperModule)

    result = WhisperFallbackTranscriptService.fetch("https://youtube.com/watch?v=AAAA")

    assert result == "Local whisper transcript"
