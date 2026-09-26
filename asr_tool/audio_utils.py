"""
Audio helper utilities: format conversion and microphone capture.

Keeping these separate from engine.py keeps the recognition backends
free of I/O/formatting concerns and makes both halves independently
testable.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import speech_recognition as sr


class AudioUtilsError(Exception):
    pass


def convert_to_wav(input_path: str, output_path: str | None = None) -> str:
    """Convert any ffmpeg-readable audio/video file to 16kHz mono WAV.

    ASR backends work best (and PocketSphinx requires) 16kHz mono PCM WAV.
    Requires `ffmpeg` to be installed and on PATH.
    """
    if shutil.which("ffmpeg") is None:
        raise AudioUtilsError(
            "ffmpeg is required for audio conversion but was not found on PATH. "
            "Install it with: sudo apt-get install ffmpeg"
        )

    src = Path(input_path)
    if not src.exists():
        raise AudioUtilsError(f"Input file not found: {input_path}")

    dst = Path(output_path) if output_path else src.with_suffix(".wav")

    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-ac", "1",        # mono
        "-ar", "16000",    # 16kHz sample rate
        "-vn",              # no video stream
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise AudioUtilsError(f"ffmpeg conversion failed: {result.stderr[-500:]}")
    return str(dst)


def record_from_microphone(
    duration: int | None = None,
    output_path: str = "mic_capture.wav",
    ambient_noise_adjust_seconds: float = 0.5,
) -> str:
    """Record audio from the default microphone and save it as a WAV file.

    Args:
        duration: Max seconds to record. None records until silence is
            detected (phrase-based capture).
        output_path: Where to save the recorded WAV file.
        ambient_noise_adjust_seconds: Seconds spent calibrating for
            background noise before recording starts.

    Note: requires a working audio input device (PyAudio/PortAudio) and
    is intended for interactive/local use, not for headless CI.
    """
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=ambient_noise_adjust_seconds)
        audio = recognizer.listen(source, phrase_time_limit=duration)

    with open(output_path, "wb") as f:
        f.write(audio.get_wav_data())
    return output_path
