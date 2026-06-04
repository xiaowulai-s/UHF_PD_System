# -*- coding: utf-8 -*-
"""
PD 数据采集服务 - AcquisitionService

管理 FPGA 采集主机的数据采集流程。

Fixes applied (P0/P1):
- Thread-safe get_or_create_* (RLock)
- Per-channel sample rate storage
- Processor cleanup on device stop
- PRPD matrix exponential decay
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from core.foundation.pd_data_bus import PDDataBus
from core.processing import FFTProcessor, PeakDetector, PRPDProcessor, PRPSProcessor, RingBuffer

logger = logging.getLogger(__name__)


class AcquisitionResult:
    """单次采集结果"""

    __slots__ = (
        "device_id",
        "channel_id",
        "success",
        "timestamp",
        "duration_ms",
        "frame_type",
        "data",
        "error_message",
    )

    def __init__(self, device_id: str, channel_id: int = 0):
        self.device_id = device_id
        self.channel_id = channel_id
        self.success = False
        self.timestamp = datetime.now()
        self.duration_ms = 0.0
        self.frame_type: Optional[str] = None
        self.data: Any = None
        self.error_message: str = ""

    def __repr__(self):
        status = "OK" if self.success else f"FAIL({self.error_message})"
        return f"AcquisitionResult({self.device_id}, ch{self.channel_id}, {self.frame_type}, {status})"


class AcquisitionService:
    """
    数据采集服务

    管理从 FPGA 采集主机接收数据的完整流程。
    线程安全，支持多设备多通道并发。

    Args:
        sample_rate: 默认采样率 (Hz)
        waveform_points: 波形点数
    """

    PRPD_DECAY_FACTOR = 0.995  # PRPD 矩阵指数衰减系数

    def __init__(
        self,
        sample_rate: int = 100_000_000,
        waveform_points: int = 4096,
    ):
        self._default_sample_rate = sample_rate
        self._waveform_points = waveform_points

        # 协议解析器
        self._protocol: Any = None

        # 信号处理器（每个通道一个实例）
        self._fft_processors: Dict[str, FFTProcessor] = {}
        self._prpd_processors: Dict[str, PRPDProcessor] = {}
        self._prps_processors: Dict[str, PRPSProcessor] = {}
        self._ring_buffers: Dict[str, RingBuffer] = {}
        self._peak_detectors: Dict[str, PeakDetector] = {}
        self._sample_rates: Dict[str, int] = {}  # 按通道存储采样率

        # 数据回调
        self._on_waveform_cb: Optional[Callable] = None
        self._on_pd_event_cb: Optional[Callable] = None

        # 采集状态
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # PRPD 帧计数（用于衰减）
        self._prpd_frame_count: Dict[str, int] = {}

        # 统计
        self._stats = {
            "frames_received": 0,
            "waveforms_processed": 0,
            "pd_events_detected": 0,
            "fft_computed": 0,
            "errors": 0,
            "start_time": 0.0,
        }

        self._data_bus = PDDataBus.instance()

    # ── 连接管理 ─────────────────────────────────────

    def set_protocol(self, protocol: Any) -> None:
        self._protocol = protocol

    def start(self) -> bool:
        with self._lock:
            self._is_running = True
            self._stats["start_time"] = time.time()
            logger.info("采集服务已启动")
            return True

    def stop(self) -> None:
        with self._lock:
            self._is_running = False
            # 清理所有处理器
            self._fft_processors.clear()
            self._prpd_processors.clear()
            self._prps_processors.clear()
            self._ring_buffers.clear()
            self._peak_detectors.clear()
            self._sample_rates.clear()
            self._prpd_frame_count.clear()
        logger.info("采集服务已停止")

    @property
    def is_running(self) -> bool:
        return self._is_running

    # ── 通道管理器（线程安全）─────────────────────────

    def _channel_key(self, device_id: str, channel_id: int) -> str:
        return f"{device_id}:{channel_id}"

    def get_or_create_fft(self, device_id: str, channel_id: int) -> FFTProcessor:
        with self._lock:
            key = self._channel_key(device_id, channel_id)
            if key not in self._fft_processors:
                sr = self._sample_rates.get(key, self._default_sample_rate)
                self._fft_processors[key] = FFTProcessor(
                    sample_rate=sr,
                    window_size=min(self._waveform_points, 4096),
                )
            return self._fft_processors[key]

    def get_or_create_prpd(self, device_id: str, channel_id: int) -> PRPDProcessor:
        with self._lock:
            key = self._channel_key(device_id, channel_id)
            if key not in self._prpd_processors:
                self._prpd_processors[key] = PRPDProcessor(phase_bins=360, amplitude_bins=256)
            return self._prpd_processors[key]

    def get_or_create_prps(self, device_id: str, channel_id: int) -> PRPSProcessor:
        with self._lock:
            key = self._channel_key(device_id, channel_id)
            if key not in self._prps_processors:
                self._prps_processors[key] = PRPSProcessor(rows=512, cols=360)
            return self._prps_processors[key]

    def get_or_create_buffer(self, device_id: str, channel_id: int) -> RingBuffer:
        with self._lock:
            key = self._channel_key(device_id, channel_id)
            if key not in self._ring_buffers:
                self._ring_buffers[key] = RingBuffer(maxlen=1_000_000)
            return self._ring_buffers[key]

    def get_or_create_peak_detector(self, device_id: str, channel_id: int) -> PeakDetector:
        with self._lock:
            key = self._channel_key(device_id, channel_id)
            if key not in self._peak_detectors:
                self._peak_detectors[key] = PeakDetector(adaptive=True)
            return self._peak_detectors[key]

    # ── 数据处理 Pipeline ────────────────────────────

    def process_data_frame(self, device_id: str, channel_id: int, data: Any) -> AcquisitionResult:
        start = time.time()
        result = AcquisitionResult(device_id, channel_id)

        try:
            data_type = type(data).__name__

            if "WaveformData" in data_type:
                result = self._process_waveform(device_id, channel_id, data)
            elif "FFTData" in data_type:
                result = self._process_fft(device_id, channel_id, data)
            elif isinstance(data, dict) and "phase" in data:
                result = self._process_pd_event(device_id, channel_id, data)
            else:
                result.success = True
                result.frame_type = data_type
                result.data = data

            result.duration_ms = (time.time() - start) * 1000
            self._stats["frames_received"] += 1

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self._stats["errors"] += 1
            logger.error("[%s] 数据处理失败: %s", device_id, e)

        return result

    def _process_waveform(self, device_id: str, channel_id: int, wf_data: Any) -> AcquisitionResult:
        result = AcquisitionResult(device_id, channel_id)
        result.frame_type = "waveform"

        samples = np.array(getattr(wf_data, "samples", []), dtype=np.float64)
        if len(samples) < 2:
            result.error_message = "波形数据不足"
            return result

        # 按通道独立存储采样率
        sr = getattr(wf_data, "sample_rate", self._default_sample_rate) or self._default_sample_rate
        key = self._channel_key(device_id, channel_id)
        self._sample_rates[key] = sr

        # 存入环形缓冲区
        buffer = self.get_or_create_buffer(device_id, channel_id)
        buffer.extend(samples.tolist())

        # 峰值检测
        detector = self.get_or_create_peak_detector(device_id, channel_id)
        pd_events = []
        try:
            pd_events = detector.detect_pd_events(samples)
            for peak in pd_events:
                self._data_bus.publish_pd_event(
                    device_id,
                    channel_id,
                    {
                        "amplitude": peak.amplitude,
                        "position": peak.position,
                        "energy": peak.energy,
                        "width": peak.width,
                        "timestamp": time.time(),
                    },
                )
                self._stats["pd_events_detected"] += 1
        except Exception as e:
            logger.debug("[%s] 峰值检测异常: %s", device_id, e)

        # FFT 计算
        try:
            fft_proc = self.get_or_create_fft(device_id, channel_id)
            fft_result = fft_proc.compute(samples, detect_peaks=True)
            self._data_bus.publish_fft_result(device_id, channel_id, fft_result)
            self._stats["fft_computed"] += 1
        except Exception as e:
            logger.debug("[%s] FFT 异常: %s", device_id, e)

        # PRPD 更新 + 指数衰减
        try:
            prpd_proc = self.get_or_create_prpd(device_id, channel_id)
            prpd_proc.add_waveform(samples, phase_offset=0)

            # 每 20 帧应用一次指数衰减
            if key not in self._prpd_frame_count:
                self._prpd_frame_count[key] = 0
            self._prpd_frame_count[key] += 1
            if self._prpd_frame_count[key] >= 20:
                self._prpd_frame_count[key] = 0
                prpd_proc._matrix *= self.PRPD_DECAY_FACTOR

            # 定期发布 PRPD（每 50 帧）
            self._stats["waveforms_processed"] += 1
            if self._stats["waveforms_processed"] % 50 == 0:
                prpd_result = prpd_proc.compute()
                self._data_bus.publish_prpd_result(device_id, channel_id, prpd_result)
        except Exception as e:
            logger.debug("[%s] PRPD 异常: %s", device_id, e)

        # PRPS 更新
        try:
            prps_proc = self.get_or_create_prps(device_id, channel_id)
            phase_binned = np.zeros(360)
            for peak in pd_events[:360]:
                phase_idx = int((peak.position / len(samples)) * 360) % 360
                phase_binned[phase_idx] = max(phase_binned[phase_idx], abs(peak.amplitude))
            prps_proc.add_cycle(phase_binned)
            prps_result = prps_proc.compute()
            self._data_bus.publish_prps_result(device_id, channel_id, prps_result)
        except Exception as e:
            logger.debug("[%s] PRPS 异常: %s", device_id, e)

        # 发布波形到 UI
        self._data_bus.publish_waveform(device_id, channel_id, samples)

        result.success = True
        result.data = {
            "samples": samples,
            "sample_rate": sr,
            "n_peaks": len(pd_events),
        }
        return result

    def _process_fft(self, device_id: str, channel_id: int, fft_data: Any) -> AcquisitionResult:
        result = AcquisitionResult(device_id, channel_id)
        result.frame_type = "fft"
        result.success = True
        result.data = fft_data
        self._data_bus.publish_fft_result(device_id, channel_id, fft_data)
        self._stats["fft_computed"] += 1
        return result

    def _process_pd_event(self, device_id: str, channel_id: int, event: dict) -> AcquisitionResult:
        result = AcquisitionResult(device_id, channel_id)
        result.frame_type = "pd_event"
        result.success = True
        result.data = event

        if "phase" in event and "amplitude" in event:
            prpd = self.get_or_create_prpd(device_id, channel_id)
            prpd.add_event(
                phase=event["phase"],
                amplitude=event["amplitude"],
                polarity=event.get("polarity", 0),
                energy=event.get("energy", 0.0),
            )

        self._data_bus.publish_pd_event(device_id, channel_id, event)
        self._stats["pd_events_detected"] += 1
        return result

    # ── 回调 ─────────────────────────────────────────

    def set_on_waveform_callback(self, cb: Optional[Callable]) -> None:
        self._on_waveform_cb = cb

    def set_on_pd_event_callback(self, cb: Optional[Callable]) -> None:
        self._on_pd_event_cb = cb

    # ── 统计 ─────────────────────────────────────────

    def get_stats(self) -> dict:
        s = dict(self._stats)
        if s["start_time"] > 0:
            s["uptime_seconds"] = time.time() - s["start_time"]
        return s

    def get_channel_stats(self, device_id: str, channel_id: int) -> dict:
        key = self._channel_key(device_id, channel_id)
        buf = self._ring_buffers.get(key)
        return {
            "buffer_size": buf.size if buf else 0,
            "sample_rate": self._sample_rates.get(key, self._default_sample_rate),
            "fft_ready": key in self._fft_processors,
            "prpd_ready": key in self._prpd_processors,
            "prps_ready": key in self._prps_processors,
        }

    def reset_stats(self) -> None:
        for k in self._stats:
            if k != "start_time":
                self._stats[k] = 0

    def release_channel(self, device_id: str, channel_id: int) -> None:
        key = self._channel_key(device_id, channel_id)
        with self._lock:
            self._fft_processors.pop(key, None)
            self._prpd_processors.pop(key, None)
            self._prps_processors.pop(key, None)
            self._ring_buffers.pop(key, None)
            self._peak_detectors.pop(key, None)
            self._sample_rates.pop(key, None)
            self._prpd_frame_count.pop(key, None)

    def release_device(self, device_id: str) -> None:
        prefix = f"{device_id}:"
        with self._lock:
            for d in list(self._fft_processors.keys()):
                if d.startswith(prefix):
                    del self._fft_processors[d]
            for d in list(self._prpd_processors.keys()):
                if d.startswith(prefix):
                    del self._prpd_processors[d]
            for d in list(self._prps_processors.keys()):
                if d.startswith(prefix):
                    del self._prps_processors[d]
            for d in list(self._ring_buffers.keys()):
                if d.startswith(prefix):
                    del self._ring_buffers[d]
            for d in list(self._peak_detectors.keys()):
                if d.startswith(prefix):
                    del self._peak_detectors[d]
            for d in list(self._sample_rates.keys()):
                if d.startswith(prefix):
                    del self._sample_rates[d]
            for d in list(self._prpd_frame_count.keys()):
                if d.startswith(prefix):
                    del self._prpd_frame_count[d]
