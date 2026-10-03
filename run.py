#!/usr/bin/env python3
"""
Whisper Speech-to-Text & FFmpeg Media Transcriber
Application Launcher
"""

import os
import sys
import shutil
import uvicorn

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ffmpeg_utils import check_ffmpeg_installed
from app.sample_generator import generate_demo_samples
from app.config import AVAILABLE_MODELS, DEFAULT_MODEL


def main():
    print("=" * 68)
    print("  🎙️  Whisper Speech-to-Text & FFmpeg Media Transcriber")
    print("=" * 68)

    # 1. Check FFmpeg
    if not check_ffmpeg_installed():
        print("❌ Warning: FFmpeg is not detected in your PATH!")
        print("   Please install FFmpeg to enable video audio extraction.")
    else:
        ffmpeg_bin = shutil.which("ffmpeg")
        print(f"✅ FFmpeg detected: {ffmpeg_bin}")

    # 2. Check Whisper
    try:
        import whisper
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"✅ PyTorch ({torch.__version__}) & Whisper ({whisper.__version__}) on {device.upper()}")
        print(f"   Available models: {', '.join(AVAILABLE_MODELS.keys())} (default: {DEFAULT_MODEL})")
    except ImportError as e:
        print(f"❌ Error importing Whisper/PyTorch: {e}")
        sys.exit(1)

    # 3. Generate demo samples
    print("⏳ Checking demo samples...")
    try:
        generate_demo_samples()
        print("✅ Demo samples ready (sample_audio.wav & sample_video.mp4)")
    except Exception as e:
        print(f"⚠️  Notice: Demo samples warning: {e}")

    print("-" * 68)
    print("🌐 Web server starting on: http://localhost:8000")
    print("   Open this URL in your web browser to use the application.")
    print("=" * 68)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
