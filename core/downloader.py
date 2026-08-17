"""Concurrent downloader using the embedded yt-dlp Python API."""
from __future__ import annotations

import threading
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import yt_dlp
from PyQt6.QtCore import QObject, pyqtSignal

from VideoDownloader.utils import format_size
from .runtime import build_js_runtime_config, clean_console_text, summarize_process_error


class DownloadState(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    MERGING = "merging"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadTask:
    def __init__(
        self,
        task_id: str,
        url: str,
        format_id: str,
        output_path: str,
        title: str = "",
        platform: str = "",
    ):
        self.task_id = task_id
        self.url = url
        self.format_id = format_id
        self.output_path = output_path
        self.title = title
        self.platform = platform
        self.state = DownloadState.PENDING
        self.progress = 0.0
        self.speed = ""
        self.eta = ""
        self.size = ""
        self.error: Optional[str] = None
        self._completion_emitted = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "url": self.url,
            "format_id": self.format_id,
            "output_path": self.output_path,
            "title": self.title,
            "platform": self.platform,
            "state": self.state.value,
            "progress": self.progress,
            "speed": self.speed,
            "eta": self.eta,
            "size": self.size,
            "error": self.error,
        }


class _TaskLogger:
    def __init__(self):
        self.lines: list[str] = []

    def _append(self, message: str) -> None:
        value = clean_console_text(message)
        if value and not value.startswith("[debug]"):
            self.lines.append(value)
            self.lines = self.lines[-120:]

    def debug(self, message: str) -> None:
        if not message.startswith("[debug]"):
            self._append(message)

    def info(self, message: str) -> None:
        self._append(message)

    def warning(self, message: str) -> None:
        self._append(message)

    def error(self, message: str) -> None:
        self._append(message)


