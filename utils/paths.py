"""Application and bundled-tool path helpers."""
from __future__ import annotations

import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def app_root() -> Path:
    """Return the portable application directory."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def data_path(path: str | Path) -> Path:
    """Resolve user-writable data relative to the portable app directory."""
    value = Path(path).expanduser()
    return value if value.is_absolute() else app_root() / value


def _candidate_paths(name: str, preferred_dir: Optional[str | Path] = None) -> Iterable[Path]:
    exe_name = f"{name}.exe" if sys.platform == "win32" else name
    root = app_root()

    if preferred_dir:
        preferred = Path(preferred_dir)
        yield preferred / exe_name if preferred.is_dir() else preferred

    yield root / "tools" / exe_name
    yield root / "tools" / name / exe_name
    yield root / "bundled" / name / exe_name
    if name == "deno":
        yield Path.home() / ".deno" / "bin" / exe_name

    if name in {"ffmpeg", "ffprobe"}:
        yield root / "tools" / "ffmpeg" / "bin" / exe_name
        for build in sorted((root / "tools" / "ffmpeg_full").glob("*/bin")):
            yield build / exe_name
        yield root / "tools" / "ffmpeg_bin" / exe_name

    system_path = shutil.which(name)
    if system_path:
        yield Path(system_path)


def _probe(path: Path, name: str) -> bool:
    if not path.exists() or not path.is_file():
        return False
    version_flag = "--version" if name == "deno" else "-version"
    try:
        result = subprocess.run(
            [str(path), version_flag],
            capture_output=True,
            timeout=4,
            creationflags=_NO_WINDOW,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@lru_cache(maxsize=32)
def find_tool(name: str, custom_path: str = "", preferred_dir: str = "") -> str:
    """Return a verified executable path or an empty string."""
    if custom_path:
        custom = Path(custom_path).expanduser()
        if _probe(custom, name):
            return str(custom.resolve())
        return ""

    seen: set[str] = set()
    for candidate in _candidate_paths(name, preferred_dir or None):
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if _probe(candidate, name):
            return str(candidate.resolve())
    return ""


def clear_tool_cache() -> None:
    find_tool.cache_clear()
