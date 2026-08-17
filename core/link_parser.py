"""Video URL parsing powered by the embedded yt-dlp API."""
from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import yt_dlp

from .runtime import build_js_runtime_config, summarize_process_error


class LinkParser:
    """Identify direct streams and delegate websites to yt-dlp."""

    PATTERNS = {
        "youtube": r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/",
        "bilibili": r"(?:https?://)?(?:www\.)?(?:bilibili\.com|b23\.tv)/",
        "weibo": r"(?:https?://)?(?:www\.)?(?:weibo\.com|t\.cn)/",
        "xiaohongshu": r"(?:https?://)?(?:www\.)?(?:xiaohongshu\.com|xhslink\.com)/",
        "douyin": r"(?:https?://)?(?:www\.|v\.)?douyin\.com/",
    }
    SHORT_HOSTS = {"t.cn", "b23.tv", "xhslink.com", "v.douyin.com"}

    def __init__(
        self,
        yt_dlp_path: str = "yt-dlp",
        ffmpeg_path: str = "",
        deno_path: Optional[str] = None,
    ):
        self.yt_dlp_path = yt_dlp_path
        self.ffmpeg_path = ffmpeg_path
        self.deno_path = deno_path

    @staticmethod
    def normalize_url(url: str) -> str:
        """Convert supported share-page URLs into extractor-friendly URLs."""
        value = (url or "").strip()
        parsed = urllib.parse.urlparse(value)
        host = (parsed.hostname or "").lower()
        path = parsed.path.rstrip("/")
        is_jingxuan = path == "/jingxuan" or path.startswith("/jingxuan/")
        if host in {"douyin.com", "www.douyin.com"} and is_jingxuan:
            modal_id = (urllib.parse.parse_qs(parsed.query).get("modal_id") or [""])[0]
            if re.fullmatch(r"\d{10,24}", modal_id):
                return f"https://www.douyin.com/video/{modal_id}"
        return value

    def identify_platform(self, url: str) -> Optional[str]:
        value = (url or "").strip()
        if not value:
            return None
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        if re.search(r"\.m3u8(?:$|[?#])", value, re.IGNORECASE):
            return "m3u8"
        for platform, pattern in self.PATTERNS.items():
            if re.match(pattern, value, re.IGNORECASE):
                return platform
        return "generic"

    def parse(self, url: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        original_url = self.normalize_url(url)
        platform = self.identify_platform(original_url)
        if not platform:
            raise ValueError("请输入完整的 http:// 或 https:// 视频链接")

        parsed = urllib.parse.urlparse(original_url)
        if parsed.netloc.lower() in self.SHORT_HOSTS:
            resolved = self._resolve_short_url(original_url)
            if resolved:
                original_url = resolved
                platform = self.identify_platform(original_url) or platform

        if platform == "m3u8":
            return self._parse_m3u8(original_url)
        return self._parse_yt_dlp(original_url, cookies_path, platform)

    def _resolve_short_url(self, url: str) -> Optional[str]:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                final_url = response.geturl()
            if "passport.weibo.com" in final_url:
                params = urllib.parse.parse_qs(urllib.parse.urlparse(final_url).query)
                if params.get("url"):
                    return urllib.parse.unquote(params["url"][0])
            return final_url
        except (OSError, urllib.error.URLError):
            return None

    @staticmethod
    def _parse_m3u8(url: str) -> Dict[str, Any]:
        path = urllib.parse.urlparse(url).path
        title = urllib.parse.unquote(Path(path).stem) or "m3u8_video"
        return {
            "platform": "m3u8",
            "url": url,
            "title": title,
            "formats": [
                {
                    "format_id": "m3u8",
                    "ext": "mp4",
                    "resolution": "原始画质",
                    "height": 0,
                    "vcodec": "unknown",
                    "acodec": "unknown",
                }
            ],
            "thumbnail": None,
            "duration": None,
            "uploader": "",
        }

    def _parse_yt_dlp(
        self,
        url: str,
        cookies_path: Optional[str],
        platform: str,
    ) -> Dict[str, Any]:
        options: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            "js_runtimes": build_js_runtime_config(self.deno_path),
        }
        if cookies_path and Path(cookies_path).exists():
            options["cookiefile"] = cookies_path
        if self.ffmpeg_path:
            options["ffmpeg_location"] = self.ffmpeg_path

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                data = ydl.extract_info(url, download=False)
                data = ydl.sanitize_info(data)
        except yt_dlp.utils.DownloadError as error:
            raise RuntimeError(
                summarize_process_error(str(error), "视频解析失败")
            ) from error
        except Exception as error:
            raise RuntimeError(f"视频解析失败：{error}") from error

        if isinstance(data, dict) and data.get("_type") == "playlist":
            entries = data.get("entries") or []
            data = next((entry for entry in entries if entry), data)
        if not isinstance(data, dict):
            raise RuntimeError("解析器没有返回可用的视频信息")
        return self._format_video_info(data, platform, url)

    @staticmethod
    def _format_video_info(
        data: Dict[str, Any],
        platform: str,
        source_url: str,
    ) -> Dict[str, Any]:
        formats: List[Dict[str, Any]] = []
        for item in data.get("formats") or []:
            ext = item.get("ext") or ""
            if not ext:
                continue
            width = item.get("width") or 0
            height = item.get("height") or 0
            resolution = item.get("resolution") or (
                f"{width}x{height}" if width and height else f"{height}p" if height else "未知"
            )
            formats.append(
                {
                    "format_id": item.get("format_id", ""),
                    "format_note": item.get("format_note", ""),
                    "ext": ext,
                    "resolution": resolution,
                    "width": width,
                    "height": height,
                    "fps": item.get("fps") or 0,
                    "filesize": item.get("filesize") or item.get("filesize_approx") or 0,
                    "vcodec": item.get("vcodec") or "none",
                    "acodec": item.get("acodec") or "none",
                    "tbr": item.get("tbr") or 0,
                    "language": item.get("language") or "",
                    "dynamic_range": item.get("dynamic_range") or "",
                }
            )

        return {
            "platform": platform,
            "url": data.get("webpage_url") or data.get("original_url") or source_url,
            "title": data.get("title") or "未命名视频",
            "thumbnail": data.get("thumbnail"),
            "duration": data.get("duration"),
            "description": data.get("description") or "",
            "uploader": data.get("uploader") or data.get("channel") or "",
            "upload_date": data.get("upload_date") or "",
            "formats": formats,
        }

    @staticmethod
    def available_heights(formats: List[Dict[str, Any]]) -> List[int]:
        heights = {
            int(item.get("height") or 0)
            for item in formats
            if item.get("vcodec") != "none" and int(item.get("height") or 0) > 0
        }
        return sorted(heights, reverse=True)
