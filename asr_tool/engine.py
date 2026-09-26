"""
Core ASR (Automatic Speech Recognition) engine.

Provides a small, pluggable backend architecture so the same CLI/API can
transcribe audio using different recognition engines:

  - "sphinx"  : CMU PocketSphinx (fully offline, bundled acoustic model,
                works with zero network access, default backend)
  - "whisper" : OpenAI Whisper (offline once model weights are downloaded,
                higher accuracy, needs internet on first run to fetch weights)
  - "google"  : Google Web Speech API (free tier via SpeechRecognition,
                requires internet access at call time)

Each backend implements the ASRBackend interface, so new engines can be
added without touching the CLI or calling code.
"""

from __future__ import annotations

import abc
import dataclasses
import time
from pathlib import Path

import speech_recognition as sr


class ASRError(Exception):
    """Raised when transcription fails for a recoverable/reportable reason."""


@dataclasses.dataclass
class TranscriptionResult:
    """Normalized result returned by every backend."""

    text: str
    backend: str
    audio_path: str
    duration_seconds: float
    elapsed_seconds: float

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class ASRBackend(abc.ABC):
    """Common interface every recognition backend must implement."""

    name: str = "base"

    @abc.abstractmethod
    def transcribe(self, audio_path: str, language: str = "en-US") -> str:
        """Return the transcribed text for the given audio file."""
        raise NotImplementedError


class SphinxBackend(ASRBackend):
    """Fully offline backend using CMU PocketSphinx.

    No model download or network access is required: the SpeechRecognition
    package ships PocketSphinx with a bundled English acoustic/language
    model. This makes it the ideal default/test backend for this project.
    """

    name = "sphinx"

    def __init__(self) -> None:
        self._recognizer = sr.Recognizer()

    def transcribe(self, audio_path: str, language: str = "en-US") -> str:
        with sr.AudioFile(audio_path) as source:
            audio = self._recognizer.record(source)
        try:
            return self._recognizer.recognize_sphinx(audio, language=language)
        except sr.UnknownValueError as exc:
            raise ASRError("PocketSphinx could not understand the audio") from exc
        except sr.RequestError as exc:
            raise ASRError(f"PocketSphinx error: {exc}") from exc


class GoogleBackend(ASRBackend):
    """Backend using the free Google Web Speech API.

    Requires network access at call time; provided for higher accuracy
    when internet connectivity is available. No API key needed for the
    free tier (rate-limited, not for production use).
    """

    name = "google"

    def __init__(self) -> None:
        self._recognizer = sr.Recognizer()

    def transcribe(self, audio_path: str, language: str = "en-US") -> str:
        with sr.AudioFile(audio_path) as source:
            audio = self._recognizer.record(source)
        try:
            return self._recognizer.recognize_google(audio, language=language)
        except sr.UnknownValueError as exc:
            raise ASRError("Google ASR could not understand the audio") from exc
        except sr.RequestError as exc:
            raise ASRError(f"Google ASR request failed: {exc}") from exc


class WhisperBackend(ASRBackend):
    """Backend using OpenAI Whisper (local inference, higher accuracy).

    Requires the `openai-whisper` package and its model weights. Model
    weights are downloaded once on first use (needs internet); after
    that, transcription runs fully offline. Import is deferred so the
    rest of the tool works without this optional, heavier dependency.
    """

    name = "whisper"

    def __init__(self, model_size: str = "base") -> None:
        try:
            import whisper  # type: ignore
        except ImportError as exc:
            raise ASRError(
                "The 'whisper' backend requires the optional dependency "
                "'openai-whisper'. Install it with: pip install openai-whisper"
            ) from exc
        self._whisper = whisper
        self._model = whisper.load_model(model_size)

    def transcribe(self, audio_path: str, language: str = "en-US") -> str:
        lang_code = language.split("-")[0]  # e.g. "en-US" -> "en"
        result = self._model.transcribe(audio_path, language=lang_code)
        return result.get("text", "").strip()


BACKENDS = {
    "sphinx": SphinxBackend,
    "google": GoogleBackend,
    "whisper": WhisperBackend,
}


def get_backend(name: str = "sphinx", **kwargs) -> ASRBackend:
    """Factory that instantiates a backend by name."""
    try:
        backend_cls = BACKENDS[name]
    except KeyError as exc:
        valid = ", ".join(sorted(BACKENDS))
        raise ASRError(f"Unknown backend '{name}'. Valid options: {valid}") from exc
    return backend_cls(**kwargs)


def _audio_duration_seconds(audio_path: str) -> float:
    with sr.AudioFile(audio_path) as source:
        return source.DURATION or 0.0


def transcribe_file(
    audio_path: str,
    backend: str = "sphinx",
    language: str = "en-US",
    backend_kwargs: dict | None = None,
) -> TranscriptionResult:
    """High-level convenience function: transcribe a single audio file.

    Args:
        audio_path: Path to a WAV/AIFF/FLAC audio file.
        backend: One of "sphinx" (default, offline), "google", "whisper".
        language: BCP-47 language code, e.g. "en-US".
        backend_kwargs: Extra keyword args passed to the backend constructor
            (e.g. {"model_size": "small"} for whisper).

    Returns:
        TranscriptionResult with the recognized text and timing metadata.
    """
    path = Path(audio_path)
    if not path.exists():
        raise ASRError(f"Audio file not found: {audio_path}")
    if path.suffix.lower() not in {".wav", ".aiff", ".aif", ".flac"}:
        raise ASRError(
            f"Unsupported audio format '{path.suffix}'. "
            "Convert to WAV/AIFF/FLAC first (e.g. with ffmpeg)."
        )

    engine = get_backend(backend, **(backend_kwargs or {}))

    start = time.perf_counter()
    text = engine.transcribe(str(path), language=language)
    elapsed = time.perf_counter() - start

    try:
        duration = _audio_duration_seconds(str(path))
    except Exception:
        duration = 0.0

    return TranscriptionResult(
        text=text,
        backend=engine.name,
        audio_path=str(path),
        duration_seconds=round(duration, 3),
        elapsed_seconds=round(elapsed, 3),
    )
