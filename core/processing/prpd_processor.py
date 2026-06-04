# -*- coding: utf-8 -*-
"""
PRPD 分析处理器 - Phase Resolved Partial Discharge

基于工频同步信号 + 局放事件，生成相位分布图谱。
支持三种显示模式：
- 散点图 (Scatter): 每个放电事件一个点
- 热力图 (Heatmap): 相位-幅值二维直方图
- 密度图 (Density): 高斯核密度估计
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np


class PRPDMode(Enum):
    """PRPD 显示模式"""

    SCATTER = "scatter"  # 散点图
    HEATMAP = "heatmap"  # 热力图
    DENSITY = "density"  # 密度图


@dataclass
class PRPDResult:
    """PRPD 分析结果"""

    phase_bins: np.ndarray  # 相位轴 (0~360°)
    amplitude_bins: np.ndarray  # 幅值轴
    matrix: np.ndarray  # 二维矩阵 (phase_bins × amplitude_bins)
    events: List[PDEvent] = field(default_factory=list)  # 原始事件
    mode: PRPDMode = PRPDMode.HEATMAP
    total_events: int = 0
    max_amplitude: float = 0.0
    min_amplitude: float = 0.0


@dataclass
class PDEvent:
    """局放事件点"""

    phase: float  # 相位 (0~360°)
    amplitude: float  # 幅值 (mV)
    polarity: int = 0  # 极性: 0=正, 1=负
    energy: float = 0.0  # 能量 (pC)
    timestamp: float = 0.0  # 时间戳


class PRPDProcessor:
    """
    PRPD 图谱处理器

    将工频周期 (0~360°) 与放电幅值映射到二维矩阵，
    每个单元格存储该 (相位, 幅值) 区间内的放电次数或能量。

    Args:
        phase_bins: 相位分辨率 (默认 360, 即每度 1 个 bin)
        amplitude_bins: 幅值分辨率 (默认 256)
        max_amplitude: 最大幅值范围 (mV)
        min_amplitude: 最小幅值范围
    """

    def __init__(
        self,
        phase_bins: int = 360,
        amplitude_bins: int = 256,
        max_amplitude: float = 100.0,
        min_amplitude: float = 0.0,
    ):
        self._phase_bins = phase_bins
        self._amplitude_bins = amplitude_bins
        self._max_amplitude = max_amplitude
        self._min_amplitude = min_amplitude

        # PRPD 矩阵 [phase_bins, amplitude_bins]
        self._matrix = np.zeros((phase_bins, amplitude_bins), dtype=np.float64)
        self._max_events = 100000  # 最大缓存事件数
        self._events: deque = deque(maxlen=self._max_events)

    # ── 属性 ─────────────────────────────────────────

    @property
    def phase_bins(self) -> int:
        return self._phase_bins

    @property
    def amplitude_bins(self) -> int:
        return self._amplitude_bins

    @property
    def matrix(self) -> np.ndarray:
        return self._matrix

    @property
    def max_amplitude(self) -> float:
        return self._max_amplitude

    @max_amplitude.setter
    def max_amplitude(self, value: float) -> None:
        self._max_amplitude = value

    # ── 数据更新 ─────────────────────────────────────

    def add_event(self, phase: float, amplitude: float, polarity: int = 0, energy: float = 0.0) -> None:
        """
        添加单个局放事件

        Args:
            phase: 相位 (0~360°)
            amplitude: 幅值 (mV)
            polarity: 极性 (0=正, 1=负)
            energy: 放电能量 (pC)
        """
        event = PDEvent(
            phase=phase % 360,
            amplitude=amplitude,
            polarity=polarity,
            energy=energy,
        )
        # deque maxlen 自动淘汰旧事件
        if len(self._events) == self._max_events:
            removed = self._events[0]
            p_idx_r = self._phase_to_index(removed.phase)
            a_idx_r = self._amplitude_to_index(removed.amplitude)
            if 0 <= p_idx_r < self._phase_bins and 0 <= a_idx_r < self._amplitude_bins:
                self._matrix[p_idx_r, a_idx_r] = max(0, self._matrix[p_idx_r, a_idx_r] - 1.0)

        self._events.append(event)

        # 更新矩阵
        p_idx = self._phase_to_index(event.phase)
        a_idx = self._amplitude_to_index(event.amplitude)

        if 0 <= p_idx < self._phase_bins and 0 <= a_idx < self._amplitude_bins:
            self._matrix[p_idx, a_idx] += 1.0

    def add_events(self, events: List[Tuple[float, float]]) -> None:
        """
        批量添加事件 (phase, amplitude)

        Args:
            events: (相位, 幅值) 元组列表
        """
        for phase, amplitude in events:
            self.add_event(phase, amplitude)

    def add_waveform(self, waveform: np.ndarray, phase_offset: float = 0.0) -> None:
        """
        从波形数据中提取 PRPD 事件

        通过对波形进行峰值检测，提取超过阈值的峰值点作为局放事件。

        Args:
            waveform: 波形数据
            phase_offset: 相位偏移 (度)
        """
        from .peak_detector import PeakDetector

        detector = PeakDetector()
        peaks = detector.detect_peaks_simple(waveform)

        # 将峰值点映射到相位 (假设波形覆盖一个完整工频周期)
        n = len(waveform)
        for peak in peaks:
            phase = (peak.position / n * 360 + phase_offset) % 360
            self.add_event(phase, peak.amplitude, polarity=1 if peak.amplitude > 0 else 0)

    # ── 分析 ─────────────────────────────────────────

    def compute(self, mode: PRPDMode = PRPDMode.HEATMAP) -> PRPDResult:
        """
        计算 PRPD 结果

        Args:
            mode: 显示模式

        Returns:
            PRPDResult 对象
        """
        amplitude_bins = np.linspace(self._min_amplitude, self._max_amplitude, self._amplitude_bins)
        phase_bins = np.linspace(0, 360, self._phase_bins)

        result_matrix = self._matrix.copy()

        # 密度图模式: 高斯核平滑
        if mode == PRPDMode.DENSITY:
            from scipy.ndimage import gaussian_filter

            result_matrix = gaussian_filter(result_matrix, sigma=1.5)

        amplitudes = [e.amplitude for e in self._events]
        max_amp = max(amplitudes) if amplitudes else 0
        min_amp = min(amplitudes) if amplitudes else 0

        return PRPDResult(
            phase_bins=phase_bins,
            amplitude_bins=amplitude_bins,
            matrix=result_matrix,
            events=list(self._events)[-5000:],  # 最多保留 5000 个散点
            mode=mode,
            total_events=len(self._events),
            max_amplitude=max_amp,
            min_amplitude=min_amp,
        )

    def compute_stats(self) -> dict:
        """
        计算 PRPD 统计特征

        Returns:
            包含统计特征的字典
        """
        if len(self._events) == 0:
            return {
                "total_events": 0,
                "max_amplitude": 0,
                "avg_amplitude": 0,
                "positive_ratio": 0,
                "phase_concentration": 0,
            }

        amplitudes = np.array([e.amplitude for e in self._events])
        phases = np.array([e.phase for e in self._events])
        polarities = np.array([e.polarity for e in self._events])

        # 相位集中度 (0~1, 越接近 1 表示越集中在特定相位)
        phase_hist, _ = np.histogram(phases, bins=36, range=(0, 360))
        phase_concentration = float(np.max(phase_hist) / (np.sum(phase_hist) + 1e-10))

        return {
            "total_events": len(self._events),
            "max_amplitude": float(np.max(amplitudes)),
            "avg_amplitude": float(np.mean(amplitudes)),
            "positive_ratio": float(np.sum(polarities == 0) / len(polarities)),
            "phase_concentration": phase_concentration,
        }

    def reset(self) -> None:
        """重置所有数据"""
        self._matrix.fill(0)
        self._events.clear()

    # ── 内部辅助 ────────────────────────────────────

    def _phase_to_index(self, phase: float) -> int:
        """相位值 → 矩阵列索引"""
        idx = int(phase / 360.0 * self._phase_bins)
        return max(0, min(self._phase_bins - 1, idx))

    def _amplitude_to_index(self, amplitude: float) -> int:
        """幅值 → 矩阵行索引"""
        normalized = (amplitude - self._min_amplitude) / (self._max_amplitude - self._min_amplitude + 1e-10)
        idx = int(normalized * (self._amplitude_bins - 1))
        return max(0, min(self._amplitude_bins - 1, idx))

    def __repr__(self) -> str:
        return f"PRPDProcessor(bins={self._phase_bins}×{self._amplitude_bins}, events={len(self._events)})"
