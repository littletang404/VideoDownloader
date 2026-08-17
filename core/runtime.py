"""Shared yt-dlp runtime helpers."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def build_js_runtime_args(deno_path: Optional[str]) -> list[str]:
    """Build current yt-dlp CLI arguments for an optional Deno runtime."""
    if not deno_path:
        return []
    value = str(deno_path)
    runtime = "deno" if value.lower() == "deno" else f"deno:{Path(value).resolve()}"
    return ["--js-runtimes", runtime]


def build_js_runtime_config(deno_path: Optional[str]) -> dict:
    """Build the Python API js_runtimes option."""
    if not deno_path or str(deno_path).lower() == "deno":
        return {"deno": {}}
    return {"deno": {"path": str(Path(deno_path).resolve())}}


def clean_console_text(value: str) -> str:
    return _ANSI.sub("", value or "").strip()


def summarize_process_error(stderr: str, fallback: str = "操作失败") -> str:
    cleaned = clean_console_text(stderr)
    lowered = cleaned.lower()
    if "fresh cookies" in lowered and "douyin" in lowered:
        return (
            "抖音要求提供刚从浏览器导出的 Cookie。\n"
            "请在右上角「Cookie」中选择「抖音」，导入最新 cookies.txt 后重新解析。"
        )

    if "http error 412" in lowered and "bilibili" in lowered:
        return (
            "Bilibili 拒绝了本次解析请求（HTTP 412）。\n"
            "请确认程序已更新；若仍失败，请导入最新 Bilibili Cookie，"
            "等待几分钟后重试。"
        )

    lines = [clean_console_text(line) for line in (stderr or "").splitlines()]
    useful = [
        line for line in lines
        if line and not line.lower().startswith(("[debug]", "debug:"))
    ]
    return ("\n".join(useful[-8:])[-1600:] if useful else fallback)
