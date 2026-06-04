# -*- coding: utf-8 -*-
"""趋势分析页面 - 集成 TrendChartWidget"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.design_tokens import DT
from ui.widgets import TrendChartWidget


class TrendPage(QWidget):
    """趋势分析 - 趋势曲线"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("trendPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(DT.S.XL, DT.S.LG, DT.S.XL, DT.S.LG)
        layout.setSpacing(DT.S.MD)

        # 页面标题
        title = QLabel("趋势分析")
        title.setFont(DT.T.get_font(*DT.T.TITLE_XLARGE[:2], "Bold"))
        title.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        layout.addWidget(title)

        subtitle = QLabel("局放次数 · 最大幅值 · 平均幅值 · 放电能量 · 噪声水平")
        subtitle.setFont(DT.T.get_font(*DT.T.BODY[:2]))
        subtitle.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY};")
        layout.addWidget(subtitle)

        # 趋势图 (TrendChartWidget)
        chart_frame = QFrame()
        chart_frame.setObjectName("cardContainer")
        chart_frame.setStyleSheet(
            f"""
            QFrame#cardContainer {{
                background: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.LG}px;
            }}
        """
        )
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)

        self._trend_chart = TrendChartWidget(title="趋势曲线")
        # 预制示例系列
        self._trend_chart.add_series("局放次数")
        self._trend_chart.add_series("最大幅值")
        self._trend_chart.add_series("平均幅值")
        chart_layout.addWidget(self._trend_chart)

        layout.addWidget(chart_frame, 1)

    @property
    def trend_chart(self) -> TrendChartWidget:
        return self._trend_chart
