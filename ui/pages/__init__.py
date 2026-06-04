# -*- coding: utf-8 -*-
"""UHF PD Monitor 页面模块"""

from .alarm_page import AlarmPage
from .dashboard_page import DashboardPage
from .device_page import DevicePage
from .realtime_monitor_page import RealtimeMonitorPage
from .settings_page import SettingsPage
from .trend_page import TrendPage

__all__ = [
    "DashboardPage",
    "RealtimeMonitorPage",
    "TrendPage",
    "AlarmPage",
    "DevicePage",
    "SettingsPage",
]
