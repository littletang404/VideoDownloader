"""设置对话框"""
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QGroupBox, QLineEdit, QPushButton, QSpinBox,
                             QRadioButton, QLabel, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self.resize(500, 350)

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
            QLineEdit:focus, QSpinBox:focus {
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
            QRadioButton::indicator {
                border: 1px solid #4a9eff;
            }
        """)

        layout = QVBoxLayout()

        # 下载设置
        download_group = QGroupBox("下载设置")
        download_layout = QFormLayout()

        # 下载路径
        self.download_path_edit = QLineEdit()
        self.download_path_edit.setText(self.config.get('download_path', ''))
        download_path_btn = QPushButton("浏览...")
        download_path_btn.clicked.connect(self.browse_download_path)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.download_path_edit)
        path_layout.addWidget(download_path_btn)
        download_layout.addRow("默认下载路径:", path_layout)

        # 并发数
        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setMinimum(1)
        self.max_concurrent_spin.setMaximum(5)
        self.max_concurrent_spin.setValue(self.config.get('max_concurrent', 3))
        download_layout.addRow("最大并发数:", self.max_concurrent_spin)

        download_group.setLayout(download_layout)
        layout.addWidget(download_group)

        # 工具路径
        tools_group = QGroupBox("工具路径")
        tools_layout = QFormLayout()

        # ffmpeg
        self.ffmpeg_builtin = QRadioButton("内置 (推荐)")
        self.ffmpeg_custom = QRadioButton("自定义")
        ffmpeg_layout = QHBoxLayout()
        ffmpeg_layout.addWidget(self.ffmpeg_builtin)
        ffmpeg_layout.addWidget(self.ffmpeg_custom)

        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setText(str(Path(__file__).parent.parent / 'tools' / 'ffmpeg_bin' / 'ffmpeg.exe'))
        self.ffmpeg_path_edit.setEnabled(False)
        self.ffmpeg_path_edit.setPlaceholderText("内置 ffmpeg，自动使用")
        ffmpeg_btn = QPushButton("浏览...")
        ffmpeg_btn.clicked.connect(self.browse_ffmpeg)

        if self.config.get('ffmpeg_custom', False):
            self.ffmpeg_custom.setChecked(True)
            self.ffmpeg_path_edit.setEnabled(True)
            self.ffmpeg_path_edit.setText(self.config.get('ffmpeg_path', ''))
        else:
            self.ffmpeg_builtin.setChecked(True)

        self.ffmpeg_builtin.toggled.connect(lambda: self._toggle_path_enabled(self.ffmpeg_path_edit, False))
        self.ffmpeg_custom.toggled.connect(lambda: self._toggle_path_enabled(self.ffmpeg_path_edit, True))

        ffmpeg_path_layout = QHBoxLayout()
        ffmpeg_path_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_path_layout.addWidget(ffmpeg_btn)

        tools_layout.addRow("ffmpeg:", ffmpeg_layout)
        tools_layout.addRow("", ffmpeg_path_layout)

        # Deno
        self.deno_builtin = QRadioButton("内置")
        self.deno_custom = QRadioButton("自定义")
        deno_layout = QHBoxLayout()
        deno_layout.addWidget(self.deno_builtin)
        deno_layout.addWidget(self.deno_custom)

        self.deno_path_edit = QLineEdit()
        self.deno_path_edit.setText(self.config.get('deno_path', ''))
        self.deno_path_edit.setEnabled(False)
        deno_btn = QPushButton("浏览...")
        deno_btn.clicked.connect(self.browse_deno)

        if self.config.get('deno_custom', False):
            self.deno_custom.setChecked(True)
            self.deno_path_edit.setEnabled(True)
        else:
            self.deno_builtin.setChecked(True)

        self.deno_builtin.toggled.connect(lambda: self._toggle_path_enabled(self.deno_path_edit, False))
        self.deno_custom.toggled.connect(lambda: self._toggle_path_enabled(self.deno_path_edit, True))

        deno_path_layout = QHBoxLayout()
        deno_path_layout.addWidget(self.deno_path_edit)
        deno_path_layout.addWidget(deno_btn)

        tools_layout.addRow("Deno:", deno_layout)
        tools_layout.addRow("", deno_path_layout)

        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # Cookie 存储路径
        cookie_group = QGroupBox("Cookie 存储")
        cookie_layout = QFormLayout()

        self.cookie_path_edit = QLineEdit()
        self.cookie_path_edit.setText(self.config.get('cookie_path', 'cookies'))
        cookie_btn = QPushButton("浏览...")
        cookie_btn.clicked.connect(self.browse_cookie_path)
        cookie_path_layout = QHBoxLayout()
        cookie_path_layout.addWidget(self.cookie_path_edit)
        cookie_path_layout.addWidget(cookie_btn)
        cookie_layout.addRow("存储路径:", cookie_path_layout)

        cookie_group.setLayout(cookie_layout)
        layout.addWidget(cookie_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _toggle_path_enabled(self, edit: QLineEdit, enabled: bool):
        edit.setEnabled(enabled)

    def browse_download_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择下载路径", self.download_path_edit.text())
        if path:
            self.download_path_edit.setText(path)

    def browse_ffmpeg(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择 ffmpeg", "", "ffmpeg.exe")
        if file:
            self.ffmpeg_path_edit.setText(file)
            self.ffmpeg_custom.setChecked(True)
            self.ffmpeg_path_edit.setEnabled(True)

    def browse_deno(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择 Deno", self.deno_path_edit.text(), "deno.exe")
        if file:
            self.deno_path_edit.setText(file)

    def browse_cookie_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择 Cookie 存储路径", self.cookie_path_edit.text())
        if path:
            self.cookie_path_edit.setText(path)

    def save(self):
        self.config['download_path'] = self.download_path_edit.text()
        self.config['max_concurrent'] = self.max_concurrent_spin.value()
        self.config['ffmpeg_custom'] = self.ffmpeg_custom.isChecked()
        self.config['ffmpeg_path'] = self.ffmpeg_path_edit.text() if self.ffmpeg_custom.isChecked() else ''
        self.config['deno_custom'] = self.deno_custom.isChecked()
        self.config['deno_path'] = self.deno_path_edit.text()
        self.config['cookie_path'] = self.cookie_path_edit.text()
        self.accept()

    def get_config(self) -> dict:
        return self.config