# -*- coding: utf-8 -*-
"""
AE 声发射参数提取器

从检测到的 AE hit 中提取标准特征向量，遵循 ASTM E976 / ISO 22096:
- 信号强度、平均信号电平(ASL)
- 平均频率、振铃频率、起始频率
- 工频相位映射、首次运动极性
"""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np

from .ae_peak_detector import AEHitInfo

logger = logging.getLogger(__name__)


class AEParameterExtractor:
    """
    AE 参数提取器

    无状态工具类，对单个 hit 计算完整 AE 特征集。
    """

    def extract(
        self,
        samples: np.ndarray,
        envelope: np.ndarray,
        hit: AEHitInfo,
        sample_rate: int,
        power_line_freq: float = 50.0,
    ) -> dict:
        """
        提取 AE hit 的完整特征向量

        Args:
            samples: 原始信号数组
            envelope: 包络信号数组
            hit: AEHitInfo (包含起始/结束位置)
            sample_rate: 采样率 (Hz)
            power_line_freq: 工频 (Hz), 默认 50

        Returns:
            特征字典
        """
        start = max(0, hit.start_position)
        end = min(len(samples) - 1, hit.end_position)

        hit_raw = samples[start : end + 1] if end > start else samples[start : start + 1]
        hit_env = envelope[start : end + 1] if end > start else envelope[start : start + 1]

        features = {}

        # ── 基本参数 (来自 AEHitInfo) ──────────────
        features["amplitude"] = hit.peak_amplitude
        features["rise_time_us"] = hit.rise_time_us
        features["duration_us"] = hit.duration_us
        features["counts"] = hit.counts
        features["marse_energy"] = hit.marse_energy
        features["avg_frequency_khz"] = hit.avg_frequency_khz

        # ── 信号强度 (ASL) ─────────────────────────
        # ASL = 20 * log10(RMS / 1uV)  (dB)
        # 这里简化为 RMS 值
        features["rms"] = hit.rms
        features["asl_db"] = float(20 * np.log10(max(hit.rms, 1e-10)))

        # ── 信号强度 (pV-s) ────────────────────────
        # 包络积分 = 信号强度
        if len(hit_env) > 1:
            try:
                features["signal_strength"] = float(np.trapz(hit_env)) / sample_rate
            except AttributeError:
                features["signal_strength"] = float(np.trapezoid(hit_env)) / sample_rate
        else:
            features["signal_strength"] = 0.0

        # ── 振铃频率 (kHz) ─────────────────────────
        # 峰值后的振铃计数 / (持续时间 - 上升时间)
        if hit.duration_us > hit.rise_time_us:
            reverb_time_us = hit.duration_us - hit.rise_time_us
            # 估算峰值后的振铃计数
            peak_pos = min(hit.peak_position - start, len(hit_env) - 1)
            after_peak = hit_env[peak_pos:]
            reverb_counts = 0
            crossed = False
            half_thresh = (np.max(hit_env) if len(hit_env) > 0 else 0) * 0.3
            for val in after_peak:
                if val > half_thresh and not crossed:
                    reverb_counts += 1
                    crossed = True
                elif val <= half_thresh:
                    crossed = False
            features["reverberation_frequency_khz"] = (
                (reverb_counts / reverb_time_us) * 1000 if reverb_time_us > 0 else 0.0
            )
        else:
            features["reverberation_frequency_khz"] = 0.0

        # ── 起始频率 (kHz) ─────────────────────────
        # 峰值前的振铃计数 / 上升时间
        if hit.rise_time_us > 0:
            before_peak = hit_env[: max(1, min(hit.peak_position - start, len(hit_env) - 1))]
            init_counts = 0
            crossed = False
            thresh = (np.max(hit_env) if len(hit_env) > 0 else 0) * 0.3
            for val in before_peak:
                if val > thresh and not crossed:
                    init_counts += 1
                    crossed = True
                elif val <= thresh:
                    crossed = False
            features["initiation_frequency_khz"] = (init_counts / hit.rise_time_us) * 1000
        else:
            features["initiation_frequency_khz"] = 0.0

        # ── 平均频率 (kHz, 再次确认) ──────────────
        features["average_frequency_khz"] = (
            (hit.counts / max(hit.duration_us, 1)) * 1000 if hit.duration_us > 0 else 0.0
        )

        # ── 幅值 (dB) ──────────────────────────────
        features["amplitude_db"] = float(20 * np.log10(max(hit.peak_amplitude, 1e-10)))

        # ── 能量 (pJ) ──────────────────────────────
        features["energy"] = hit.marse_energy

        # ── 工频相位 ───────────────────────────────
        hit_phase = self._compute_phase(hit.arrival_time, sample_rate, power_line_freq)
        features["phase_deg"] = hit_phase
        features["phase_deg_start"] = self._compute_phase(
            hit.start_position / sample_rate, sample_rate, power_line_freq
        )
        hit.phase_deg = hit_phase

        # ── 首次运动极性 ───────────────────────────
        polarity = self._detect_polarity(hit_raw)
        features["polarity"] = polarity
        hit.polarity = polarity

        # ── 信号质量 ───────────────────────────────
        # 基于 SNR 的粗略估计
        noise_rms = float(np.std(hit_raw)) if len(hit_raw) > 1 else 0
        snr = hit.peak_amplitude / max(noise_rms, 1e-10)
        features["signal_quality"] = min(100, int(snr * 10))

        return features

    def _compute_phase(self, arrival_time: float, sample_rate: int, power_line_freq: float) -> float:
        """计算到达时间对应的工频相位 (0-360°)"""
        # 用 absolute arrival_time modulo 工频周期
        cycle_time = 1.0 / max(power_line_freq, 1)
        phase_rad = (arrival_time % cycle_time) / cycle_time * 2 * np.pi
        return float(np.degrees(phase_rad)) % 360.0

    def _detect_polarity(self, raw_segment: np.ndarray) -> int:
        """检测首次运动极性: 0=正, 1=负"""
        if len(raw_segment) < 2:
            return 0
        # 取信号起始段的斜率
        init = raw_segment[: min(len(raw_segment), 50)]
        if len(init) < 2:
            return 0
        slope = init[-1] - init[0]
        return 0 if slope >= 0 else 1
