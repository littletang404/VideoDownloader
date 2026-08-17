"""Modern main window for the universal video downloader."""
from __future__ import annotations

import json
import shutil
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QByteArray, Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from VideoDownloader.core.cookie_manager import CookieManager
from VideoDownloader.core.downloader import (
    DownloadState,
    DownloadTask,
    Downloader,
)
from VideoDownloader.core.ffmpeg_handler import FFmpegHandler
from VideoDownloader.core.link_parser import LinkParser
from VideoDownloader.core.task_manager import TaskManager, TaskRecord
from VideoDownloader.ui.cookie_dialog import CookieDialog
from VideoDownloader.ui.settings_dialog import SettingsDialog
from VideoDownloader.ui.theme import apply_theme
from VideoDownloader.ui.transcode_dialog import TranscodeDialog
from VideoDownloader.utils import (
    clean_filename,
    clear_tool_cache,
    data_path,
    find_tool,
    format_duration,
)


class ParseThread(QThread):
    parsed = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, parser: LinkParser, url: str, cookies_path: Optional[str]):
        super().__init__()
        self.parser = parser
        self.url = url
        self.cookies_path = cookies_path

    def run(self) -> None:
        try:
            self.parsed.emit(self.parser.parse(self.url, self.cookies_path))
        except Exception as error:
            self.failed.emit(str(error))


class ThumbnailThread(QThread):
    loaded = pyqtSignal(bytes)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self) -> None:
        try:
            request = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = response.read(5 * 1024 * 1024)
            self.loaded.emit(payload)
        except Exception:
            return


class M3u8DownloadThread(QThread):
    progress = pyqtSignal(float)
    completed = pyqtSignal(bool, str)

    def __init__(self, handler: FFmpegHandler, url: str, output_path: str):
        super().__init__()
        self.handler = handler
        self.url = url
        self.output_path = output_path

    def run(self) -> None:
        success = self.handler.download_m3u8(
            self.url,
            self.output_path,
            self.progress.emit,
        )
        self.completed.emit(success, "" if success else self.handler.last_error)


