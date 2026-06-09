# -*- coding: utf-8 -*-
"""实时监测页面 - 波形/PRPD/FFT + 独立峰值列表"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_tokens import DT
from ui.widgets import FFTWidget, PRPDWidget, PRPSWidget, WaveformWidget


class RealtimeMonitorPage(QWidget):
    """实时监测 - 波形 / PRPD / FFT / 峰值列表"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("monitorPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(DT.S.XL, DT.S.LG, DT.S.XL, DT.S.LG)
        layout.setSpacing(DT.S.MD)

        self._build_header(layout)
        self._build_waveform(layout)

        # 底部三栏：PRPD + FFT(无峰值列表) + 独立峰值列表
        bottom = QHBoxLayout()
        bottom.setSpacing(DT.S.MD)

        self._build_prpd_panel(bottom)
        self._build_fft_panel(bottom)
        self._build_peak_list_panel(bottom)

        layout.addLayout(bottom, 2)

    # ── 标题 ─────────────────────────────────────────

    def _build_header(self, layout: QVBoxLayout) -> None:
        h = QHBoxLayout()
        title = QLabel("实时监测")
        title.setFont(DT.T.get_font(*DT.T.TITLE_XLARGE[:2], "Bold"))
        title.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        h.addWidget(title)
        h.addStretch()
        self._ch_label = QLabel("通道: CH-01  |  设备: —")
        self._ch_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 13px;")
        h.addWidget(self._ch_label)
        layout.addLayout(h)

    # ── 波形（独占一行）──────────────────────────────

    def _build_waveform(self, layout: QVBoxLayout) -> None:
        frame = QFrame()
        frame.setObjectName("cardContainer")
        frame.setStyleSheet(
            f"""
            QFrame#cardContainer {{
                background: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.LG}px;
            }}
        """
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)
        self._waveform = WaveformWidget(title="实时波形 (20 FPS)", max_points=4096)
        fl.addWidget(self._waveform)
        layout.addWidget(frame, 3)

    # ── PRPD 面板 ────────────────────────────────────

    def _build_prpd_panel(self, parent: QHBoxLayout) -> None:
        frame = QFrame()
        frame.setObjectName("cardContainer")
        frame.setStyleSheet(
            f"""
            QFrame#cardContainer {{
                background: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.LG}px;
            }}
        """
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)
        self._prpd = PRPDWidget(title="PRPD 图谱 (10 FPS)")
        fl.addWidget(self._prpd)

        # PRPS 控件：与 PRPD 同卡片，纵向排列
        self._prps = PRPSWidget(title="PRPS 序列 (10 FPS)", rows=512, cols=360)
        fl.addWidget(self._prps)

        parent.addWidget(frame, 1)

    # ── FFT 面板（无内嵌峰值列表）────────────────────

    def _build_fft_panel(self, parent: QHBoxLayout) -> None:
        frame = QFrame()
        frame.setObjectName("cardContainer")
        frame.setStyleSheet(
            f"""
            QFrame#cardContainer {{
                background: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.LG}px;
            }}
        """
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)
        self._fft = FFTWidget(title="FFT 频谱 (10 FPS)", show_peak_list=False)
        fl.addWidget(self._fft)
        parent.addWidget(frame, 1)

    # ── 独立峰值列表面板 ─────────────────────────────

    def _build_peak_list_panel(self, parent: QHBoxLayout) -> None:
        frame = QFrame()
        frame.setObjectName("cardContainer")
        frame.setStyleSheet(
            f"""
            QFrame#cardContainer {{
                background: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.LG}px;
            }}
        """
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)

        title = QLabel("峰值列表")
        title.setFont(DT.T.get_font(*DT.T.TITLE_SMALL[:2], "SemiBold"))
        title.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        fl.addWidget(title)

        self._peak_table = QTableWidget()
        self._peak_table.setColumnCount(3)
        self._peak_table.setHorizontalHeaderLabels(["频率 (MHz)", "幅值 (dBm)", "类型"])
        self._peak_table.setAlternatingRowColors(True)
        self._peak_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._peak_table.verticalHeader().setVisible(False)
        self._peak_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._peak_table.setStyleSheet(
            f"""
            QTableWidget {{
                background: {DT.C.BG_PRIMARY};
                alternate-background-color: {DT.C.BG_SECONDARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.MD}px;
                font-size: 11px;
                outline: none;
            }}
            QTableWidget::item {{ padding: 4px 6px; border-bottom: 1px solid {DT.C.DIVIDER}; }}
            QHeaderView::section {{
                background: {DT.C.BG_SECONDARY};
                color: {DT.C.TEXT_SECONDARY};
                border: none;
                border-bottom: 2px solid {DT.C.BORDER_DEFAULT};
                padding: 4px;
                font-size: 10px;
                font-weight: 600;
            }}
        """
        )
        self._peak_table.horizontalHeader().setStretchLastSection(True)
        fl.addWidget(self._peak_table)

        parent.addWidget(frame, 1)

    def update_peak_list(self, peaks: list) -> None:
        """更新峰值列表（由控制器调用）"""
        top = sorted(peaks, key=lambda p: p.get("magnitude", 0), reverse=True)[:10]
        self._peak_table.setRowCount(len(top))

        for row, peak in enumerate(top):
            freq = peak.get("frequency", 0) / 1e6
            mag = peak.get("magnitude", 0)
            is_harm = peak.get("is_harmonic", False)
            order = peak.get("harmonic_order", 0)

            fi = QTableWidgetItem(f"{freq:.2f}")
            mi = QTableWidgetItem(f"{mag:.1f}")
            ti = QTableWidgetItem(f"谐波{order}" if is_harm and order > 1 else "基频" if is_harm else "峰值")

            if row == 0:
                c = QColor(220, 80, 60)
            elif row < 3:
                c = QColor(200, 160, 50)
            else:
                c = QColor(DT.C.TEXT_SECONDARY)
            fi.setForeground(c)
            mi.setForeground(c)

            self._peak_table.setItem(row, 0, fi)
            self._peak_table.setItem(row, 1, mi)
            self._peak_table.setItem(row, 2, ti)

        self._peak_table.resizeColumnsToContents()

    # ── 属性 ─────────────────────────────────────────

    @property
    def waveform(self) -> WaveformWidget:
        return self._waveform

    @property
    def prpd(self) -> PRPDWidget:
        return self._prpd

    @property
    def fft(self) -> FFTWidget:
        return self._fft

    @property
    def prps(self) -> PRPSWidget:
        return self._prps
