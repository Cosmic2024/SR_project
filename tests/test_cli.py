"""Tests for the asr_tool.cli module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asr_tool.cli import main

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def _samples_available() -> bool:
    return (SAMPLES_DIR / "open_the_door.wav").exists()


pytestmark = pytest.mark.skipif(
    not _samples_available(),
    reason="Sample audio not found; run scripts/generate_sample_audio.py first",
)


def test_cli_transcribe_prints_text(capsys):
    audio_path = str(SAMPLES_DIR / "stop_the_music.wav")
    exit_code = main(["transcribe", audio_path, "--backend", "sphinx"])
    out = capsys.readouterr().out.strip().lower()

    assert exit_code == 0
    assert out == "stop the music"


def test_cli_transcribe_json_output(capsys):
    audio_path = str(SAMPLES_DIR / "turn_on_lights.wav")
    exit_code = main(["transcribe", audio_path, "--backend", "sphinx", "--json"])
    out = capsys.readouterr().out

    assert exit_code == 0
    data = json.loads(out)
    assert data["text"].lower() == "turn on the lights"
    assert data["backend"] == "sphinx"
    assert "duration_seconds" in data


def test_cli_missing_file_returns_error_exit_code(capsys):
    exit_code = main(["transcribe", "nonexistent_file.wav"])
    err = capsys.readouterr().err

    assert exit_code == 1
    assert "not found" in err.lower()


def test_cli_invalid_backend_rejected_by_argparse():
    with pytest.raises(SystemExit):
        main(["transcribe", "samples/open_the_door.wav", "--backend", "not_a_backend"])
