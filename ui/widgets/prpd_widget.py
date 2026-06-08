# -*- coding: utf-8 -*-
"""
PRPD 图谱控件 - PRPDWidget

基于 PyQtGraph + Matplotlib 实现 Phase Resolved Partial Discharge 图谱。
支持四种显示模式:
- 散点图 (Scatter): 每个放电事件一个点
- 热力图 (Heatmap): 相位-幅值二维直方图 (ImageItem)
- 密度图 (Density): 高斯核平滑后的热力图
- 3D散点图 (PRPS): 三维相位-周期-幅值散点（Matplotlib 3D）

性能: >=10 FPS (2D), >=10 FPS (3D)
"""

from __future__ import annotations

import math
from enum import Enum
from typing import List, Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtGui import QPen, QTransform
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.design_tokens import DT

pg.setConfigOptions(antialias=True, foreground="#333333")

# Matplotlib 3D 支持
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    HAS_MPL3D = True
except ImportError:
    HAS_MPL3D = False


class PRPDDisplayMode(Enum):
    """PRPD 显示模式"""

    SCATTER = "散点图"
    HEATMAP = "热力图"
    DENSITY = "密度图"
    SCATTER_3D = "3D散点图"


class PRPDWidget(QWidget):
    """PRPD 图谱控件"""

    mode_changed = Signal(str)

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
        self._heatmap_data: Optional[np.ndarray] = None
        self._heatmap_log: Optional[np.ndarray] = None
        self._display_mode = "heatmap"

        # 3D 视图状态（Matplotlib）
        self._mpl_canvas = None  # FigureCanvasQTAgg
        self._mpl_fig = None  # Figure
        self._mpl_ax = None  # Axes3D
        self._view_stack = None

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

        self._info_label = QLabel("0 \u4E8B\u4EF6")
        self._info_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 11px;")
        header.addWidget(self._info_label)

        # 模式选择（默认热力图）
        self._mode_combo = QComboBox()
        self._mode_combo.blockSignals(True)
        for mode in PRPDDisplayMode:
            if mode == PRPDDisplayMode.SCATTER_3D and not HAS_MPL3D:
                continue
            self._mode_combo.addItem(mode.value, mode.name.lower())
        self._mode_combo.setCurrentIndex(1)
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
            QComboBox:hover {{ border-color: {DT.C.BORDER_HOVER}; }}
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

        btn_reset = QPushButton("\u91CD\u7F6E")
        btn_reset.setFixedHeight(26)
        btn_reset.setStyleSheet(self._button_style())
        btn_reset.clicked.connect(self._on_reset)
        header.addWidget(btn_reset)

        layout.addLayout(header)

        # PyQtGraph 绘图控件（2D 视图）
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._plot_widget.setMinimumHeight(150)
        self._plot_widget.setLabel("left", "\u5E45\u503C", units="mV")
        self._plot_widget.setLabel("bottom", "\u76F8\u4F4D", units="\u00B0")
        self._plot_widget.setXRange(0, 360)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)

        self._scatter_plot = pg.ScatterPlotItem(
            size=4,
            pen=pg.mkPen(None),
            brush=pg.mkBrush(200, 80, 50, 180),
        )
        self._plot_widget.addItem(self._scatter_plot)
        self._scatter_plot.setVisible(False)

        self._image_item = pg.ImageItem()
        self._image_item.setVisible(False)
        self._plot_widget.addItem(self._image_item)
        self._image_transform = None

        # 用 QStackedWidget 切换 2D/3D 视图
        self._view_stack = QStackedWidget()
        self._view_stack.addWidget(self._plot_widget)  # index 0 = 2D (PyQtGraph)
        if HAS_MPL3D:
            mpl_w = self._build_mpl_3d_widget()
            self._view_stack.addWidget(mpl_w)  # index 1 = 3D (Matplotlib)
        self._view_stack.setCurrentIndex(0)
        layout.addWidget(self._view_stack)

    # ── 数据更新 ─────────────────────────────────────

    def update_heatmap(self, matrix: np.ndarray, phase_bins: int = 360, amplitude_bins: int = 256) -> None:
        self._heatmap_data = matrix
        self._phase_bins = phase_bins
        self._amplitude_bins = amplitude_bins

        img_data = matrix.T.copy()
        if np.max(img_data) > 0:
            img_data = np.log1p(img_data)
        self._heatmap_log = img_data.copy()

        self._image_item.setImage(img_data, autoLevels=True)
        tr = QTransform()
        tr.translate(0, 0)
        tr.scale(360 / phase_bins, self._max_amplitude / amplitude_bins)
        self._image_item.setTransform(tr)

        self._image_item.setVisible(self._display_mode != "scatter")
        self._scatter_plot.setVisible(self._display_mode == "scatter")

        cmap = pg.colormap.get(self.COLORMAP)
        if cmap is not None:
            self._image_item.setColorMap(cmap)

        total = int(np.sum(matrix))
        self._info_label.setText(f"{total} \u4E8B\u4EF6")
        self._sync_3d_view()

    def update_scatter(self, phases: List[float], amplitudes: List[float]) -> None:
        self._scatter_phases = list(phases)
        self._scatter_amplitudes = list(amplitudes)

        if len(phases) == 0:
            return

        spots = [{"pos": (p, a), "size": 4} for p, a in zip(phases, amplitudes)]
        self._scatter_plot.setData(spots)
        self._image_item.setVisible(self._display_mode == "heatmap" or self._display_mode == "density")
        self._scatter_plot.setVisible(self._display_mode == "scatter")
        self._info_label.setText(f"{len(phases)} \u4E8B\u4EF6")

        if self._display_mode == "scatter_3d":
            self._update_3d_scatter()

    # ── 3D 视图（Matplotlib）─────────────────────────

    def _build_mpl_3d_widget(self):
        """
        构建 Matplotlib 3D 视口。

        参数与 plot_PRPS.py 完全一致：
        - X: 相位 (0~360°)
        - Y: 工频周期 (0~50)
        - Z: 放电量 (真实值)
        - 视角: elev=36°, azim=-122°
        - box_aspect: (1.45, 1.15, 1.20)
        - 颜色映射: jet
        """
        fig = Figure(figsize=(10, 8), facecolor="white", dpi=100)
        ax = fig.add_subplot(111, projection="3d")

        # 中文字体设置
        try:
            import matplotlib

            matplotlib.rcParams["font.sans-serif"] = ["SimHei", "SimSun", "Microsoft YaHei"]
            matplotlib.rcParams["axes.unicode_minus"] = False
        except Exception:
            pass

        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        canvas.setMinimumHeight(200)

        self._mpl_canvas = canvas
        self._mpl_fig = fig
        self._mpl_ax = ax

        return canvas

    def _update_3d_scatter(self) -> None:
        """使用 Matplotlib 绘制 3D PRPS 散点图（参数与 plot_PRPS.py 一致）"""
        if not HAS_MPL3D or self._mpl_ax is None or self._mpl_fig is None:
            return
        try:
            self._do_update_3d_scatter_mpl()
        except Exception:
            import traceback

            traceback.print_exc()

    def _do_update_3d_scatter_mpl(self) -> None:
        """Matplotlib 3D 散点图内核实现"""
        ax = self._mpl_ax
        fig = self._mpl_fig

        # 获取数据
        phases = np.array(self._scatter_phases, dtype=np.float64)
        amps = np.array(self._scatter_amplitudes, dtype=np.float64)
        n = len(phases)

        # 数据不足时从热力图回退
        used_fallback = False
        if n < 10 and self._heatmap_data is not None:
            h, w = self._heatmap_data.shape
            rows, cols = np.nonzero(self._heatmap_data > 0)
            if len(rows) < 10 and self._heatmap_log is not None:
                rows, cols = np.mgrid[0:h, 0:w].reshape(2, -1)
                vals = self._heatmap_data.ravel()
                mask = vals > 0
                rows, cols = rows[mask], cols[mask]
            if len(rows) > 0:
                phases = (cols.astype(np.float64) + 0.5) * (360 / w)
                amps = (rows.astype(np.float64) + 0.5) * (self._max_amplitude / h)
                n = len(phases)
                used_fallback = True

        if n < 10:
            return

        print(
            f"[3D-MPL] \u6E32\u67D3 {n} \u4E2A\u70B9 (fallback={used_fallback}), "
            f"amp=[{float(amps.min()):.1f}, {float(amps.max()):.1f}]"
        )

        # ── 与 plot_PRPS.py 完全一致的数据处理 ──
        N_CYCLES = 50
        events_per_cycle = max(1, n // N_CYCLES)
        cycle_nums = np.clip(np.floor(np.arange(n) / events_per_cycle), 0, N_CYCLES - 1)

        raw_cycle_local = ((cycle_nums) % 50) + 1
        phase = phases
        discharge = np.abs(amps)

        # 清空旧图形（包括旧 colorbar）并重新绘制
        # fig.clear() 清除所有 axes 和 colorbar，然后重建 3D 子图
        fig.clear()
        ax_new = fig.add_subplot(111, projection="3d")
        # 替换引用
        self._mpl_ax = ax_new
        ax = ax_new

        # 绘制 3D 散点（参数与 plot_PRPS.py 一致，散点适当放大）
        scatter = ax.scatter(
            phase,
            raw_cycle_local,
            discharge,
            s=25,
            c=discharge,
            cmap="jet",
            marker="o",
            edgecolors="none",
        )

        # ColorBar（放大填充）
        cb = fig.colorbar(scatter, ax=ax, shrink=0.88, pad=0.02)
        cb.set_label("Discharge (a.u.)")
        cb.ax.tick_params(labelsize=9)

        # 坐标轴设置（参数与 plot_PRPS.py 一致）
        ax.set_xlabel("\u76F8\u4F4D (\u00B0)", fontsize=10, labelpad=6)
        ax.set_ylabel("\u5DE5\u9891\u5468\u671F (n)", fontsize=10, labelpad=8)
        ax.set_zlabel("\u653E\u7535\u91CF", fontsize=10, labelpad=10)
        ax.tick_params(axis="both", which="major", labelsize=9)
        ax.zaxis.set_tick_params(labelsize=9)

        # Z 轴标签纵向显示（沿坐标轴方向）
        ax.zaxis.label.set_rotation(90)

        ax.set_xlim(0, 360)
        ax.set_ylim(0, 50)
        ax.set_yticks([0, 10, 20, 30, 40, 50])
        z_max_val = max(1000.0, float(np.max(discharge) * 1.05))
        ax.set_zlim(0, z_max_val)
        ax.set_xticks([0, 60, 120, 180, 240, 300, 360])

        # 视角（参数与 plot_PRPS.py 一致）
        ax.view_init(elev=36, azim=-122)

        # 盒子比例（参数与 plot_PRPS.py 一致）
        ax.set_box_aspect((1.45, 1.15, 1.20))

        # 不设标题

        # 调整边距：四周留白确保刻度 "0" 等不被截断
        fig.subplots_adjust(left=0.12, right=0.92, bottom=0.08, top=0.96)
        fig.tight_layout(rect=[0.12, 0.06, 0.92, 0.96])

        # 刷新画布
        self._mpl_canvas.draw()

    def _sync_3d_view(self) -> None:
        if self._display_mode == "scatter_3d":
            self._update_3d_scatter()

    def set_max_amplitude(self, max_amp: float) -> None:
        self._max_amplitude = max_amp
        self._plot_widget.setYRange(0, max_amp)
        self._sync_3d_view()

    # ── 模式切换 ─────────────────────────────────────

    def _on_mode_changed(self, idx: int) -> None:
        mode_name = self._mode_combo.itemData(idx)
        self._display_mode = mode_name
        self.mode_changed.emit(mode_name)

        if mode_name == "scatter":
            self._scatter_plot.setVisible(True)
            self._image_item.setVisible(False)
            self._view_stack.setCurrentIndex(0)
            self._plot_widget.setLabel("left", "\u5E45\u503C", units="mV")
            self._plot_widget.setLabel("bottom", "\u76F8\u4F4D", units="\u00B0")
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
            self._scatter_plot.setVisible(False)
            self._image_item.setVisible(True)
            self._view_stack.setCurrentIndex(0)
            self._plot_widget.setLabel("left", "\u5E45\u503C", units="mV")
            self._plot_widget.setLabel("bottom", "\u76F8\u4F4D", units="\u00B0")
            self._plot_widget.setXRange(0, 360)
            self._plot_widget.setYRange(0, self._max_amplitude)
            self._apply_density_smooth()
            self._plot_widget.showGrid(x=True, y=True, alpha=0.2)

        elif mode_name == "scatter_3d":
            self._scatter_plot.setVisible(False)
            self._image_item.setVisible(False)
            self._view_stack.setCurrentIndex(1)
            self._update_3d_scatter()

        else:
            self._scatter_plot.setVisible(False)
            self._image_item.setVisible(True)
            self._view_stack.setCurrentIndex(0)
            self._plot_widget.setLabel("left", "\u5E45\u503C", units="mV")
            self._plot_widget.setLabel("bottom", "\u76F8\u4F4D", units="\u00B0")
            self._plot_widget.setXRange(0, 360)
            self._plot_widget.setYRange(0, self._max_amplitude)
            if self._heatmap_log is not None:
                self._image_item.setImage(self._heatmap_log, autoLevels=True)
            self._plot_widget.showGrid(x=True, y=True, alpha=0.2)

    def _apply_density_smooth(self) -> None:
        if self._heatmap_data is None:
            return
        try:
            from scipy.ndimage import gaussian_filter

            smoothed = gaussian_filter(self._heatmap_log, sigma=1.5) if self._heatmap_log is not None else None
            if smoothed is not None:
                self._image_item.setImage(smoothed, autoLevels=True)
        except ImportError:
            pass

    def _on_reset(self) -> None:
        self._scatter_plot.setData([])
        self._image_item.clear()
        self._heatmap_data = None
        self._heatmap_log = None
        self._scatter_phases.clear()
        self._scatter_amplitudes.clear()
        self._info_label.setText("0 \u4E8B\u4EF6")

        # 清除 3D 视图
        if self._mpl_ax is not None:
            self._mpl_ax.clear()
            self._mpl_canvas.draw()

        self._view_stack.setCurrentIndex(0)

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
