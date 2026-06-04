# -*- coding: utf-8 -*-
"""
FFT 频谱分析处理器

基于 numpy.fft.rfft 实现，支持：
- 实时频谱计算
- 峰值检测与标注
- 频段统计（自定义频段划分）
- 噪声水平估计
- 频谱数据平滑
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class FFTResult:
    """FFT 分析结果"""

    frequencies: np.ndarray  # 频率数组 (Hz)
    magnitudes: np.ndarray  # 幅值数组
    phases: np.ndarray  # 相位数组
    peaks: List[PeakInfo] = field(default_factory=list)  # 检测到的峰值
    band_stats: Dict[str, BandStats] = field(default_factory=dict)  # 频段统计
    noise_floor: float = 0.0  # 噪声底噪
    snr_db: float = 0.0  # 信噪比 (dB)
    sample_rate: int = 0  # 采样率 (Hz)


@dataclass
class PeakInfo:
    """峰值信息"""

    frequency: float  # 频率 (Hz)
    magnitude: float  # 幅值
    bandwidth: float  # 带宽 (Hz)
    is_harmonic: bool = False  # 是否为谐波
    harmonic_order: int = 0  # 谐波次数


@dataclass
class BandStats:
    """频段统计"""

    band_name: str  # 频段名称
    f_min: float  # 起始频率 (Hz)
    f_max: float  # 终止频率 (Hz)
    energy: float = 0.0  # 频段能量
    peak_magnitude: float = 0.0  # 频段内峰值
    peak_frequency: float = 0.0  # 峰值对应频率
    avg_magnitude: float = 0.0  # 平均幅值


class FFTProcessor:
    """
    FFT 频谱分析处理器

    Args:
        sample_rate: 采样率 (Hz)，默认 100MHz
        window_size: FFT 窗口大小（点数），默认 4096
        overlap: 窗口重叠率 0.0~1.0，默认 0.5
    """

    # 常用频段划分 (MHz 范围)
    DEFAULT_BANDS = {
        "VLF": (0, 300),  # 甚低频
        "UHF_low": (300, 1000),  # UHF 低频段
        "UHF_mid": (1000, 2000),  # UHF 中频段
        "UHF_high": (2000, 3000),  # UHF 高频段
    }

    def __init__(
        self,
        sample_rate: int = 100_000_000,
        window_size: int = 4096,
        overlap: float = 0.5,
    ):
        self._sample_rate = sample_rate
        self._window_size = window_size
        self._overlap = np.clip(overlap, 0.0, 0.95)
        self._window = np.hanning(window_size)
        self._norm_factor = 2.0 / np.sum(self._window)

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value: int) -> None:
        self._sample_rate = value

    @property
    def window_size(self) -> int:
        return self._window_size

    @property
    def frequency_resolution(self) -> float:
        """频率分辨率 (Hz)"""
        return self._sample_rate / self._window_size

    @property
    def nyquist_frequency(self) -> float:
        """奈奎斯特频率 (Hz)"""
        return self._sample_rate / 2.0

    # ── 核心计算 ─────────────────────────────────────

    def compute(self, waveform: np.ndarray, detect_peaks: bool = True) -> FFTResult:
        """
        计算 FFT 频谱

        Args:
            waveform: 输入波形数据 (1D numpy array)
            detect_peaks: 是否检测峰值

        Returns:
            FFTResult 分析结果
        """
        if len(waveform) < 2:
            return self._empty_result()

        # 防止 NaN/Inf 传播
        if not np.all(np.isfinite(waveform)):
            return self._empty_result()

        # 应用窗函数
        n = min(len(waveform), self._window_size)
        windowed = waveform[:n] * self._window[:n]

        # FFT 计算
        spectrum = np.fft.rfft(windowed, n=self._window_size)
        frequencies = np.fft.rfftfreq(self._window_size, d=1.0 / self._sample_rate)

        magnitudes = np.abs(spectrum) * self._norm_factor
        phases = np.angle(spectrum)

        # 直流分量不缩放
        magnitudes[0] = magnitudes[0] * self._window_size / np.sum(self._window)

        result = FFTResult(
            frequencies=frequencies,
            magnitudes=magnitudes,
            phases=phases,
            sample_rate=self._sample_rate,
        )

        # 噪声底噪估计（取后 10% 幅值中位数）
        noise_samples = magnitudes[int(len(magnitudes) * 0.9) :]
        result.noise_floor = float(np.median(noise_samples)) if len(noise_samples) > 0 else 0.0

        # 信噪比
        signal_power = np.mean(magnitudes**2)
        noise_power = result.noise_floor**2
        result.snr_db = float(10 * np.log10(signal_power / (noise_power + 1e-10)))

        # 峰值检测
        if detect_peaks:
            result.peaks = self.detect_peaks(frequencies, magnitudes)

        # 频段统计
        result.band_stats = self.compute_band_stats(frequencies, magnitudes)

        return result

    def compute_spectrogram(
        self,
        waveform: np.ndarray,
        time_axis: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算频谱图（用于瀑布图显示）

        Args:
            waveform: 输入波形
            time_axis: 是否返回时间轴

        Returns:
            (times, frequencies, spectrogram) 元组
        """
        stride = int(self._window_size * (1 - self._overlap))
        n_frames = max(1, (len(waveform) - self._window_size) // stride + 1)

        freq_bins = self._window_size // 2 + 1
        spectrogram = np.zeros((n_frames, freq_bins))

        for i in range(n_frames):
            start = i * stride
            end = start + self._window_size
            if end > len(waveform):
                break
            frame = waveform[start:end] * self._window
            spectrum = np.fft.rfft(frame, n=self._window_size)
            spectrogram[i] = np.abs(spectrum) * self._norm_factor

        frequencies = np.fft.rfftfreq(self._window_size, d=1.0 / self._sample_rate)

        if time_axis:
            times = np.arange(n_frames) * stride / self._sample_rate
            return times, frequencies, spectrogram.T
        return np.array([]), frequencies, spectrogram.T

    # ── 峰值检测 ─────────────────────────────────────

    def detect_peaks(
        self,
        frequencies: np.ndarray,
        magnitudes: np.ndarray,
        min_height: Optional[float] = None,
        min_distance: int = 5,
        prominence: float = 3.0,
    ) -> List[PeakInfo]:
        """
        检测频谱峰值

        Args:
            frequencies: 频率数组
            magnitudes: 幅值数组
            min_height: 最小峰值高度（默认自动基于噪声底噪）
            min_distance: 峰之间最小距离（点数）
            prominence: 峰值显著度（相对于噪声底噪的倍数）

        Returns:
            峰值列表
        """
        from scipy.signal import find_peaks

        if min_height is None:
            min_height = float(np.percentile(magnitudes, 90))

        peaks_idx, properties = find_peaks(
            magnitudes,
            height=min_height,
            distance=min_distance,
            prominence=prominence * float(np.median(np.abs(magnitudes))),
        )

        result = []
        base_freq = self._detect_fundamental_frequency(frequencies, magnitudes, peaks_idx)

        for idx in peaks_idx:
            # 带宽估计 (3dB 带宽)
            half_max = magnitudes[idx] / 2
            left = idx
            right = idx
            while left > 0 and magnitudes[left] > half_max:
                left -= 1
            while right < len(magnitudes) - 1 and magnitudes[right] > half_max:
                right += 1

            bandwidth = frequencies[right] - frequencies[left] if right > left else 0

            freq = float(frequencies[idx])
            is_harmonic = False
            harmonic_order = 0

            if base_freq > 0:
                order = round(freq / base_freq)
                if order > 1 and abs(freq - order * base_freq) < base_freq * 0.05:
                    is_harmonic = True
                    harmonic_order = order

            result.append(
                PeakInfo(
                    frequency=freq,
                    magnitude=float(magnitudes[idx]),
                    bandwidth=float(bandwidth),
                    is_harmonic=is_harmonic,
                    harmonic_order=harmonic_order,
                )
            )

        # 按幅值降序排列
        result.sort(key=lambda p: p.magnitude, reverse=True)
        return result

    def _detect_fundamental_frequency(
        self,
        frequencies: np.ndarray,
        magnitudes: np.ndarray,
        peaks_idx: np.ndarray,
    ) -> float:
        """检测基频"""
        if len(peaks_idx) == 0:
            return 0.0

        # 找最大峰作为基频候选（排除 DC）
        non_dc = peaks_idx[peaks_idx > 0]
        if len(non_dc) == 0:
            return 0.0

        main_peak_idx = non_dc[np.argmax(magnitudes[non_dc])]
        return float(frequencies[main_peak_idx])

    # ── 频段统计 ─────────────────────────────────────

    def compute_band_stats(
        self,
        frequencies: np.ndarray,
        magnitudes: np.ndarray,
        bands: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> Dict[str, BandStats]:
        """
        计算频段统计

        Args:
            frequencies: 频率数组 (Hz)
            magnitudes: 幅值数组
            bands: 频段配置，默认使用 UHF 频段划分

        Returns:
            频段统计字典
        """
        if bands is None:
            bands = self.DEFAULT_BANDS

        # 将 MHz 转换为 Hz
        bands_hz = {name: (f_min * 1e6, f_max * 1e6) for name, (f_min, f_max) in bands.items()}

        stats = {}
        for name, (f_min, f_max) in bands_hz.items():
            mask = (frequencies >= f_min) & (frequencies <= f_max)
            band_mags = magnitudes[mask]
            band_freqs = frequencies[mask]

            if len(band_mags) == 0:
                stats[name] = BandStats(name, f_min / 1e6, f_max / 1e6)
                continue

            peak_idx = np.argmax(band_mags)
            stats[name] = BandStats(
                band_name=name,
                f_min=f_min / 1e6,
                f_max=f_max / 1e6,
                energy=float(np.sum(band_mags**2)),
                peak_magnitude=float(band_mags[peak_idx]),
                peak_frequency=float(band_freqs[peak_idx]),
                avg_magnitude=float(np.mean(band_mags)),
            )

        return stats

    # ── 辅助 ─────────────────────────────────────────

    def _empty_result(self) -> FFTResult:
        """返回空结果"""
        return FFTResult(
            frequencies=np.array([]),
            magnitudes=np.array([]),
            phases=np.array([]),
            sample_rate=self._sample_rate,
        )

    def apply_filter(
        self,
        magnitudes: np.ndarray,
        frequencies: np.ndarray,
        f_min: float = 0,
        f_max: float = float("inf"),
    ) -> np.ndarray:
        """频率滤波器"""
        mask = (frequencies >= f_min) & (frequencies <= f_max)
        result = magnitudes.copy()
        result[~mask] = 0
        return result

    def smooth_spectrum(self, magnitudes: np.ndarray, window_size: int = 5) -> np.ndarray:
        """频谱平滑"""
        if window_size < 2:
            return magnitudes
        from scipy.ndimage import uniform_filter1d

        return uniform_filter1d(magnitudes, size=window_size)
