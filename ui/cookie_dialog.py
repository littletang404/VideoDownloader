"""Focused Cookie management dialog."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .theme import apply_theme


class CookieDialog(QDialog):
    changed = pyqtSignal()

    PLATFORM_KEYS = {
        "YouTube": "youtube",
        "Bilibili": "bilibili",
        "抖音": "douyin",
    }

    def __init__(self, cookie_manager, parent=None):
        super().__init__(parent)
        self.cookie_manager = cookie_manager
        self.setWindowTitle("Cookie 与登录状态")
        self.setMinimumSize(640, 480)
        apply_theme(self)
        self._build_ui()
        self._refresh_status()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel("Cookie 与登录状态")
        title.setObjectName("HeroTitle")
        layout.addWidget(title)

        hint = QLabel(
            "仅在下载会员、年龄限制或需要登录的内容时使用。"
            "数据只保存在本机，不会上传到本程序之外。"
        )
        hint.setProperty("muted", True)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        platform_row = QHBoxLayout()
        platform_row.addWidget(QLabel("平台"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(self.PLATFORM_KEYS)
        self.platform_combo.currentIndexChanged.connect(self._refresh_status)
        platform_row.addWidget(self.platform_combo)
        platform_row.addStretch()
        self.status_label = QLabel()
        self.status_label.setObjectName("StatusChip")
        platform_row.addWidget(self.status_label)
        layout.addLayout(platform_row)

        self.cookie_edit = QTextEdit()
        self.cookie_edit.setPlaceholderText(
            "粘贴 Netscape cookies.txt 内容，或浏览器插件导出的 JSON 数组…"
        )
        layout.addWidget(self.cookie_edit, 1)

        action_row = QHBoxLayout()
        import_btn = QPushButton("从文件导入")
        import_btn.clicked.connect(self._import_file)
        action_row.addWidget(import_btn)

        delete_btn = QPushButton("删除当前 Cookie")
        delete_btn.setProperty("danger", True)
        delete_btn.clicked.connect(self._delete_cookie)
        action_row.addWidget(delete_btn)
        action_row.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        action_row.addWidget(close_btn)

        save_btn = QPushButton("保存 Cookie")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self._save_text)
        action_row.addWidget(save_btn)
        layout.addLayout(action_row)

    def _platform_key(self) -> str:
        return self.PLATFORM_KEYS[self.platform_combo.currentText()]

    def _refresh_status(self) -> None:
        key = self._platform_key()
        status = self.cookie_manager.get_all_cookies_status().get(key, {})
        if status.get("valid"):
            self.status_label.setText("已加载")
            self.status_label.setProperty("warning", False)
        elif status.get("exists"):
            self.status_label.setText("格式可能无效")
            self.status_label.setProperty("warning", True)
        else:
            self.status_label.setText("未加载")
            self.status_label.setProperty("warning", True)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _import_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Cookie 文件",
            "",
            "Cookie 文件 (*.txt *.json);;所有文件 (*.*)",
        )
        if not file_path:
            return
        if self.cookie_manager.import_from_file(self._platform_key(), file_path):
            self.cookie_edit.clear()
            self._refresh_status()
            self.changed.emit()
            QMessageBox.information(self, "导入成功", "Cookie 已保存到本机。")
        else:
            QMessageBox.warning(self, "导入失败", "无法识别该 Cookie 文件，请检查格式。")

    def _save_text(self) -> None:
        content = self.cookie_edit.toPlainText().strip()
        if not content:
            QMessageBox.information(self, "尚未填写", "请先粘贴 Cookie 内容。")
            return
        if self.cookie_manager.import_from_text(self._platform_key(), content):
            self.cookie_edit.clear()
            self._refresh_status()
            self.changed.emit()
            QMessageBox.information(self, "保存成功", "Cookie 已保存到本机。")
        else:
            QMessageBox.warning(self, "保存失败", "Cookie 内容为空或格式无法识别。")

    def _delete_cookie(self) -> None:
        reply = QMessageBox.question(
            self,
            "删除 Cookie",
            "确定删除当前平台保存在本机的 Cookie 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.cookie_manager.delete_cookie(self._platform_key()):
            self.cookie_edit.clear()
            self._refresh_status()
            self.changed.emit()
