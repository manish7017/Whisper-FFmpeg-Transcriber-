import logging
import subprocess
from pathlib import Path

from app.config import FFMPEG_PATH, SAMPLES_DIR

logger = logging.getLogger(__name__)


def generate_demo_samples():
    """Generate sample audio and video files for testing the application."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    audio_sample_path = SAMPLES_DIR / "sample_audio.wav"
    video_sample_path = SAMPLES_DIR / "sample_video.mp4"

    # 1. Generate Audio Sample
    if not audio_sample_path.exists() or audio_sample_path.stat().st_size == 0:
        logger.info("Generating demo audio sample...")
        text_audio = (
            "Hello! Welcome to the Whisper speech-to-text platform. "
            "Whisper converts spoken words into accurate text transcripts and subtitles. "
            "You can upload podcasts, interviews, or voice notes in any supported format."
        )
        try:
            # Try espeak-ng first
            subprocess.run(
                ["espeak-ng", "-s", "145", text_audio, "-w", str(audio_sample_path)],
                check=True,
                capture_output=True,
            )
        except Exception as e:
            logger.warning(f"Could not use espeak-ng for audio sample: {e}. Generating tone fallback.")
            subprocess.run(
                [
                    FFMPEG_PATH, "-y",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
                    str(audio_sample_path),
                ],
                check=True,
                capture_output=True,
            )

    # 2. Generate Video Sample
    if not video_sample_path.exists() or video_sample_path.stat().st_size == 0:
        logger.info("Generating demo video sample with speech audio...")
        temp_wav = SAMPLES_DIR / "temp_video_audio.wav"
        text_video = (
            "This is a video presentation demonstration. "
            "Our system uses FFmpeg to isolate and extract the audio stream from this video. "
            "Then, the OpenAI Whisper model transcribes the speech into text with precise timestamps."
        )
        try:
            subprocess.run(
                ["espeak-ng", "-s", "140", text_video, "-w", str(temp_wav)],
                check=True,
                capture_output=True,
            )
            # Create MP4 video with a clean title card and audio
            cmd = [
                FFMPEG_PATH, "-y",
                "-i", str(temp_wav),
                "-f", "lavfi",
                "-i", "color=c=0x1e1b4b:s=1280x720:r=25",
                "-vf", (
                    "drawtext=text='Whisper + FFmpeg Demo Video':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=(h-text_h)/2-60,"
                    "drawtext=text='Audio stream will be extracted and transcribed to text':fontcolor=0x93c5fd:fontsize=26:x=(w-text_w)/2:y=(h-text_h)/2+20"
                ),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                str(video_sample_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                # If drawtext filter font issue arises, fallback without drawtext
                logger.warning(f"drawtext failed ({res.stderr[:100]}), falling back to plain color background.")
                subprocess.run(
                    [
                        FFMPEG_PATH, "-y",
                        "-i", str(temp_wav),
                        "-f", "lavfi", "-i", "color=c=0x1e1b4b:s=854x480:r=24",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest",
                        str(video_sample_path),
                    ],
                    check=True,
                    capture_output=True,
                )
        except Exception as e:
            logger.error(f"Failed to generate video sample: {e}")
        finally:
            if temp_wav.exists():
                temp_wav.unlink()


if __name__ == "__main__":
    generate_demo_samples()
    print("Demo samples verified!")
