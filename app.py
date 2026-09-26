"""
Web frontend for asr_tool.

Serves a single-page UI where a user can drop/upload an audio file and see
it transcribed, backed by the same asr_tool.engine used by the CLI.

Run:
    python app.py
Then open http://127.0.0.1:5000 in a browser.
"""

from __future__ import annotations

import tempfile
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from asr_tool.audio_utils import AudioUtilsError, convert_to_wav, extract_waveform_peaks
from asr_tool.engine import ASRError, transcribe_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload cap

UPLOAD_DIR = Path(tempfile.gettempdir()) / "asr_tool_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aiff", ".aif", ".webm"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file was sent."}), 400

    file = request.files["audio"]
    if not file.filename:
        return jsonify({"error": "No file selected."}), 400

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"Unsupported file type '{suffix}'. "
                     f"Try one of: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        }), 400

    backend = request.form.get("backend", "sphinx")
    if backend not in {"sphinx", "google", "whisper"}:
        return jsonify({"error": f"Unknown backend '{backend}'."}), 400

    job_id = uuid.uuid4().hex
    saved_path = UPLOAD_DIR / f"{job_id}{suffix}"
    file.save(saved_path)

    try:
        wav_path = str(saved_path) if suffix == ".wav" else convert_to_wav(str(saved_path))
        peaks = extract_waveform_peaks(wav_path, num_peaks=120)
        result = transcribe_file(wav_path, backend=backend)
        return jsonify({**result.to_dict(), "peaks": peaks})
    except (ASRError, AudioUtilsError) as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:  # noqa: BLE001 - surface unexpected errors to the UI
        return jsonify({"error": f"Unexpected error: {exc}"}), 500
    finally:
        # Clean up temp files (original upload + any converted WAV copy).
        for p in UPLOAD_DIR.glob(f"{job_id}*"):
            p.unlink(missing_ok=True)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": time.time()})


if __name__ == "__main__":
    app.run(debug=False, port=5000)
