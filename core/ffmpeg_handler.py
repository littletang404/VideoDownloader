"""ffmpeg wrapper for HLS downloads and local transcoding."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional

from VideoDownloader.utils import find_tool


_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class FFmpegHandler:
    def __init__(self, ffmpeg_path: str = ""):
        self.ffmpeg_path = ffmpeg_path
        self.last_error = ""

    def merge_av(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-i", audio_path,
            "-c", "copy",
            "-y",
            output_path,
        ]
        return self._run_command(cmd, progress_callback)

    def transcode(
        self,
        input_path: str,
        output_path: str,
        video_codec: str = "copy",
        audio_codec: str = "copy",
        video_bitrate: Optional[str] = None,
        audio_bitrate: str = "192k",
        resolution: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        duration = self.get_duration(input_path)
        if resolution and video_codec == "copy":
            video_codec = "h264"

        cmd = [self.ffmpeg_path, "-i", input_path, "-y"]
        video_options = {
            "copy": ["-c:v", "copy"],
            "h264": ["-c:v", "libx264", "-preset", "medium"],
            "h265": ["-c:v", "libx265", "-preset", "medium"],
            "av1": ["-c:v", "libaom-av1", "-cpu-used", "4"],
        }
        cmd.extend(video_options.get(video_codec, video_options["h264"]))
        if video_bitrate and video_codec != "copy":
            cmd.extend(["-b:v", video_bitrate])

        audio_options = {
            "copy": ["-c:a", "copy"],
            "aac": ["-c:a", "aac", "-b:a", audio_bitrate],
            "mp3": ["-c:a", "libmp3lame", "-b:a", audio_bitrate],
            "flac": ["-c:a", "flac"],
        }
        cmd.extend(audio_options.get(audio_codec, audio_options["aac"]))

        if resolution:
            if resolution.endswith("p"):
                height = resolution[:-1]
                cmd.extend(["-vf", f"scale=-2:{height}"])
            elif re.fullmatch(r"\d{2,5}x\d{2,5}", resolution):
                cmd.extend(["-vf", f"scale={resolution}"])
            else:
                self.last_error = "分辨率格式不正确，请使用 1920x1080 或 1080p"
                return False

        cmd.append(output_path)
        return self._run_command(cmd, progress_callback, duration)

    def download_m3u8(
        self,
        m3u8_url: str,
        output_path: str,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        cmd = [
            self.ffmpeg_path,
            "-i", m3u8_url,
            "-c", "copy",
            "-y",
            output_path,
        ]
        return self._run_command(cmd, progress_callback)

    def get_media_info(self, file_path: str) -> Optional[Dict]:
        preferred_dir = str(Path(self.ffmpeg_path).parent) if self.ffmpeg_path else ""
        ffprobe_path = find_tool("ffprobe", preferred_dir=preferred_dir)
        if not ffprobe_path:
            self.last_error = "未找到 ffprobe，无法读取媒体时长"
            return None
        cmd = [
            ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                creationflags=_NO_WINDOW,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            self.last_error = result.stderr.strip() or "ffprobe 读取失败"
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
            self.last_error = str(error)
        return None

    def _run_command(
        self,
        cmd: List[str],
        progress_callback: Optional[Callable] = None,
        duration: float = 0.0,
    ) -> bool:
        self.last_error = ""
        if not self.ffmpeg_path:
            self.last_error = "未找到 ffmpeg，请在设置中配置"
            return False

        output_path = Path(cmd[-1]).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_lines: list[str] = []
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=_NO_WINDOW,
            )
            if process.stderr:
                for line in process.stderr:
                    stderr_lines.append(line.rstrip())
                    if len(stderr_lines) > 160:
                        del stderr_lines[:80]
                    if progress_callback and "time=" in line:
                        current_time = self._parse_progress(line)
                        progress_callback(
                            min(100.0, current_time / duration * 100.0)
                            if duration > 0 else -1.0
                        )
            return_code = process.wait()
            if return_code == 0:
                if progress_callback:
                    progress_callback(100.0)
                return True
            useful = [line for line in stderr_lines if line.strip()]
            self.last_error = "\n".join(useful[-10:])[-1800:] or "ffmpeg 执行失败"
            return False
        except FileNotFoundError:
            self.last_error = "未找到 ffmpeg，请在设置中配置"
            return False
        except Exception as error:
            self.last_error = str(error)
            return False

    @staticmethod
    def _parse_progress(line: str) -> float:
        match = re.search(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", line)
        if not match:
            return 0.0
        hours, minutes, seconds = match.groups()
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    def get_duration(self, file_path: str) -> float:
        info = self.get_media_info(file_path)
        try:
            return float((info or {}).get("format", {}).get("duration") or 0)
        except (TypeError, ValueError):
            return 0.0

    def is_available(self) -> bool:
        if not self.ffmpeg_path:
            return False
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                timeout=5,
                creationflags=_NO_WINDOW,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
