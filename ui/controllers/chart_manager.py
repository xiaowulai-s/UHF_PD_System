# -*- coding: utf-8 -*-
"""Chart manager - handles real-time chart display and updates."""

from __future__ import annotations

import time
from typing import Any, Dict

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    from ui.design_tokens import DT

    DESIGN_TOKENS_AVAILABLE = True
except ImportError:
    DESIGN_TOKENS_AVAILABLE = False


class ChartManager(QObject):
    """图表管理器

    职责：
    - 管理实时曲线图的显示和更新
    - 处理曲线图的创建、数据追加和清空
    - 管理图表标题标签
    - 管理设备卡片历史数据
    """

    def __init__(self, state, parent: QObject = None) -> None:
        super().__init__(parent)
        self._state = state
        self._chart_layout: QVBoxLayout = None
        self._chart_title_label: QLabel = None
        self._card_history: Dict[str, Dict[str, list]] = {}

    @property
    def chart_layout(self) -> QVBoxLayout:
        return self._chart_layout

    @chart_layout.setter
    def chart_layout(self, value: QVBoxLayout) -> None:
        self._chart_layout = value

    @property
    def chart_title_label(self) -> QLabel:
        return self._chart_title_label

    @chart_title_label.setter
    def chart_title_label(self, value: QLabel) -> None:
        self._chart_title_label = value

    @property
    def card_history(self) -> Dict[str, Dict[str, list]]:
        return self._card_history

    def clear_card_history(self, device_id: str = None) -> None:
        if device_id:
            self._card_history.pop(device_id, None)
        else:
            self._card_history.clear()

    def update_selected_card_chart(self, card_name: str, value: float) -> None:
        device_id = self._state.current_device_id or ""
        if device_id not in self._card_history:
            self._card_history[device_id] = {}
        device_history = self._card_history[device_id]
        if card_name not in device_history:
            device_history[card_name] = []

        history = device_history[card_name]
        history.append(value)
        max_points = self._state.max_history_points
        if len(history) > max_points:
            history.pop(0)

        if card_name == self._state.selected_card_name:
            current_chart = self._state.current_chart
            if current_chart is not None and self._state.current_chart_card_name == card_name:
                current_chart.add_point(card_name, time.time(), float(value))
                current_chart.update()
            else:
                self._refresh_chart_for_card(card_name)

    def _refresh_chart_for_card(self, card_name: str) -> None:
        device_id = self._state.current_device_id or ""
        device_history = self._card_history.get(device_id, {})
        history = device_history.get(card_name, [])

        if not history:
            self._clear_chart()
            self._state.reset_chart_state()
            empty = QLabel("← 点击左侧数据卡片查看实时曲线")
            if DESIGN_TOKENS_AVAILABLE:
                empty.setStyleSheet(
                    f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px; background: transparent;"
                )
            else:
                empty.setStyleSheet("color: #8B949E; font-size: 13px; background: transparent;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._chart_layout.addWidget(empty)
            return

        try:
            from ui.widgets.visual import RealtimeChart

            current_chart = self._state.current_chart
            if current_chart is not None and self._state.current_chart_card_name == card_name:
                current_chart.clear_series(card_name)
                current_chart.add_series(card_name, "#3B82F6")
                base_time = time.time() - len(history)
                for i, val in enumerate(history):
                    current_chart.add_point(card_name, base_time + i, float(val))
                current_chart.update()
                return

            self._clear_chart()

            chart = RealtimeChart(title="")
            chart.add_series(card_name, "#3B82F6")
            base_time = time.time() - len(history)
            for i, val in enumerate(history):
                chart.add_point(card_name, base_time + i, float(val))

            self._chart_layout.addWidget(chart)
            self._state.current_chart = chart
            self._state.current_chart_card_name = card_name
        except Exception as e:
            self._clear_chart()
            self._state.reset_chart_state()
            empty = QLabel(f"曲线图加载失败: {e}")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._chart_layout.addWidget(empty)

    def _clear_chart(self) -> None:
        while self._chart_layout.count():
            item = self._chart_layout.itemAt(0)
            if item and item.widget():
                item.widget().deleteLater()
                self._chart_layout.removeItem(item)

    def clear_chart(self) -> None:
        self._clear_chart()
        self._state.reset_chart_state()