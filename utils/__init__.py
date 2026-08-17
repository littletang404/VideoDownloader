"""Shared utility helpers."""
from __future__ import annotations

import os
import sys

from .paths import (
    PROJECT_ROOT,
    app_root,
    clear_tool_cache,
    data_path,
    find_tool,
)


def get_resource_path(relative_path: str) -> str:
    """Return a read-only resource path, including PyInstaller bundles."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = str(PROJECT_ROOT)
    return os.path.join(base_path, relative_path)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def format_size(size: int) -> str:
    if not size:
        return "未知"
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return "未知"


def format_duration(seconds: float) -> str:
    if not seconds:
        return "未知"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}小时{minutes}分"
    if minutes:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


def clean_filename(filename: str) -> str:
    value = filename.strip().rstrip(". ")
    for char in '/\\:*?"<>|':
        value = value.replace(char, "_")
    return value[:180] or "video"


__all__ = [
    "PROJECT_ROOT",
    "app_root",
    "clear_filename",
    "clear_tool_cache",
    "data_path",
    "ensure_dir",
    "find_tool",
    "format_duration",
    "format_size",
    "get_resource_path",
]
