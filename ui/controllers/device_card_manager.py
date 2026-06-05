# -*- coding: utf-8 -*-
"""Device card manager - handles data card creation, selection, and click events."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    from ui.design_tokens import DT

    DESIGN_TOKENS_AVAILABLE = True
except ImportError:
    DESIGN_TOKENS_AVAILABLE = False


class DeviceCardManager(QObject):
    """数据卡片管理器

    职责：
    - 数据卡片的创建和显示更新
    - 卡片选中状态的切换和高亮
    - 卡片点击事件的分发
    - 卡片的清空和重置
    """

    def __init__(self, state, chart_manager, parent: QObject = None) -> None:
        super().__init__(parent)
        self._state = state
        self._chart_manager = chart_manager
        self._device_cards_layout: QVBoxLayout = None

    @property
    def cards_layout(self) -> QVBoxLayout:
        return self._device_cards_layout

    @cards_layout.setter
    def cards_layout(self, value: QVBoxLayout) -> None:
        self._device_cards_layout = value

    def update_cards_display(
        self,
        current_device_id: str,
        device_cards: Dict[str, Any],
        data_card_cls: type,
        event_filter_target: QObject,
    ) -> None:
        self._state.current_device_id = current_device_id

        while self._device_cards_layout.count():
            item = self._device_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._state.clear_card_widgets()
        self._state.clear_card_mappings()
        self._state.reset_selection()

        if not current_device_id:
            empty_label = QLabel("请先选择一个设备")
            if DESIGN_TOKENS_AVAILABLE:
                empty_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px;")
            else:
                empty_label.setStyleSheet("color: #8B949E; font-size: 13px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._device_cards_layout.addWidget(empty_label)
            return

        cards_config = device_cards.get(current_device_id, [])

        if not cards_config:
            empty_label = QLabel("该设备暂无数据卡片配置")
            if DESIGN_TOKENS_AVAILABLE:
                empty_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px;")
            else:
                empty_label.setStyleSheet("color: #8B949E; font-size: 13px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._device_cards_layout.addWidget(empty_label)
            return

        first_card = None
        for config in cards_config:
            register_name = config.get("register_name", "")
            card_title = config.get("title", register_name)

            card = data_card_cls(title=card_title, value="--")
            card.register_name = register_name
            self._state.set_card_precision(register_name, config.get("decimal_places", 2))

            if DESIGN_TOKENS_AVAILABLE:
                card.setMinimumSize(150, 95)
                card.setStyleSheet(
                    f"""
                    DataCard {{
                        background-color: {DT.C.BG_PRIMARY};
                        border: 1px solid {DT.C.BORDER_DEFAULT};
                        border-radius: {DT.R.MD}px;
                        padding: {DT.S.XS}px;
                    }}
                    DataCard:hover {{
                        border-color: {DT.C.ACCENT_PRIMARY};
                        background-color: {DT.C.BG_HOVER};
                    }}
                """
                )
            else:
                card.setMinimumSize(140, 90)

            card.installEventFilter(event_filter_target)
            self._state.add_card_register_mapping(card, register_name)

            self._device_cards_layout.addWidget(card)
            self._state.add_card_widget(register_name, card)

            if first_card is None:
                first_card = (register_name, card)

        if first_card:
            name, widget = first_card
            QTimer.singleShot(100, lambda n=name, w=widget: self._on_card_clicked(n, w))

    def _on_card_clicked(self, card_name: str, card_widget: QWidget) -> None:
        prev_widget = self._state.selected_card_widget
        if prev_widget is not None:
            prev_widget.setStyleSheet(
                f"""
                DataCard {{
                    background: {'#F8FAFC' if DESIGN_TOKENS_AVAILABLE else '#FFFFFF'};
                    border: 1px solid {'#E5E7EB' if DESIGN_TOKENS_AVAILABLE else '#E5E7EB'};
                    border-radius: 10px;
                    padding: 14px;
                }}
                DataCard:hover {{
                    border-color: {'#93C5FD' if DESIGN_TOKENS_AVAILABLE else '#3B82F6'};
                    background: {'#EFF6FF' if DESIGN_TOKENS_AVAILABLE else '#F0F7FF'};
                }}
                """
            )

        self._state.selected_card_name = card_name
        self._state.selected_card_widget = card_widget

        card_widget.setStyleSheet(
            f"""
            DataCard {{
                background: {'#EFF6FF' if DESIGN_TOKENS_AVAILABLE else '#EBF5FF'};
                border: 2px solid {'#3B82F6' if DESIGN_TOKENS_AVAILABLE else '#2563EB'};
                border-radius: 10px;
                padding: 14px;
            }}
            """
        )

        self._chart_manager.chart_title_label.setText(f"实时曲线 — {card_name}")
        self._chart_manager._refresh_chart_for_card(card_name)

    def handle_card_click_via_event(self, obj: QWidget) -> None:
        register_name = self._state.card_to_register.get(obj)
        if register_name:
            self._on_card_clicked(register_name, obj)

    def clear_all_cards(self) -> None:
        self._state.reset_selection()
        self._state.reset_chart_state()
        self._state.clear_card_precisions()
        self._state.clear_card_mappings()
        device_id = self._state.current_device_id or ""
        self._chart_manager.clear_card_history(device_id)
        while self._device_cards_layout.count():
            item = self._device_cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._state.clear_card_widgets()
        self._chart_manager.clear_chart()