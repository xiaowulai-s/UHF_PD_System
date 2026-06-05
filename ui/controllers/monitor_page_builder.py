# -*- coding: utf-8 -*-
"""Monitor page builder - handles UI construction of the monitor page."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from ui.design_tokens import DT

    DESIGN_TOKENS_AVAILABLE = True
except ImportError:
    DESIGN_TOKENS_AVAILABLE = False


class MonitorPageBuilder:
    """UI 构建器 - 负责监控页面的所有 UI 布局和组件创建

    纯 UI 构建逻辑，不包含业务状态管理。
    通过注入的方式接收子组件管理器，将布局引用回写。
    """

    def build(
        self,
        parent: QWidget,
        styles: dict,
        constants: dict,
        on_expand_panel: Callable,
        state,
        log_manager,
        chart_manager,
        card_manager,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        expand_btn, title_label = self._build_header(constants, on_expand_panel)
        layout.addLayout(self._build_header_layout(expand_btn, title_label))

        status_badge = self._build_info_container()
        info_container, name_label, desc_label, last_update_label = self._build_info_container_widget(status_badge)
        layout.addWidget(info_container)

        right_splitter = QSplitter(Qt.Orientation.Vertical)

        monitor_tabs = QTabWidget()
        self._style_tabs(monitor_tabs, styles, constants)

        data_tab = self._build_data_tab(styles, chart_manager, card_manager)
        register_tab, register_table = self._build_register_tab()

        tab_data_text = constants.get("TAB_REALTIME_DATA", "实时数据")
        tab_reg_text = constants.get("TAB_REGISTERS", "寄存器")

        monitor_tabs.addTab(data_tab, str(tab_data_text))
        monitor_tabs.addTab(register_tab, str(tab_reg_text))

        self._style_tab_bar(monitor_tabs, tab_data_text, tab_reg_text)

        right_splitter.addWidget(monitor_tabs)

        log_panel = log_manager.build_panel(constants)
        right_splitter.addWidget(log_panel)

        right_splitter.setStretchFactor(0, 7)
        right_splitter.setStretchFactor(1, 3)

        initial_height = 600
        monitor_h = int(initial_height * 0.70)
        log_h = int(initial_height * 0.30)
        right_splitter.setSizes([monitor_h, log_h])

        layout.addWidget(right_splitter)

        return {
            "page": page,
            "expand_btn": expand_btn,
            "title_label": title_label,
            "status_badge": status_badge,
            "right_splitter": right_splitter,
            "monitor_tabs": monitor_tabs,
            "register_table": register_table,
            "device_name_label": name_label,
            "device_desc_label": desc_label,
            "last_update_label": last_update_label,
        }

    def _build_header(self, constants: dict, on_expand_panel: Callable):
        expand_btn = QPushButton(">")
        expand_btn.setObjectName("left_expand_btn")
        expand_btn.setFixedSize(24, 24)
        expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        expand_btn.setToolTip("展开面板")
        if DESIGN_TOKENS_AVAILABLE:
            expand_font = DT.T.get_font(*DT.T.BODY_SMALL)
            expand_btn.setFont(expand_font)
        else:
            expand_font = QFont("Segoe UI Symbol", 10)
            expand_btn.setFont(expand_font)
        expand_btn.clicked.connect(on_expand_panel)
        expand_btn.hide()

        title_label = QLabel(constants.get("DEVICE_MONITOR_TITLE", "设备监控"))
        if DESIGN_TOKENS_AVAILABLE:
            title_font = DT.T.get_font(*DT.T.TITLE_MEDIUM)
            title_label.setFont(title_font)
            title_label.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY}; background: transparent;")
        else:
            title_label.setFont(QFont("Segoe UI Variable", 18, QFont.Weight.Bold))
            title_label.setStyleSheet("color: #24292F; background: transparent;")

        return expand_btn, title_label

    def _build_header_layout(self, expand_btn: QPushButton, title_label: QLabel) -> QHBoxLayout:
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        header_layout.addWidget(expand_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        return header_layout

    def _build_info_container_widget(self, status_badge):
        info_container = QWidget()
        if DESIGN_TOKENS_AVAILABLE:
            info_container.setStyleSheet(
                f"""
                background-color: {DT.C.BG_SECONDARY};
                border-radius: {DT.R.SM}px;
                padding: {DT.S.SM}px;
            """
            )
        else:
            info_container.setStyleSheet(
                "background-color: #F6F8FA; border-radius: 6px; padding: 8px;"
            )
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(16)

        name_label = QLabel("未选择设备")
        if DESIGN_TOKENS_AVAILABLE:
            name_font = DT.T.get_font(*DT.T.BODY)
            name_label.setFont(name_font)
            name_label.setStyleSheet(
                f"color: {DT.C.TEXT_PRIMARY}; background: transparent; font-weight: 500;"
            )
        else:
            name_label.setStyleSheet("color: #24292F; font-size: 14px; font-weight: 500; background: transparent;")
        info_layout.addWidget(name_label)

        desc_label = QLabel("")
        if DESIGN_TOKENS_AVAILABLE:
            desc_font = DT.T.get_font(*DT.T.CAPTION)
            desc_label.setFont(desc_font)
            desc_label.setStyleSheet(f"color: {DT.C.TEXT_SECONDARY}; background: transparent;")
        else:
            desc_label.setStyleSheet("color: #8B949E; font-size: 11px; background: transparent;")
        info_layout.addWidget(desc_label)

        info_layout.addWidget(status_badge)
        info_layout.addStretch()

        last_update_label = QLabel("-")
        if DESIGN_TOKENS_AVAILABLE:
            update_font = DT.T.get_font(*DT.T.CAPTION)
            last_update_label.setFont(update_font)
            last_update_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; background: transparent;")
        else:
            last_update_label.setStyleSheet("color: #8B949E; font-size: 11px; background: transparent;")
        info_layout.addWidget(last_update_label)

        return info_container, name_label, desc_label, last_update_label

    def _build_info_container(self):
        from ui.widgets.visual import AnimatedStatusBadge

        return AnimatedStatusBadge("Not Connected")

    def _build_data_tab(self, styles: dict, chart_manager, card_manager) -> QWidget:
        tab = QWidget()
        main_layout = QHBoxLayout(tab)
        if DESIGN_TOKENS_AVAILABLE:
            main_layout.setContentsMargins(DT.S.SM, DT.S.SM, DT.S.SM, DT.S.SM)
            main_layout.setSpacing(DT.S.MD)
        else:
            main_layout.setContentsMargins(12, 12, 12, 12)
            main_layout.setSpacing(16)

        left_panel = QWidget()
        left_panel.setMinimumWidth(180)
        left_panel.setMaximumWidth(260)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        cards_title = QLabel("数据列表")
        if DESIGN_TOKENS_AVAILABLE:
            title_font = DT.T.get_font(*DT.T.LABEL)
            cards_title.setFont(title_font)
            cards_title.setStyleSheet(
                f"color: {DT.C.TEXT_SECONDARY}; background: transparent; font-weight: {DT.T.LABEL[2]};"
            )
        else:
            cards_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #57606A; background: transparent;")
        left_layout.addWidget(cards_title)

        cards_scroll_area = QScrollArea()
        cards_scroll_area.setWidgetResizable(True)
        cards_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        if DESIGN_TOKENS_AVAILABLE:
            cards_scroll_area.setStyleSheet(
                f"""
                QScrollArea {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea > QWidget > QWidget {{
                    background: {DT.C.BG_PRIMARY};
                }}
            """
            )
        else:
            cards_scroll_area.setStyleSheet(
                """
                QScrollArea { background: transparent; border: none; }
                QScrollArea > QWidget > QWidget { background: #FFFFFF; }
            """
            )

        device_cards_layout = QVBoxLayout()
        device_cards_layout.setSpacing(10)
        device_cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        if DESIGN_TOKENS_AVAILABLE:
            device_cards_layout.setContentsMargins(DT.S.SM, DT.S.SM, DT.S.SM, DT.S.SM)
        else:
            device_cards_layout.setContentsMargins(8, 8, 8, 8)

        scroll_content = QWidget()
        scroll_content.setLayout(device_cards_layout)
        cards_scroll_area.setWidget(scroll_content)
        left_layout.addWidget(cards_scroll_area, 1)
        main_layout.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        chart_title_label = QLabel("实时曲线 — 请选择变量")
        if DESIGN_TOKENS_AVAILABLE:
            chart_title_font = DT.T.get_font(*DT.T.LABEL)
            chart_title_label.setFont(chart_title_font)
            chart_title_label.setStyleSheet(
                f"color: {DT.C.TEXT_SECONDARY}; background: transparent; font-weight: {DT.T.LABEL[2]};"
            )
        else:
            chart_title_label.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #57606A; background: transparent;"
            )

        chart_header = QHBoxLayout()
        chart_header.addWidget(chart_title_label)
        chart_header.addStretch()
        right_layout.addLayout(chart_header)

        chart_container = QWidget()
        if DESIGN_TOKENS_AVAILABLE:
            chart_container.setStyleSheet(
                f"""
                background-color: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_SUBTLE};
                border-radius: {DT.R.SM}px;
            """
            )
        else:
            chart_container.setStyleSheet(
                "background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px;"
            )

        chart_layout = QVBoxLayout(chart_container)
        if DESIGN_TOKENS_AVAILABLE:
            chart_layout.setContentsMargins(DT.S.MD, DT.S.MD, DT.S.MD, DT.S.MD)
            chart_layout.setSpacing(DT.S.SM)
        else:
            chart_layout.setContentsMargins(12, 12, 12, 12)
            chart_layout.setSpacing(8)

        chart_empty_label = QLabel("← 点击左侧数据卡片查看实时曲线")
        if DESIGN_TOKENS_AVAILABLE:
            chart_empty_label.setStyleSheet(
                f"color: {DT.C.TEXT_TERTIARY}; font-size: {DT.T.BODY[1]}px; background: transparent;"
            )
        else:
            chart_empty_label.setStyleSheet("color: #8B949E; font-size: 13px; background: transparent;")
        chart_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_layout.addWidget(chart_empty_label)

        right_layout.addWidget(chart_container, 1)
        main_layout.addWidget(right_panel, 1)

        card_manager.cards_layout = device_cards_layout
        chart_manager.chart_layout = chart_layout
        chart_manager.chart_title_label = chart_title_label

        return tab

    def _build_register_tab(self):
        from ui.widgets import DataTable

        tab = QWidget()
        layout = QVBoxLayout(tab)
        if DESIGN_TOKENS_AVAILABLE:
            layout.setContentsMargins(DT.S.MD, DT.S.MD, DT.S.MD, DT.S.MD)
        else:
            layout.setContentsMargins(8, 8, 8, 8)

        register_table = DataTable(columns=["Address", "Function Code", "Variable Name", "Value", "Unit"])
        register_table.horizontalHeader().setStretchLastSection(True)
        register_table.verticalHeader().setVisible(False)
        if DESIGN_TOKENS_AVAILABLE:
            table_font = DT.T.get_font(*DT.T.BODY_SMALL)
            register_table.setFont(table_font)
        layout.addWidget(register_table)

        return tab, register_table

    def _style_tabs(self, monitor_tabs: QTabWidget, styles: dict, constants: dict) -> None:
        if DESIGN_TOKENS_AVAILABLE:
            tab_stylesheet = f"""
                QTabWidget::pane {{
                    border: 1px solid {DT.C.BORDER_DEFAULT};
                    border-radius: {DT.R.MD}px;
                    background-color: {DT.C.BG_PRIMARY};
                    padding: {DT.S.SM}px;
                }}
                QTabBar::tab {{
                    background-color: {DT.C.BG_SECONDARY};
                    color: {DT.C.TEXT_SECONDARY};
                    border: 1px solid {DT.C.BORDER_DEFAULT};
                    border-bottom: none;
                    border-top-left-radius: {DT.R.MD}px;
                    border-top-right-radius: {DT.R.MD}px;
                    padding: {DT.S.SM}px {DT.S.MD}px;
                    margin-right: 2px;
                    font-family: '{DT.T.BODY[0]}';
                    font-size: {DT.T.BODY[1]}px;
                    font-weight: {DT.T.BODY[2]};
                }}
                QTabBar::tab:selected {{
                    background-color: {DT.C.BG_PRIMARY};
                    color: {DT.C.TEXT_PRIMARY};
                    border-bottom: 2px solid {DT.C.ACCENT_PRIMARY};
                    font-weight: 600;
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: {DT.C.BG_HOVER};
                    color: {DT.C.TEXT_PRIMARY};
                }}
            """
            monitor_tabs.setStyleSheet(tab_stylesheet)
        else:
            monitor_tabs.setStyleSheet(styles.get("TAB_WIDGET", ""))
        monitor_tabs.setDocumentMode(True)

    def _style_tab_bar(self, monitor_tabs: QTabWidget, tab_data_text: str, tab_reg_text: str) -> None:
        if DESIGN_TOKENS_AVAILABLE:
            tab_font = DT.T.get_font(*DT.T.LABEL)
            monitor_tabs.tabBar().setFont(tab_font)
            max_text_len = max(len(tab_data_text), len(tab_reg_text))
            min_width = max(100, max_text_len * 16 + 32)
            monitor_tabs.tabBar().setMinimumWidth(min_width)
        else:
            monitor_tabs.tabBar().setMinimumWidth(100)