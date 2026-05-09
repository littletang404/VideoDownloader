"""ffmpeg 处理模块 - 视频合并、格式转换"""
import subprocess
import os
from pathlib import Path
from typing import Optional, List, Dict, Callable


class FFmpegHandler:
    """ffmpeg 处理器"""

    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        self.ffmpeg_path = ffmpeg_path

    def merge_av(self, video_path: str, audio_path: str, output_path: str,
                 progress_callback: Optional[Callable] = None) -> bool:
        """合并视频和音频"""
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-i', audio_path,
            '-c', 'copy',  # 直接复制，不重新编码
            '-y',  # 覆盖输出
            output_path
        ]

        return self._run_command(cmd, progress_callback)

    def transcode(self, input_path: str, output_path: str,
                  video_codec: str = 'copy', audio_codec: str = 'copy',
                  video_bitrate: Optional[str] = None,
                  audio_bitrate: str = '192k',
                  resolution: Optional[str] = None,
                  progress_callback: Optional[Callable] = None) -> bool:
        """转码视频

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            video_codec: 视频编码 (copy, h264, h265, av1)
            audio_codec: 音频编码 (copy, aac, mp3, flac)
            video_bitrate: 视频比特率 (如 '5M')
            audio_bitrate: 音频比特率 (如 '192k')
            resolution: 分辨率 (如 '1920x1080' 或 '1080p')
            progress_callback: 进度回调函数（返回百分比 0-100）
        """
        # 获取视频时长用于计算百分比
        duration = self.get_duration(input_path)
        cmd = [
            self.ffmpeg_path,
            '-i', input_path,
            '-y',
        ]

        # 视频编码
        if video_codec == 'copy':
            cmd.extend(['-c:v', 'copy'])
        elif video_codec == 'h264':
            cmd.extend(['-c:v', 'libx264', '-preset', 'medium'])
            if video_bitrate:
                cmd.extend(['-b:v', video_bitrate])
        elif video_codec == 'h265':
            cmd.extend(['-c:v', 'libx265', '-preset', 'medium'])
            if video_bitrate:
                cmd.extend(['-b:v', video_bitrate])
        elif video_codec == 'av1':
            cmd.extend(['-c:v', 'libaom-av1', '-cpu-used', '4'])
            if video_bitrate:
                cmd.extend(['-b:v', video_bitrate])

        # 音频编码
        if audio_codec == 'copy':
            cmd.extend(['-c:a', 'copy'])
        elif audio_codec == 'aac':
            cmd.extend(['-c:a', 'aac', '-b:a', audio_bitrate])
        elif audio_codec == 'mp3':
            cmd.extend(['-c:a', 'libmp3lame', '-b:a', audio_bitrate])
        elif audio_codec == 'flac':
            cmd.extend(['-c:a', 'flac'])

        # 分辨率
        if resolution:
            if resolution.endswith('p'):
                # 设置高度，保持宽高比
                cmd.extend(['-vf', f'scale=-2:{resolution.rstrip("p")}'])
            else:
                cmd.extend(['-vf', f'scale={resolution}'])

        cmd.append(output_path)

        return self._run_command(cmd, progress_callback, duration)

    def download_m3u8(self, m3u8_url: str, output_path: str,
                      progress_callback: Optional[Callable] = None) -> bool:
        """下载 m3u8 视频"""
        # m3u8 无法预先获取时长，使用不确定进度
        duration = 0.0
        cmd = [
            self.ffmpeg_path,
            '-i', m3u8_url,
            '-c', 'copy',
            '-y',
            output_path
        ]

        return self._run_command(cmd, progress_callback, duration)

    def get_media_info(self, file_path: str) -> Optional[Dict]:
        """获取媒体文件信息"""
        # 使用与 ffmpeg 相同目录的 ffprobe
        ffprobe_path = str(Path(self.ffmpeg_path).parent / 'ffprobe.exe')
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
        except Exception as e:
            print(f"获取媒体信息失败: {e}")
        return None

    def _run_command(self, cmd: List[str], progress_callback: Optional[Callable] = None, duration: float = 0.0) -> bool:
        """执行 ffmpeg 命令"""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # 解析进度
            for line in process.stderr:
                if progress_callback and 'time=' in line:
                    current_time = self._parse_progress(line)
                    if duration > 0:
                        # 计算百分比
                        percent = min(100, (current_time / duration) * 100)
                        progress_callback(percent)
                    else:
                        # 无法计算百分比，发送 -1 表示不确定进度
                        progress_callback(-1)

            process.wait()
            return process.returncode == 0

        except Exception as e:
            print(f"ffmpeg 执行失败: {e}")
            return False

    def _parse_progress(self, line: str) -> float:
        """解析 ffmpeg 输出进度"""
        import re
        match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds
        return 0.0

    def get_duration(self, file_path: str) -> float:
        """获取视频时长（秒）"""
        info = self.get_media_info(file_path)
        if info and 'format' in info:
            return float(info['format'].get('duration', 0))
        return 0.0

    def is_available(self) -> bool:
        """检查 ffmpeg 是否可用"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False