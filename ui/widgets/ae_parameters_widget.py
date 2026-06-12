# -*- coding: utf-8 -*-
"""
AE 参数面板组件

显示 AE hit 的特征参数:
- 当前 hit 关键参数 (幅值、上升时间、持续时间、振铃计数、MARSE能量、平均频率)
- 最近 N 条 hit 历史表
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_tokens import DT


class AEParametersWidget(QWidget):
    """AE 参数面板"""

    # 颜色编码等级
    LEVEL_COLORS = {
        "normal": QColor(80, 180, 80),
        "warning": QColor(200, 160, 50),
        "critical": QColor(220, 80, 60),
    }

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._history: List[Dict] = []  # 最近 hit 历史
        self._max_history = 100

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._build_current_params(layout)
        self._build_history_table(layout)

    # ── 当前参数 ─────────────────────────────────────

    def _build_current_params(self, parent: QVBoxLayout) -> None:
        """当前 hit 关键参数网格"""
        frame = QFrame()
        frame.setObjectName("aeParamCard")
        frame.setStyleSheet(
            f"""
            QFrame#aeParamCard {{
                background: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.MD}px;
            }}
        """
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(8, 4, 8, 4)

        title = QLabel("当前 AE Hit")
        title.setFont(DT.T.get_font(*DT.T.TITLE_SMALL[:2], "SemiBold"))
        title.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        fl.addWidget(title)

        # 2x3 参数网格
        grid = QGridLayout()
        grid.setSpacing(4)

        self._param_labels = {}
        params = [
            ("幅值", "amplitude", "0.0 mV"),
            ("上升时间", "rise_time", "0.0 us"),
            ("持续时间", "duration", "0.0 us"),
            ("振铃计数", "counts", "0"),
            ("MARSE 能量", "marse_energy", "0.0"),
            ("平均频率", "avg_freq", "0.0 kHz"),
        ]
        for idx, (name, key, default) in enumerate(params):
            row, col = idx // 3, idx % 3
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background: {DT.C.BG_SECONDARY}; border-radius: 4px; }}"
            )
            c = QVBoxLayout(card)
            c.setContentsMargins(8, 4, 8, 4)
            c.setSpacing(0)

            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 10px;")
            c.addWidget(lbl_name)

            lbl_val = QLabel(default)
            lbl_val.setStyleSheet(
                f"color: {DT.C.ACCENT_PRIMARY}; font-size: 16px; font-weight: 700;"
            )
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignLeft)
            c.addWidget(lbl_val)

            self._param_labels[key] = lbl_val
            grid.addWidget(card, row, col)

        fl.addLayout(grid)
        parent.addWidget(frame)

    # ── 历史表 ───────────────────────────────────────

    def _build_history_table(self, parent: QVBoxLayout) -> None:
        """最近 hit 历史表"""
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["幅值 (mV)", "上升 (us)", "持续 (us)", "计数", "能量", "频率 (kHz)"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setStyleSheet(
            f"""
            QTableWidget {{
                background: {DT.C.BG_PRIMARY};
                alternate-background-color: {DT.C.BG_SECONDARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.MD}px;
                font-size: 10px;
                outline: none;
            }}
            QTableWidget::item {{ padding: 2px 4px; border-bottom: 1px solid {DT.C.DIVIDER}; }}
            QHeaderView::section {{
                background: {DT.C.BG_SECONDARY};
                color: {DT.C.TEXT_SECONDARY};
                border: none;
                border-bottom: 2px solid {DT.C.BORDER_DEFAULT};
                padding: 2px;
                font-size: 9px;
                font-weight: 600;
            }}
        """
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setMaximumHeight(180)
        parent.addWidget(self._table)

    # ── 更新 ─────────────────────────────────────────

    def update_hit(self, features: dict) -> None:
        """
        更新 AE hit 参数显示

        Args:
            features: AEParameterExtractor.extract() 返回的特征字典
        """
        # 更新当前参数
        amplitude = features.get("amplitude", 0)
        self._param_labels["amplitude"].setText(f"{amplitude:.1f} mV")
        self._param_labels["rise_time"].setText(f'{features.get("rise_time_us", 0):.1f} us')
        self._param_labels["duration"].setText(f'{features.get("duration_us", 0):.1f} us')
        self._param_labels["counts"].setText(str(features.get("counts", 0)))
        self._param_labels["marse_energy"].setText(f'{features.get("marse_energy", 0):.2e}')
        self._param_labels["avg_freq"].setText(f'{features.get("avg_frequency_khz", 0):.1f} kHz')

        # 幅值颜色编码
        amp_color = self.LEVEL_COLORS.get(
            "critical" if amplitude > 30 else "warning" if amplitude > 10 else "normal"
        )
        self._param_labels["amplitude"].setStyleSheet(
            f"color: {amp_color.name()}; font-size: 16px; font-weight: 700;"
        )

        # 记录历史
        self._history.insert(0, features)
        if len(self._history) > self._max_history:
            self._history.pop()

        # 更新表格 (显示最近 20 条)
        self._refresh_table()

    def _refresh_table(self) -> None:
        """刷新历史表"""
        shown = self._history[:20]
        self._table.setRowCount(len(shown))

        for row, h in enumerate(shown):
            items = [
                f'{h.get("amplitude", 0):.1f}',
                f'{h.get("rise_time_us", 0):.1f}',
                f'{h.get("duration_us", 0):.1f}',
                str(h.get("counts", 0)),
                f'{h.get("marse_energy", 0):.2e}',
                f'{h.get("avg_frequency_khz", 0):.1f}',
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 0:
                    amp = h.get("amplitude", 0)
                    c = self.LEVEL_COLORS.get(
                        "critical" if amp > 30 else "warning" if amp > 10 else "normal"
                    )
                    item.setForeground(c)
                self._table.setItem(row, col, item)

        self._table.resizeColumnsToContents()

    def clear(self) -> None:
        """清空数据"""
        self._history.clear()
        self._table.setRowCount(0)
        for key, lbl in self._param_labels.items():
            if key == "counts":
                lbl.setText("0")
            elif key == "marse_energy":
                lbl.setText("0.0")
            else:
                lbl.setText("0.0")
