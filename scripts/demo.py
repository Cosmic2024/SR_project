"""
Minimal demo of using asr_tool programmatically (not via the CLI).

Usage:
    python scripts/demo.py
"""

from asr_tool.engine import transcribe_file

if __name__ == "__main__":
    for sample in ["samples/open_the_door.wav", "samples/turn_on_lights.wav", "samples/stop_the_music.wav"]:
        result = transcribe_file(sample, backend="sphinx")
        print(f"{sample:35s} -> \"{result.text}\"  ({result.elapsed_seconds}s)")
