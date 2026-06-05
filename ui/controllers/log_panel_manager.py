# -*- coding: utf-8 -*-
"""Log panel manager - handles unified log panel creation and log operations."""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import QDateTime, QObject
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

try:
    from ui.design_tokens import DT

    DESIGN_TOKENS_AVAILABLE = True
except ImportError:
    DESIGN_TOKENS_AVAILABLE = False


class LogPanelManager(QObject):
    """日志面板管理器

    职责：
    - 构建统一日志面板 UI
    - 追加日志消息（带时间戳和颜色编码）
    - 清空日志
    """

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)
        self._unified_log_view: QTextBrowser = None
        self._log_clear_btn: QPushButton = None
        self._constants: Dict[str, str] = {}

    @property
    def log_view(self) -> QTextBrowser:
        return self._unified_log_view

    @property
    def clear_btn(self) -> QPushButton:
        return self._log_clear_btn

    def build_panel(self, constants: dict) -> QWidget:
        self._constants = constants

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        log_title = QLabel("系统日志")
        if DESIGN_TOKENS_AVAILABLE:
            title_font = DT.T.get_font(*DT.T.LABEL)
            log_title.setFont(title_font)
            log_title.setStyleSheet(
                f"color: {DT.C.TEXT_SECONDARY}; background: transparent; font-weight: {DT.T.LABEL[2]};"
            )
        else:
            log_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #57606A; background: transparent;")
        header_layout.addWidget(log_title)

        clear_btn_text = constants.get("BTN_CLEAR_LOG", "清空日志")
        from ui.widgets import SecondaryButton

        self._log_clear_btn = SecondaryButton(clear_btn_text)
        self._log_clear_btn.setFixedSize(80, 26)
        self._log_clear_btn.clicked.connect(self._clear_log)
        header_layout.addStretch()
        header_layout.addWidget(self._log_clear_btn)
        layout.addLayout(header_layout)

        self._unified_log_view = QTextBrowser()
        self._unified_log_view.setReadOnly(True)
        self._unified_log_view.setOpenLinks(False)

        if DESIGN_TOKENS_AVAILABLE:
            bg_color = DT.C.BG_PRIMARY
            border_color = DT.C.BORDER_SUBTLE
            text_color = DT.C.TEXT_PRIMARY
            radius = f"{DT.R.SM}px"
            self._unified_log_view.setStyleSheet(
                f"""
                QTextBrowser {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                    border-radius: {radius};
                    color: {text_color};
                    font-family: '{DT.T.CODE[0]}';
                    font-size: {DT.T.CODE[1]}px;
                    padding: {DT.S.SM}px;
                }}
            """
            )
        else:
            self._unified_log_view.setStyleSheet(
                """
                QTextBrowser {
                    background-color: #1E1E1E;
                    border: 1px solid #333;
                    border-radius: 6px;
                    color: #D4D4D4;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 11px;
                    padding: 8px;
                }
            """
            )

        layout.addWidget(self._unified_log_view)
        return container

    def append_log(self, message: str, level: str = "INFO") -> None:
        if self._unified_log_view is None:
            return
        ts = QDateTime.currentDateTime().toString("HH:mm:ss.zzz")
        color_map = {
            "INFO": "#4CAF50",
            "SUCCESS": "#2196F3",
            "WARNING": "#FF9800",
            "ERROR": "#F44336",
            "CRITICAL": "#E91E63",
        }
        color = color_map.get(level, "#D4D4D4")
        html = f'<span style="color:#888;">[{ts}]</span> <span style="color:{color};">[{level}]</span> <span style="color:#D4D4D4;">{message}</span>'
        self._unified_log_view.append(html)

    def _clear_log(self) -> None:
        if self._unified_log_view is not None:
            self._unified_log_view.clear()

    def clear_log(self) -> None:
        self._clear_log()