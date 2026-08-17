"""Local media conversion dialog."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from .theme import apply_theme


class TranscodeThread(QThread):
    progress = pyqtSignal(float)
    completed = pyqtSignal(bool, str)

    def __init__(self, handler, input_path: str, output_path: str, settings: dict):
        super().__init__()
        self.handler = handler
        self.input_path = input_path
        self.output_path = output_path
        self.settings = settings

    def run(self) -> None:
        try:
            success = self.handler.transcode(
                self.input_path,
                self.output_path,
                video_codec=self.settings["video_codec"],
                audio_codec=self.settings["audio_codec"],
                resolution=self.settings["resolution"],
                progress_callback=self.progress.emit,
            )
            self.completed.emit(success, "" if success else self.handler.last_error)
        except Exception as error:
            self.completed.emit(False, str(error))


class TranscodeDialog(QDialog):
    def __init__(self, ffmpeg_handler, parent=None):
        super().__init__(parent)
        self.ffmpeg_handler = ffmpeg_handler
        self.transcode_thread = None
        self.setWindowTitle("视频转换")
        self.setMinimumSize(680, 470)
        apply_theme(self)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        title = QLabel("视频转换")
        title.setObjectName("HeroTitle")
        layout.addWidget(title)

        hint = QLabel("转换封装格式、编码或分辨率。调整分辨率时会自动重新编码视频。")
        hint.setProperty("muted", True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(12)

        input_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("选择需要转换的视频")
        input_row.addWidget(self.input_edit, 1)
        input_btn = QPushButton("选择")
        input_btn.clicked.connect(self._browse_input)
        input_row.addWidget(input_btn)
        form.addRow("输入文件", input_row)

        output_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("选择输出位置")
        output_row.addWidget(self.output_edit, 1)
        output_btn = QPushButton("选择")
        output_btn.clicked.connect(self._browse_output)
        output_row.addWidget(output_btn)
        form.addRow("输出文件", output_row)

        self.format_combo = QComboBox()
        self.format_combo.addItem("MP4 · 通用兼容", "mp4")
        self.format_combo.addItem("MKV · 多轨与高兼容", "mkv")
        self.format_combo.addItem("MOV · 剪辑软件", "mov")
        self.format_combo.addItem("AVI · 旧设备", "avi")
        self.format_combo.currentIndexChanged.connect(self._sync_output_suffix)
        form.addRow("容器格式", self.format_combo)

        self.video_combo = QComboBox()
        self.video_combo.addItem("保持原编码（最快）", "copy")
        self.video_combo.addItem("H.264 · 兼容优先", "h264")
        self.video_combo.addItem("H.265 · 体积优先", "h265")
        self.video_combo.addItem("AV1 · 高压缩率", "av1")
        form.addRow("视频编码", self.video_combo)

        self.audio_combo = QComboBox()
        self.audio_combo.addItem("AAC · 推荐", "aac")
        self.audio_combo.addItem("保持原编码", "copy")
        self.audio_combo.addItem("MP3", "mp3")
        self.audio_combo.addItem("FLAC · 无损", "flac")
        form.addRow("音频编码", self.audio_combo)

        self.resolution_combo = QComboBox()
        self.resolution_combo.setEditable(True)
        self.resolution_combo.addItem("保持原分辨率", "")
        self.resolution_combo.addItem("4K · 2160p", "2160p")
        self.resolution_combo.addItem("Full HD · 1080p", "1080p")
        self.resolution_combo.addItem("HD · 720p", "720p")
        self.resolution_combo.setToolTip("也可以直接输入 1920x1080")
        form.addRow("分辨率", self.resolution_combo)

        layout.addLayout(form)

        self.status_label = QLabel("准备就绪")
        self.status_label.setProperty("muted", True)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        actions = QHBoxLayout()
        actions.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        actions.addWidget(close_btn)
        self.start_btn = QPushButton("开始转换")
        self.start_btn.setProperty("primary", True)
        self.start_btn.clicked.connect(self._start)
        actions.addWidget(self.start_btn)
        layout.addLayout(actions)

    def _browse_input(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.mkv *.avi *.mov *.webm *.ts);;所有文件 (*.*)",
        )
        if not file_path:
            return
        self.input_edit.setText(file_path)
        if not self.output_edit.text().strip():
            source = Path(file_path)
            self.output_edit.setText(
                str(source.with_name(f"{source.stem}_converted.mp4"))
            )

    def _browse_output(self) -> None:
        suffix = self.format_combo.currentData()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择输出文件",
            self.output_edit.text().strip(),
            f"{suffix.upper()} 文件 (*.{suffix});;所有文件 (*.*)",
        )
        if file_path:
            self.output_edit.setText(file_path)
            self._sync_output_suffix()

    def _sync_output_suffix(self) -> None:
        value = self.output_edit.text().strip()
        if not value:
            return
        suffix = "." + str(self.format_combo.currentData())
        self.output_edit.setText(str(Path(value).with_suffix(suffix)))

    def _settings(self) -> dict:
        resolution = self.resolution_combo.currentData()
        if self.resolution_combo.currentText() not in {
            self.resolution_combo.itemText(i)
            for i in range(self.resolution_combo.count())
        }:
            resolution = self.resolution_combo.currentText().strip()
        return {
            "video_codec": self.video_combo.currentData(),
            "audio_codec": self.audio_combo.currentData(),
            "resolution": resolution or None,
        }

    def _start(self) -> None:
        input_path = Path(self.input_edit.text().strip()).expanduser()
        output_path = Path(self.output_edit.text().strip()).expanduser()
        if not input_path.is_file():
            QMessageBox.warning(self, "输入文件无效", "请选择存在的视频文件。")
            return
        if not self.output_edit.text().strip():
            QMessageBox.warning(self, "输出位置为空", "请选择输出文件。")
            return

        output_path = output_path.with_suffix("." + str(self.format_combo.currentData()))
        self.output_edit.setText(str(output_path))
        if output_path.exists():
            reply = QMessageBox.question(
                self,
                "覆盖已有文件",
                f"{output_path.name} 已存在，是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if not self.ffmpeg_handler.is_available():
            QMessageBox.warning(
                self,
                "ffmpeg 不可用",
                "没有检测到可用的 ffmpeg，请先到设置中配置。",
            )
            return

        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在转换，请不要关闭窗口…")

        self.transcode_thread = TranscodeThread(
            self.ffmpeg_handler,
            str(input_path),
            str(output_path),
            self._settings(),
        )
        self.transcode_thread.progress.connect(self._on_progress)
        self.transcode_thread.completed.connect(self._on_finished)
        self.transcode_thread.start()

    def _on_progress(self, progress: float) -> None:
        if progress < 0:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(round(progress))

    def _on_finished(self, success: bool, error: str) -> None:
        self.start_btn.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("转换完成")
            QMessageBox.information(self, "转换完成", "视频已成功转换。")
        else:
            self.status_label.setText("转换失败")
            QMessageBox.critical(
                self,
                "转换失败",
                error or "ffmpeg 未能完成转换，请检查输入文件和编码设置。",
            )

    def closeEvent(self, event) -> None:
        if self.transcode_thread and self.transcode_thread.isRunning():
            QMessageBox.information(
                self,
                "正在转换",
                "转换仍在进行中。为避免输出文件损坏，请等待任务完成后再关闭。",
            )
            event.ignore()
            return
        event.accept()
