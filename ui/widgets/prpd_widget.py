# -*- coding: utf-8 -*-
"""
PRPD 图谱控件 - PRPDWidget

基于 PyQtGraph 实现 Phase Resolved Partial Discharge 图谱。
支持三种显示模式:
- 散点图 (Scatter): 每个放电事件一个点
- 热力图 (Heatmap): 相位-幅值二维直方图 (ImageItem)
- 密度图 (Density): 高斯核平滑后的热力图

性能: ≥10 FPS
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ui.design_tokens import DT

pg.setConfigOptions(antialias=True, foreground="#333333")


class PRPDDisplayMode(Enum):
    """PRPD 显示模式"""

    SCATTER = "散点图"
    HEATMAP = "热力图"
    DENSITY = "密度图"


class PRPDWidget(QWidget):
    """PRPD 图谱控件"""

    mode_changed = Signal(str)

    # Colormap 颜色方案
    COLORMAP = "viridis"

    def __init__(self, title: str = "PRPD 图谱", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._mode = PRPDDisplayMode.HEATMAP
        self._phase_bins = 360
        self._amplitude_bins = 256
        self._max_amplitude = 100.0

        self._scatter_phases: List[float] = []
        self._scatter_amplitudes: List[float] = []
        self._heatmap_data: Optional[np.ndarray] = None  # 原始矩阵
        self._heatmap_log: Optional[np.ndarray] = None  # log1p 后的显示数据
        self._display_mode = "heatmap"

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 标题栏
        header = QHBoxLayout()
        self._title_label = QLabel(self._title)
        self._title_label.setFont(DT.T.get_font(*DT.T.TITLE_SMALL[:2], "SemiBold"))
        self._title_label.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        header.addWidget(self._title_label)

        header.addStretch()

        self._info_label = QLabel("0 事件")
        self._info_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 11px;")
        header.addWidget(self._info_label)

        # 模式选择（默认热力图）
        self._mode_combo = QComboBox()
        self._mode_combo.blockSignals(True)
        for mode in PRPDDisplayMode:
            self._mode_combo.addItem(mode.value, mode.name.lower())
        self._mode_combo.setCurrentIndex(1)  # 默认热力图
        self._mode_combo.blockSignals(False)
        self._mode_combo.setFixedHeight(26)
        self._mode_combo.setStyleSheet(
            f"""
            QComboBox {{
                background: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                color: {DT.C.TEXT_PRIMARY};
            }}
            QComboBox:hover {{
                border-color: {DT.C.BORDER_HOVER};
            }}
            QComboBox::drop-down {{ border: none; width: 18px; }}
            QComboBox QAbstractItemView {{
                background: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                selection-background-color: {DT.C.ACCENT_SUBTLE};
                selection-color: {DT.C.ACCENT_PRIMARY};
                font-size: 11px;
            }}
        """
        )
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        header.addWidget(self._mode_combo)

        btn_reset = QPushButton("重置")
        btn_reset.setFixedHeight(26)
        btn_reset.setStyleSheet(self._button_style())
        btn_reset.clicked.connect(self._on_reset)
        header.addWidget(btn_reset)

        layout.addLayout(header)

        # PyQtGraph 绘图控件
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._plot_widget.setMinimumHeight(150)

        self._plot_widget.setLabel("left", "幅值", units="mV")
        self._plot_widget.setLabel("bottom", "相位", units="°")
        self._plot_widget.setXRange(0, 360)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)

        # 散点图
        self._scatter_plot = pg.ScatterPlotItem(
            size=4,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(200, 80, 50, 180),
        )
        self._plot_widget.addItem(self._scatter_plot)
        self._scatter_plot.setVisible(False)

        # 热力图 (ImageItem)
        self._image_item = pg.ImageItem()
        self._image_item.setVisible(False)
        self._plot_widget.addItem(self._image_item)

        # 设置热力图坐标映射
        self._image_transform = None

        layout.addWidget(self._plot_widget)

    # ── 数据更新 ─────────────────────────────────────

    def update_heatmap(self, matrix: np.ndarray, phase_bins: int = 360, amplitude_bins: int = 256) -> None:
        """
        更新热力图数据

        Args:
            matrix: 二维矩阵 [phase_bins, amplitude_bins]
            phase_bins: 相位分辨率
            amplitude_bins: 幅值分辨率
        """
        self._heatmap_data = matrix
        self._phase_bins = phase_bins
        self._amplitude_bins = amplitude_bins

        # 转置以使 X=相位, Y=幅值
        img_data = matrix.T.copy()

        # 对数压缩以增强对比度
        if np.max(img_data) > 0:
            img_data = np.log1p(img_data)

        self._heatmap_log = img_data.copy()  # 保存用于模式恢复

        self._image_item.setImage(img_data, autoLevels=True)

        # 设置坐标映射: X: 0~360°, Y: 0~max_amplitude
        tr = QTransform()
        tr.translate(0, 0)
        tr.scale(360 / phase_bins, self._max_amplitude / amplitude_bins)
        self._image_item.setTransform(tr)

        self._image_item.setVisible(self._display_mode != "scatter")
        self._scatter_plot.setVisible(self._display_mode == "scatter")

        # 设置 colormap
        cmap = pg.colormap.get(self.COLORMAP)
        if cmap is not None:
            self._image_item.setColorMap(cmap)

        # 更新信息
        total = int(np.sum(matrix))
        self._info_label.setText(f"{total} 事件")

    def update_scatter(self, phases: List[float], amplitudes: List[float]) -> None:
        """
        更新散点图数据

        Args:
            phases: 相位列表 (0~360°)
            amplitudes: 幅值列表 (mV)
        """
        self._scatter_phases = list(phases)
        self._scatter_amplitudes = list(amplitudes)

        if len(phases) == 0:
            return

        spots = [{"pos": (p, a), "size": 4} for p, a in zip(phases, amplitudes)]
        self._scatter_plot.setData(spots)
        self._image_item.setVisible(self._display_mode == "heatmap" or self._display_mode == "density")
        self._scatter_plot.setVisible(self._display_mode == "scatter")

        self._info_label.setText(f"{len(phases)} 事件")

    def set_max_amplitude(self, max_amp: float) -> None:
        """设置最大幅值显示范围"""
        self._max_amplitude = max_amp
        self._plot_widget.setYRange(0, max_amp)

    # ── 模式切换 ─────────────────────────────────────

    def _on_mode_changed(self, idx: int) -> None:
        mode_name = self._mode_combo.itemData(idx)
        self._display_mode = mode_name
        self.mode_changed.emit(mode_name)

        if mode_name == "scatter":
            # 散点图模式 — X:相位 0-360°, Y:幅值(自动)
            self._scatter_plot.setVisible(True)
            self._image_item.setVisible(False)
            self._plot_widget.setLabel("left", "幅值", units="mV")
            self._plot_widget.setLabel("bottom", "相位", units="°")
            if self._scatter_phases:
                spots = [
                    {"pos": (p, a), "size": 4}
                    for p, a in zip(self._scatter_phases[:5000], self._scatter_amplitudes[:5000])
                ]
                self._scatter_plot.setData(spots)
                y_max = max(self._scatter_amplitudes[:5000]) * 1.1
                self._plot_widget.setXRange(0, 360)
                self._plot_widget.setYRange(0, y_max)
            self._plot_widget.showGrid(x=True, y=True, alpha=0.2)

        elif mode_name == "density":
            # 密度图模式 — X:相位 0-360°, Y:幅值
            self._scatter_plot.setVisible(False)
            self._image_item.setVisible(True)
            self._plot_widget.setLabel("left", "幅值", units="mV")
            self._plot_widget.setLabel("bottom", "相位", units="°")
            self._plot_widget.setXRange(0, 360)
            self._plot_widget.setYRange(0, self._max_amplitude)
            self._apply_density_smooth()
            self._plot_widget.showGrid(x=True, y=True, alpha=0.2)

        else:
            # 热力图模式（默认）— X:相位 0-360°, Y:幅值
            self._scatter_plot.setVisible(False)
            self._image_item.setVisible(True)
            self._plot_widget.setLabel("left", "幅值", units="mV")
            self._plot_widget.setLabel("bottom", "相位", units="°")
            self._plot_widget.setXRange(0, 360)
            self._plot_widget.setYRange(0, self._max_amplitude)
            if self._heatmap_log is not None:
                self._image_item.setImage(self._heatmap_log, autoLevels=True)
            self._plot_widget.showGrid(x=True, y=True, alpha=0.2)

    def _apply_density_smooth(self) -> None:
        """应用密度图平滑（在 log1p 空间上平滑）"""
        if self._heatmap_data is None:
            return
        try:
            from scipy.ndimage import gaussian_filter

            # 在 log1p 空间平滑，保持一致的数据空间
            smoothed = gaussian_filter(self._heatmap_log, sigma=1.5) if self._heatmap_log is not None else None
            if smoothed is not None:
                self._image_item.setImage(smoothed, autoLevels=True)
        except ImportError:
            pass

    def _on_reset(self) -> None:
        """重置图谱"""
        self._scatter_plot.setData([])
        self._image_item.clear()
        self._heatmap_data = None
        self._heatmap_log = None
        self._scatter_phases.clear()
        self._scatter_amplitudes.clear()
        self._info_label.setText("0 事件")

    def set_title(self, title: str) -> None:
        self._title = title
        self._title_label.setText(title)

    @property
    def plot_widget(self) -> pg.PlotWidget:
        return self._plot_widget

    @staticmethod
    def _button_style() -> str:
        return (
            f"QPushButton {{ background: transparent; color: {DT.C.TEXT_SECONDARY}; "
            f"border: 1px solid {DT.C.BORDER_DEFAULT}; border-radius: 4px; padding: 4px 10px; "
            f"font-size: 11px; }}"
            f"QPushButton:hover {{ background: {DT.C.BG_HOVER}; border-color: {DT.C.BORDER_HOVER}; }}"
        )
