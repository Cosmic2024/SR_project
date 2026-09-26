"""
Audio helper utilities: format conversion and microphone capture.

Keeping these separate from engine.py keeps the recognition backends
free of I/O/formatting concerns and makes both halves independently
testable.
"""

from __future__ import annotations

import audioop
import shutil
import subprocess
import wave
from pathlib import Path

import speech_recognition as sr


class AudioUtilsError(Exception):
    pass


def extract_waveform_peaks(wav_path: str, num_peaks: int = 120) -> list[float]:
    """Downsample a WAV file into `num_peaks` normalized amplitude values (0-1).

    Used to draw a waveform that reflects the actual uploaded audio, rather
    than a decorative placeholder. Requires 16-bit PCM WAV (which is what
    convert_to_wav() and the sample files already produce).
    """
    with wave.open(wav_path, "rb") as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sample_width != 2:
        # Coerce to 16-bit if the file is some other bit depth.
        raw = audioop.lin2lin(raw, sample_width, 2)
        sample_width = 2

    if n_channels > 1:
        raw = audioop.tomono(raw, sample_width, 0.5, 0.5)

    total_samples = len(raw) // sample_width
    if total_samples == 0 or num_peaks <= 0:
        return [0.0] * max(num_peaks, 0)

    chunk_size = max(1, total_samples // num_peaks)
    peaks: list[float] = []
    for i in range(num_peaks):
        start = i * chunk_size * sample_width
        end = start + chunk_size * sample_width
        chunk = raw[start:end]
        if not chunk:
            peaks.append(0.0)
            continue
        peak_amplitude = audioop.max(chunk, sample_width)
        peaks.append(peak_amplitude / 32768.0)

    # Normalize so the loudest peak hits 1.0 (keeps quiet clips visible).
    loudest = max(peaks) or 1.0
    return [round(min(p / loudest, 1.0), 4) for p in peaks]


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
