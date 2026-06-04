# -*- coding: utf-8 -*-
"""
通信驱动层
Communication Driver Layer

驱动层:
- base_driver:    驱动基类 (QObject + 信号)
- tcp_driver:     TCP 通信驱动 (Modbus FC08 心跳)
- udp_driver:     UDP 通信驱动 (FPGA 高速数据)
- serial_driver:  串口通信驱动

协议层:
- modbus_protocol: Modbus TCP/RTU 协议
- fpga_protocol:   FPGA 通信协议
"""

from .base_driver import BaseDriver
from .tcp_driver import TCPDriver
from .serial_driver import SerialDriver

# PD 通信组件（可选）
try:
    from .udp_driver import UDPDriver
    from .fpga_protocol import (
        DataFrame, DataType, DeviceStatusData,
        FFTData, FpgaProtocol, PRPDData, PRPSData, WaveformData,
    )
except ImportError:
    pass

__all__ = [
    "BaseDriver",
    "TCPDriver",
    "SerialDriver",
    "UDPDriver",
    "FpgaProtocol",
    "DataFrame",
    "DataType",
    "WaveformData",
    "FFTData",
    "PRPDData",
    "PRPSData",
    "DeviceStatusData",
]
