"""任务管理模块 - 管理下载队列和历史"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class TaskRecord:
    """任务记录"""

    def __init__(self, url: str, title: str, platform: str,
                 format_id: str, output_path: str,
                 status: str, duration: float = 0,
                 file_size: int = 0, error: str = ''):
        self.url = url
        self.title = title
        self.platform = platform
        self.format_id = format_id
        self.output_path = output_path
        self.status = status
        self.duration = duration
        self.file_size = file_size
        self.error = error
        self.created_at = datetime.now().isoformat()
        self.completed_at = None

    def to_dict(self) -> dict:
        return {
            'url': self.url,
            'title': self.title,
            'platform': self.platform,
            'format_id': self.format_id,
            'output_path': self.output_path,
            'status': self.status,
            'duration': self.duration,
            'file_size': self.file_size,
            'error': self.error,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict):
        record = cls(
            url=data['url'],
            title=data['title'],
            platform=data['platform'],
            format_id=data['format_id'],
            output_path=data['output_path'],
            status=data['status'],
            duration=data.get('duration', 0),
            file_size=data.get('file_size', 0),
            error=data.get('error', ''),
        )
        record.created_at = data.get('created_at', datetime.now().isoformat())
        record.completed_at = data.get('completed_at')
        return record


class TaskManager:
    """任务管理器"""

    def __init__(self, history_file: str = 'config/task_history.json'):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[TaskRecord] = []
        self.load_history()

    def add_record(self, record: TaskRecord):
        """添加任务记录"""
        self.history.insert(0, record)
        # 只保留最近 100 条
        if len(self.history) > 100:
            self.history = self.history[:100]
        self.save_history()

    def update_record(self, url: str, status: str, output_path: str = '',
                      error: str = '', file_size: int = 0, duration: float = 0):
        """更新任务记录"""
        for record in self.history:
            if record.url == url:
                record.status = status
                if output_path:
                    record.output_path = output_path
                record.error = error
                record.file_size = file_size
                record.duration = duration
                if status in ['completed', 'failed', 'cancelled']:
                    record.completed_at = datetime.now().isoformat()
                break
        self.save_history()

    def get_history(self, limit: int = 50) -> List[TaskRecord]:
        """获取下载历史"""
        return self.history[:limit]

    def get_history_by_platform(self, platform: str) -> List[TaskRecord]:
        """按平台获取历史"""
        return [r for r in self.history if r.platform == platform]

    def clear_history(self):
        """清空历史"""
        self.history = []
        self.save_history()

    def save_history(self):
        """保存历史到文件"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in self.history], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史失败: {e}")

    def load_history(self):
        """从文件加载历史"""
        if not self.history_file.exists():
            return

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.history = [TaskRecord.from_dict(d) for d in data]
        except Exception as e:
            print(f"加载历史失败: {e}")

    def search(self, keyword: str) -> List[TaskRecord]:
        """搜索历史"""
        keyword = keyword.lower()
        return [r for r in self.history
                if keyword in r.title.lower() or keyword in r.url.lower()]