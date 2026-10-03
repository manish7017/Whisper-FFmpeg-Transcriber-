import asyncio
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import (
    ALLOWED_EXTENSIONS,
    APP_DIR,
    AUDIO_EXTENSIONS,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    MAX_UPLOAD_SIZE_MB,
    SAMPLES_DIR,
    STATIC_DIR,
    TEMPLATES_DIR,
    UPLOAD_DIR,
    VIDEO_EXTENSIONS,
)
from app.ffmpeg_utils import (
    check_ffmpeg_installed,
    convert_audio_to_wav,
    extract_audio_from_video,
    probe_media,
)
from app.sample_generator import generate_demo_samples
from app.task_manager import TaskManager, TranscriptionTask, task_manager
from app.whisper_service import transcribe_audio_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("whisper_app")

app = FastAPI(
    title="Whisper AI Speech-to-Text & FFmpeg Media Transcriber",
    description="Convert audio and video to accurate text transcripts with timestamps, powered by OpenAI Whisper and FFmpeg.",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
async def startup_event():
    """Verify directories, samples, and ffmpeg binary on app start."""
    logger.info("Initializing Whisper & FFmpeg Application...")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not check_ffmpeg_installed():
        logger.error("WARNING: FFmpeg or FFprobe is NOT installed or not found in PATH!")
    else:
        logger.info("FFmpeg and FFprobe verified successfully.")
    # Ensure demo samples are ready
    try:
        generate_demo_samples()
    except Exception as e:
        logger.warning(f"Could not generate demo samples: {e}")


def run_pipeline(
    task: TranscriptionTask,
    original_path: Path,
    model_name: str,
    language: Optional[str],
    task_mode: str,
    normalize: bool,
):
    """Synchronous pipeline executed in background worker thread."""
    try:
        # Step 1: Probe Media
        task.add_step("Inspecting Media Format", "Probing streams with FFprobe...", progress=15)
        media_info = probe_media(original_path)
        task.media_info = media_info
        task.is_video = media_info.get("is_video", False)
        task.original_file_path = str(original_path)

        audio_input_path: Path

        if task.is_video:
            # Step 2: Extract audio from video via FFmpeg
            audio_output_path = UPLOAD_DIR / f"{task.task_id}_extracted_audio.wav"
            task.add_step(
                "Converting Video to Audio via FFmpeg",
                f"Extracting 16kHz audio stream using: ffmpeg -i {original_path.name} -vn -acodec pcm_s16le -ar 16000 -ac 1 ...",
                progress=35,
            )
            ffmpeg_res = extract_audio_from_video(original_path, audio_output_path, normalize=normalize)
            task.ffmpeg_result = ffmpeg_res
            task.audio_file_path = str(audio_output_path)
            audio_input_path = audio_output_path
            task.add_step(
                "FFmpeg Audio Extraction Complete",
                f"Extracted {ffmpeg_res['output_size_mb']}MB 16kHz audio in {ffmpeg_res['elapsed_seconds']}s",
                progress=50,
            )
        else:
            # For audio files, normalize to 16kHz PCM WAV if desired or if non-standard
            audio_output_path = UPLOAD_DIR / f"{task.task_id}_normalized.wav"
            task.add_step("Preparing Audio Stream", "Normalizing audio sample rate to 16kHz...", progress=35)
            try:
                ffmpeg_res = convert_audio_to_wav(original_path, audio_output_path, normalize=normalize)
                task.ffmpeg_result = ffmpeg_res
                task.audio_file_path = str(audio_output_path)
                audio_input_path = audio_output_path
                task.add_step("Audio Processing Complete", f"Audio ready in {ffmpeg_res['elapsed_seconds']}s", progress=50)
            except Exception as e:
                logger.warning(f"Audio conversion notice: {e}. Using original file directly.")
                audio_input_path = original_path
                task.audio_file_path = str(original_path)

        # Step 3: Run Whisper Speech to Text
        task.add_step(
            f"Running Whisper Model ('{model_name}')",
            f"Transcribing audio with task={task_mode}, language={language or 'auto-detect'}...",
            progress=65,
        )
        task.status = "transcribing"

        transcription_result = transcribe_audio_file(
            audio_path=audio_input_path,
            model_name=model_name,
            language=language,
            task=task_mode,
        )

        # Step 4: Finalize
        task.progress = 95
        task.add_step("Formatting Transcript & Subtitles", "Generated SRT, VTT, and timestamped segments.", progress=95)
        task.complete(transcription_result)

    except Exception as exc:
        logger.exception(f"Pipeline error for task {task.task_id}: {exc}")
        task.set_error(str(exc))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render main application UI."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "models": AVAILABLE_MODELS,
            "default_model": DEFAULT_MODEL,
            "max_upload_size": MAX_UPLOAD_SIZE_MB,
        },
    )


