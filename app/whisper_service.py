import io
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import whisper

from app.config import AVAILABLE_MODELS, DEFAULT_MODEL
from app.ffmpeg_utils import format_timestamp

logger = logging.getLogger(__name__)

# Model Cache and Thread Lock
_model_cache: Dict[str, whisper.Whisper] = {}
_model_lock = threading.Lock()
_device = "cuda" if torch.cuda.is_available() else "cpu"


def get_whisper_model(model_name: str = DEFAULT_MODEL) -> whisper.Whisper:
    """Load or retrieve a cached Whisper model."""
    if model_name not in AVAILABLE_MODELS:
        model_name = DEFAULT_MODEL

    with _model_lock:
        if model_name not in _model_cache:
            logger.info(f"Loading Whisper model '{model_name}' on device '{_device}'...")
            model = whisper.load_model(model_name, device=_device)
            _model_cache[model_name] = model
            logger.info(f"Whisper model '{model_name}' loaded successfully.")
        return _model_cache[model_name]


def generate_srt(segments: List[Dict[str, Any]]) -> str:
    """Generate SubRip (.srt) subtitle string from transcript segments."""
    output = io.StringIO()
    for i, seg in enumerate(segments, start=1):
        start_srt = format_timestamp(seg["start"], srt_format=True)
        end_srt = format_timestamp(seg["end"], srt_format=True)
        text = seg["text"].strip()
        output.write(f"{i}\n{start_srt} --> {end_srt}\n{text}\n\n")
    return output.getvalue().strip()


def generate_vtt(segments: List[Dict[str, Any]]) -> str:
    """Generate WebVTT (.vtt) subtitle string from transcript segments."""
    output = io.StringIO()
    output.write("WEBVTT\n\n")
    for i, seg in enumerate(segments, start=1):
        start_vtt = format_timestamp(seg["start"], srt_format=False)
        end_vtt = format_timestamp(seg["end"], srt_format=False)
        # WebVTT uses . instead of ,
        text = seg["text"].strip()
        output.write(f"{i}\n{start_vtt} --> {end_vtt}\n{text}\n\n")
    return output.getvalue().strip()


def transcribe_audio_file(
    audio_path: Path,
    model_name: str = DEFAULT_MODEL,
    language: Optional[str] = None,
    task: str = "transcribe",
) -> Dict[str, Any]:
    """
    Run Whisper model transcription on an audio file.
    Returns structured transcript with segments, timestamps, SRT, VTT, and statistics.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = get_whisper_model(model_name)

    transcribe_options: Dict[str, Any] = {
        "task": task,
        "fp16": (_device == "cuda"),
        "temperature": 0.0,
        "verbose": False,
    }

    if language and language.lower() not in ("auto", "none", ""):
        transcribe_options["language"] = language.lower()

    t_start = time.time()

    with _model_lock:
        raw_result = model.transcribe(str(audio_path), **transcribe_options)

    t_elapsed = round(time.time() - t_start, 2)

    raw_segments = raw_result.get("segments", [])
    full_text = raw_result.get("text", "").strip()
    detected_lang = raw_result.get("language", "en")

    # Format segments
    formatted_segments: List[Dict[str, Any]] = []
    total_audio_duration = 0.0

    for idx, seg in enumerate(raw_segments):
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", 0.0))
        text = seg.get("text", "").strip()
        if end > total_audio_duration:
            total_audio_duration = end

        formatted_segments.append({
            "id": idx + 1,
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "start_fmt": format_timestamp(start),
            "end_fmt": format_timestamp(end),
            "text": text,
        })

    # Generate subtitles
    srt_content = generate_srt(formatted_segments)
    vtt_content = generate_vtt(formatted_segments)

    # Word stats
    words = full_text.split()
    word_count = len(words)
    speed_factor = round(total_audio_duration / t_elapsed, 1) if t_elapsed > 0 and total_audio_duration > 0 else 1.0

    return {
        "text": full_text,
        "language": detected_lang,
        "task": task,
        "model": model_name,
        "device": _device,
        "segments": formatted_segments,
        "segment_count": len(formatted_segments),
        "word_count": word_count,
        "audio_duration_seconds": round(total_audio_duration, 2),
        "audio_duration_fmt": format_timestamp(total_audio_duration),
        "transcription_seconds": t_elapsed,
        "speed_factor": speed_factor,
        "srt": srt_content,
        "vtt": vtt_content,
    }
