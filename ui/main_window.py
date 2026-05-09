import sys
import os
import time
import re
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QFormLayout, QGroupBox, QLineEdit, QPushButton,
                             QLabel, QComboBox, QTextEdit, QProgressBar,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QMenuBar, QMenu, QMessageBox,
                             QFileDialog, QCheckBox, QScrollArea, QFrame,
                             QStatusBar, QProgressDialog, QDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QCursor

from VideoDownloader.core import LinkParser, CookieManager, Downloader, FFmpegHandler, TaskManager, TaskRecord, DownloadTask
from VideoDownloader.ui.settings_dialog import SettingsDialog
from VideoDownloader.ui.transcode_dialog import TranscodeDialog


class ParseThread(QThread):
    """解析线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, parser, url, cookies_path):
        super().__init__()
        self.parser = parser
        self.url = url
        self.cookies_path = cookies_path

    def run(self):
        try:
            print(f"[DEBUG] ParseThread starting: url={self.url}, cookies={self.cookies_path}")
            info = self.parser.parse(self.url, self.cookies_path)
            print(f"[DEBUG] ParseThread success")
            self.finished.emit(info)
        except Exception as e:
            print(f"[DEBUG] ParseThread error: {e}")
            self.error.emit(str(e))


class M3u8DownloadThread(QThread):
    """m3u8下载线程"""
    completed = pyqtSignal(bool, str)  # success, error_message

    def __init__(self, ffmpeg_handler, url, output_path):
        super().__init__()
        self.ffmpeg_handler = ffmpeg_handler
        self.url = url
        self.output_path = output_path

    def run(self):
        try:
            success = self.ffmpeg_handler.download_m3u8(self.url, self.output_path)
            self.completed.emit(success, '' if success else '下载失败')
        except Exception as e:
            self.completed.emit(False, str(e))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.current_video_info = None
        self.parse_thread = None

        # 初始化核心组件
        self._init_core()

        self.init_ui()
        self._update_ffmpeg_path()
        self._update_deno_path()
        self._update_cookie_manager()

    def _init_core(self):
        """初始化核心组件"""
        self.ffmpeg_handler = FFmpegHandler(self._get_ffmpeg_path())
        self.downloader = Downloader(
            yt_dlp_path='yt-dlp',
            ffmpeg_path=self._get_ffmpeg_path(),
            deno_path=self._get_deno_path(),
            max_concurrent=self.config.get('max_concurrent', 3)
        )
        self.cookie_manager = CookieManager(self.config.get('cookie_path', 'cookies'))
        self.task_manager = TaskManager()
        self.link_parser = LinkParser(
            yt_dlp_path='yt-dlp',
            ffmpeg_path=self._get_ffmpeg_path()
        )

        # 连接下载器信号（只连接一次）
        self.downloader.progress_updated.connect(self._on_download_progress)
        self.downloader.download_completed.connect(self._on_download_complete)

    def _get_ffmpeg_path(self) -> str:
        if self.config.get('ffmpeg_custom') and self.config.get('ffmpeg_path'):
            return self.config['ffmpeg_path']
        # 默认使用内置 ffmpeg（相对于 exe 所在目录）
        if getattr(sys, 'frozen', False):
            # 打包后：exe 同目录下的 tools
            exe_dir = Path(sys.executable).parent
            return str(exe_dir / 'tools' / 'ffmpeg_full' / 'ffmpeg-8.1.1-essentials_build' / 'bin' / 'ffmpeg.exe')
        else:
            # 开发环境
            return str(Path(__file__).parent.parent / 'tools' / 'ffmpeg_full' / 'ffmpeg-8.1.1-essentials_build' / 'bin' / 'ffmpeg.exe')

    def _get_deno_path(self) -> str:
        if self.config.get('deno_custom') and self.config.get('deno_path'):
            return self.config['deno_path']
        return 'deno'

    def _update_ffmpeg_path(self):
        self.ffmpeg_handler.ffmpeg_path = self._get_ffmpeg_path()

    def _update_deno_path(self):
        self.downloader.deno_path = self._get_deno_path()

    def _update_cookie_manager(self):
        cookie_dir = self.config.get('cookie_path', 'cookies')
        self.cookie_manager = CookieManager(cookie_dir)

    def init_ui(self):
        self.setWindowTitle("视频下载器 v1.1.0")
        self.setMinimumSize(950, 800)

        # 深色主题样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
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
            QLineEdit, QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus, QComboBox:focus {
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
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QTableWidget {
                background-color: #252525;
                color: #e0e0e0;
                gridline-color: #3a3a3a;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #4a9eff;
                padding: 5px;
                border: none;
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
            QStatusBar {
                background-color: #1e1e1e;
                color: #c0c0c0;
            }
            QMenuBar {
                background-color: #252525;
                color: #e0e0e0;
            }
            QMenuBar::item:selected {
                background-color: #3a3a3a;
            }
            QMenu {
                background-color: #252525;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
            }
            QMenu::item:selected {
                background-color: #4a9eff;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #3a3a3a;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4a4a4a;
            }
            QScrollBar:horizontal {
                background-color: #1e1e1e;
                height: 12px;
            }
            QScrollBar::handle:horizontal {
                background-color: #3a3a3a;
                border-radius: 6px;
            }
        """)

        # 创建菜单栏
        self._create_menu_bar()

        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 链接输入区
        layout.addWidget(self._create_input_group())

        # 视频信息预览区
        layout.addWidget(self._create_preview_group())

        # Cookie 和保存路径区
        layout.addWidget(self._create_options_group())

        # 按钮区
        layout.addWidget(self._create_button_group())

        # 任务列表区
        layout.addWidget(self._create_task_group(), stretch=1)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        # 启动时自动加载 Cookie 状态
        self._update_cookie_status()
        self._update_cookie_combo_selection()

        # 当平台选择变化时更新状态
        self.cookie_combo.currentIndexChanged.connect(self._update_cookie_status)

        central_widget.setLayout(layout)

    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        settings_action = QAction("设置...", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具")

        transcode_action = QAction("转码/格式转换", self)
        transcode_action.triggered.connect(self.open_transcode)
        tools_menu.addAction(transcode_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _create_input_group(self) -> QGroupBox:
        """链接输入区"""
        group = QGroupBox("视频链接")
        layout = QHBoxLayout()

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("输入 YouTube、Bilibili 或 m3u8 链接...")
        self.url_edit.returnPressed.connect(self.parse_url)
        layout.addWidget(self.url_edit, stretch=1)

        self.parse_btn = QPushButton("解析")
        self.parse_btn.clicked.connect(self.parse_url)
        layout.addWidget(self.parse_btn)

        group.setLayout(layout)
        return group

    def _create_preview_group(self) -> QGroupBox:
        """视频信息预览区"""
        group = QGroupBox("视频信息预览")
        layout = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("请输入链接并点击解析")
        self.title_edit.setText("请输入链接并点击解析")
        layout.addRow("标题:", self.title_edit)

        # 画质选择
        self.format_combo = QComboBox()
        self.format_combo.setMinimumWidth(300)
        layout.addRow("画质选择:", self.format_combo)

        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        layout.addRow("详情:", self.info_label)

        group.setLayout(layout)
        return group

    def _create_options_group(self) -> QGroupBox:
        """Cookie 和保存路径区"""
        group = QGroupBox("下载选项")
        layout = QVBoxLayout()

        # Cookie 导入区
        cookie_group = QGroupBox("Cookie 导入")
        cookie_layout = QFormLayout()

        # 平台选择
        cookie_platform_layout = QHBoxLayout()
        self.cookie_combo = QComboBox()
        self.cookie_combo.addItems(['YouTube', 'Bilibili'])
        cookie_platform_layout.addWidget(QLabel("平台:"))
        cookie_platform_layout.addWidget(self.cookie_combo)
        cookie_platform_layout.addStretch()

        # 状态显示
        self.cookie_status_label = QLabel("未导入")
        self.cookie_status_label.setStyleSheet("color: #888;")
        cookie_platform_layout.addWidget(self.cookie_status_label)

        # 粘贴区域
        self.cookie_text_edit = QTextEdit()
        self.cookie_text_edit.setPlaceholderText("粘贴 JSON 格式 Cookie 内容（从浏览器插件导出）...")
        self.cookie_text_edit.setMaximumHeight(150)
        self.cookie_text_edit.setTabStopDistance(40)

        # 导入按钮
        cookie_btn_layout = QHBoxLayout()
        self.cookie_import_btn = QPushButton("导入 Cookie")
        self.cookie_import_btn.clicked.connect(self.import_cookie_from_text)
        self.cookie_import_btn.setStyleSheet("QPushButton { background-color: #4a9eff; color: white; }")
        cookie_btn_layout.addWidget(self.cookie_import_btn)

        self.cookie_file_btn = QPushButton("从文件选择...")
        self.cookie_file_btn.clicked.connect(self.import_cookie_file)
        cookie_btn_layout.addWidget(self.cookie_file_btn)

        cookie_btn_layout.addStretch()

        cookie_layout.addRow("平台:", cookie_platform_layout)
        cookie_layout.addRow("Cookie:", self.cookie_text_edit)
        cookie_layout.addRow("", cookie_btn_layout)

        cookie_group.setLayout(cookie_layout)
        layout.addWidget(cookie_group)

        # 保存路径区
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("保存路径:"))

        self.save_path_edit = QLineEdit()
        self.save_path_edit.setText(self.config.get('download_path', ''))
        path_layout.addWidget(self.save_path_edit, stretch=1)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_save_path)
        path_layout.addWidget(self.browse_btn)

        layout.addLayout(path_layout)

        group.setLayout(layout)
        return group

    def _create_button_group(self) -> QGroupBox:
        """按钮区"""
        group = QGroupBox("")
        group.setFlat(True)
        layout = QHBoxLayout()

        self.download_btn = QPushButton("下载 >>>")
        self.download_btn.setMinimumSize(120, 45)
        self.download_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; font-size: 14px; border-radius: 5px; } QPushButton:disabled { background-color: #cccccc; }")
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setEnabled(False)
        layout.addWidget(self.download_btn)

        self.transcode_btn = QPushButton("转码 >>>")
        self.transcode_btn.setMinimumSize(120, 45)
        self.transcode_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; font-size: 14px; border-radius: 5px; }")
        self.transcode_btn.clicked.connect(self.open_transcode)
        layout.addWidget(self.transcode_btn)

        self.settings_btn = QPushButton("设置 >>>")
        self.settings_btn.setMinimumSize(120, 45)
        self.settings_btn.setStyleSheet("QPushButton { background-color: #9E9E9E; color: white; font-weight: bold; font-size: 14px; border-radius: 5px; }")
        self.settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(self.settings_btn)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def _create_task_group(self) -> QGroupBox:
        """任务列表区"""
        group = QGroupBox("下载任务")
        layout = QVBoxLayout()

        # 工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addStretch()

        self.clear_history_btn = QPushButton("清空记录")
        self.clear_history_btn.clicked.connect(self.clear_task_history)
        toolbar_layout.addWidget(self.clear_history_btn)

        layout.addLayout(toolbar_layout)

        self.task_table = QTableWidget()
        self.task_table.setColumnCount(6)
        self.task_table.setHorizontalHeaderLabels(['标题', '画质', '进度', '状态', '操作', ''])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().hideSection(5)  # 隐藏 ID 列
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.task_table)

        # 必须设置 layout 给 group！
        group.setLayout(layout)

        # 加载历史记录
        self._load_task_history()

        return group

    def parse_url(self):
        """解析 URL"""
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入视频链接")
            return

        # 获取对应平台的 Cookie
        platform = self.cookie_manager.auto_detect_platform(url)
        cookies_path = None
        if platform:
            cookies_path = self.cookie_manager.get_cookie_path_for_yt_dlp(platform)

        self.parse_btn.setEnabled(False)
        self.parse_btn.setText("解析中...")
        self.status_bar.showMessage("正在解析...")

        self.parse_thread = ParseThread(self.link_parser, url, cookies_path)
        self.parse_thread.finished.connect(self._on_parse_finished)
        self.parse_thread.error.connect(self._on_parse_error)
        self.parse_thread.start()

    def _on_parse_finished(self, info: dict):
        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("解析")
        self.status_bar.showMessage("解析完成")

        self.current_video_info = info
        self._update_preview(info)
        self.download_btn.setEnabled(True)

    def _on_parse_error(self, error: str):
        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("解析")
        self.status_bar.showMessage("解析失败")
        print(f"[DEBUG] Parse error: {error}")
        QMessageBox.critical(self, "解析错误", error)

    def _update_preview(self, info: dict):
        """更新视频预览"""
        self.title_edit.setText(info.get('title', '未知标题'))

        # 填充画质选项
        self.format_combo.clear()
        formats = info.get('formats', [])

        if not formats:
            self.format_combo.addItem("m3u8 直链", 'm3u8')
            self.info_label.setText("m3u8 直链视频")
            return

        # 如果是 m3u8 格式
        if info.get('platform') == 'm3u8':
            self.format_combo.addItem("m3u8 直链", 'm3u8')
            self.info_label.setText("m3u8 直链视频")
            return

        # 填充画质选项（普通视频）
        self.format_combo.clear()

        # 分离纯视频、纯音频、混合格式
        video_only = []
        audio_only = []
        combined = []

        for f in formats:
            res = f.get('resolution', '未知')
            fid = f.get('format_id', '')
            filesize = f.get('filesize', 0)
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')

            if filesize:
                size_str = f"{filesize / (1024*1024):.1f} MB"
            else:
                size_str = ""

            # 混合格式（视频+音频一起的，通常文件名带 f 开头如 f30232）
            if vcodec != 'none' and acodec != 'none':
                display = f"✅混合 {res} ({fid}) {size_str}".strip()
                combined.append((fid, display, 'combined'))
            elif vcodec != 'none' and acodec == 'none':
                display = f"📹视频 {res} ({fid}) {size_str}".strip()
                video_only.append((fid, display, 'video'))
            elif vcodec == 'none' and acodec != 'none':
                display = f"🔊音频 {res} ({fid}) {size_str}".strip()
                audio_only.append((fid, display, 'audio'))

        # 按分辨率排序
        def get_height(item):
            res = item[1]
            import re
            # 优先匹配 x 分辨率格式（如 3840x2160）
            match = re.search(r'(\d+)x(\d+)', res)
            if match:
                return int(match.group(2))
            # 再匹配 p 分辨率格式（如 1080p）
            match = re.search(r'(\d+)p', res)
            if match:
                return int(match.group(1))
            return 0

        # 按分辨率和文件大小排序（相同分辨率时，大文件排前面）
        def sort_key(item):
            fid, display, fmt_type = item
            height = get_height(item)
            # 从 display 中提取引擎文件大小用于二次排序
            # 格式: "📹视频 3840x2160 (100035) 2149.8 MB"
            size_match = re.search(r'([\d.]+)\s*MB', display)
            size = float(size_match.group(1)) if size_match else 0
            # 返回 (分辨率高度, 文件大小) 降序排列
            return (height, size)

        combined.sort(key=get_height, reverse=True)
        combined.sort(key=sort_key, reverse=True)
        video_only.sort(key=get_height, reverse=True)
        video_only.sort(key=sort_key, reverse=True)
        audio_only.sort(key=get_height, reverse=True)

        # 优先显示混合格式
        current_index = 0
        for fid, display, fmt_type in combined:
            self.format_combo.addItem(display, (fid, fmt_type))
            current_index += 1

        # 如果没有混合格式，显示视频+音频的组合选项
        if combined and (video_only or audio_only):
            self.format_combo.addItem("--- 或分别选择 ---", None)
            current_index += 1

        for fid, display, fmt_type in video_only:
            self.format_combo.addItem(display, (fid, fmt_type))

        if video_only and audio_only:
            self.format_combo.addItem("--- 音频轨道 ---", None)

        for fid, display, fmt_type in audio_only:
            self.format_combo.addItem(display, (fid, fmt_type))

        # 默认选择最高画质
        self.format_combo.setCurrentIndex(0)

        # 显示详情
        platform = info.get('platform', '')
        duration = info.get('duration', 0)
        if duration:
            mins = int(duration // 60)
            secs = int(duration % 60)
            duration_str = f"{mins}分{secs}秒"
        else:
            duration_str = "未知"

        details = f"平台: {platform} | 时长: {duration_str} | 格式数: {len(formats)}"
        self.info_label.setText(details)

    def import_cookie_file(self):
        """导入 Cookie 文件"""
        platform_map = {'YouTube': 'youtube', 'Bilibili': 'bilibili'}
        platform = self.cookie_combo.currentText()
        platform_key = platform_map.get(platform)

        if not platform_key:
            QMessageBox.warning(self, "提示", "请选择平台")
            return

        file, _ = QFileDialog.getOpenFileName(
            self, "选择 Cookie 文件", "",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )

        if file:
            if self.cookie_manager.import_from_file(platform_key, file):
                QMessageBox.information(self, "成功", f"{platform} Cookie 导入成功")
                self._update_cookie_status()
            else:
                QMessageBox.critical(self, "错误", "Cookie 导入失败")

    def import_cookie_from_text(self):
        """从文本框导入 Cookie"""
        platform_map = {'YouTube': 'youtube', 'Bilibili': 'bilibili'}
        platform = self.cookie_combo.currentText()
        platform_key = platform_map.get(platform)

        if not platform_key:
            QMessageBox.warning(self, "提示", "请选择平台")
            return

        content = self.cookie_text_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请先粘贴 Cookie 内容")
            return

        # 检查是否是 JSON 格式
        content_stripped = content.strip()
        if content_stripped.startswith('[') or content_stripped.startswith('{'):
            # JSON 格式，转换为 Netscape
            content = self.cookie_manager._convert_json_to_netscape(content_stripped)
            print(f"[DEBUG] Converted JSON to Netscape format, {len(content)} chars")

        # 保存 Cookie
        if self.cookie_manager.save_cookie(platform_key, content):
            QMessageBox.information(self, "成功", f"{platform} Cookie 导入成功！")
            self.cookie_text_edit.clear()
            self._update_cookie_status()
        else:
            QMessageBox.critical(self, "错误", "Cookie 保存失败")

    def paste_cookie_text(self):
        """粘贴 Cookie 文本"""
        platform_map = {'YouTube': 'youtube', 'Bilibili': 'bilibili'}
        platform = self.cookie_combo.currentText()
        platform_key = platform_map.get(platform)

        if not platform_key:
            QMessageBox.warning(self, "提示", "请选择平台")
            return

        # 创建一个简单的文本输入对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"粘贴 {platform} Cookie")
        dialog.resize(500, 300)

        layout = QVBoxLayout()
        label = QLabel("请粘贴 Cookie 内容（Netscape 格式）:")
        layout.addWidget(label)

        text_edit = QTextEdit()
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            content = text_edit.toPlainText()
            if content:
                if self.cookie_manager.save_cookie(platform_key, content):
                    QMessageBox.information(self, "成功", f"{platform} Cookie 保存成功")
                    self._update_cookie_status()
                else:
                    QMessageBox.critical(self, "错误", "Cookie 保存失败")

    def _update_cookie_status(self):
        """更新 Cookie 状态显示"""
        platform_map = {'YouTube': 'youtube', 'Bilibili': 'bilibili'}
        platform = self.cookie_combo.currentText()
        platform_key = platform_map.get(platform)

        if platform_key:
            status = self.cookie_manager.get_all_cookies_status().get(platform_key, {})
            if status.get('valid'):
                self.cookie_status_label.setText("✓ 已加载")
            elif status.get('exists'):
                self.cookie_status_label.setText("⚠ 格式可能无效")
            else:
                self.cookie_status_label.setText("✗ 未加载")
        else:
            self.cookie_status_label.setText("")

    def _update_cookie_combo_selection(self):
        """根据已加载的 Cookie 自动选择平台"""
        platform_map = {'youtube': 'YouTube', 'bilibili': 'Bilibili'}
        for platform_key, display_name in platform_map.items():
            if self.cookie_manager.is_cookie_valid(platform_key):
                # 找到对应的 combo index
                index = self.cookie_combo.findText(display_name)
                if index >= 0:
                    self.cookie_combo.setCurrentIndex(index)
                    break

    def browse_save_path(self):
        """浏览保存路径"""
        path = QFileDialog.getExistingDirectory(
            self, "选择保存路径", self.save_path_edit.text()
        )
        if path:
            self.save_path_edit.setText(path)

    def start_download(self):
        """开始下载"""
        if not self.current_video_info:
            QMessageBox.warning(self, "提示", "请先解析视频")
            return

        info = self.current_video_info
        # 优先使用解析后的真实URL（用于处理短链接）
        url = info.get('url') or self.url_edit.text().strip()
        format_data = self.format_combo.currentData()
        save_path = self.save_path_edit.text().strip()

        if not save_path:
            QMessageBox.warning(self, "提示", "请选择保存路径")
            return

        # 生成输出文件名（使用用户自定义的标题）
        title = self.title_edit.text().strip() or 'video'
        title = title.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')

        if format_data == 'm3u8':
            output_path = os.path.join(save_path, f"{title}.mp4")
            self._download_m3u8(url, output_path)
        elif format_data is None:
            QMessageBox.warning(self, "提示", "请选择有效的画质")
        else:
            # format_data 是元组 (format_id, type) 或单个值
            if isinstance(format_data, tuple):
                format_id, fmt_type = format_data
            else:
                format_id = format_data
                fmt_type = 'unknown'

            print(f"[DEBUG] Selected format_id={format_id}, fmt_type={fmt_type}")

            if fmt_type == 'combined':
                # 混合格式，直接下载
                output_path = os.path.join(save_path, f"{title}.%(ext)s")
                self._download_yt_dlp(url, format_id, output_path, info)
            else:
                # 纯视频或纯音频 - 自动下载并合并
                output_path = os.path.join(save_path, f"{title}.%(ext)s")
                self._download_and_merge(url, format_id, fmt_type, output_path, info)

    def _download_m3u8(self, url: str, output_path: str):
        """下载 m3u8 视频"""
        self.download_btn.setEnabled(False)
        self.status_bar.showMessage("正在下载 m3u8...")

        # 先添加到任务列表
        info = self.current_video_info
        title = self.title_edit.text().strip() or 'm3u8_video'

        # 使用 downloader 来管理任务（虽然不是 yt-dlp）
        task_id = f'm3u8_{int(time.time())}'
        task = DownloadTask(task_id, url, 'm3u8', output_path, title, 'm3u8')
        self.downloader.tasks[task_id] = task
        self._add_task_to_table(task_id)

        # 使用 Qt 线程避免直接操作 UI
        self.m3u8_thread = M3u8DownloadThread(self.ffmpeg_handler, url, output_path)
        self.m3u8_thread.completed.connect(lambda success, err: self._on_m3u8_complete(task_id, success, err))
        self.m3u8_thread.start()

    def _on_m3u8_complete(self, task_id: str, success: bool, error: str):
        """m3u8 下载完成回调"""
        self._on_download_complete(task_id, 'completed' if success else 'failed', error)

    def _download_yt_dlp(self, url: str, format_id: str, output_path: str, info: dict):
        """使用 yt-dlp 下载"""
        platform = info.get('platform', '')
        platform_map = {'YouTube': 'youtube', 'Bilibili': 'bilibili'}
        platform_key = platform_map.get(platform, platform)  # handle both 'Bilibili' and 'bilibili'
        cookies_path = None

        if platform_key:
            cookies_path = self.cookie_manager.get_cookie_path_for_yt_dlp(platform_key)

        self.download_btn.setEnabled(False)
        self.status_bar.showMessage("正在下载...")

        task_id = self.downloader.download(
            url=url,
            format_id=format_id,
            output_path=output_path,
            cookies_path=cookies_path,
            title=info.get('title', ''),
            platform=platform,
        )

        self._add_task_to_table(task_id)

    def _download_and_merge(self, url: str, format_id: str, fmt_type: str, output_path: str, info: dict):
        """下载并合并视频和音频"""
        platform = info.get('platform', '')
        platform_map = {'YouTube': 'youtube', 'Bilibili': 'bilibili'}
        platform_key = platform_map.get(platform, platform)  # handle both 'Bilibili' and 'bilibili'
        cookies_path = None

        if platform_key:
            cookies_path = self.cookie_manager.get_cookie_path_for_yt_dlp(platform_key)

        formats = info.get('formats', [])

        # 根据用户选择构建合并格式
        if fmt_type == 'video':
            # 用户选择了纯视频 - 匹配最佳音频
            merge_format = f"{format_id}+bestaudio/best"
        elif fmt_type == 'audio':
            # 用户选择了纯音频 - 匹配最佳视频
            merge_format = f"bestvideo+{format_id}/best"
        else:
            # 降级为最佳格式
            merge_format = "bestvideo+bestaudio/best"

        print(f"[DEBUG] Merge format: {merge_format}")
        print(f"[DEBUG] Cookie path: {cookies_path}")
        print(f"[DEBUG] URL: {url[:80]}...")
        self.download_btn.setEnabled(False)
        self.status_bar.showMessage("正在下载并合并...")

        task_id = self.downloader.download(
            url=url,
            format_id=merge_format,
            output_path=output_path,
            cookies_path=cookies_path,
            title=info.get('title', ''),
            platform=platform,
        )

        self._add_task_to_table(task_id)

    def _on_download_progress(self, task_id: str, progress: dict):
        """下载进度更新"""
        self._update_task_in_table(task_id, progress)
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

    def _load_task_history(self):
        """加载历史记录到任务列表"""
        history = self.task_manager.get_history(limit=100)
        for record in reversed(history):  # 反转，最新的在前面
            row = self.task_table.rowCount()
            self.task_table.insertRow(row)

            self.task_table.setItem(row, 0, QTableWidgetItem(record.title))
            self.task_table.setItem(row, 1, QTableWidgetItem(record.format_id))

            # 进度条
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(100)
            if record.status == 'completed':
                progress_bar.setValue(100)
            elif record.status == 'downloading':
                progress_bar.setValue(0)
            else:
                progress_bar.setValue(0)
            progress_bar.setTextVisible(True)
            progress_bar.setFormat(f"{record.status}")
            self.task_table.setCellWidget(row, 2, progress_bar)

            status_text = {
                'completed': '已完成',
                'failed': '失败',
                'cancelled': '已取消',
                'downloading': '下载中'
            }.get(record.status, record.status)
            self.task_table.setItem(row, 3, QTableWidgetItem(status_text))

            # 操作按钮（只有completed可以重新下载）
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)

            redownload_btn = QPushButton("重试")
            redownload_btn.clicked.connect(lambda _, r=record: self._redownload_from_record(r))
            btn_layout.addWidget(redownload_btn)

            btn_widget.setLayout(btn_layout)
            self.task_table.setCellWidget(row, 4, btn_widget)

            # 隐藏列，存task_id用于进度更新
            self.task_table.setItem(row, 5, QTableWidgetItem(f"history_{record.url}"))

        self.task_table.resizeRowsToContents()

    def _redownload_from_record(self, record):
        """从历史记录重新下载"""
        self.url_edit.setText(record.url)
        self.parse_url()

    def clear_task_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有下载记录吗？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.task_manager.clear_history()
            self.task_table.setRowCount(0)
            QMessageBox.information(self, "成功", "历史记录已清空")

    def _on_download_complete(self, task_id: str, status: str, error: str):
        """下载完成"""
        print(f"[DEBUG] _on_download_complete called: task_id={task_id}, status={status}, error={error[:100] if error else None}")
        self.download_btn.setEnabled(True)

        # 获取任务信息用于保存记录
        task = self.downloader.get_task(task_id)

        if status == 'completed':
            self.status_bar.showMessage("下载完成")
            # 更新进度条为100%
            for row in range(self.task_table.rowCount()):
                item = self.task_table.item(row, 5)
                if item and item.text() == task_id:
                    progress_bar = self.task_table.cellWidget(row, 2)
                    if progress_bar and isinstance(progress_bar, QProgressBar):
                        progress_bar.setValue(100)
                        progress_bar.setFormat("100%")
                    self.task_table.item(row, 3).setText("已完成")
            QMessageBox.information(self, "完成", "下载完成！")
        else:
            self.status_bar.showMessage(f"下载失败")
            print(f"[DEBUG] Download failed. Error: {error}")
            QMessageBox.critical(self, "下载失败", f"错误:\n{error[:500]}")

        # 保存到历史记录
        if task:
            record = TaskRecord(
                url=task.url,
                title=task.title,
                platform=task.platform,
                format_id=task.format_id,
                output_path=task.output_path,
                status=status,
                error=error or ''
            )
            self.task_manager.add_record(record)

        self._refresh_task_list()

    def _add_task_to_table(self, task_id: str):
        """添加任务到表格"""
        print(f"[DEBUG] _add_task_to_table called with task_id={task_id}")
        task = self.downloader.get_task(task_id)
        print(f"[DEBUG] get_task result: {task}")
        if not task:
            return

        row = self.task_table.rowCount()
        self.task_table.insertRow(row)

        self.task_table.setItem(row, 0, QTableWidgetItem(task.title))
        self.task_table.setItem(row, 1, QTableWidgetItem(task.format_id))
        self.task_table.setItem(row, 3, QTableWidgetItem("下载中"))

        # 进度条
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("0%")
        progress_bar.setMinimumHeight(20)  # 确保进度条有足够高度
        self.task_table.setCellWidget(row, 2, progress_bar)

        # 设置行高
        self.task_table.verticalHeader().setDefaultSectionSize(30)

        # 操作按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(lambda: self.cancel_task(task_id))
        self.task_table.setCellWidget(row, 4, cancel_btn)

        # 隐藏列，存task_id用于进度更新
        self.task_table.setItem(row, 5, QTableWidgetItem(task_id))
        print(f"[DEBUG] _add_task_to_table completed. Row={row}, title={task.title}")
        print(f"[DEBUG] Table info: rows={self.task_table.rowCount()}, cols={self.task_table.columnCount()}")
        print(f"[DEBUG] Item(0,0)={self.task_table.item(0, 0).text() if self.task_table.item(0, 0) else 'None'}")
        print(f"[DEBUG] Item(0,3)={self.task_table.item(0, 3).text() if self.task_table.item(0, 3) else 'None'}")
        print(f"[DEBUG] Widget(0,2)={self.task_table.cellWidget(0, 2)}")

        # 调整行高以确保进度条可见
        self.task_table.resizeRowsToContents()
        # 强制刷新表格显示
        self.task_table.viewport().update()
        self.task_table.repaint()

    def _update_task_in_table(self, task_id: str, progress: dict):
        """更新任务进度"""
        print(f"[DEBUG _update_task_in_table] task_id={task_id}, table rows={self.task_table.rowCount()}")
        for row in range(self.task_table.rowCount()):
            # 获取存储的 task_id（在第5列，隐藏列）
            item = self.task_table.item(row, 5)
            print(f"[DEBUG] Checking row {row}, item={item}")
            if item and item.text() == task_id:
                print(f"[DEBUG] Found matching task at row {row}")
                progress_val = progress.get('progress', 0)
                if progress_val >= 0:
                    # 更新进度条
                    progress_bar = self.task_table.cellWidget(row, 2)
                    print(f"[DEBUG] Progress bar widget: {progress_bar}, type: {type(progress_bar)}")
                    if progress_bar and isinstance(progress_bar, QProgressBar):
                        progress_bar.setValue(int(progress_val))
                        progress_bar.setFormat(f"{progress_val:.1f}%")
                        print(f"[DEBUG] Updated progress bar to {progress_val}%")
                if 'merging' in str(progress):
                    self.task_table.item(row, 3).setText("合并中...")
                elif progress_val >= 0:
                    self.task_table.item(row, 3).setText("下载中")
                break
        else:
            print(f"[DEBUG] Task {task_id} not found in table!")

    def _refresh_task_list(self):
        """刷新任务列表"""
        import traceback
        print(f"[DEBUG] _refresh_task_list called. Current rows: {self.task_table.rowCount()}")
        print(f"[DEBUG] _refresh_task_list call stack:")
        traceback.print_stack()
        self.task_table.setRowCount(0)
        for task_id, task in self.downloader.get_all_tasks().items():
            row = self.task_table.rowCount()
            self.task_table.insertRow(row)

            self.task_table.setItem(row, 0, QTableWidgetItem(task.title))
            self.task_table.setItem(row, 1, QTableWidgetItem(task.format_id))
            self.task_table.setItem(row, 3, QTableWidgetItem(task.state.value))

            # 进度条
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(100)
            progress_bar.setValue(int(task.progress))
            progress_bar.setTextVisible(True)
            progress_bar.setFormat(f"{task.progress:.1f}%")
            self.task_table.setCellWidget(row, 2, progress_bar)

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)

            if task.state.value == 'downloading':
                pause_btn = QPushButton("暂停")
                pause_btn.clicked.connect(lambda _, tid=task_id: self.pause_task(tid))
                btn_layout.addWidget(pause_btn)

            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(lambda _, tid=task_id: self.cancel_task(tid))
            btn_layout.addWidget(cancel_btn)

            btn_widget.setLayout(btn_layout)
            self.task_table.setCellWidget(row, 4, btn_widget)

            # 隐藏列，存task_id用于进度更新
            self.task_table.setItem(row, 5, QTableWidgetItem(task_id))

        print(f"[DEBUG] _refresh_task_list completed. Rows: {self.task_table.rowCount()}, Tasks in downloader: {len(self.downloader.get_all_tasks())}")

    def pause_task(self, task_id: str):
        self.downloader.pause(task_id)
        self._refresh_task_list()

    def cancel_task(self, task_id: str):
        self.downloader.cancel(task_id)
        self._refresh_task_list()

    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = dialog.get_config()
            self._save_config()
            self._update_ffmpeg_path()
            self._update_deno_path()
            self._update_cookie_manager()
            self.save_path_edit.setText(self.config.get('download_path', ''))
            QMessageBox.information(self, "成功", "设置已保存")

    def open_transcode(self):
        """打开转码对话框"""
        dialog = TranscodeDialog(self.ffmpeg_handler, self)
        dialog.exec()

    def show_about(self):
        """显示关于"""
        QMessageBox.about(self, "关于",
                         "视频下载器 v1.0\n\n"
                         "支持 YouTube、Bilibili、m3u8 直链下载\n"
                         "内置 ffmpeg 转码功能")

    def _save_config(self):
        """保存配置"""
        import json
        config_path = 'config/settings.json'
        os.makedirs('config', exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def closeEvent(self, event):
        """关闭时保存配置"""
        self._save_config()
        event.accept()