"""External speech-to-text adapters with explicit provider failures."""

import io
import tempfile
import gc
import itertools
from functools import lru_cache
from pathlib import Path

import numpy as np
import requests

from app.config.settings import settings


class TranscriptionError(ValueError):
    """Raised when configured speech transcription cannot be completed."""


def transcribe_audio(filename: str, content: bytes) -> tuple[str, str]:
    provider = settings.TRANSCRIPTION_PROVIDER.lower().strip()
    if provider in {"local", "faster-whisper", "faster_whisper"}:
        return _transcribe_local(filename, content)
    if provider == "openai":
        return _transcribe_openai(filename, content)
    if provider == "deepgram":
        return _transcribe_deepgram(filename, content)
    raise TranscriptionError(
        "Audio transcription is not configured. Set TRANSCRIPTION_PROVIDER to local, openai, or deepgram."
    )


@lru_cache(maxsize=1)
def _get_local_whisper_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise TranscriptionError(
            "Local transcription requires faster-whisper. Install backend requirements and restart the server."
        ) from error
    try:
        return WhisperModel(
            settings.LOCAL_WHISPER_MODEL,
            device=settings.LOCAL_WHISPER_DEVICE,
            compute_type=settings.LOCAL_WHISPER_COMPUTE_TYPE,
        )
    except Exception as error:
        raise TranscriptionError(f"Unable to initialize local Whisper: {error}") from error


def _transcribe_local(filename: str, content: bytes) -> tuple[str, str]:
    if not content:
        raise TranscriptionError("The audio upload is empty.")
    suffix = Path(filename or "audio").suffix or ".audio"
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(content)
            temporary_path = temporary_file.name
        audio = _decode_audio_for_pyav19(temporary_path)
        segments, _ = _get_local_whisper_model().transcribe(
            audio,
            vad_filter=True,
            beam_size=5,
        )
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
    except TranscriptionError:
        raise
    except Exception as error:
        raise TranscriptionError(f"Local Whisper transcription failed: {error}") from error
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
    if not text:
        raise TranscriptionError("Local Whisper returned an empty transcript.")
    return text, "local_faster_whisper"


def _decode_audio_for_pyav19(input_file: str, sampling_rate: int = 16000) -> np.ndarray:
    """Decode audio without the removed PyAV ``metadata_errors`` argument."""
    try:
        import av
    except ImportError as error:
        raise TranscriptionError("Local transcription requires PyAV.") from error

    resampler = av.audio.resampler.AudioResampler(
        format="s16",
        layout="mono",
        rate=sampling_rate,
    )
    raw_buffer = io.BytesIO()
    dtype = None
    try:
        with av.open(input_file, mode="r") as container:
            for frame in _resample_audio_frames(container.decode(audio=0), resampler, av):
                array = frame.to_ndarray()
                dtype = array.dtype
                raw_buffer.write(array)
    except Exception as error:
        raise TranscriptionError(f"Unable to decode audio for local Whisper: {error}") from error
    finally:
        del resampler
        gc.collect()

    if dtype is None:
        raise TranscriptionError("The audio upload contains no decodable audio frames.")
    return np.frombuffer(raw_buffer.getbuffer(), dtype=dtype).astype(np.float32) / 32768.0


def _resample_audio_frames(frames, resampler, av):
    """Resample frames while tolerating malformed frames in the input."""
    for frame in itertools.chain(frames, [None]):
        try:
            yield from resampler.resample(frame)
        except av.error.InvalidDataError:
            continue


def _transcribe_openai(filename: str, content: bytes) -> tuple[str, str]:
    if not settings.OPENAI_API_KEY:
        raise TranscriptionError("OPENAI_API_KEY is required when TRANSCRIPTION_PROVIDER=openai.")
    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "X-Data-Usage-Policy": "zero-retention",
            },
            files={"file": (filename or "audio", io.BytesIO(content))},
            data={"model": settings.OPENAI_TRANSCRIPTION_MODEL},
            timeout=120,
        )
    except requests.RequestException as error:
        raise TranscriptionError(f"OpenAI transcription request failed: {error}") from error
    if response.status_code >= 400:
        raise TranscriptionError(f"OpenAI transcription failed ({response.status_code}).")
    text = response.json().get("text", "").strip()
    if not text:
        raise TranscriptionError("OpenAI returned an empty transcript.")
    return text, "openai_whisper"


def _transcribe_deepgram(filename: str, content: bytes) -> tuple[str, str]:
    if not settings.DEEPGRAM_API_KEY:
        raise TranscriptionError("DEEPGRAM_API_KEY is required when TRANSCRIPTION_PROVIDER=deepgram.")
    try:
        response = requests.post(
            "https://api.deepgram.com/v1/listen",
            params={"model": settings.DEEPGRAM_MODEL, "smart_format": "true"},
            headers={
                "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
                "Content-Type": "application/octet-stream",
                "X-Data-Usage-Policy": "zero-retention",
            },
            data=content,
            timeout=120,
        )
    except requests.RequestException as error:
        raise TranscriptionError(f"Deepgram transcription request failed: {error}") from error
    if response.status_code >= 400:
        raise TranscriptionError(f"Deepgram transcription failed ({response.status_code}).")
    try:
        text = response.json()["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise TranscriptionError("Deepgram returned an invalid transcript response.") from error
    if not text:
        raise TranscriptionError("Deepgram returned an empty transcript.")
    return text, "deepgram"
