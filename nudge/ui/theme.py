from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QFont

BLUE = QColor("#4F8EF7")
BLUE_DEEP = QColor("#2F6FE0")
AMBER = QColor("#F5A524")
GREEN = QColor("#34C77B")
RED = QColor("#F2545B")
INK = QColor("#0E1117")
PANEL = QColor(18, 21, 28, 238)
LINE = QColor(255, 255, 255, 28)
TEXT = QColor("#F4F6FB")
MUTED = QColor("#9AA3B5")

FAMILY = ".AppleSystemUIFont" if sys.platform == "darwin" else "Segoe UI"


def font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont(FAMILY)
    f.setPixelSize(size)
    f.setWeight(weight)
    return f


STYLE = f"""
QWidget#bar {{ background: transparent; }}
QLabel {{ color: {TEXT.name()}; }}
QLabel[muted="true"] {{ color: {MUTED.name()}; }}
QLineEdit, QPlainTextEdit {{
    background: rgba(255,255,255,0.06);
    color: {TEXT.name()};
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    padding: 6px 12px;
    selection-background-color: {BLUE.name()};
}}
QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid rgba(255,255,255,0.24); }}
QLineEdit#goal:focus {{ border: 1px solid rgba(255,255,255,0.10); }}
QPushButton {{
    color: {TEXT.name()};
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    padding: 8px 16px;
}}
QPushButton:hover {{ background: rgba(255,255,255,0.14); }}
QPushButton:focus {{ border: 2px solid {BLUE.name()}; }}
QPushButton[kind="primary"] {{ background: {BLUE.name()}; border: none; color: white; }}
QPushButton[kind="primary"]:hover {{ background: {BLUE_DEEP.name()}; }}
QPushButton[kind="danger"] {{ background: {RED.name()}; border: none; color: white; }}
QPushButton[kind="danger"]:hover {{ background: #d9434a; }}
QPushButton[kind="warn"] {{ background: {AMBER.name()}; border: none; color: #1b1300; }}
QFrame#card {{ background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; }}
QPushButton[kind="stop"] {{ background: transparent; border: 1px solid rgba(242,84,91,0.6); color: #F2A0A4; }}
QPushButton[kind="stop"]:hover {{ background: rgba(242,84,91,0.14); }}
QPushButton[kind="link"] {{ background: transparent; border: none; color: {MUTED.name()}; padding: 10px 6px; }}
QPushButton[kind="link"]:hover {{ color: {TEXT.name()}; }}
QPushButton[kind="choice"] {{ text-align: left; padding: 0; }}
QToolButton#micMute, QToolButton#micArrow {{ background: transparent; border: none; padding: 0; margin: 0; }}
QToolButton#micMute {{ border-top-left-radius: 9px; border-bottom-left-radius: 9px; }}
QToolButton#micArrow {{ border-top-right-radius: 9px; border-bottom-right-radius: 9px; }}
QToolButton#micMute:hover, QToolButton#micArrow:hover {{ background: rgba(255,255,255,0.08); }}
QToolButton#micMute:pressed, QToolButton#micArrow:pressed {{ background: rgba(255,255,255,0.12); }}
QMenu {{ background: #1A1F2A; color: {TEXT.name()}; border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 14px; border-radius: 7px; }}
QMenu::item:selected {{ background: rgba(79,142,247,0.22); }}
QMenu::item:disabled {{ color: {MUTED.name()}; }}
QMenu::separator {{ height: 1px; background: rgba(255,255,255,0.08); margin: 4px 6px; }}
QScrollArea#feed, QWidget#feedBody {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 6px; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.16); border-radius: 3px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""
