"""下载器模块 - yt-dlp 包装器（修复线程安全）"""
import subprocess
import os
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal


class DownloadState(Enum):
    """下载状态"""
    PENDING = 'pending'
    DOWNLOADING = 'downloading'
    MERGING = 'merging'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PAUSED = 'paused'
    CANCELLED = 'cancelled'


class DownloadTask:
    """下载任务"""

    def __init__(self, task_id: str, url: str, format_id: str, output_path: str,
                 title: str = '', platform: str = ''):
        self.task_id = task_id
        self.url = url
        self.format_id = format_id
        self.output_path = output_path
        self.title = title
        self.platform = platform
        self.state = DownloadState.PENDING
        self.progress = 0.0
        self.speed = ''
        self.eta = ''
        self.error = None
        self.temp_files = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'url': self.url,
            'format_id': self.format_id,
            'output_path': self.output_path,
            'title': self.title,
            'platform': self.platform,
            'state': self.state.value,
            'progress': self.progress,
            'speed': self.speed,
            'eta': self.eta,
            'error': self.error,
        }


class Downloader(QObject):
    """视频下载器（Qt线程安全版本）"""

    progress_updated = pyqtSignal(str, dict)  # task_id, progress_info
    download_completed = pyqtSignal(str, str, str)  # task_id, status, error

    def __init__(self, yt_dlp_path: str = 'yt-dlp', ffmpeg_path: str = 'ffmpeg',
                 deno_path: Optional[str] = None, max_concurrent: int = 3):
        super().__init__()
        self.yt_dlp_path = yt_dlp_path
        self.ffmpeg_path = ffmpeg_path
        self.deno_path = deno_path
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self.tasks: Dict[str, DownloadTask] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self._task_counter = 0
        self._lock = threading.Lock()

    def download(self, url: str, format_id: str, output_path: str,
                 cookies_path: Optional[str] = None,
                 title: str = '',
                 platform: str = '',
                 progress_callback: Optional[Any] = None,
                 completed_callback: Optional[Any] = None) -> str:
        """开始下载任务"""
        with self._lock:
            self._task_counter += 1
            task_id = f'task_{self._task_counter}'

        task = DownloadTask(task_id, url, format_id, output_path, title, platform)
        self.tasks[task_id] = task
        print(f"[DEBUG Downloader] Created task {task_id}, total tasks: {len(self.tasks)}")

        thread = threading.Thread(
            target=self._download_thread,
            args=(task_id, cookies_path, progress_callback, completed_callback)
        )
        thread.daemon = True
        thread.start()

        return task_id

    def _download_thread(self, task_id: str, cookies_path: Optional[str],
                          progress_callback: Optional[Any], completed_callback: Optional[Any]):
        """下载线程"""
        task = self.tasks.get(task_id)
        if not task:
            return

        self._semaphore.acquire()
        try:
            task.state = DownloadState.DOWNLOADING

            # 生成绝对路径并规范化分隔符
            abs_output_path = Path(task.output_path).resolve()
            abs_output_str = str(abs_output_path).replace('\\', '/')

            cmd = [
                self.yt_dlp_path,
                '-f', task.format_id,
                '-o', abs_output_str,
                '--no-warnings',
                '--newline',
            ]

            if cookies_path and Path(cookies_path).exists():
                cmd.extend(['--cookies', cookies_path])

            # YouTube 需要 Deno 运行时
            if task.platform == 'youtube':
                if self.deno_path:
                    cmd.extend(['--js-runtimes', 'deno', '--js-deno-path', self.deno_path])
                else:
                    cmd.extend(['--js-runtimes', 'deno'])

            cmd.extend(['--merge-output-format', 'mp4'])
            cmd.extend(['--ffmpeg-location', self.ffmpeg_path])
            cmd.append(task.url)

            # Debug: 打印完整命令和当前目录
            import os
            print(f"[DEBUG] Working dir: {os.getcwd()}")
            print(f"[DEBUG] Output path: {abs_output_str}")
            print(f"[DEBUG] Platform: {task.platform}")
            print(f"[DEBUG] Full command: {' '.join(cmd)}")
            print(f"[DEBUG] ffmpeg exists: {os.path.exists(self.ffmpeg_path)}")

            # 执行下载
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',  # 替换无法解码的字符
                bufsize=1  # 行缓冲
            )
            self.processes[task_id] = process

            # yt-dlp 使用 --no-warnings 时输出到 stdout
            stdout_lines = []
            stderr_lines = []

            import threading

            def read_stdout():
                for line in process.stdout:
                    stdout_lines.append(line)
                    if '[download]' in line:
                        progress = self._parse_progress(line, task_id)
                        if progress:
                            # 更新任务的进度属性
                            if 'progress' in progress and progress['progress'] >= 0:
                                task.progress = progress['progress']
                            self.progress_updated.emit(task_id, progress)
                    if '[ffmpeg]' in line.lower() or 'merging' in line.lower():
                        print(f"[DEBUG] FFmpeg: {line.strip()}")
                    if ' Deleting' in line:
                        print(f"[DEBUG] Cleanup: {line.strip()}")

            def read_stderr():
                for line in process.stderr:
                    stderr_lines.append(line)

            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()

            # 等待进程完成
            process.wait()

            # 等待读取线程完成
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)

            stderr_text = ''.join(stderr_lines)

            print(f"[DEBUG] Process return code: {process.returncode}")
            print(f"[DEBUG] Stderr length: {len(stderr_text)}")
            print(f"[DEBUG] Number of stderr lines: {len(stderr_lines)}")
            if stderr_lines:
                print(f"[DEBUG] First stderr line: {stderr_lines[0][:100] if stderr_lines[0] else '(empty)'}")
                print(f"[DEBUG] Last stderr line: {stderr_lines[-1][:100] if stderr_lines[-1] else '(empty)'}")
            if process.returncode != 0:
                print(f"[DEBUG] Error output (first 500 chars): {stderr_text[:500]}")

            if process.returncode == 0:
                task.state = DownloadState.COMPLETED
                task.progress = 100.0
                self.download_completed.emit(task_id, 'completed', '')
            else:
                task.state = DownloadState.FAILED
                task.error = stderr_text or '下载失败'
                print(f"[DEBUG] Download failed: {task.error}")
                self.download_completed.emit(task_id, 'failed', task.error)

        except Exception as e:
            task.state = DownloadState.FAILED
            task.error = str(e)
            self.download_completed.emit(task_id, 'failed', str(e))

        finally:
            self._semaphore.release()
            if task_id in self.processes:
                del self.processes[task_id]

    def _parse_progress(self, line: str, task_id: str) -> Optional[Dict]:
        """解析下载进度"""
        import re

        match = re.search(r'\[download\]\s+(\d+\.?\d*)%\s+of\s+([^\s]+)\s+at\s+(.+?)\s+ETA\s+([^\s]+)', line)
        if match:
            return {
                'progress': float(match.group(1)),
                'size': match.group(2),
                'speed': match.group(3),
                'eta': match.group(4),
            }

        if 'merging' in line.lower() or ' merging' in line.lower():
            return {'progress': -1, 'status': 'merging'}

        return None

    def pause(self, task_id: str) -> bool:
        """暂停任务"""
        if task_id in self.processes:
            try:
                self.processes[task_id].terminate()
                self.tasks[task_id].state = DownloadState.PAUSED
                return True
            except Exception as e:
                print(f"暂停任务失败: {e}")
        return False

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.processes:
            try:
                self.processes[task_id].terminate()
                del self.processes[task_id]
            except Exception:
                pass

        if task_id in self.tasks:
            self.tasks[task_id].state = DownloadState.CANCELLED
            for f in self.tasks[task_id].temp_files:
                try:
                    if Path(f).exists():
                        Path(f).unlink()
                except Exception:
                    pass

        return True

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, DownloadTask]:
        return self.tasks.copy()

    def clear_completed(self):
        completed = [tid for tid, t in self.tasks.items()
                     if t.state in [DownloadState.COMPLETED, DownloadState.CANCELLED, DownloadState.FAILED]]
        for tid in completed:
            del self.tasks[tid]

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                [self.yt_dlp_path, '--version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False