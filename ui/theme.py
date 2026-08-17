"""Central visual system for the desktop UI."""

APP_STYLE = """
QMainWindow, QDialog {
    background: #0B1020;
}
QWidget {
    color: #E8EDF7;
    font-family: "Microsoft YaHei UI", "Segoe UI";
    font-size: 13px;
}
QWidget#Root {
    background: #0B1020;
}
QLabel#AppTitle {
    font-size: 24px;
    font-weight: 700;
    color: #F8FAFF;
}
QLabel#AppSubtitle, QLabel[muted="true"] {
    color: #8994AA;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: 700;
    color: #F5F7FB;
}
QLabel#HeroTitle {
    font-size: 18px;
    font-weight: 700;
    color: #F8FAFF;
}
QLabel#PlatformBadge {
    background: #1C2845;
    color: #8CB7FF;
    border: 1px solid #294273;
    border-radius: 10px;
    padding: 3px 9px;
    font-weight: 600;
}
QLabel#StatusChip {
    background: #14251F;
    color: #66D9A3;
    border: 1px solid #23503E;
    border-radius: 10px;
    padding: 3px 9px;
}
QLabel#StatusChip[warning="true"] {
    background: #2A2114;
    color: #F7C66A;
    border-color: #60481E;
}
QLabel#EmptyIcon {
    color: #58709E;
    font-size: 32px;
    font-weight: 700;
}
QFrame#Card {
    background: #11182A;
    border: 1px solid #202B43;
    border-radius: 16px;
}
QFrame#Inset {
    background: #0D1424;
    border: 1px solid #1B2740;
    border-radius: 12px;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background: #0C1322;
    color: #F0F4FB;
    border: 1px solid #26334D;
    border-radius: 9px;
    padding: 9px 11px;
    selection-background-color: #397DF6;
}
QLineEdit {
    min-height: 22px;
}
QTextEdit {
    padding: 10px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #4C8DFF;
}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled {
    background: #101726;
    color: #69758B;
}
QComboBox {
    min-height: 22px;
    padding-right: 28px;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox QAbstractItemView {
    background: #111A2D;
    color: #E8EDF7;
    border: 1px solid #2A3853;
    selection-background-color: #285BB0;
    padding: 5px;
}
QPushButton {
    min-height: 20px;
    background: #1A2438;
    color: #DDE5F3;
    border: 1px solid #2A3852;
    border-radius: 9px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #22304A;
    border-color: #3A4D70;
}
QPushButton:pressed {
    background: #162034;
}
QPushButton:disabled {
    background: #141B29;
    color: #5F6878;
    border-color: #202838;
}
QPushButton[primary="true"] {
    background: #397DF6;
    color: white;
    border-color: #397DF6;
}
QPushButton[primary="true"]:hover {
    background: #4B8BFF;
    border-color: #4B8BFF;
}
QPushButton[danger="true"] {
    color: #FF9C9C;
    border-color: #5C3038;
    background: #25171D;
}
QPushButton[flat="true"] {
    background: transparent;
    border-color: transparent;
    color: #9BA8BD;
}
QPushButton[flat="true"]:hover {
    background: #172136;
    color: #F0F4FB;
}
QTableWidget {
    background: transparent;
    alternate-background-color: #0E1627;
    border: none;
    gridline-color: transparent;
    outline: none;
}
QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #1C263B;
}
QTableWidget::item:selected {
    background: #172A4C;
}
QHeaderView::section {
    background: #0E1627;
    color: #7F8CA3;
    border: none;
    border-bottom: 1px solid #202B43;
    padding: 9px;
    font-weight: 600;
}
QProgressBar {
    background: #0B1220;
    color: #DDE5F3;
    border: 1px solid #22304A;
    border-radius: 6px;
    min-height: 13px;
    text-align: center;
}
QProgressBar::chunk {
    background: #397DF6;
    border-radius: 5px;
}
QTabWidget::pane {
    border: 1px solid #202B43;
    border-radius: 12px;
    background: #11182A;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: #8793A9;
    padding: 10px 18px;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #EAF1FF;
    border-bottom: 2px solid #397DF6;
}
QGroupBox {
    border: 1px solid #202B43;
    border-radius: 12px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
    font-weight: 700;
    color: #E8EDF7;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QRadioButton, QCheckBox {
    spacing: 7px;
}
QStatusBar {
    background: #0B1020;
    color: #8490A5;
    border-top: 1px solid #172033;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    width: 10px;
    background: transparent;
}
QScrollBar::handle:vertical {
    background: #2B3852;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QToolTip {
    background: #172136;
    color: #E8EDF7;
    border: 1px solid #31425F;
    padding: 6px;
}
"""


def apply_theme(widget) -> None:
    widget.setStyleSheet(APP_STYLE)
