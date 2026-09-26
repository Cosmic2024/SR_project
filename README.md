# ASR Tool

A simple, pluggable **Automatic Speech Recognition (ASR)** command-line tool
and Python library that converts spoken audio into text.

It works fully **offline out of the box** (default backend needs no API key,
no model download, and no internet connection), and can optionally use
higher-accuracy cloud/local backends when available.

```
$ asr-tool transcribe samples/turn_on_lights.wav
turn on the lights
```

## Features

- 🎙️ Transcribe audio files (WAV, MP3, FLAC, M4A, ...) to text
- 🔌 Pluggable backend architecture — swap recognition engines without
  changing calling code
- 📴 **Fully offline** default backend (CMU PocketSphinx) — works with zero
  network access
- ☁️ Optional cloud backend (Google Web Speech API) for higher accuracy
- 🧠 Optional local neural backend (OpenAI Whisper) for the best accuracy
- 🎤 Live microphone transcription
- 🔁 Automatic audio format conversion (via ffmpeg) — feed it mp3/m4a/etc.
  directly
- 🧪 Fully tested with an offline-generated sample audio set (no network
  or external test fixtures required)
- 🐍 Usable both as a CLI and as a Python library

## Tools & Technologies Used

| Purpose                          | Technology |
|-----------------------------------|------------|
| Language                          | Python 3.9+ |
| ASR engine (default, offline)     | [CMU PocketSphinx](https://github.com/cmusphinx/pocketsphinx) via [SpeechRecognition](https://github.com/Uberi/speech_recognition) |
| ASR engine (optional, cloud)      | Google Web Speech API |
| ASR engine (optional, local NN)   | [OpenAI Whisper](https://github.com/openai/whisper) |
| Audio format conversion           | [ffmpeg](https://ffmpeg.org/) |
| Test-audio synthesis (offline)    | [SVOX Pico TTS](https://packages.debian.org/libttspico-utils) (`pico2wave`) |
| Testing framework                 | [pytest](https://pytest.org) |
| CLI                                | Python `argparse` |
| Packaging                          | `pyproject.toml` / setuptools |

## Project Structure

```
asr-tool/
├── asr_tool/
│   ├── __init__.py
│   ├── engine.py          # Core ASR logic: backends + transcribe_file()
│   ├── audio_utils.py      # ffmpeg conversion + microphone capture
│   └── cli.py               # Command-line interface
├── scripts/
│   ├── generate_sample_audio.py   # Creates offline test audio (pico2wave)
│   └── demo.py                     # Minimal library-usage example
├── samples/                  # Pre-generated sample WAV files for testing/demo
├── tests/
│   ├── test_engine.py
│   └── test_cli.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

## Installation

### 1. System dependencies

PocketSphinx and audio conversion need a couple of system packages:

```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install -y ffmpeg

# For live microphone input (optional):
sudo apt-get install -y portaudio19-dev

# For regenerating the sample test audio (optional, only needed for devs):
sudo apt-get install -y libttspico-utils
```

### 2. Python dependencies

```bash
git clone <your-repo-url>
cd asr-tool
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
# or, for development (adds pytest):
pip install -r requirements-dev.txt

# Optional extras:
pip install openai-whisper   # for the "whisper" backend
pip install PyAudio          # for the "mic" command
```

Alternatively, install as a package:

```bash
pip install .
# or with extras:
pip install ".[whisper,mic,dev]"
```

## Usage

### CLI

Transcribe an audio file (default: offline PocketSphinx backend):

```bash
asr-tool transcribe samples/open_the_door.wav
# -> open the door please
```

Use a different backend:

```bash
# Google Web Speech API (needs internet)
asr-tool transcribe samples/open_the_door.wav --backend google

# OpenAI Whisper (needs `pip install openai-whisper`; downloads model
# weights the first time it runs)
asr-tool transcribe samples/open_the_door.wav --backend whisper --model-size small
```

Get structured JSON output:

```bash
asr-tool transcribe samples/open_the_door.wav --json
```
```json
{
  "text": "open the door please",
  "backend": "sphinx",
  "audio_path": "samples/open_the_door.wav",
  "duration_seconds": 1.98,
  "elapsed_seconds": 0.55
}
```

Non-WAV input is converted automatically via ffmpeg:

```bash
asr-tool transcribe podcast_clip.mp3
```

Transcribe live from your microphone:

```bash
asr-tool mic --duration 5
```

If you didn't run `pip install .`, invoke the CLI as a module instead:

```bash
python -m asr_tool.cli transcribe samples/open_the_door.wav
```

### As a Python library

```python
from asr_tool.engine import transcribe_file

result = transcribe_file("samples/turn_on_lights.wav", backend="sphinx")
print(result.text)                # "turn on the lights"
print(result.elapsed_seconds)     # e.g. 0.44
print(result.to_dict())           # dict, JSON-serializable
```

Run the included demo:

```bash
python scripts/demo.py
```

## Testing

The test suite is fully offline: it uses pre-generated sample WAV files in
`samples/` (synthesized with `pico2wave`, checked into the repo) so tests
are deterministic and require no network access or live microphone.

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

To regenerate the sample audio yourself (requires `pico2wave` and `ffmpeg`):

```bash
python scripts/generate_sample_audio.py
```

### What's covered

- Backend factory (`get_backend`) — valid and invalid backend names
- End-to-end transcription accuracy against known phrases
- Result metadata (timing, backend name, `to_dict()` serialization)
- Error handling: missing files, unsupported formats
- CLI: text output, `--json` output, error exit codes, argparse validation

## Backend Notes / Trade-offs

| Backend    | Offline? | Accuracy | Setup |
|------------|----------|----------|-------|
| `sphinx`   | ✅ Fully offline, bundled model | Good for short, clear commands; weaker on long/complex sentences | None — works out of the box |
| `google`   | ❌ Needs internet | High | None (free tier, rate-limited) |
| `whisper`  | ✅ After first download | Highest | `pip install openai-whisper`; downloads model weights (~150MB–1.5GB depending on size) on first use |

For production use with high accuracy requirements, `whisper` (or a paid
cloud API) is recommended. `sphinx` is included as the default because it
requires zero setup and zero network access, which keeps this project easy
to clone and run anywhere, including in offline/sandboxed environments.

## License

MIT — see [LICENSE](LICENSE).