class MainWindow(QMainWindow):
    VERSION = "2.0.4"

    STATUS_TEXT = {
        "pending": "排队中",
        "queued": "排队中",
        "downloading": "下载中",
        "merging": "合并中",
        "completed": "已完成",
        "failed": "失败",
        "cancelled": "已取消",
    }

    def __init__(self, config: dict):
        super().__init__()
        self.config = dict(config)
        self.current_video_info: Optional[dict] = None
        self.parse_thread: Optional[ParseThread] = None
        self.thumbnail_thread: Optional[ThumbnailThread] = None
        self.m3u8_threads: dict[str, M3u8DownloadThread] = {}

        self._init_core()
        self._build_ui()
        self._load_task_history()
        self._update_cookie_status()
        self._update_tool_status()

    def _init_core(self) -> None:
        ffmpeg_path, deno_path = self._resolve_tools()
        yt_dlp_path = shutil.which("yt-dlp") or "yt-dlp"
        self.cookie_manager = CookieManager(self.config.get("cookie_path", "cookies"))
        self.task_manager = TaskManager()
        self.ffmpeg_handler = FFmpegHandler(ffmpeg_path)
        self.link_parser = LinkParser(
            yt_dlp_path=yt_dlp_path,
            ffmpeg_path=ffmpeg_path,
            deno_path=deno_path,
        )
        self.downloader = Downloader(
            yt_dlp_path=yt_dlp_path,
            ffmpeg_path=ffmpeg_path,
            deno_path=deno_path,
            max_concurrent=self.config.get("max_concurrent", 3),
        )
        self.downloader.progress_updated.connect(self._on_download_progress)
        self.downloader.download_completed.connect(self._on_download_complete)

    def _resolve_tools(self) -> tuple[str, str]:
        ffmpeg_custom = (
            self.config.get("ffmpeg_path", "")
            if self.config.get("ffmpeg_custom") else ""
        )
        deno_custom = (
            self.config.get("deno_path", "")
            if self.config.get("deno_custom") else ""
        )
        return find_tool("ffmpeg", ffmpeg_custom), find_tool("deno", deno_custom)

    def _build_ui(self) -> None:
        self.setWindowTitle(f"万能视频下载器 · {self.VERSION}")
        self.setMinimumSize(980, 720)
        self.resize(1180, 820)
        apply_theme(self)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(14)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_url_card())
        layout.addLayout(self._build_workspace(), 2)
        layout.addWidget(self._build_tasks_card(), 3)

        self.status_bar = QStatusBar()
        self.status_bar.showMessage("准备就绪")
        self.setStatusBar(self.status_bar)
        self._install_shortcuts()

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        brand = QVBoxLayout()
        brand.setSpacing(1)
        title = QLabel("万能视频下载器")
        title.setObjectName("AppTitle")
        subtitle = QLabel("一个链接，自动识别画质并完成下载与合并")
        subtitle.setObjectName("AppSubtitle")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        row.addLayout(brand)
        row.addStretch()

        self.tool_health_label = QLabel()
        self.tool_health_label.setProperty("muted", True)
        row.addWidget(self.tool_health_label)

        cookie_btn = QPushButton("Cookie")
        cookie_btn.setProperty("flat", True)
        cookie_btn.clicked.connect(self.open_cookie_manager)
        row.addWidget(cookie_btn)

        transcode_btn = QPushButton("视频转换")
        transcode_btn.setProperty("flat", True)
        transcode_btn.clicked.connect(self.open_transcode)
        row.addWidget(transcode_btn)

        settings_btn = QPushButton("设置")
        settings_btn.setProperty("flat", True)
        settings_btn.clicked.connect(self.open_settings)
        row.addWidget(settings_btn)
        return row

    def _build_url_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("粘贴视频链接")
        title.setObjectName("SectionTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        support = QLabel("YouTube · Bilibili · 抖音 · 微博 · 小红书 · m3u8 · 更多站点")
        support.setProperty("muted", True)
        title_row.addWidget(support)
        layout.addLayout(title_row)

        input_row = QHBoxLayout()
        input_row.setSpacing(9)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://…")
        self.url_edit.returnPressed.connect(self.parse_url)
        input_row.addWidget(self.url_edit, 1)

        paste_btn = QPushButton("粘贴")
        paste_btn.clicked.connect(self._paste_url)
        input_row.addWidget(paste_btn)

        self.parse_btn = QPushButton("解析视频")
        self.parse_btn.setProperty("primary", True)
        self.parse_btn.clicked.connect(self.parse_url)
        input_row.addWidget(self.parse_btn)
        layout.addLayout(input_row)
        return card

    def _build_workspace(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self._build_preview_card(), 6)
        row.addWidget(self._build_download_card(), 5)
        return row

    def _build_preview_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        heading = QLabel("视频信息")
        heading.setObjectName("SectionTitle")
        layout.addWidget(heading)

        media_row = QHBoxLayout()
        media_row.setSpacing(15)
        self.thumbnail_label = QLabel("VIDEO")
        self.thumbnail_label.setObjectName("EmptyIcon")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setFixedSize(196, 112)
        self.thumbnail_label.setStyleSheet(
            "background:#0D1424;border:1px solid #1B2740;border-radius:12px;"
        )
        media_row.addWidget(self.thumbnail_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        self.platform_badge = QLabel("等待解析")
        self.platform_badge.setObjectName("PlatformBadge")
        self.platform_badge.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )
        info_layout.addWidget(self.platform_badge)

        self.video_title_label = QLabel("还没有解析视频")
        self.video_title_label.setObjectName("HeroTitle")
        self.video_title_label.setWordWrap(True)
        info_layout.addWidget(self.video_title_label)

        self.video_meta_label = QLabel("粘贴链接后，标题、来源和时长会显示在这里。")
        self.video_meta_label.setProperty("muted", True)
        self.video_meta_label.setWordWrap(True)
        info_layout.addWidget(self.video_meta_label)
        info_layout.addStretch()
        media_row.addLayout(info_layout, 1)
        layout.addLayout(media_row)

        filename_row = QHBoxLayout()
        filename_row.addWidget(QLabel("保存名称"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("解析后可修改文件名")
        self.title_edit.setEnabled(False)
        filename_row.addWidget(self.title_edit, 1)
        layout.addLayout(filename_row)
        return card

    def _build_download_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(11)

        heading_row = QHBoxLayout()
        heading = QLabel("下载设置")
        heading.setObjectName("SectionTitle")
        heading_row.addWidget(heading)
        heading_row.addStretch()
        self.cookie_status_label = QLabel("无需登录")
        self.cookie_status_label.setObjectName("StatusChip")
        heading_row.addWidget(self.cookie_status_label)
        layout.addLayout(heading_row)

        layout.addWidget(QLabel("画质与格式"))
        self.format_combo = QComboBox()
        self.format_combo.setEnabled(False)
        self.format_combo.addItem("请先解析视频")
        layout.addWidget(self.format_combo)

        layout.addWidget(QLabel("保存位置"))
        path_row = QHBoxLayout()
        self.save_path_edit = QLineEdit(self.config.get("download_path", ""))
        path_row.addWidget(self.save_path_edit, 1)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_save_path)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        self.download_hint_label = QLabel("解析完成后即可开始下载")
        self.download_hint_label.setProperty("muted", True)
        self.download_hint_label.setWordWrap(True)
        layout.addWidget(self.download_hint_label)

        layout.addStretch()
        self.download_btn = QPushButton("开始下载")
        self.download_btn.setProperty("primary", True)
        self.download_btn.setMinimumHeight(40)
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.start_download)
        layout.addWidget(self.download_btn)
        return card

    def _build_tasks_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        heading_row = QHBoxLayout()
        title = QLabel("下载任务")
        title.setObjectName("SectionTitle")
        heading_row.addWidget(title)
        self.task_count_label = QLabel("0 个任务")
        self.task_count_label.setProperty("muted", True)
        heading_row.addWidget(self.task_count_label)
        heading_row.addStretch()
        clear_btn = QPushButton("清空历史")
        clear_btn.setProperty("flat", True)
        clear_btn.clicked.connect(self.clear_task_history)
        heading_row.addWidget(clear_btn)
        layout.addLayout(heading_row)

        self.task_empty_label = QLabel(
            "↓\n还没有下载任务\n解析一个链接，然后选择画质开始下载"
        )
        self.task_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_empty_label.setProperty("muted", True)
        self.task_empty_label.setMinimumHeight(120)
        layout.addWidget(self.task_empty_label, 1)

        self.task_table = QTableWidget(0, 7)
        self.task_table.setHorizontalHeaderLabels(
            ["名称", "来源", "状态", "进度", "速度 / 剩余", "操作", ""]
        )
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.task_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.verticalHeader().setDefaultSectionSize(46)
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.task_table.setColumnWidth(3, 180)
        self.task_table.setColumnWidth(5, 96)
        self.task_table.hideColumn(6)
        self.task_table.setVisible(False)
        layout.addWidget(self.task_table, 1)
        return card

    def _install_shortcuts(self) -> None:
        focus_url = QAction(self)
        focus_url.setShortcut("Ctrl+L")
        focus_url.triggered.connect(self.url_edit.setFocus)
        self.addAction(focus_url)

        settings = QAction(self)
        settings.setShortcut("Ctrl+,")
        settings.triggered.connect(self.open_settings)
        self.addAction(settings)

    def _paste_url(self) -> None:
        value = QApplication.clipboard().text().strip()
        if value:
            self.url_edit.setText(value)
            self.parse_url()

    def parse_url(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            self.status_bar.showMessage("请先粘贴视频链接")
            self.url_edit.setFocus()
            return
        if self.parse_thread and self.parse_thread.isRunning():
            return

        platform = self.cookie_manager.auto_detect_platform(url)
        cookies_path = (
            self.cookie_manager.get_cookie_path_for_yt_dlp(platform)
            if platform else None
        )

        self.current_video_info = None
        self.download_btn.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.parse_btn.setEnabled(False)
        self.parse_btn.setText("正在解析…")
        self.video_title_label.setText("正在读取视频信息…")
        self.video_meta_label.setText("这通常需要几秒钟")
        self.status_bar.showMessage("正在解析视频链接…")

        self.parse_thread = ParseThread(self.link_parser, url, cookies_path)
        self.parse_thread.parsed.connect(self._on_parse_finished)
        self.parse_thread.failed.connect(self._on_parse_error)
        self.parse_thread.start()

    def _on_parse_finished(self, info: dict) -> None:
        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("解析视频")
        self.current_video_info = info
        self._update_preview(info)
        self._populate_formats(info)
        self.download_btn.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.title_edit.setEnabled(True)
        self.status_bar.showMessage("解析完成，可以开始下载")

    def _on_parse_error(self, error: str) -> None:
        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("解析视频")
        self.video_title_label.setText("解析失败")
        self.video_meta_label.setText(error)
        self.status_bar.showMessage("解析失败")
        QMessageBox.warning(self, "无法解析这个链接", error)

    def _update_preview(self, info: dict) -> None:
        title = info.get("title") or "未命名视频"
        platform = (info.get("platform") or "generic").upper()
        uploader = info.get("uploader") or "未知作者"
        duration = format_duration(info.get("duration") or 0)

        self.video_title_label.setText(title)
        self.title_edit.setText(title)
        self.platform_badge.setText(platform)
        self.video_meta_label.setText(f"{uploader}  ·  {duration}")

        self.thumbnail_label.clear()
        self.thumbnail_label.setText("VIDEO")
        thumbnail = info.get("thumbnail")
        if thumbnail:
            self.thumbnail_thread = ThumbnailThread(thumbnail)
            self.thumbnail_thread.loaded.connect(self._set_thumbnail)
            self.thumbnail_thread.start()

    def _set_thumbnail(self, payload: bytes) -> None:
        pixmap = QPixmap()
        if not pixmap.loadFromData(QByteArray(payload)):
            return
        scaled = pixmap.scaled(
            self.thumbnail_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.thumbnail_label.setPixmap(scaled)

    def _populate_formats(self, info: dict) -> None:
        self.format_combo.clear()
        if info.get("platform") == "m3u8":
            self.format_combo.addItem(
                "原始画质（HLS 直链）",
                {"selector": "m3u8", "kind": "m3u8", "label": "原始画质"},
            )
            self.download_hint_label.setText("将使用 ffmpeg 保存原始 HLS 流")
            return

        self.format_combo.addItem(
            "最佳画质（自动）",
            {
                "selector": "bestvideo*+bestaudio/best",
                "kind": "video",
                "label": "最佳画质",
            },
        )

        heights = self.link_parser.available_heights(info.get("formats", []))
        seen = set()
        labels = {
            2160: "4K / 2160p",
            1440: "2K / 1440p",
            1080: "全高清 / 1080p",
            720: "高清 / 720p",
            480: "标清 / 480p",
            360: "流畅 / 360p",
        }
        for height in heights:
            if height in seen or len(seen) >= 7:
                continue
            seen.add(height)
            friendly = labels.get(height, f"{height}p")
            self.format_combo.addItem(
                friendly,
                {
                    "selector": (
                        f"bestvideo[height<={height}]+bestaudio/"
                        f"best[height<={height}]"
                    ),
                    "kind": "video",
                    "label": f"{height}p",
                },
            )

        self.format_combo.addItem(
            "仅音频（最佳音质）",
            {
                "selector": "bestaudio/best",
                "kind": "audio",
                "label": "仅音频",
            },
        )
        self.download_hint_label.setText(
            f"检测到 {len(info.get('formats', []))} 个媒体流，已整理为常用选项"
        )

    def browse_save_path(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "选择保存位置",
            self.save_path_edit.text().strip(),
        )
        if path:
            self.save_path_edit.setText(path)
            self.config["download_path"] = path

    def start_download(self) -> None:
        info = self.current_video_info
        selection = self.format_combo.currentData()
        if not info or not isinstance(selection, dict):
            self.status_bar.showMessage("请先解析并选择画质")
            return

        save_dir = Path(self.save_path_edit.text().strip()).expanduser()
        try:
            save_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            QMessageBox.warning(self, "保存位置不可用", str(error))
            return

        title = clean_filename(self.title_edit.text())
        url = info.get("url") or self.url_edit.text().strip()
        if selection["kind"] == "m3u8":
            output_path = save_dir / f"{title}.mp4"
            if output_path.exists():
                reply = QMessageBox.question(
                    self,
                    "覆盖已有文件",
                    f"{output_path.name} 已存在，是否覆盖？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self._start_m3u8(url, output_path, title)
            return

        output_template = save_dir / f"{title}.%(ext)s"
        platform = info.get("platform") or "generic"
        cookie_platform = self.cookie_manager.auto_detect_platform(url)
        cookies_path = (
            self.cookie_manager.get_cookie_path_for_yt_dlp(cookie_platform)
            if cookie_platform else None
        )
        task_id = self.downloader.download(
            url=url,
            format_id=selection["selector"],
            output_path=str(output_template),
            cookies_path=cookies_path,
            title=title,
            platform=platform,
        )
        self._add_active_task(task_id, selection["label"])
        self.status_bar.showMessage(f"已加入下载队列：{title}")

    def _start_m3u8(self, url: str, output_path: Path, title: str) -> None:
        if not self.ffmpeg_handler.is_available():
            QMessageBox.warning(
                self,
                "ffmpeg 不可用",
                "下载 m3u8 需要 ffmpeg，请先到设置中配置。",
            )
            return
        task_id = f"m3u8_{uuid.uuid4().hex[:10]}"
        task = DownloadTask(task_id, url, "m3u8", str(output_path), title, "m3u8")
        task.state = DownloadState.DOWNLOADING
        self.downloader.tasks[task_id] = task
        self._add_active_task(task_id, "原始画质")

        thread = M3u8DownloadThread(
            self.ffmpeg_handler,
            url,
            str(output_path),
        )
        thread.progress.connect(
            lambda value, tid=task_id: self._on_download_progress(
                tid,
                {
                    "progress": value,
                    "status": "downloading",
                    "speed": "",
                    "eta": "",
                },
            )
        )
        thread.completed.connect(
            lambda success, error, tid=task_id: self._on_m3u8_complete(
                tid, success, error
            )
        )
        thread.finished.connect(lambda tid=task_id: self.m3u8_threads.pop(tid, None))
        self.m3u8_threads[task_id] = thread
        thread.start()
        self.status_bar.showMessage(f"正在下载：{title}")

    def _on_m3u8_complete(self, task_id: str, success: bool, error: str) -> None:
        task = self.downloader.get_task(task_id)
        if task:
            task.state = DownloadState.COMPLETED if success else DownloadState.FAILED
            task.progress = 100.0 if success else task.progress
            task.error = error or None
        self._on_download_complete(
            task_id,
            "completed" if success else "failed",
            error,
        )

    def _load_task_history(self) -> None:
        for index, record in enumerate(reversed(self.task_manager.get_history(40))):
            self._add_history_row(record, index)
        self._sync_task_empty_state()

    def _add_history_row(self, record: TaskRecord, index: int) -> None:
        task_id = f"history:{index}:{record.created_at}"
        row = self.task_table.rowCount()
        self.task_table.insertRow(row)
        self.task_table.setItem(row, 0, QTableWidgetItem(record.title))
        self.task_table.setItem(row, 1, QTableWidgetItem(record.platform.upper()))
        self.task_table.setItem(
            row,
            2,
            QTableWidgetItem(self.STATUS_TEXT.get(record.status, record.status)),
        )

        progress = QProgressBar()
        progress.setValue(100 if record.status == "completed" else 0)
        progress.setFormat("100%" if record.status == "completed" else "—")
        self.task_table.setCellWidget(row, 3, progress)
        self.task_table.setItem(row, 4, QTableWidgetItem("历史记录"))
        self.task_table.setCellWidget(row, 5, self._history_action(record))
        self.task_table.setItem(row, 6, QTableWidgetItem(task_id))

    def _history_action(self, record: TaskRecord) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        if record.status == "completed" and record.output_path:
            button = QPushButton("打开位置")
            button.clicked.connect(
                lambda: self._open_output_location(record.output_path)
            )
        else:
            button = QPushButton("重试")
            button.clicked.connect(lambda: self._retry_record(record))
        row.addWidget(button)
        return widget

    def _add_active_task(self, task_id: str, quality_label: str) -> None:
        task = self.downloader.get_task(task_id)
        if not task:
            return
        self.task_table.insertRow(0)
        self.task_table.setItem(0, 0, QTableWidgetItem(task.title))
        self.task_table.setItem(0, 1, QTableWidgetItem(task.platform.upper()))
        self.task_table.setItem(0, 2, QTableWidgetItem("排队中"))

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setFormat("0%")
        progress.setToolTip(quality_label)
        self.task_table.setCellWidget(0, 3, progress)
        self.task_table.setItem(0, 4, QTableWidgetItem("等待开始"))

        action = QWidget()
        action_layout = QHBoxLayout(action)
        action_layout.setContentsMargins(0, 0, 0, 0)
        cancel_btn = QPushButton("取消")
        if task_id.startswith("m3u8_"):
            cancel_btn.setText("进行中")
            cancel_btn.setEnabled(False)
        else:
            cancel_btn.setProperty("danger", True)
            cancel_btn.clicked.connect(lambda: self.cancel_task(task_id))
        action_layout.addWidget(cancel_btn)
        self.task_table.setCellWidget(0, 5, action)
        self.task_table.setItem(0, 6, QTableWidgetItem(task_id))
        self._sync_task_empty_state()

    def _find_task_row(self, task_id: str) -> int:
        for row in range(self.task_table.rowCount()):
            item = self.task_table.item(row, 6)
            if item and item.text() == task_id:
                return row
        return -1

    def _on_download_progress(self, task_id: str, progress: dict) -> None:
        row = self._find_task_row(task_id)
        if row < 0:
            return
        status = progress.get("status", "downloading")
        progress_bar = self.task_table.cellWidget(row, 3)
        value = float(progress.get("progress") or 0)
        if isinstance(progress_bar, QProgressBar):
            if value < 0:
                progress_bar.setRange(0, 0)
                progress_bar.setFormat("")
            else:
                progress_bar.setRange(0, 100)
                progress_bar.setValue(round(value))
                progress_bar.setFormat(f"{value:.1f}%")
        self.task_table.item(row, 2).setText(
            self.STATUS_TEXT.get(status, status)
        )
        speed = progress.get("speed") or ""
        eta = progress.get("eta") or ""
        detail = " · ".join(part for part in (speed, f"剩余 {eta}" if eta else "") if part)
        self.task_table.item(row, 4).setText(detail or "正在连接…")

    def _on_download_complete(self, task_id: str, status: str, error: str) -> None:
        task = self.downloader.get_task(task_id)
        row = self._find_task_row(task_id)
        if row >= 0:
            self.task_table.item(row, 2).setText(
                self.STATUS_TEXT.get(status, status)
            )
            progress = self.task_table.cellWidget(row, 3)
            if isinstance(progress, QProgressBar):
                progress.setRange(0, 100)
                progress.setValue(100 if status == "completed" else round(task.progress if task else 0))
                progress.setFormat("100%" if status == "completed" else "—")
            self.task_table.item(row, 4).setText(
                "已保存" if status == "completed" else (error[:80] if error else "已取消")
            )
            if task:
                self.task_table.setCellWidget(
                    row,
                    5,
                    self._completed_action(task, status),
                )

        if task:
            self.task_manager.add_record(
                TaskRecord(
                    url=task.url,
                    title=task.title,
                    platform=task.platform,
                    format_id=task.format_id,
                    output_path=task.output_path,
                    status=status,
                    error=error or "",
                )
            )

        if status == "completed":
            self.status_bar.showMessage(f"下载完成：{task.title if task else ''}", 8000)
        elif status == "cancelled":
            self.status_bar.showMessage("任务已取消", 5000)
        else:
            self.status_bar.showMessage("下载失败", 8000)
            QMessageBox.warning(
                self,
                "下载失败",
                error or "下载没有完成，请检查网络、Cookie 或工具设置。",
            )
        self._sync_task_empty_state()

    def _completed_action(self, task: DownloadTask, status: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        if status == "completed":
            button = QPushButton("打开位置")
            button.clicked.connect(lambda: self._open_output_location(task.output_path))
        else:
            button = QPushButton("重试")
            button.clicked.connect(lambda: self._retry_task(task))
        layout.addWidget(button)
        return widget

    def cancel_task(self, task_id: str) -> None:
        if self.downloader.cancel(task_id):
            self.status_bar.showMessage("正在取消任务…")

    def _retry_record(self, record: TaskRecord) -> None:
        self.url_edit.setText(record.url)
        self.parse_url()

    def _retry_task(self, task: DownloadTask) -> None:
        self.url_edit.setText(task.url)
        self.parse_url()

    @staticmethod
    def _open_output_location(output_path: str) -> None:
        value = Path(output_path)
        if "%(" in output_path:
            value = value.parent
        elif value.is_file():
            value = value.parent
        else:
            value = value.parent if value.suffix else value
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(value)))

    def clear_task_history(self) -> None:
        history_rows = [
            row for row in range(self.task_table.rowCount())
            if (self.task_table.item(row, 6) or QTableWidgetItem()).text().startswith("history:")
        ]
        if not history_rows:
            self.status_bar.showMessage("没有可清空的历史记录")
            return
        reply = QMessageBox.question(
            self,
            "清空下载历史",
            "只会删除历史记录，不会删除已下载的视频。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.task_manager.clear_history()
        for row in reversed(history_rows):
            self.task_table.removeRow(row)
        self._sync_task_empty_state()

    def _sync_task_empty_state(self) -> None:
        count = self.task_table.rowCount()
        self.task_empty_label.setVisible(count == 0)
        self.task_table.setVisible(count > 0)
        self.task_count_label.setText(f"{count} 个任务")

    def _update_cookie_status(self) -> None:
        statuses = self.cookie_manager.get_all_cookies_status()
        valid = [name for name, state in statuses.items() if state.get("valid")]
        if valid:
            labels = {
                "youtube": "YouTube",
                "bilibili": "Bilibili",
                "douyin": "抖音",
            }
            self.cookie_status_label.setText(
                "已登录 " + " / ".join(labels[name] for name in valid)
            )
            self.cookie_status_label.setProperty("warning", False)
        else:
            self.cookie_status_label.setText("未导入 Cookie")
            self.cookie_status_label.setProperty("warning", True)
        self.cookie_status_label.style().unpolish(self.cookie_status_label)
        self.cookie_status_label.style().polish(self.cookie_status_label)

    def _update_tool_status(self) -> None:
        ffmpeg_ok = bool(self.ffmpeg_handler.ffmpeg_path)
        deno_ok = bool(self.link_parser.deno_path)
        parts = [
            "ffmpeg ✓" if ffmpeg_ok else "ffmpeg 未配置",
            "Deno ✓" if deno_ok else "Deno 未配置",
        ]
        self.tool_health_label.setText("  ·  ".join(parts))
        if not ffmpeg_ok:
            self.download_hint_label.setText(
                "未检测到 ffmpeg；高画质合并和 m3u8 下载将不可用"
            )

    def open_cookie_manager(self) -> None:
        dialog = CookieDialog(self.cookie_manager, self)
        dialog.changed.connect(self._update_cookie_status)
        dialog.exec()
        self._update_cookie_status()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.config = dialog.get_config()
        self._save_config()
        clear_tool_cache()
        ffmpeg_path, deno_path = self._resolve_tools()
        self.ffmpeg_handler.ffmpeg_path = ffmpeg_path
        self.link_parser.ffmpeg_path = ffmpeg_path
        self.link_parser.deno_path = deno_path
        applied = self.downloader.update_settings(
            ffmpeg_path,
            deno_path,
            self.config.get("max_concurrent", 3),
        )
        self.save_path_edit.setText(self.config.get("download_path", ""))
        self._update_tool_status()
        if not applied:
            self.status_bar.showMessage("工具路径已更新；并发数将在当前任务完成后生效")
        else:
            self.status_bar.showMessage("设置已保存", 5000)

    def open_transcode(self) -> None:
        TranscodeDialog(self.ffmpeg_handler, self).exec()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于万能视频下载器",
            f"万能视频下载器 {self.VERSION}\n\n"
            "基于 PyQt6、yt-dlp 与 ffmpeg。\n"
            "请仅下载你有权保存和使用的内容。",
        )

    def _save_config(self) -> None:
        path = data_path("config/settings.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def closeEvent(self, event) -> None:
        running_m3u8 = any(thread.isRunning() for thread in self.m3u8_threads.values())
        if running_m3u8:
            QMessageBox.information(
                self,
                "仍有任务运行",
                "m3u8 下载仍在进行中，请等待完成后再退出。",
            )
            event.ignore()
            return

        active = [
            task_id for task_id, task in self.downloader.get_all_tasks().items()
            if task.state in {DownloadState.PENDING, DownloadState.DOWNLOADING, DownloadState.MERGING}
        ]
        if active:
            reply = QMessageBox.question(
                self,
                "退出并取消下载",
                f"仍有 {len(active)} 个任务未完成。退出会取消这些任务，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            for task_id in active:
                self.downloader.cancel(task_id)

        self._save_config()
        event.accept()
