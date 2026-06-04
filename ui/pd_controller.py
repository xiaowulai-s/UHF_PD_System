# -*- coding: utf-8 -*-
"""
PD 系统总控制器 - PDSystemController

整合所有服务层组件并连接 UI 页面:
- AcquisitionService: 数据采集与信号处理
- PDAlarmService: 报警检测与管理
- PDStorageService: 数据持久化
- PDSimulator: 测试数据生成
- PDDataBus: 事件总线（连接服务和 UI）

架构:
    PDSimulator / FPGA
         ↓ (波形数据)
    AcquisitionService → PDDataBus → UI (WaveformWidget, PRPDWidget, FFTWidget)
         ↓ (峰值/事件)
    PDAlarmService → PDDataBus → UI (AlarmPage)
         ↓ (报警记录)
    PDStorageService → SQLite
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QObject, QTimer

from core.foundation.pd_data_bus import PDDataBus
from core.services import AcquisitionService, PDAlarmService, PDStorageService

logger = logging.getLogger(__name__)


class PDSystemController(QObject):
    """
    PD 系统总控制器

    负责:
    1. 初始化所有服务
    2. 连接 DataBus 信号到 UI
    3. 启动/停止数据采集
    4. 管理测试模拟器
    """

    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self._db_manager = db_manager
        self._data_bus = PDDataBus.instance()

        # 服务
        self._acquisition: Optional[AcquisitionService] = None
        self._alarm: Optional[PDAlarmService] = None
        self._storage: Optional[PDStorageService] = None
        self._simulator: Any = None

        # UI 页面引用
        self._pages: dict = {}

        # 统计定时器
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_status_stats)
        self._stats_timer.setInterval(2000)

        logger.info("PDSystemController 已创建")

    # ── 初始化 ───────────────────────────────────────

    def initialize(self, pages: dict = None) -> None:
        """
        初始化所有服务

        Args:
            pages: UI 页面字典 {key: page_widget}
        """
        if pages:
            self._pages = pages

        # 初始化服务
        self._acquisition = AcquisitionService(
            sample_rate=100_000_000,
            waveform_points=4096,
        )

        self._alarm = PDAlarmService(db_manager=self._db_manager)
        self._storage = PDStorageService(
            db_manager=self._db_manager,
            flush_interval=5.0,
            batch_size=100,
        )

        # 连接服务到 DataBus
        self._connect_services()

        # 启动存储
        if self._storage:
            self._storage.start()

        # 连接 UI
        self._connect_ui()

        self._stats_timer.start()

        logger.info("PDSystemController 初始化完成")

    def _connect_services(self) -> None:
        """连接服务层"""
        bus = self._data_bus

        # 采集 → 报警
        bus.pd_event_detected.connect(self._on_pd_event_for_alarm)
        bus.device_status_changed.connect(self._on_device_status_for_alarm)

        # 采集 → 存储
        bus.pd_event_detected.connect(self._on_pd_event_for_storage)
        bus.waveform_received.connect(self._on_waveform_for_storage)

        logger.debug("服务层信号连接完成")

    def _connect_ui(self) -> None:
        """连接 UI 信号"""
        bus = self._data_bus
        pages = self._pages

        # 波形 → WaveformWidget
        bus.waveform_received.connect(self._on_waveform_for_ui)

        # FFT → FFTWidget
        bus.fft_result_ready.connect(self._on_fft_for_ui)

        # PRPD → PRPDWidget
        bus.prpd_result_ready.connect(self._on_prpd_for_ui)

        # PRPS → PRPSWidget
        bus.prps_result_ready.connect(self._on_prps_for_ui)

        # 报警 → AlarmPage
        bus.pd_alarm_triggered.connect(self._on_alarm_for_ui)

        # 设备状态
        bus.device_status_changed.connect(self._on_device_status_for_ui)

        # 连接报警服务到报警页面
        if "alarm" in pages:
            pages["alarm"].set_alarm_service(self._alarm)

        logger.debug("UI 信号连接完成")

    # ── 服务回调 ─────────────────────────────────────

    def _on_pd_event_for_alarm(self, device_id: str, channel_id: int, event: dict) -> None:
        """局放事件 → 报警检测"""
        if not self._alarm:
            return
        amplitude = event.get("amplitude", 0)
        alarm = self._alarm.check_amplitude(device_id, channel_id, amplitude)
        if alarm:
            self._alarm.trigger_alarm(alarm)

    def _on_device_status_for_alarm(self, device_id: str, status: int, status_data: dict) -> None:
        """设备状态 → 报警检测"""
        if not self._alarm or status == 1:
            return
        status_alarm = self._alarm.check_device_status(device_id, status_data)
        if status_alarm:
            self._alarm.trigger_alarm(status_alarm)

    def _on_pd_event_for_storage(self, device_id: str, channel_id: int, event: dict) -> None:
        """局放事件 → 存储"""
        if self._storage:
            self._storage.store_pd_event(device_id, channel_id, event)

    def _on_waveform_for_storage(self, device_id: str, channel_id: int, waveform: Any) -> None:
        """波形数据 → 存储（每 50 帧记录一次趋势）"""
        if self._storage and hasattr(self._acquisition, "_stats"):
            stats = self._acquisition.get_stats()
            if stats.get("waveforms_processed", 0) % 50 == 0:
                self._storage.store_trend_data(
                    device_id,
                    channel_id,
                    "1h",
                    {
                        "pd_count": stats.get("pd_events_detected", 0),
                        "max_amplitude": 0,
                        "avg_amplitude": 0,
                        "total_energy": 0,
                        "noise_level": 0,
                    },
                )

    # ── UI 回调 ──────────────────────────────────────

    def _on_waveform_for_ui(self, device_id: str, channel_id: int, waveform: Any) -> None:
        """波形数据 → UI 更新"""
        import numpy as np

        data = np.array(waveform.samples) if hasattr(waveform, "samples") else np.array(waveform)
        if len(data) < 2:
            return

        # Monitor: 全功能波形控件
        if "monitor" in self._pages:
            try:
                self._pages["monitor"]._waveform.update_waveform(data, sample_rate=100_000_000)
            except Exception:
                pass

        # Dashboard: 仅更新快照（每 10 帧一次）
        if "dashboard" in self._pages:
            try:
                if getattr(self, "_waveform_frame_count", 0) % 10 == 0:
                    self._pages["dashboard"].update_waveform_snapshot(data, 100_000_000)
                self._waveform_frame_count = getattr(self, "_waveform_frame_count", 0) + 1
            except Exception:
                pass

    def _on_fft_for_ui(self, device_id: str, channel_id: int, fft_result: Any) -> None:
        """FFT 结果 → UI"""
        pages = self._pages
        freqs = fft_result.frequencies
        mags = fft_result.magnitudes

        # Monitor: 全功能频谱控件
        if "monitor" in pages:
            try:
                peaks = [
                    {
                        "frequency": p.frequency,
                        "magnitude": p.magnitude,
                        "is_harmonic": p.is_harmonic,
                        "harmonic_order": p.harmonic_order,
                    }
                    for p in (fft_result.peaks or [])
                ]
                pages["monitor"]._fft.update_spectrum(
                    freqs,
                    mags,
                    peaks=peaks,
                    noise_floor=fft_result.noise_floor,
                    snr_db=fft_result.snr_db,
                )
                pages["monitor"].update_peak_list(peaks)
            except Exception:
                pass

        # Dashboard: 仅更新快照
        if "dashboard" in pages:
            try:
                pages["dashboard"].update_fft_snapshot(freqs, mags)
            except Exception:
                pass

    def _on_prpd_for_ui(self, device_id: str, channel_id: int, prpd_result: Any) -> None:
        """PRPD 结果 → UI"""
        pages = self._pages
        # Monitor: 全功能 PRPD 控件
        if "monitor" in pages:
            try:
                pages["monitor"]._prpd.update_heatmap(prpd_result.matrix, 360, 256)
            except Exception:
                pass

        # Dashboard: 仅更新快照
        if "dashboard" in pages:
            try:
                pages["dashboard"].update_prpd_snapshot(prpd_result.matrix)
            except Exception:
                pass

    def _on_prps_for_ui(self, device_id: str, channel_id: int, prps_result: Any) -> None:
        """PRPS 结果 → UI"""
        if "monitor" in self._pages:
            try:
                self._pages["monitor"]._prpd.update_heatmap(prps_result.matrix, 360, 256)
            except Exception:
                pass

    def _on_alarm_for_ui(self, device_id: str, alarm_dict: dict) -> None:
        """报警 → AlarmPage + Dashboard"""
        if "alarm" in self._pages:
            self._pages["alarm"].add_alarm(alarm_dict)
        # Dashboard 最新报警
        if "dashboard" in self._pages:
            try:
                desc = alarm_dict.get("description", "")
                if desc:
                    self._pages["dashboard"].set_latest_alarm(desc[:60])
            except Exception:
                pass

    def _on_device_status_for_ui(self, device_id: str, status: int, status_data: dict) -> None:
        """设备状态 → UI 更新"""
        pass

    def _update_status_stats(self) -> None:
        """定时更新状态栏统计"""
        pass

    # ── 模拟器 ───────────────────────────────────────

    def start_simulator(self, pd_type: str = "internal", fps: int = 20) -> None:
        """
        启动数据模拟器（用于测试和演示）

        Args:
            pd_type: 局放类型 (corona/surface/internal/floating)
            fps: 帧率
        """
        from core.utils.pd_simulator import PDSimulator

        self._simulator = PDSimulator(
            sample_rate=100_000_000,
            waveform_points=4096,
            pulse_rate=50,
            noise_level=2.0,
        )
        self._simulator.set_pd_type(pd_type)

        # 模拟器 → 采集服务
        self._simulator.set_on_waveform_callback(lambda dev, ch, wf: self._acquisition.process_data_frame(dev, ch, wf))

        self._simulator.start(interval_ms=1000 // fps)
        logger.info("模拟器已启动: type=%s, %d FPS", pd_type, fps)

    def stop_simulator(self) -> None:
        """停止模拟器"""
        if self._simulator:
            self._simulator.stop()
            self._simulator = None

    # ── 生命周期 ─────────────────────────────────────

    def shutdown(self) -> None:
        """关闭所有服务"""
        self._stats_timer.stop()
        self.stop_simulator()
        if self._acquisition:
            self._acquisition.stop()
        if self._storage:
            self._storage.stop()
        if self._alarm:
            self._alarm.shutdown()
        self._data_bus.shutdown()
        logger.info("PDSystemController 已关闭")