class Downloader(QObject):
    progress_updated = pyqtSignal(str, dict)
    download_completed = pyqtSignal(str, str, str)

    def __init__(
        self,
        yt_dlp_path: str = "yt-dlp",
        ffmpeg_path: str = "",
        deno_path: Optional[str] = None,
        max_concurrent: int = 3,
    ):
        super().__init__()
        self.yt_dlp_path = yt_dlp_path
        self.ffmpeg_path = ffmpeg_path
        self.deno_path = deno_path
        self.max_concurrent = max(1, int(max_concurrent))
        self._semaphore = threading.Semaphore(self.max_concurrent)
        self.tasks: Dict[str, DownloadTask] = {}
        self._task_counter = 0
        self._lock = threading.RLock()

    def update_settings(
        self,
        ffmpeg_path: str,
        deno_path: Optional[str],
        max_concurrent: int,
    ) -> bool:
        with self._lock:
            self.ffmpeg_path = ffmpeg_path
            self.deno_path = deno_path
            unfinished = any(
                task.state in {
                    DownloadState.PENDING,
                    DownloadState.DOWNLOADING,
                    DownloadState.MERGING,
                }
                for task in self.tasks.values()
            )
            if unfinished:
                return False
            self.max_concurrent = max(1, int(max_concurrent))
            self._semaphore = threading.Semaphore(self.max_concurrent)
            return True

    def download(
        self,
        url: str,
        format_id: str,
        output_path: str,
        cookies_path: Optional[str] = None,
        title: str = "",
        platform: str = "",
        progress_callback: Optional[Any] = None,
        completed_callback: Optional[Any] = None,
    ) -> str:
        with self._lock:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}"
            task = DownloadTask(task_id, url, format_id, output_path, title, platform)
            self.tasks[task_id] = task

        self.progress_updated.emit(task_id, {"progress": 0.0, "status": "queued"})
        threading.Thread(
            target=self._download_thread,
            args=(task_id, cookies_path),
            name=f"download-{task_id}",
            daemon=True,
        ).start()
        return task_id

    def _download_thread(self, task_id: str, cookies_path: Optional[str]) -> None:
        task = self.tasks.get(task_id)
        if not task:
            return

        self._semaphore.acquire()
        logger = _TaskLogger()
        try:
            if task.state == DownloadState.CANCELLED:
                return
            task.state = DownloadState.DOWNLOADING
            self.progress_updated.emit(
                task_id, {"progress": 0.0, "status": "downloading"}
            )

            output = Path(task.output_path).expanduser().resolve()
            output.parent.mkdir(parents=True, exist_ok=True)

            def progress_hook(data: dict) -> None:
                if task.state == DownloadState.CANCELLED:
                    raise yt_dlp.utils.DownloadCancelled()
                payload = self._progress_payload(data)
                if payload:
                    self._apply_progress(task, payload)
                    self.progress_updated.emit(task_id, payload)

            def postprocessor_hook(data: dict) -> None:
                if task.state == DownloadState.CANCELLED:
                    raise yt_dlp.utils.DownloadCancelled()
                if data.get("status") in {"started", "processing"}:
                    task.state = DownloadState.MERGING
                    self.progress_updated.emit(
                        task_id,
                        {"progress": task.progress, "status": "merging"},
                    )

            options: Dict[str, Any] = {
                "format": task.format_id,
                "outtmpl": str(output),
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "continuedl": True,
                "windowsfilenames": True,
                "merge_output_format": "mp4",
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
                "logger": logger,
                "js_runtimes": build_js_runtime_config(self.deno_path),
            }
            if cookies_path and Path(cookies_path).exists():
                options["cookiefile"] = cookies_path
            if self.ffmpeg_path:
                options["ffmpeg_location"] = self.ffmpeg_path

            with yt_dlp.YoutubeDL(options) as ydl:
                result = ydl.download([task.url])

            if task.state == DownloadState.CANCELLED:
                self._emit_completion(task, "cancelled", "")
            elif result == 0:
                task.state = DownloadState.COMPLETED
                task.progress = 100.0
                self._emit_completion(task, "completed", "")
            else:
                raise yt_dlp.utils.DownloadError("下载器返回失败状态")
        except yt_dlp.utils.DownloadCancelled:
            task.state = DownloadState.CANCELLED
            self._emit_completion(task, "cancelled", "")
        except yt_dlp.utils.DownloadError as error:
            if task.state == DownloadState.CANCELLED:
                self._emit_completion(task, "cancelled", "")
            else:
                task.state = DownloadState.FAILED
                task.error = summarize_process_error(
                    "\n".join(logger.lines + [str(error)]),
                    "下载失败，请检查链接、网络或登录状态",
                )
                self._emit_completion(task, "failed", task.error)
        except Exception as error:
            if task.state == DownloadState.CANCELLED:
                self._emit_completion(task, "cancelled", "")
            else:
                task.state = DownloadState.FAILED
                task.error = str(error)
                self._emit_completion(task, "failed", task.error)
        finally:
            self._semaphore.release()

    @staticmethod
    def _progress_payload(data: dict) -> Optional[Dict[str, Any]]:
        status = data.get("status")
        if status == "finished":
            return {"progress": 100.0, "status": "merging"}
        if status != "downloading":
            return None

        downloaded = float(data.get("downloaded_bytes") or 0)
        total = float(
            data.get("total_bytes")
            or data.get("total_bytes_estimate")
            or 0
        )
        progress = downloaded / total * 100.0 if total else 0.0
        speed = data.get("speed")
        eta = data.get("eta")
        return {
            "progress": max(0.0, min(progress, 100.0)),
            "size": format_size(int(total)) if total else "",
            "speed": f"{format_size(int(speed))}/s" if speed else "",
            "eta": Downloader._format_eta(eta),
            "status": "downloading",
        }

    @staticmethod
    def _format_eta(seconds: Any) -> str:
        try:
            value = max(0, int(seconds))
        except (TypeError, ValueError):
            return ""
        minutes, secs = divmod(value, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:d}:{secs:02d}"

    @staticmethod
    def _apply_progress(task: DownloadTask, progress: Dict[str, Any]) -> None:
        task.progress = max(task.progress, float(progress.get("progress") or 0.0))
        task.speed = progress.get("speed") or task.speed
        task.eta = progress.get("eta") or task.eta
        task.size = progress.get("size") or task.size

    def _emit_completion(self, task: DownloadTask, status: str, error: str) -> None:
        if task._completion_emitted:
            return
        task._completion_emitted = True
        self.download_completed.emit(task.task_id, status, error)

    def cancel(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task or task.state in {
            DownloadState.COMPLETED,
            DownloadState.FAILED,
            DownloadState.CANCELLED,
        }:
            return False
        was_pending = task.state == DownloadState.PENDING
        task.state = DownloadState.CANCELLED
        if was_pending:
            self._emit_completion(task, "cancelled", "")
        return True

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, DownloadTask]:
        with self._lock:
            return self.tasks.copy()

    def clear_finished(self) -> None:
        with self._lock:
            finished = {
                DownloadState.COMPLETED,
                DownloadState.CANCELLED,
                DownloadState.FAILED,
            }
            for task_id in [
                key for key, task in self.tasks.items() if task.state in finished
            ]:
                self.tasks.pop(task_id, None)

    @staticmethod
    def is_available() -> bool:
        return True
