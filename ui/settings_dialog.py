"""Modern application settings dialog."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from VideoDownloader.utils import find_tool
from .theme import apply_theme


class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = dict(config)
        self.setWindowTitle("设置")
        self.setMinimumSize(660, 500)
        apply_theme(self)
        self._build_ui()
        self._refresh_tool_status()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        title = QLabel("设置")
        title.setObjectName("HeroTitle")
        root.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_download_tab(), "下载")
        tabs.addTab(self._build_tools_tab(), "工具")
        root.addWidget(tabs, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(cancel_btn)
        save_btn = QPushButton("保存设置")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self._save)
        actions.addWidget(save_btn)
        root.addLayout(actions)

    def _build_download_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        group = QGroupBox("下载行为")
        form = QFormLayout(group)
        form.setSpacing(12)

        path_row = QHBoxLayout()
        self.download_path_edit = QLineEdit(self.config.get("download_path", ""))
        path_row.addWidget(self.download_path_edit, 1)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self._browse_download_path)
        path_row.addWidget(browse_btn)
        form.addRow("默认保存位置", path_row)

        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 6)
        self.max_concurrent_spin.setValue(int(self.config.get("max_concurrent", 3)))
        self.max_concurrent_spin.setSuffix(" 个任务")
        form.addRow("同时下载", self.max_concurrent_spin)

        note = QLabel("并发数越高，对网络、磁盘和处理器的压力越大，建议保持 2–3。")
        note.setProperty("muted", True)
        note.setWordWrap(True)
        form.addRow("", note)

        layout.addWidget(group)
        layout.addStretch()
        return tab

    def _build_tools_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        ffmpeg_group = QGroupBox("ffmpeg · 合并与转码")
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        self.ffmpeg_status = QLabel()
        self.ffmpeg_status.setProperty("muted", True)
        self.ffmpeg_status.setWordWrap(True)
        ffmpeg_layout.addWidget(self.ffmpeg_status)

        self.ffmpeg_custom_check = QCheckBox("使用自定义 ffmpeg.exe")
        self.ffmpeg_custom_check.setChecked(bool(self.config.get("ffmpeg_custom")))
        self.ffmpeg_custom_check.toggled.connect(self._toggle_ffmpeg)
        ffmpeg_layout.addWidget(self.ffmpeg_custom_check)

        ffmpeg_row = QHBoxLayout()
        self.ffmpeg_path_edit = QLineEdit(self.config.get("ffmpeg_path", ""))
        self.ffmpeg_path_edit.setPlaceholderText("选择 ffmpeg.exe")
        ffmpeg_row.addWidget(self.ffmpeg_path_edit, 1)
        ffmpeg_btn = QPushButton("选择")
        ffmpeg_btn.clicked.connect(self._browse_ffmpeg)
        ffmpeg_row.addWidget(ffmpeg_btn)
        ffmpeg_layout.addLayout(ffmpeg_row)
        layout.addWidget(ffmpeg_group)

        deno_group = QGroupBox("Deno · YouTube 解析")
        deno_layout = QVBoxLayout(deno_group)
        self.deno_status = QLabel()
        self.deno_status.setProperty("muted", True)
        self.deno_status.setWordWrap(True)
        deno_layout.addWidget(self.deno_status)

        self.deno_custom_check = QCheckBox("使用自定义 deno.exe")
        self.deno_custom_check.setChecked(bool(self.config.get("deno_custom")))
        self.deno_custom_check.toggled.connect(self._toggle_deno)
        deno_layout.addWidget(self.deno_custom_check)

        deno_row = QHBoxLayout()
        self.deno_path_edit = QLineEdit(self.config.get("deno_path", ""))
        self.deno_path_edit.setPlaceholderText("选择 deno.exe")
        deno_row.addWidget(self.deno_path_edit, 1)
        deno_btn = QPushButton("选择")
        deno_btn.clicked.connect(self._browse_deno)
        deno_row.addWidget(deno_btn)
        deno_layout.addLayout(deno_row)

        deno_note = QLabel("YouTube 当前需要 Deno 2.3 或更高版本来处理 JavaScript 挑战。")
        deno_note.setProperty("muted", True)
        deno_note.setWordWrap(True)
        deno_layout.addWidget(deno_note)
        layout.addWidget(deno_group)

        self._toggle_ffmpeg(self.ffmpeg_custom_check.isChecked())
        self._toggle_deno(self.deno_custom_check.isChecked())
        layout.addStretch()
        return tab

    def _toggle_ffmpeg(self, enabled: bool) -> None:
        self.ffmpeg_path_edit.setEnabled(enabled)

    def _toggle_deno(self, enabled: bool) -> None:
        self.deno_path_edit.setEnabled(enabled)

    def _refresh_tool_status(self) -> None:
        ffmpeg = find_tool(
            "ffmpeg",
            self.config.get("ffmpeg_path", "") if self.config.get("ffmpeg_custom") else "",
        )
        deno = find_tool(
            "deno",
            self.config.get("deno_path", "") if self.config.get("deno_custom") else "",
        )
        self.ffmpeg_status.setText(
            f"已检测到：{ffmpeg}" if ffmpeg else "未检测到可用 ffmpeg；下载合并和转码将不可用。"
        )
        self.deno_status.setText(
            f"已检测到：{deno}" if deno else "未检测到 Deno；部分 YouTube 视频可能无法完整解析。"
        )

    def _browse_download_path(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "选择默认保存位置", self.download_path_edit.text()
        )
        if path:
            self.download_path_edit.setText(path)

    def _browse_ffmpeg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 ffmpeg.exe", self.ffmpeg_path_edit.text(), "ffmpeg (ffmpeg.exe)"
        )
        if path:
            self.ffmpeg_path_edit.setText(path)
            self.ffmpeg_custom_check.setChecked(True)

    def _browse_deno(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 deno.exe", self.deno_path_edit.text(), "Deno (deno.exe)"
        )
        if path:
            self.deno_path_edit.setText(path)
            self.deno_custom_check.setChecked(True)

    def _save(self) -> None:
        download_path = Path(self.download_path_edit.text().strip()).expanduser()
        if not self.download_path_edit.text().strip():
            QMessageBox.warning(self, "保存位置为空", "请选择默认保存位置。")
            return
        try:
            download_path.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            QMessageBox.warning(self, "保存位置不可用", str(error))
            return

        if self.ffmpeg_custom_check.isChecked():
            ffmpeg_path = Path(self.ffmpeg_path_edit.text().strip())
            if not ffmpeg_path.is_file():
                QMessageBox.warning(self, "ffmpeg 路径无效", "请选择有效的 ffmpeg.exe。")
                return

        if self.deno_custom_check.isChecked():
            deno_path = Path(self.deno_path_edit.text().strip())
            if not deno_path.is_file():
                QMessageBox.warning(self, "Deno 路径无效", "请选择有效的 deno.exe。")
                return

        self.config.update(
            {
                "download_path": str(download_path),
                "max_concurrent": self.max_concurrent_spin.value(),
                "ffmpeg_custom": self.ffmpeg_custom_check.isChecked(),
                "ffmpeg_path": self.ffmpeg_path_edit.text().strip()
                if self.ffmpeg_custom_check.isChecked() else "",
                "deno_custom": self.deno_custom_check.isChecked(),
                "deno_path": self.deno_path_edit.text().strip()
                if self.deno_custom_check.isChecked() else "",
            }
        )
        self.accept()

    def get_config(self) -> dict:
        return dict(self.config)
