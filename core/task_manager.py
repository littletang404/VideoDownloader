"""Persistent download history."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

from VideoDownloader.utils import data_path


class TaskRecord:
    def __init__(
        self,
        url: str,
        title: str,
        platform: str,
        format_id: str,
        output_path: str,
        status: str,
        duration: float = 0,
        file_size: int = 0,
        error: str = "",
    ):
        self.url = url
        self.title = title
        self.platform = platform
        self.format_id = format_id
        self.output_path = output_path
        self.status = status
        self.duration = duration
        self.file_size = file_size
        self.error = error
        self.created_at = datetime.now().isoformat(timespec="seconds")
        self.completed_at = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "platform": self.platform,
            "format_id": self.format_id,
            "output_path": self.output_path,
            "status": self.status,
            "duration": self.duration,
            "file_size": self.file_size,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskRecord":
        record = cls(
            url=data.get("url", ""),
            title=data.get("title", "未命名任务"),
            platform=data.get("platform", ""),
            format_id=data.get("format_id", ""),
            output_path=data.get("output_path", ""),
            status=data.get("status", "failed"),
            duration=data.get("duration", 0),
            file_size=data.get("file_size", 0),
            error=data.get("error", ""),
        )
        record.created_at = data.get("created_at") or record.created_at
        record.completed_at = data.get("completed_at")
        return record


class TaskManager:
    def __init__(self, history_file: str = "config/task_history.json"):
        self.history_file = data_path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[TaskRecord] = []
        self.load_history()

    def add_record(self, record: TaskRecord) -> None:
        record.completed_at = datetime.now().isoformat(timespec="seconds")
        self.history.insert(0, record)
        self.history = self.history[:100]
        self.save_history()

    def get_history(self, limit: int = 50) -> List[TaskRecord]:
        return self.history[:limit]

    def clear_history(self) -> None:
        self.history = []
        self.save_history()

    def save_history(self) -> None:
        try:
            payload = [record.to_dict() for record in self.history]
            self.history_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            print(f"保存历史失败: {error}")

    def load_history(self) -> None:
        if not self.history_file.exists():
            return
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.history = [
                    TaskRecord.from_dict(item)
                    for item in data
                    if isinstance(item, dict)
                ][:100]
        except (OSError, ValueError, TypeError) as error:
            print(f"加载历史失败: {error}")

    def search(self, keyword: str) -> List[TaskRecord]:
        value = keyword.lower().strip()
        return [
            record for record in self.history
            if value in record.title.lower() or value in record.url.lower()
        ]
