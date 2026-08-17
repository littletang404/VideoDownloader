"""VideoDownloader application entry point."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from VideoDownloader.ui.main_window import MainWindow
from VideoDownloader.utils import data_path, get_resource_path


DEFAULT_CONFIG = {
    "download_path": str(Path.home() / "Downloads"),
    "max_concurrent": 3,
    "ffmpeg_custom": False,
    "ffmpeg_path": "",
    "deno_custom": False,
    "deno_path": "",
    "cookie_path": "cookies",
}


def load_config() -> dict:
    config_path = data_path("config/settings.json")
    config = DEFAULT_CONFIG.copy()
    if config_path.exists():
        try:
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                config.update(saved)
        except (OSError, ValueError) as error:
            print(f"加载配置失败: {error}")
    return config


def main() -> None:
    smoke_test = "--smoke-test" in sys.argv
    app = QApplication(sys.argv)
    app.setApplicationName("万能视频下载器")
    app.setOrganizationName("VideoDownloader")
    app.setWindowIcon(QIcon(get_resource_path("resources/app_icon.png")))
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 10))

    window = MainWindow(load_config())
    if smoke_test:
        window.ensurePolished()
        app.processEvents()
        window.deleteLater()
        app.processEvents()
        return

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
