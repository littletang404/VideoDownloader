"""视频链接解析模块 - 自动识别平台并获取视频信息"""
import re
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, List, Any


class LinkParser:
    """视频链接解析器"""

    # 平台正则匹配
    PATTERNS = {
        'youtube': r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/',
        'bilibili': r'(?:https?://)?(?:www\.)?bilibili\.com/',
        'weibo': r'(?:https?://)?(?:www\.)?(?:weibo\.com|t\.cn)/',
        'xiaohongshu': r'(?:https?://)?(?:www\.)?xiaohongshu\.com/',
        'm3u8': r'.*\.m3u8(?:\?.*)?$',
    }

    def __init__(self, yt_dlp_path: str = 'yt-dlp', ffmpeg_path: str = 'ffmpeg'):
        self.yt_dlp_path = yt_dlp_path
        self.ffmpeg_path = ffmpeg_path

    def identify_platform(self, url: str) -> Optional[str]:
        """识别视频平台"""
        if re.match(self.PATTERNS['youtube'], url):
            return 'youtube'
        elif re.match(self.PATTERNS['bilibili'], url):
            return 'bilibili'
        elif re.match(self.PATTERNS['weibo'], url):
            return 'weibo'
        elif re.match(self.PATTERNS['xiaohongshu'], url):
            return 'xiaohongshu'
        elif re.match(self.PATTERNS['m3u8'], url):
            return 'm3u8'
        return None

    def parse(self, url: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        """解析视频URL，返回视频信息"""
        platform = self.identify_platform(url)
        if not platform:
            raise ValueError(f"不支持的链接格式: {url}")

        # 微博短链接需要先解析真实URL
        if platform == 'weibo' and 't.cn' in url:
            url = self._resolve_short_url(url)
            if not url:
                raise ValueError("微博短链接解析失败")

        if platform == 'm3u8':
            return self._parse_m3u8(url)
        else:
            return self._parse_yt_dlp(url, cookies_path, platform)

    def _resolve_short_url(self, url: str) -> Optional[str]:
        """解析短链接的真实URL"""
        import urllib.request
        import urllib.parse
        import urllib.error
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response = urllib.request.urlopen(req, timeout=10)
            final_url = response.geturl()
            print(f"[DEBUG] Resolved short URL: {url} -> {final_url}")

            # 如果重定向到 passport 页面，尝试从 url 参数中提取真实地址
            if 'passport.weibo.com' in final_url:
                parsed = urllib.parse.urlparse(final_url)
                params = urllib.parse.parse_qs(parsed.query)
                if 'url' in params:
                    real_url = urllib.parse.unquote(params['url'][0])
                    print(f"[DEBUG] Extracted real URL from passport: {real_url}")
                    return real_url

            return final_url
        except Exception as e:
            print(f"[DEBUG] Failed to resolve short URL: {e}")
            return None

    def _parse_m3u8(self, url: str) -> Dict[str, Any]:
        """解析 m3u8 直链"""
        return {
            'platform': 'm3u8',
            'url': url,
            'title': self._extract_title_from_url(url),
            'formats': [{'format_id': 'm3u8', 'ext': 'mp4', 'resolution': '原始'}],
            'thumbnail': None,
            'duration': None,
        }

    def _parse_yt_dlp(self, url: str, cookies_path: Optional[str], platform: str) -> Dict[str, Any]:
        """使用 yt-dlp 解析视频信息"""
        cmd = [
            self.yt_dlp_path,
            '--dump-json',
            '--no-download',
            '--no-warnings',
        ]

        if cookies_path and Path(cookies_path).exists():
            cmd.extend(['--cookies', cookies_path])

        # YouTube 需要 Deno 运行时
        if platform == 'youtube':
            cmd.extend(['--js-runtimes', 'deno'])

        # 微博视频不需要特殊处理
        cmd.append(url)

        print(f"[DEBUG] yt-dlp command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            print(f"[DEBUG] yt-dlp return code: {result.returncode}")
            if result.returncode != 0:
                print(f"[DEBUG] yt-dlp stderr: {result.stderr}")
                raise RuntimeError(f"解析失败: {result.stderr}")

            data = json.loads(result.stdout)
            return self._format_video_info(data, platform)
        except subprocess.CalledProcessError as e:
            print(f"[DEBUG] CalledProcessError: {e}")
            raise RuntimeError(f"解析失败: {e.stderr}")

    def _format_video_info(self, data: Dict, platform: str) -> Dict[str, Any]:
        """格式化视频信息"""
        formats = []
        for f in data.get('formats', []):
            format_id = f.get('format_id', '')
            ext = f.get('ext', '')
            resolution = f.get('resolution', '未知')
            filesize = f.get('filesize', 0) or f.get('filesize_approx', 0)

            # 简化分辨率显示
            if f.get('width') and f.get('height'):
                resolution = f"{f['width']}x{f['height']}"
            elif f.get('height'):
                resolution = f"{f['height']}p"

            # 过滤无效格式
            if not ext:
                continue

            formats.append({
                'format_id': format_id,
                'ext': ext,
                'resolution': resolution,
                'filesize': filesize,
                'vcodec': f.get('vcodec', 'none'),
                'acodec': f.get('acodec', 'none'),
                'tbr': f.get('tbr', 0),
            })

        return {
            'platform': platform,
            'url': data.get('webpage_url', ''),
            'title': data.get('title', '未知标题'),
            'thumbnail': data.get('thumbnail'),
            'duration': data.get('duration'),
            'description': data.get('description', ''),
            'uploader': data.get('uploader', ''),
            'upload_date': data.get('upload_date', ''),
            'formats': formats,
        }

    def _extract_title_from_url(self, url: str) -> str:
        """从 URL 中提取标题（m3u8 用）"""
        # 尝试从路径中提取
        path = url.split('?')[0]
        parts = path.rstrip('/').split('/')
        if parts:
            return parts[-1]
        return 'm3u8_video'

    def get_best_formats(self, formats: List[Dict]) -> tuple:
        """获取最佳视频和音频格式组合"""
        video_formats = [f for f in formats if f['vcodec'] != 'none' and f['acodec'] == 'none']
        audio_formats = [f for f in formats if f['vcodec'] == 'none' and f['acodec'] != 'none']

        # 按文件大小或比特率排序
        video_formats.sort(key=lambda x: x.get('filesize', 0) or x.get('tbr', 0), reverse=True)
        audio_formats.sort(key=lambda x: x.get('filesize', 0) or x.get('tbr', 0), reverse=True)

        best_video = video_formats[0] if video_formats else None
        best_audio = audio_formats[0] if audio_formats else None

        return best_video, best_audio

    def select_format_by_resolution(self, formats: List[Dict], resolution: str) -> tuple:
        """按分辨率选择格式，返回 (视频format_id, 音频format_id)"""
        target_height = int(resolution.rstrip('p'))

        # 找最接近目标分辨率的视频格式
        video_formats = [f for f in formats if f['vcodec'] != 'none' and f['acodec'] == 'none']
        video_formats.sort(key=lambda x: abs(int(x['resolution'].rstrip('p').split('x')[-1]) - target_height) if x['resolution'] != '未知' else 9999)

        # 找最佳音频格式
        audio_formats = [f for f in formats if f['vcodec'] == 'none' and f['acodec'] != 'none']
        audio_formats.sort(key=lambda x: x.get('filesize', 0) or x.get('tbr', 0), reverse=True)

        best_video = video_formats[0] if video_formats else None
        best_audio = audio_formats[0] if audio_formats else None

        return best_video, best_audio