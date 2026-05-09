"""转码对话框"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QGroupBox, QLineEdit, QPushButton, QFileDialog,
                             QRadioButton, QSpinBox, QLabel, QProgressBar,
                             QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class TranscodeThread(QThread):
    """转码线程"""
    progress = pyqtSignal(float)
    finished = pyqtSignal(bool, str)

    def __init__(self, handler, input_path, output_path, settings):
        super().__init__()
        self.handler = handler
        self.input_path = input_path
        self.output_path = output_path
        self.settings = settings

    def run(self):
        try:
            success = self.handler.transcode(
                self.input_path,
                self.output_path,
                video_codec=self.settings.get('video_codec', 'copy'),
                audio_codec=self.settings.get('audio_codec', 'copy'),
                video_bitrate=self.settings.get('video_bitrate'),
                audio_bitrate=self.settings.get('audio_bitrate', '192k'),
                resolution=self.settings.get('resolution'),
                progress_callback=self._on_progress
            )
            self.finished.emit(success, '' if success else '转码失败')
        except Exception as e:
            self.finished.emit(False, str(e))

    def _on_progress(self, progress: float):
        self.progress.emit(progress)


class TranscodeDialog(QDialog):
    """转码对话框"""

    def __init__(self, ffmpeg_handler, parent=None):
        super().__init__(parent)
        self.ffmpeg_handler = ffmpeg_handler
        self.transcode_thread = None
        self.input_file = ''
        self.output_file = ''
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("转码/格式转换")
        self.setMinimumWidth(500)
        self.resize(500, 450)

        # 深色主题样式
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #4a9eff;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
            QLabel {
                color: #c0c0c0;
            }
            QLineEdit, QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #4a9eff;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QRadioButton {
                color: #e0e0e0;
            }
            QProgressBar {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background-color: #2d2d2d;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #4a9eff;
                border-radius: 3px;
            }
        """)

        layout = QVBoxLayout()

        # 文件选择
        file_group = QGroupBox("文件选择")
        file_layout = QFormLayout()

        self.input_edit = QLineEdit()
        input_btn = QPushButton("选择文件...")
        input_btn.clicked.connect(self.browse_input)
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(input_btn)
        file_layout.addRow("输入文件:", input_layout)

        self.output_edit = QLineEdit()
        output_btn = QPushButton("选择保存位置...")
        output_btn.clicked.connect(self.browse_output)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_btn)
        file_layout.addRow("输出文件:", output_layout)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # 编码设置
        encode_group = QGroupBox("编码设置")
        encode_layout = QVBoxLayout()

        # 格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出格式:"))
        self.format_group = []
        for fmt in ['MP4', 'MKV', 'AVI', 'MOV']:
            rb = QRadioButton(fmt)
            if fmt == 'MP4':
                rb.setChecked(True)
            self.format_group.append((fmt, rb))
            format_layout.addWidget(rb)
        format_layout.addStretch()
        encode_layout.addLayout(format_layout)

        # 视频编码
        video_layout = QHBoxLayout()
        video_layout.addWidget(QLabel("视频编码:"))
        self.video_codec_group = []
        for codec in [('copy', '复制（不转码）'), ('h264', 'H.264'), ('h265', 'H.265'), ('av1', 'AV1')]:
            rb = QRadioButton(codec[1])
            if codec[0] == 'copy':
                rb.setChecked(True)
            self.video_codec_group.append((codec[0], rb))
            video_layout.addWidget(rb)
        video_layout.addStretch()
        encode_layout.addLayout(video_layout)

        # 音频编码
        audio_layout = QHBoxLayout()
        audio_layout.addWidget(QLabel("音频编码:"))
        self.audio_codec_group = []
        for codec in [('copy', '复制（不转码）'), ('aac', 'AAC'), ('mp3', 'MP3'), ('flac', 'FLAC')]:
            rb = QRadioButton(codec[1])
            if codec[0] == 'aac':
                rb.setChecked(True)
            self.audio_codec_group.append((codec[0], rb))
            audio_layout.addWidget(rb)
        audio_layout.addStretch()
        encode_layout.addLayout(audio_layout)

        # 分辨率
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("分辨率:"))
        self.resolution_group = []
        for res in [('original', '原始'), ('1080p', '1080p'), ('720p', '720p')]:
            rb = QRadioButton(res[1])
            if res[0] == 'original':
                rb.setChecked(True)
            self.resolution_group.append((res[0], rb))
            res_layout.addWidget(rb)

        self.custom_res_edit = QLineEdit()
        self.custom_res_edit.setPlaceholderText("如: 1920x1080")
        self.custom_res_edit.setMaximumWidth(100)
        res_layout.addWidget(self.custom_res_edit)
        res_layout.addStretch()
        encode_layout.addLayout(res_layout)

        encode_group.setLayout(encode_layout)
        layout.addWidget(encode_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.start_btn = QPushButton("开始转码")
        self.start_btn.clicked.connect(self.start_transcode)
        cancel_btn = QPushButton("关闭")
        cancel_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def browse_input(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.mkv *.avi *.mov *.ts *.m3u8);;所有文件 (*.*)"
        )
        if file:
            self.input_file = file
            self.input_edit.setText(file)
            # 自动生成输出文件名
            if not self.output_edit.text():
                import os
                base = os.path.splitext(file)[0]
                self.output_edit.setText(f"{base}_transcoded.mp4")

    def browse_output(self):
        file, _ = QFileDialog.getSaveFileName(
            self, "选择保存位置", self.output_edit.text() or "",
            "MP4 (*.mp4);;MKV (*.mkv);;AVI (*.avi);;MOV (*.mov);;所有文件 (*.*)"
        )
        if file:
            self.output_file = file
            self.output_edit.setText(file)

    def get_settings(self) -> dict:
        """获取转码设置"""
        # 格式
        output_format = 'mp4'
        for fmt, rb in self.format_group:
            if rb.isChecked():
                output_format = fmt.lower()
                break

        # 视频编码
        video_codec = 'copy'
        for codec, rb in self.video_codec_group:
            if rb.isChecked():
                video_codec = codec
                break

        # 音频编码
        audio_codec = 'aac'
        for codec, rb in self.audio_codec_group:
            if rb.isChecked():
                audio_codec = codec
                break

        # 分辨率
        resolution = None
        for res, rb in self.resolution_group:
            if rb.isChecked():
                if res == 'original':
                    resolution = None
                else:
                    resolution = res
                break

        # 自定义分辨率
        custom_res = self.custom_res_edit.text().strip()
        if custom_res and resolution is None:
            resolution = custom_res

        return {
            'format': output_format,
            'video_codec': video_codec,
            'audio_codec': audio_codec,
            'resolution': resolution,
        }

    def start_transcode(self):
        if not self.input_file or not self.output_file:
            QMessageBox.warning(self, "提示", "请选择输入和输出文件")
            return

        settings = self.get_settings()

        # 修改输出文件扩展名
        import os
        output_path = self.output_file
        if not output_path.endswith(f".{settings['format']}"):
            output_path = f"{output_path.rsplit('.', 1)[0]}.{settings['format']}"

        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.transcode_thread = TranscodeThread(
            self.ffmpeg_handler,
            self.input_file,
            output_path,
            settings
        )
        self.transcode_thread.progress.connect(self._on_progress)
        self.transcode_thread.finished.connect(self._on_finished)
        self.transcode_thread.start()

    def _on_progress(self, progress: float):
        if progress < 0:
            # 不确定进度，只显示动画或文本
            self.progress_bar.setRange(0, 0)  # 切换到不确定模式
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int(progress))

    def _on_finished(self, success: bool, error: str):
        self.start_btn.setEnabled(True)

        if success:
            QMessageBox.information(self, "完成", "转码完成！")
        else:
            QMessageBox.critical(self, "错误", f"转码失败: {error}")

    def closeEvent(self, event):
        if self.transcode_thread and self.transcode_thread.isRunning():
            self.transcode_thread.terminate()
            self.transcode_thread.wait()
        event.accept()