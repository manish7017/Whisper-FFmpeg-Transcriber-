import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.config import (
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    FFMPEG_PATH,
    FFPROBE_PATH,
    VIDEO_EXTENSIONS,
)

logger = logging.getLogger(__name__)


def check_ffmpeg_installed() -> bool:
    """Check if ffmpeg and ffprobe are available."""
    try:
        res1 = subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, text=True)
        res2 = subprocess.run([FFPROBE_PATH, "-version"], capture_output=True, text=True)
        return res1.returncode == 0 and res2.returncode == 0
    except Exception as e:
        logger.error(f"FFmpeg check failed: {e}")
        return False


def probe_media(file_path: Path) -> Dict[str, Any]:
    """Inspect media file using ffprobe to detect streams, formats, and codecs."""
    cmd = [
        FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"ffprobe failed for {file_path}: {e}")
        ext = file_path.suffix.lower()
        is_video = ext in VIDEO_EXTENSIONS
        return {
            "is_video": is_video,
            "has_audio": True,
            "has_video": is_video,
            "duration": 0.0,
            "format": ext.lstrip("."),
            "video_codec": "unknown" if is_video else None,
            "audio_codec": "unknown",
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        }

    streams = data.get("streams", [])
    fmt = data.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration_str = fmt.get("duration") or (video_stream or {}).get("duration") or (audio_stream or {}).get("duration") or "0"
    try:
        duration = float(duration_str)
    except ValueError:
        duration = 0.0

    size_bytes = int(fmt.get("size", os.path.getsize(file_path) if os.path.exists(file_path) else 0))

    has_video = video_stream is not None
    has_audio = audio_stream is not None

    ext = file_path.suffix.lower()
    is_video = has_video or (ext in VIDEO_EXTENSIONS)

    return {
        "is_video": is_video,
        "has_video": has_video,
        "has_audio": has_audio,
        "duration": round(duration, 2),
        "duration_formatted": format_timestamp(duration),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "format": fmt.get("format_name", ext.lstrip(".")),
        "video_codec": video_stream.get("codec_name") if video_stream else None,
        "video_resolution": f"{video_stream.get('width')}x{video_stream.get('height')}" if video_stream and video_stream.get("width") else None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "audio_sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else None,
        "audio_channels": int(audio_stream.get("channels", 0)) if audio_stream else None,
    }


def extract_audio_from_video(
    video_path: Path,
    output_audio_path: Path,
    normalize: bool = False,
) -> Dict[str, Any]:
    """
    Extract audio track from video file using FFmpeg.
    Transcodes to 16kHz 16-bit mono PCM WAV (optimal Whisper input).
    """
    t_start = time.time()

    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", str(video_path),
        "-vn",  # strip video stream
        "-acodec", "pcm_s16le",
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-ac", str(AUDIO_CHANNELS),
    ]

    if normalize:
        cmd.extend(["-af", "loudnorm"])

    cmd.append(str(output_audio_path))
    cmd_str = " ".join(cmd)

    logger.info(f"Running FFmpeg: {cmd_str}")

    process = subprocess.run(cmd, capture_output=True, text=True)

    t_elapsed = round(time.time() - t_start, 3)

    if process.returncode != 0:
        err_msg = process.stderr.strip()
        if "does not contain any stream" in err_msg or "matches no streams" in err_msg:
            raise RuntimeError("The uploaded video file has no audio stream to transcribe.")
        raise RuntimeError(f"FFmpeg audio extraction failed: {err_msg[:400]}")

    if not output_audio_path.exists() or output_audio_path.stat().st_size == 0:
        raise RuntimeError("Extracted audio file is empty. Video may not contain audio.")

    audio_size = output_audio_path.stat().st_size

    return {
        "success": True,
        "command": cmd_str,
        "elapsed_seconds": t_elapsed,
        "output_path": str(output_audio_path),
        "output_size_bytes": audio_size,
        "output_size_mb": round(audio_size / (1024 * 1024), 2),
        "sample_rate": AUDIO_SAMPLE_RATE,
        "channels": AUDIO_CHANNELS,
        "ffmpeg_log": process.stderr[-1000:] if process.stderr else "Completed successfully",
    }


def convert_audio_to_wav(
    input_audio_path: Path,
    output_audio_path: Path,
    normalize: bool = False,
) -> Dict[str, Any]:
    """
    Normalize audio input to 16kHz mono PCM WAV for maximum Whisper efficiency.
    """
    t_start = time.time()

    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", str(input_audio_path),
        "-acodec", "pcm_s16le",
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-ac", str(AUDIO_CHANNELS),
    ]

    if normalize:
        cmd.extend(["-af", "loudnorm"])

    cmd.append(str(output_audio_path))
    cmd_str = " ".join(cmd)

    process = subprocess.run(cmd, capture_output=True, text=True)
    t_elapsed = round(time.time() - t_start, 3)

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg audio normalization failed: {process.stderr[:400]}")

    audio_size = output_audio_path.stat().st_size

    return {
        "success": True,
        "command": cmd_str,
        "elapsed_seconds": t_elapsed,
        "output_path": str(output_audio_path),
        "output_size_bytes": audio_size,
        "output_size_mb": round(audio_size / (1024 * 1024), 2),
    }


def format_timestamp(seconds: float, srt_format: bool = False) -> str:
    """Format seconds into HH:MM:SS or HH:MM:SS,mmm timestamp."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    if srt_format:
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    return f"{minutes:02d}:{secs:02d}.{millis:03d}"
