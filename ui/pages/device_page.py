# -*- coding: utf-8 -*-
"""设备管理页面 - 完整实现"""

from typing import Dict, Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_tokens import DT
from ui.widgets import DangerButton, PrimaryButton, SecondaryButton, SuccessButton


class DevicePage(QWidget):
    """设备管理 - 采集设备与通道配置"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("devicePage")
        self._devices: Dict[str, dict] = {}
        self._selected_device_id: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(DT.S.XL, DT.S.LG, DT.S.XL, DT.S.LG)
        layout.setSpacing(DT.S.MD)

        self._build_header(layout)
        self._build_content(layout)

    # ── 标题 ─────────────────────────────────────────

    def _build_header(self, layout: QVBoxLayout) -> None:
        header = QHBoxLayout()
        title = QLabel("设备管理")
        title.setFont(DT.T.get_font(*DT.T.TITLE_XLARGE[:2], "Bold"))
        title.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        layout.addLayout(header)

        subtitle = QLabel("UHF 采集设备注册 · 通道配置 · 参数设置 · 状态监测")
        subtitle.setFont(DT.T.get_font(*DT.T.BODY[:2]))
        subtitle.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY};")
        layout.addWidget(subtitle)

    # ── 内容区 ───────────────────────────────────────

    def _build_content(self, layout: QVBoxLayout) -> None:
        content = QHBoxLayout()
        content.setSpacing(DT.S.MD)

        # 左: 设备列表
        self._build_device_list(content)
        # 中: 通道配置
        self._build_channel_config(content)
        # 右: 设备参数
        self._build_device_params(content)

        layout.addLayout(content, 1)

    def _build_device_list(self, parent: QHBoxLayout) -> None:
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
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)

        title = QLabel("设备列表")
        title.setFont(DT.T.get_font(*DT.T.TITLE_MEDIUM[:2], "SemiBold"))
        title.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        layout.addWidget(title)

        self._device_table = QTableWidget()
        self._device_table.setColumnCount(4)
        self._device_table.setHorizontalHeaderLabels(["设备名称", "IP地址", "状态", "通道数"])
        self._device_table.setAlternatingRowColors(True)
        self._device_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._device_table.verticalHeader().setVisible(False)
        self._device_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._device_table.setStyleSheet(self._table_style())
        self._device_table.horizontalHeader().setStretchLastSection(True)
        self._device_table.itemSelectionChanged.connect(self._on_device_selected)
        layout.addWidget(self._device_table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(DT.S.SM)
        self._btn_connect = PrimaryButton("连接设备")
        self._btn_connect.clicked.connect(self._on_connect_device)
        btn_row.addWidget(self._btn_connect)
        btn_del = DangerButton("删除设备")
        btn_del.clicked.connect(self._on_delete_device)
        btn_row.addWidget(btn_del)
        self._btn_add = SuccessButton("添加设备")
        self._btn_add.clicked.connect(self._on_add_device)
        btn_row.addWidget(self._btn_add)
        self._btn_scan = SecondaryButton("扫描设备")
        btn_row.addWidget(self._btn_scan)
        layout.addLayout(btn_row)

        parent.addWidget(frame, 25)

    def _build_channel_config(self, parent: QHBoxLayout) -> None:
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
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)

        title = QLabel("通道配置")
        title.setFont(DT.T.get_font(*DT.T.TITLE_MEDIUM[:2], "SemiBold"))
        title.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        layout.addWidget(title)

        self._ch_table = QTableWidget()
        self._ch_table.setColumnCount(5)
        self._ch_table.setHorizontalHeaderLabels(["通道", "名称", "耦合方式", "增益(dB)", "状态"])
        self._ch_table.setAlternatingRowColors(True)
        self._ch_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._ch_table.verticalHeader().setVisible(False)
        self._ch_table.setStyleSheet(self._table_style())
        self._ch_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._ch_table)

        self._ch_info = QLabel("请选择设备以查看通道")
        self._ch_info.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 12px; padding: 4px;")
        layout.addWidget(self._ch_info)

        parent.addWidget(frame, 40)

    def _build_device_params(self, parent: QHBoxLayout) -> None:
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
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)
        layout.setSpacing(2)

        title = QLabel("设备参数")
        title.setFont(DT.T.get_font(*DT.T.TITLE_MEDIUM[:2], "SemiBold"))
        title.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY}; margin: 0; padding: 0;")
        title.setFixedHeight(24)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(6)
        form.setContentsMargins(0, 4, 0, 0)

        self._param_name = QLineEdit()
        self._param_name.setPlaceholderText("设备名称")
        self._param_name.setStyleSheet(self._input_style())
        form.addRow("名称:", self._param_name)

        self._param_host = QLineEdit()
        self._param_host.setPlaceholderText("192.168.1.100")
        self._param_host.setStyleSheet(self._input_style())
        form.addRow("IP地址:", self._param_host)

        self._param_tcp = QSpinBox()
        self._param_tcp.setRange(1, 65535)
        self._param_tcp.setValue(5000)
        self._param_tcp.setStyleSheet(self._spin_style())
        form.addRow("TCP端口:", self._param_tcp)

        self._param_udp = QSpinBox()
        self._param_udp.setRange(1, 65535)
        self._param_udp.setValue(6000)
        self._param_udp.setStyleSheet(self._spin_style())
        form.addRow("UDP端口:", self._param_udp)

        self._param_sample_rate = QSpinBox()
        self._param_sample_rate.setRange(1, 500)
        self._param_sample_rate.setValue(100)
        self._param_sample_rate.setSuffix(" MHz")
        self._param_sample_rate.setStyleSheet(self._spin_style())
        form.addRow("采样率:", self._param_sample_rate)

        self._param_channels = QSpinBox()
        self._param_channels.setRange(1, 32)
        self._param_channels.setValue(4)
        self._param_channels.setStyleSheet(self._spin_style())
        form.addRow("通道数:", self._param_channels)

        self._param_sim = QCheckBox("使用模拟器")
        self._param_sim.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY}; font-size: 13px;")
        form.addRow("", self._param_sim)

        layout.addLayout(form)

        layout.addStretch()

        btn_save = PrimaryButton("保存参数")
        btn_save.clicked.connect(self._on_save_params)
        layout.addWidget(btn_save)

        parent.addWidget(frame, 35)

    # ── 操作方法 ─────────────────────────────────────

    def add_device(self, device: dict) -> None:
        """添加设备到列表"""
        device_id = device.get("id", f"DEV_{len(self._devices) + 1:03d}")
        self._devices[device_id] = device

        row = self._device_table.rowCount()
        self._device_table.insertRow(row)
        self._device_table.setItem(row, 0, QTableWidgetItem(device.get("name", device_id)))
        self._device_table.setItem(row, 1, QTableWidgetItem(device.get("host", "0.0.0.0")))

        status = device.get("status", 0)
        status_text = {0: "离线", 1: "在线", 2: "告警", 3: "错误"}
        status_item = QTableWidgetItem(status_text.get(status, "未知"))
        status_color = {0: DT.C.TEXT_TERTIARY, 1: DT.C.STATUS_SUCCESS, 2: DT.C.STATUS_WARNING, 3: DT.C.STATUS_ERROR}
        status_item.setForeground(QColor(status_color.get(status, DT.C.TEXT_TERTIARY)))
        self._device_table.setItem(row, 2, status_item)

        self._device_table.setItem(row, 3, QTableWidgetItem(str(device.get("channel_count", 4))))

    def add_sample_devices(self) -> None:
        """添加示例设备"""
        self.add_device(
            {
                "id": "DEV001",
                "name": "FPGA-采集主机-01",
                "host": "192.168.1.100",
                "tcp_port": 5000,
                "udp_port": 6000,
                "status": 1,
                "channel_count": 8,
                "sample_rate": 100,
            }
        )
        self.add_device(
            {
                "id": "DEV002",
                "name": "FPGA-采集主机-02",
                "host": "192.168.1.101",
                "tcp_port": 5000,
                "udp_port": 6000,
                "status": 0,
                "channel_count": 4,
                "sample_rate": 100,
            }
        )
        self.add_device(
            {
                "id": "DEV003",
                "name": "FPGA-采集主机-03",
                "host": "192.168.1.102",
                "tcp_port": 5001,
                "udp_port": 6001,
                "status": 0,
                "channel_count": 16,
                "sample_rate": 250,
            }
        )
        # 添加示例通道
        self._update_channel_table(8)

    def _on_device_selected(self) -> None:
        """设备选择变化"""
        selected = self._device_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        name_item = self._device_table.item(row, 0)
        if not name_item:
            return
        name = name_item.text()
        for dev_id, dev in self._devices.items():
            if dev.get("name") == name:
                self._selected_device_id = dev_id
                self._param_name.setText(dev.get("name", ""))
                self._param_host.setText(dev.get("host", ""))
                self._param_tcp.setValue(dev.get("tcp_port", 5000))
                self._param_udp.setValue(dev.get("udp_port", 6000))
                self._param_sample_rate.setValue(dev.get("sample_rate", 100))
                self._param_channels.setValue(dev.get("channel_count", 4))
                self._update_channel_table(dev.get("channel_count", 4))
                break

    def _update_channel_table(self, n_channels: int) -> None:
        """更新通道表"""
        self._ch_table.setRowCount(0)
        coupling_types = [
            "UHF",
            "UHF",
            "HFCT",
            "TEV",
            "UHF",
            "UHF",
            "HFCT",
            "TEV",
            "UHF",
            "UHF",
            "HFCT",
            "TEV",
            "UHF",
            "UHF",
            "HFCT",
            "TEV",
        ]
        for i in range(min(n_channels, 16)):
            row = self._ch_table.rowCount()
            self._ch_table.insertRow(row)
            self._ch_table.setItem(row, 0, QTableWidgetItem(f"CH-{i+1:02d}"))
            self._ch_table.setItem(row, 1, QTableWidgetItem(f"通道 {i+1}"))
            self._ch_table.setItem(row, 2, QTableWidgetItem(coupling_types[i]))
            self._ch_table.setItem(row, 3, QTableWidgetItem(f"{20 + i * 2}"))
            status_item = QTableWidgetItem("正常")
            status_item.setForeground(QColor(DT.C.STATUS_SUCCESS))
            self._ch_table.setItem(row, 4, status_item)
        self._ch_info.setText(f"共 {n_channels} 个通道 | 已配置 {min(n_channels, 16)} 个")

    def _on_add_device(self) -> None:
        """添加新设备"""
        name = self._param_name.text().strip()
        if not name:
            self._param_name.setPlaceholderText("请输入设备名称!")
            return
        new_id = f"DEV_{len(self._devices) + 1:03d}"
        self.add_device(
            {
                "id": new_id,
                "name": name,
                "host": self._param_host.text() or "0.0.0.0",
                "tcp_port": self._param_tcp.value(),
                "udp_port": self._param_udp.value(),
                "status": 0,
                "channel_count": self._param_channels.value(),
                "sample_rate": self._param_sample_rate.value(),
            }
        )

    def _on_connect_device(self) -> None:
        """连接选中设备"""
        if not self._selected_device_id:
            return
        dev = self._devices.get(self._selected_device_id)
        if not dev:
            return
        # Toggle: set online
        new_status = 1 if dev.get("status") != 1 else 0
        dev["status"] = new_status
        selected = self._device_table.selectedItems()
        if selected:
            row = selected[0].row()
            status_item = self._device_table.item(row, 2)
            if status_item:
                status_text = {0: "离线", 1: "在线", 2: "告警", 3: "错误"}
                status_item.setText(status_text.get(new_status, "未知"))
                color = {0: DT.C.TEXT_TERTIARY, 1: DT.C.STATUS_SUCCESS}
                status_item.setForeground(QColor(color.get(new_status, DT.C.TEXT_TERTIARY)))
        self._btn_connect.setText("断开设备" if new_status == 1 else "连接设备")

    def _on_delete_device(self) -> None:
        """删除选中设备"""
        if not self._selected_device_id:
            return
        row = self._device_table.currentRow()
        if row >= 0:
            self._device_table.removeRow(row)
        self._devices.pop(self._selected_device_id, None)
        self._selected_device_id = None
        self._ch_table.setRowCount(0)
        self._ch_info.setText("请选择设备以查看通道")
        self._clear_params()

    def _clear_params(self) -> None:
        self._param_name.clear()
        self._param_host.clear()
        self._param_tcp.setValue(5000)
        self._param_udp.setValue(6000)
        self._param_sample_rate.setValue(100)
        self._param_channels.setValue(4)

    def _on_save_params(self) -> None:
        """保存设备参数"""
        if not self._selected_device_id:
            return
        dev = self._devices.get(self._selected_device_id)
        if dev:
            dev["name"] = self._param_name.text()
            dev["host"] = self._param_host.text()
            dev["tcp_port"] = self._param_tcp.value()
            dev["udp_port"] = self._param_udp.value()
            dev["sample_rate"] = self._param_sample_rate.value()
            dev["channel_count"] = self._param_channels.value()
            # 更新设备表
            for row in range(self._device_table.rowCount()):
                item = self._device_table.item(row, 0)
                if item and item.text() == dev.get("name", ""):
                    self._device_table.item(row, 0).setText(dev["name"])
                    self._device_table.item(row, 1).setText(dev["host"])
                    self._device_table.item(row, 3).setText(str(dev["channel_count"]))
                    break

    # ── 样式 ─────────────────────────────────────────

    @staticmethod
    def _table_style() -> str:
        return f"""
            QTableWidget {{
                background: {DT.C.BG_PRIMARY};
                alternate-background-color: {DT.C.BG_SECONDARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.MD}px;
                font-size: 12px;
                outline: none;
            }}
            QTableWidget::item {{ padding: 6px 8px; border-bottom: 1px solid {DT.C.DIVIDER}; }}
            QTableWidget::item:selected {{ background: {DT.C.ACCENT_SUBTLE}; color: {DT.C.ACCENT_PRIMARY}; }}
            QHeaderView::section {{
                background: {DT.C.BG_SECONDARY}; color: {DT.C.TEXT_SECONDARY};
                border: none; border-bottom: 2px solid {DT.C.BORDER_DEFAULT};
                padding: 6px; font-size: 11px; font-weight: 600;
            }}
        """

    @staticmethod
    def _input_style() -> str:
        return f"""
            QLineEdit {{
                background: {DT.C.BG_PRIMARY}; border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: 4px; padding: 4px 8px; font-size: 12px; color: {DT.C.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{ border-color: {DT.C.BORDER_FOCUS}; border-width: 2px; }}
        """

    @staticmethod
    def _spin_style() -> str:
        return f"""
            QSpinBox {{
                background: {DT.C.BG_PRIMARY}; border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: 4px; padding: 2px 6px; font-size: 12px; color: {DT.C.TEXT_PRIMARY};
            }}
            QSpinBox:focus {{ border-color: {DT.C.BORDER_FOCUS}; }}
        """
