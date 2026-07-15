"""Dark/green theme shared by LoginWindow and MainWindow."""

BG = "#121212"
PANEL_BG = "#1c1c1c"
BORDER = "#333333"
TEXT = "#e6e6e6"
TEXT_MUTED = "#9a9a9a"
GREEN = "#22c55e"
GREEN_DIM = "#3a7d55"
RED = "#e6413a"
INPUT_BG = "#0e0e0e"

STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI";
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {BG};
}}

QLabel {{
    color: {TEXT};
}}

QLabel[role="title"] {{
    color: {GREEN};
    font-size: 26px;
    font-weight: bold;
}}

QLabel[role="panel-title"] {{
    color: {GREEN};
    font-weight: bold;
    font-size: 12px;
}}

QLabel[role="error"] {{
    color: {RED};
    font-weight: bold;
}}

QGroupBox {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 14px;
    padding: 10px;
    font-weight: bold;
    color: {GREEN};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {GREEN};
}}

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {{
    background-color: {INPUT_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 8px;
    color: {TEXT};
    selection-background-color: {GREEN_DIM};
}}

QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {GREEN};
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}

QPushButton {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 10px 18px;
    font-weight: bold;
    color: {TEXT};
}}

QPushButton:hover {{
    border: 1px solid {GREEN};
}}

QPushButton:disabled {{
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
}}

QPushButton[role="primary"] {{
    color: {GREEN};
    border: 1px solid {GREEN};
}}

QPushButton[role="danger"] {{
    color: {RED};
    border: 1px solid {RED};
}}

QPushButton[role="close"] {{
    background-color: {RED};
    border-radius: 8px;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
    padding: 0px;
}}

QCheckBox {{
    color: {TEXT};
}}

QRadioButton {{
    color: {TEXT};
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 2px solid #555555;
    background: transparent;
}}

QRadioButton::indicator:checked {{
    background-color: {GREEN};
    border: 2px solid {GREEN};
}}

QTableWidget {{
    background-color: #000000;
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    color: {TEXT};
}}

QHeaderView::section {{
    background-color: {GREEN};
    color: #000000;
    font-weight: bold;
    padding: 6px;
    border: none;
}}

QTableWidget::item {{
    padding: 4px;
}}

QTextEdit {{
    background-color: #000000;
    border: 1px solid {BORDER};
    color: {TEXT_MUTED};
}}

QLabel[role="statusbar"] {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 8px;
    color: {TEXT_MUTED};
}}
"""
