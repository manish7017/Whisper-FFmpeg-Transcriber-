import asyncio
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)


class TranscriptionTask:
    def __init__(self, task_id: str, original_filename: str):
        self.task_id = task_id
        self.original_filename = original_filename
        self.status = "queued"  # queued, extracting_audio, transcribing, completed, failed
        self.progress = 5
        self.current_step = "Initializing..."
        self.steps: List[Dict[str, Any]] = []
        self.media_info: Dict[str, Any] = {}
        self.ffmpeg_result: Optional[Dict[str, Any]] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.is_video: bool = False
        self.created_at = time.time()
        self.completed_at: Optional[float] = None
        self.original_file_path: Optional[str] = None
        self.audio_file_path: Optional[str] = None
        self._listeners: List[asyncio.Queue] = []

    def add_step(self, title: str, detail: Optional[str] = None, progress: Optional[int] = None):
        step_data = {
            "title": title,
            "detail": detail,
            "timestamp": round(time.time() - self.created_at, 2),
        }
        self.steps.append(step_data)
        self.current_step = title
        if progress is not None:
            self.progress = progress
        self._notify_listeners()

    def set_error(self, message: str):
        self.status = "failed"
        self.error = message
        self.add_step("Failed", message, progress=100)
        self._notify_listeners()

    def complete(self, result: Dict[str, Any]):
        self.status = "completed"
        self.progress = 100
        self.completed_at = time.time()
        self.result = result
        self.add_step("Transcription Complete", f"Processed in {round(self.completed_at - self.created_at, 2)}s", progress=100)
        self._notify_listeners()

    def _notify_listeners(self):
        data = self.to_dict()
        for q in list(self._listeners):
            try:
                q.put_nowait(data)
            except Exception:
                pass

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        # Immediately send current state
        q.put_nowait(self.to_dict())
        self._listeners.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._listeners:
            self._listeners.remove(q)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "original_filename": self.original_filename,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "steps": self.steps,
            "media_info": self.media_info,
            "ffmpeg_result": self.ffmpeg_result,
            "is_video": self.is_video,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "has_original_media": self.original_file_path is not None,
            "has_extracted_audio": self.audio_file_path is not None,
        }


class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, TranscriptionTask] = {}

    def create_task(self, original_filename: str) -> TranscriptionTask:
        task_id = str(uuid.uuid4())
        task = TranscriptionTask(task_id, original_filename)
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[TranscriptionTask]:
        return self._tasks.get(task_id)

    def list_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in tasks[:limit]]


task_manager = TaskManager()
