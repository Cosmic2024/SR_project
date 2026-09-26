"""
Test suite for asr_tool.

Uses the checked-in sample WAV files (samples/) so tests run fully
offline and deterministically, with no network access and no live
microphone required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from asr_tool.engine import (
    ASRError,
    SphinxBackend,
    TranscriptionResult,
    get_backend,
    transcribe_file,
)

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

CASES = [
    ("open_the_door.wav", "open the door please"),
    ("turn_on_lights.wav", "turn on the lights"),
    ("stop_the_music.wav", "stop the music"),
]


def _samples_available() -> bool:
    return SAMPLES_DIR.exists() and all((SAMPLES_DIR / f).exists() for f, _ in CASES)


pytestmark = pytest.mark.skipif(
    not _samples_available(),
    reason="Sample audio not found; run scripts/generate_sample_audio.py first",
)


class TestBackendFactory:
    def test_get_backend_sphinx_returns_instance(self):
        backend = get_backend("sphinx")
        assert isinstance(backend, SphinxBackend)
        assert backend.name == "sphinx"

    def test_get_backend_unknown_raises(self):
        with pytest.raises(ASRError, match="Unknown backend"):
            get_backend("not_a_real_backend")


class TestTranscribeFile:
    @pytest.mark.parametrize("filename,expected_text", CASES)
    def test_transcribes_known_phrases_correctly(self, filename, expected_text):
        audio_path = SAMPLES_DIR / filename
        result = transcribe_file(str(audio_path), backend="sphinx")

        assert isinstance(result, TranscriptionResult)
        assert result.text.strip().lower() == expected_text
        assert result.backend == "sphinx"

    def test_result_includes_timing_metadata(self):
        audio_path = SAMPLES_DIR / "open_the_door.wav"
        result = transcribe_file(str(audio_path), backend="sphinx")

        assert result.duration_seconds > 0
        assert result.elapsed_seconds >= 0
        assert result.audio_path == str(audio_path)

    def test_missing_file_raises_asr_error(self):
        with pytest.raises(ASRError, match="not found"):
            transcribe_file("does_not_exist.wav", backend="sphinx")

    def test_unsupported_format_raises_asr_error(self, tmp_path):
        bogus = tmp_path / "clip.mp3"
        bogus.write_bytes(b"not really an mp3")
        with pytest.raises(ASRError, match="Unsupported audio format"):
            transcribe_file(str(bogus), backend="sphinx")

    def test_to_dict_round_trip(self):
        audio_path = SAMPLES_DIR / "stop_the_music.wav"
        result = transcribe_file(str(audio_path), backend="sphinx")
        d = result.to_dict()
        assert d["text"] == result.text
        assert d["backend"] == "sphinx"
        assert set(d.keys()) == {
            "text", "backend", "audio_path", "duration_seconds", "elapsed_seconds"
        }


class TestSphinxBackendDirect:
    def test_direct_backend_usage(self):
        backend = SphinxBackend()
        text = backend.transcribe(str(SAMPLES_DIR / "turn_on_lights.wav"))
        assert "lights" in text.lower()
