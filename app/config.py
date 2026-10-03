from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
UPLOAD_DIR = BASE_DIR / "uploads"
STATIC_DIR = APP_DIR / "static"
SAMPLES_DIR = STATIC_DIR / "samples"
TEMPLATES_DIR = APP_DIR / "templates"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# Allowed Media Extensions
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".ts",
    ".3gp", ".3gpp", ".ogv", ".mpeg", ".mpg", ".vob", ".m2ts", ".mts", ".divx", ".asf"
}
AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".opus", ".weba",
    ".aiff", ".aif", ".caf", ".amr", ".mp2", ".ac3", ".dts", ".alac", ".pcm"
}
ALLOWED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

# FFmpeg and FFprobe Binaries
FFMPEG_PATH = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
FFPROBE_PATH = shutil.which("ffprobe") or "/usr/bin/ffprobe"

# Audio Settings for Whisper Optimization
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1

# Supported Whisper Models
AVAILABLE_MODELS = {
    "tiny": {
        "name": "tiny",
        "description": "Fastest inference, lowest memory (~39 MB), good for quick checks.",
        "params": "39M",
        "speed": "~32x realtime on CPU",
        "recommended": False
    },
    "base": {
        "name": "base",
        "description": "Balanced speed and accuracy (~74 MB), ideal for general use.",
        "params": "74M",
        "speed": "~16x realtime on CPU",
        "recommended": True
    },
    "small": {
        "name": "small",
        "description": "High accuracy (~244 MB), better for noisy or accented speech.",
        "params": "244M",
        "speed": "~6x realtime on CPU",
        "recommended": False
    },
    "medium": {
        "name": "medium",
        "description": "Very high accuracy (~769 MB), slower inference on CPU.",
        "params": "769M",
        "speed": "~2x realtime on CPU",
        "recommended": False
    }
}

DEFAULT_MODEL = "base"
MAX_UPLOAD_SIZE_MB = 500
