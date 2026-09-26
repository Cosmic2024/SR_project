"""
Generate sample WAV audio files offline using the `espeak` TTS engine.

These files are used by the test suite and as demo input for the CLI,
so the whole project can be exercised end-to-end with zero network
access and zero external audio files.

Requires `libttspico-utils` (pico2wave) and `ffmpeg`:
    sudo apt-get install libttspico-utils ffmpeg

Usage:
    python scripts/generate_sample_audio.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

# Short, clear phrases transcribe most reliably with PocketSphinx's
# general-purpose acoustic model, including on synthetic TTS voices.
PHRASES = {
    "open_the_door.wav": "open the door please",
    "turn_on_lights.wav": "turn on the lights",
    "stop_the_music.wav": "stop the music",
}


def synthesize(text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path = output_path.with_suffix(".raw.wav")

    # pico2wave produces natural-sounding speech (much better ASR accuracy
    # than robotic formant synths like espeak).
    subprocess.run(
        ["pico2wave", "-l", "en-US", "-w", str(raw_path), text],
        check=True, capture_output=True,
    )

    # Resample to 16kHz mono PCM, which PocketSphinx's bundled model expects.
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw_path), "-ac", "1", "-ar", "16000", str(output_path)],
        check=True, capture_output=True,
    )
    raw_path.unlink(missing_ok=True)


def main() -> None:
    for filename, phrase in PHRASES.items():
        out_path = SAMPLES_DIR / filename
        synthesize(phrase, out_path)
        print(f"Generated {out_path}  <-  \"{phrase}\"")


if __name__ == "__main__":
    main()
