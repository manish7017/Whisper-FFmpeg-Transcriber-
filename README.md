# 🎙️ Whisper AI & FFmpeg Media Transcriber

A modern, high-performance web application that transcribes **both audio and video files** into timestamped text transcripts and subtitles using **OpenAI Whisper** and **FFmpeg**.

When a video file is uploaded, the system uses **FFmpeg** to extract and normalize the audio stream into 16,000 Hz 16-bit mono PCM audio (the native format required by Whisper), feeds it to the Whisper neural network, and renders interactive, synchronized transcripts in the browser.

---

## ✨ Key Features

- **Audio & Video Support**:
  - **Video Formats**: MP4, MKV, MOV, WebM, AVI, FLV, WMV, M4V, TS.
  - **Audio Formats**: MP3, WAV, M4A, FLAC, OGG, AAC, WMA, Opus.
- **FFmpeg Audio Extraction**:
  - Automatically isolates the audio track from videos: `ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav`.
  - Optional EBU R128 loudness normalization (`-af loudnorm`).
  - Transparent display of the exact FFmpeg command executed, extraction speed, and file metrics.
- **Whisper Speech-to-Text**:
  - Multiple model sizes: `tiny` (super fast), `base` (recommended balanced), `small` (high accuracy), `medium`.
  - Multilingual support: 99+ languages with auto-detection.
  - Translation mode: translate speech in any language directly into English text.
- **Interactive Synchronized Media Player**:
  - Integrated video and audio playback.
  - **Click-to-Seek**: Clicking any timestamp (`▶ 00:03`) instantly jumps playback to that point.
  - **Live Highlighting**: As media plays, the current transcript segment lights up in real-time.
  - Dual-track preview for videos: toggle between playing the original video and playing the extracted 16kHz WAV audio.
- **Browser Voice Recording**:
  - Record directly from your microphone with live waveform timer and transcribe in 1 click.
- **Preloaded Demo Media**:
  - 1-click test buttons for sample audio and sample video (no need to find your own files to test).
- **Multiple Export Options**:
  - **Plain Text (`.txt`)**: Continuous paragraphs with word counts and reading time.
  - **SubRip Subtitles (`.srt`)**: Timed subtitles ready for YouTube, VLC, Premiere, etc.
  - **WebVTT (`.vtt`)**: Web-standard subtitles for HTML5 video tags.
  - **JSON (`.json`)**: Detailed segment timestamps and media metadata.
  - **Extracted Audio (`.wav`)**: Download the pure audio isolated from any uploaded video.
- **Real-Time Progress**:
  - Server-Sent Events (SSE) stream the pipeline stages live with glowing progress bars.

---

## 🏗️ Architecture & Pipeline Flow

```
[ User Upload (Video or Audio) / Mic Recording ]
                       │
                       ▼
            [ Media Probe (FFprobe) ]
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
 [ Video Detected ]           [ Audio Detected ]
        │                             │
 [ FFmpeg Extraction ]        [ FFmpeg Normalization ]
 -vn -acodec pcm_s16le        -acodec pcm_s16le
 -ar 16000 -ac 1              -ar 16000 -ac 1
        │                             │
        └──────────────┬──────────────┘
                       ▼
           [ 16kHz Mono WAV Buffer ]
                       │
                       ▼
          [ OpenAI Whisper Model ]
          (tiny / base / small)
                       │
                       ▼
     [ Timestamped Segments & Subtitles ]
                       │
   ┌───────────────────┼───────────────────┐
   ▼                   ▼                   ▼
[ Synced Player ]  [ Full Text ]  [ SRT / VTT / JSON ]
```

---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.10+** (Tested on Python 3.10 - 3.14)
- **FFmpeg & FFprobe**: Ensure `ffmpeg` is installed and available in your `PATH`.
  ```bash
  # Fedora / RHEL
  sudo dnf install ffmpeg ffmpeg-free

  # Ubuntu / Debian
  sudo apt-get install ffmpeg

  # macOS
  brew install ffmpeg
  ```

### 2. Activate Virtual Environment & Install Dependencies

```bash
# Activate existing virtualenv
source .venv/bin/activate

# Or create a new one
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch the Application

```bash
# Using the launcher script
python3 run.py

# Or directly with Uvicorn
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open your browser and navigate to:
**`http://localhost:8000`**

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web user interface dashboard |
| `POST` | `/api/transcribe` | Upload audio/video file and start transcription task |
| `POST` | `/api/transcribe-sample` | Start 1-click test transcription on demo samples |
| `GET` | `/api/tasks/{task_id}` | Retrieve task status, logs, and completed transcript |
| `GET` | `/api/tasks/{task_id}/events` | Server-Sent Events (SSE) stream for live progress |
| `GET` | `/api/media/{task_id}/original` | Stream uploaded media with HTTP Range seeking support |
| `GET` | `/api/media/{task_id}/audio` | Stream FFmpeg extracted 16kHz audio track |
| `GET` | `/api/export/{task_id}/{format}` | Download `txt`, `srt`, `vtt`, `json`, or `audio` |
| `GET` | `/api/models` | List available Whisper models |
| `GET` | `/api/samples` | List available sample media files |
| `GET` | `/api/health` | Health check endpoint |

---

## 📂 Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── config.py              # Application settings, paths, models
│   ├── ffmpeg_utils.py        # FFmpeg audio extraction & media probing
│   ├── whisper_service.py     # Whisper inference, caching, SRT/VTT generation
│   ├── task_manager.py        # Async task state & Server-Sent Events
│   ├── sample_generator.py    # Auto-generation of demo media files
│   ├── main.py                # FastAPI routes & streaming handlers
│   ├── static/
│   │   ├── css/style.css      # Styling, glassmorphic UI, animations
│   │   ├── js/app.js          # Client logic, media sync, player events
│   │   └── samples/           # Sample audio (.wav) and video (.mp4)
│   └── templates/
│       └── index.html         # Responsive single-page dashboard
├── uploads/                   # Temporary upload directory
├── run.py                     # Easy launcher script
├── requirements.txt           # Python dependencies
└── README.md                  # Documentation
```

---

## 🛡️ License

MIT License. Open-source and free to modify.
