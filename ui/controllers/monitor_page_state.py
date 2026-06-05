# -*- coding: utf-8 -*-
"""Monitor page state manager - centralized state container."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget


class MonitorPageState(QObject):
    """监控页面状态管理器

    集中管理监控页面的所有状态变量，提供统一的状态访问接口。
    职责：
    - 当前选中设备和卡片的状态跟踪
    - 设备ID到卡片历史的映射
    - 卡片精度配置
    - 卡片到寄存器的映射
    """

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)
        self._current_device_id: Optional[str] = None
        self._selected_card_name: Optional[str] = None
        self._selected_card_widget: Optional[QWidget] = None
        self._current_chart = None
        self._current_chart_card_name: Optional[str] = None
        self._card_precision: Dict[str, int] = {}
        self._card_to_register: Dict[QWidget, str] = {}
        self._card_widgets: Dict[str, QWidget] = {}
        self._max_history_points: int = 120

    @property
    def current_device_id(self) -> Optional[str]:
        return self._current_device_id

    @current_device_id.setter
    def current_device_id(self, value: Optional[str]) -> None:
        self._current_device_id = value

    @property
    def selected_card_name(self) -> Optional[str]:
        return self._selected_card_name

    @selected_card_name.setter
    def selected_card_name(self, value: Optional[str]) -> None:
        self._selected_card_name = value

    @property
    def selected_card_widget(self) -> Optional[QWidget]:
        return self._selected_card_widget

    @selected_card_widget.setter
    def selected_card_widget(self, value: Optional[QWidget]) -> None:
        self._selected_card_widget = value

    @property
    def current_chart(self):
        return self._current_chart

    @current_chart.setter
    def current_chart(self, value) -> None:
        self._current_chart = value

    @property
    def current_chart_card_name(self) -> Optional[str]:
        return self._current_chart_card_name

    @current_chart_card_name.setter
    def current_chart_card_name(self, value: Optional[str]) -> None:
        self._current_chart_card_name = value

    @property
    def card_precision(self) -> Dict[str, int]:
        return self._card_precision

    @property
    def card_to_register(self) -> Dict[QWidget, str]:
        return self._card_to_register

    @property
    def card_widgets(self) -> Dict[str, QWidget]:
        return self._card_widgets

    @property
    def max_history_points(self) -> int:
        return self._max_history_points

    def get_card_precision(self, register_name: str) -> int:
        return self._card_precision.get(register_name, 2)

    def get_card_widget(self, register_name: str) -> Optional[QWidget]:
        return self._card_widgets.get(register_name)

    def get_all_card_widgets(self) -> Dict[str, QWidget]:
        return dict(self._card_widgets)

    def get_card_count(self) -> int:
        return len(self._card_widgets)

    def get_first_card(self):
        for card in self._card_widgets.values():
            return card
        return None

    def add_card_widget(self, register_name: str, widget: QWidget) -> None:
        self._card_widgets[register_name] = widget

    def add_card_register_mapping(self, widget: QWidget, register_name: str) -> None:
        self._card_to_register[widget] = register_name

    def remove_card_register_mapping(self, widget: QWidget) -> None:
        self._card_to_register.pop(widget, None)

    def set_card_precision(self, register_name: str, precision: int) -> None:
        self._card_precision[register_name] = precision

    def clear_card_precisions(self) -> None:
        self._card_precision.clear()

    def clear_card_mappings(self) -> None:
        self._card_to_register.clear()

    def clear_card_widgets(self) -> None:
        self._card_widgets.clear()

    def reset_selection(self) -> None:
        self._selected_card_name = None
        self._selected_card_widget = None

    def reset_chart_state(self) -> None:
        self._current_chart = None
        self._current_chart_card_name = None

    def full_reset(self) -> None:
        self.reset_selection()
        self.reset_chart_state()
        self.clear_card_precisions()
        self.clear_card_mappings()
        self.clear_card_widgets()