@app.get("/api/models")
async def get_models():
    """List available Whisper models."""
    return {"models": AVAILABLE_MODELS, "default": DEFAULT_MODEL}


@app.get("/api/samples")
async def get_samples():
    """List preloaded demo sample media."""
    samples = []
    audio_path = SAMPLES_DIR / "sample_audio.wav"
    video_path = SAMPLES_DIR / "sample_video.mp4"

    if audio_path.exists():
        info = probe_media(audio_path)
        samples.append({
            "id": "sample_audio",
            "name": "Speech Audio Sample (.wav)",
            "type": "audio",
            "duration": info.get("duration", 0),
            "size_mb": info.get("size_mb", 0),
            "description": "Clean spoken speech recording about Whisper AI speech-to-text.",
        })

    if video_path.exists():
        info = probe_media(video_path)
        samples.append({
            "id": "sample_video",
            "name": "Demo Video Presentation (.mp4)",
            "type": "video",
            "duration": info.get("duration", 0),
            "size_mb": info.get("size_mb", 0),
            "description": "Video presentation with spoken audio demonstrating FFmpeg extraction & transcription.",
        })

    return {"samples": samples}


@app.post("/api/transcribe")
async def transcribe_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_name: str = Form(DEFAULT_MODEL),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
    normalize: bool = Form(False),
):
    """
    Upload an audio or video file and start speech-to-text transcription.
    If video is uploaded, FFmpeg extracts the audio stream automatically.
    """
    filename = file.filename or "media_upload"
    ext = Path(filename).suffix.lower()
    if not ext:
        ext = ".bin"

    task_obj = task_manager.create_task(filename)
    saved_path = UPLOAD_DIR / f"{task_obj.task_id}_original{ext}"

    # Save uploaded file
    try:
        with open(saved_path, "wb") as f_out:
            shutil.copyfileobj(file.file, f_out)
    except Exception as e:
        task_obj.set_error(f"Failed to save upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Validate that FFmpeg/FFprobe can read media
    probe_test = probe_media(saved_path)
    if not probe_test.get("has_audio") and not probe_test.get("has_video") and ext not in ALLOWED_EXTENSIONS:
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"The uploaded file '{filename}' does not contain recognized audio or video streams.",
        )

    file_size_mb = round(saved_path.stat().st_size / (1024 * 1024), 2)
    task_obj.add_step("File Uploaded", f"Saved {filename} ({file_size_mb} MB)", progress=10)

    # Launch background thread execution
    background_tasks.add_task(
        run_pipeline,
        task=task_obj,
        original_path=saved_path,
        model_name=model_name,
        language=language,
        task_mode=task,
        normalize=normalize,
    )

    return {"task_id": task_obj.task_id, "status": "processing", "message": "Transcription task initiated"}


@app.post("/api/transcribe-sample")
async def transcribe_sample(
    background_tasks: BackgroundTasks,
    sample_id: str = Form(...),
    model_name: str = Form(DEFAULT_MODEL),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
    normalize: bool = Form(False),
):
    """Instantly test transcription using one of the bundled demo samples."""
    if sample_id == "sample_audio":
        source_path = SAMPLES_DIR / "sample_audio.wav"
        filename = "sample_audio.wav"
    elif sample_id == "sample_video":
        source_path = SAMPLES_DIR / "sample_video.mp4"
        filename = "sample_video.mp4"
    else:
        raise HTTPException(status_code=404, detail="Sample not found")

    if not source_path.exists():
        generate_demo_samples()

    ext = source_path.suffix.lower()
    task_obj = task_manager.create_task(f"Demo: {filename}")
    saved_path = UPLOAD_DIR / f"{task_obj.task_id}_original{ext}"
    shutil.copy(source_path, saved_path)

    task_obj.add_step("Loaded Sample Media", f"Copied {filename} for processing", progress=10)

    background_tasks.add_task(
        run_pipeline,
        task=task_obj,
        original_path=saved_path,
        model_name=model_name,
        language=language,
        task_mode=task,
        normalize=normalize,
    )

    return {"task_id": task_obj.task_id, "status": "processing"}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Retrieve current task status, progress, and results."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@app.get("/api/tasks/{task_id}/events")
async def task_events_stream(task_id: str):
    """Server-Sent Events (SSE) stream for real-time progress updates."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    queue = task.subscribe()

    async def event_generator():
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("status") in ("completed", "failed"):
                    break
        except asyncio.CancelledError:
            pass
        finally:
            task.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/media/{task_id}/original")
async def get_original_media(task_id: str):
    """Stream the uploaded media file (video or audio) with range requests for playback."""
    task = task_manager.get_task(task_id)
    if not task or not task.original_file_path or not os.path.exists(task.original_file_path):
        raise HTTPException(status_code=404, detail="Media file not found")
    media_type = "video/mp4" if task.is_video else "audio/wav"
    return FileResponse(task.original_file_path, media_type=media_type)


@app.get("/api/media/{task_id}/audio")
async def get_extracted_audio(task_id: str):
    """Stream the FFmpeg-extracted/normalized audio file."""
    task = task_manager.get_task(task_id)
    if not task or not task.audio_file_path or not os.path.exists(task.audio_file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(task.audio_file_path, media_type="audio/wav")


@app.get("/api/export/{task_id}/{export_format}")
async def export_transcript(task_id: str, export_format: str):
    """Export the transcript in TXT, SRT, VTT, JSON, or WAV format."""
    task = task_manager.get_task(task_id)
    if not task or not task.result:
        raise HTTPException(status_code=404, detail="Task result not available")

    base_name = Path(task.original_filename).stem

    if export_format == "txt":
        content = task.result.get("text", "")
        return Response(
            content=content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_transcript.txt"'},
        )
    elif export_format == "srt":
        content = task.result.get("srt", "")
        return Response(
            content=content,
            media_type="application/x-subrip; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_subtitles.srt"'},
        )
    elif export_format == "vtt":
        content = task.result.get("vtt", "")
        return Response(
            content=content,
            media_type="text/vtt; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_subtitles.vtt"'},
        )
    elif export_format == "json":
        data = {
            "metadata": {
                "filename": task.original_filename,
                "is_video": task.is_video,
                "media_info": task.media_info,
                "ffmpeg": task.ffmpeg_result,
                "model": task.result.get("model"),
                "language": task.result.get("language"),
                "audio_duration_seconds": task.result.get("audio_duration_seconds"),
            },
            "full_text": task.result.get("text"),
            "segments": task.result.get("segments"),
        }
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_transcript.json"'},
        )
    elif export_format == "audio":
        if not task.audio_file_path or not os.path.exists(task.audio_file_path):
            raise HTTPException(status_code=404, detail="Extracted audio file not found")
        return FileResponse(
            task.audio_file_path,
            media_type="audio/wav",
            filename=f"{base_name}_extracted_audio.wav",
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid export format. Allowed: txt, srt, vtt, json, audio")


@app.get("/api/tasks")
async def list_tasks():
    """List recent transcription tasks in current session."""
    return {"tasks": task_manager.list_recent_tasks()}


@app.get("/api/health")
async def health_check():
    """Health status and configuration."""
    return {
        "status": "online",
        "ffmpeg": check_ffmpeg_installed(),
        "default_model": DEFAULT_MODEL,
        "available_models": list(AVAILABLE_MODELS.keys()),
    }
