# -*- coding: utf-8 -*-
"""MCGS设备批量操作对话框 — 批量连接/断开/删除 + 操作结果统计"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.utils.logger import get_logger

logger = get_logger(__name__)


class _BatchWorker(QThread):
    progress = Signal(int, int)
    result = Signal(str, bool, str)
    all_done = Signal(int, int, int)

    def __init__(
        self,
        device_ids: List[str],
        operation: str,
        controller: Any,
        parent: Optional[QThread] = None,
    ):
        super().__init__(parent)
        self._device_ids = device_ids
        self._operation = operation
        self._controller = controller
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        success = 0
        failed = 0
        total = len(self._device_ids)

        for idx, device_id in enumerate(self._device_ids):
            if self._cancelled:
                break
            try:
                if self._operation == "connect":
                    self._controller.connect_device(device_id)
                    success += 1
                    self.result.emit(device_id, True, "连接请求已发送")
                elif self._operation == "disconnect":
                    self._controller.disconnect_device(device_id)
                    success += 1
                    self.result.emit(device_id, True, "断开请求已发送")
                elif self._operation == "delete":
                    self._controller.remove_device(device_id)
                    success += 1
                    self.result.emit(device_id, True, "已删除")
                else:
                    failed += 1
                    self.result.emit(device_id, False, f"未知操作: {self._operation}")
            except Exception as e:
                failed += 1
                self.result.emit(device_id, False, str(e))

            self.progress.emit(idx + 1, total)
            self.msleep(50)

        self.all_done.emit(success, failed, total)


class MCGSBatchDialog(QDialog):
    """MCGS设备批量操作对话框"""

    def __init__(
        self,
        mcgs_controller: Any = None,
        parent: Optional[QDialog] = None,
    ):
        super().__init__(parent)
        self._controller = mcgs_controller
        self._worker: Optional[_BatchWorker] = None
        self._device_configs: Dict[str, dict] = {}
        self._checkboxes: Dict[str, QCheckBox] = {}
        self.setWindowTitle("MCGS设备批量操作")
        self.setMinimumSize(550, 460)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._init_ui()
        self._load_devices()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title_label = QLabel("MCGS设备批量管理")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #111827;")
        layout.addWidget(title_label)

        desc_label = QLabel("勾选设备后选择操作：批量连接、断开或删除")
        desc_label.setStyleSheet("font-size: 12px; color: #6B7280;")
        layout.addWidget(desc_label)

        select_layout = QHBoxLayout()
        select_layout.setSpacing(8)

        self._select_all_btn = QPushButton("全选")
        self._select_all_btn.setFixedHeight(30)
        self._select_all_btn.clicked.connect(self._select_all)
        select_layout.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("取消全选")
        self._deselect_all_btn.setFixedHeight(30)
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        select_layout.addWidget(self._deselect_all_btn)

        self._selected_count_label = QLabel("已选: 0 台")
        self._selected_count_label.setStyleSheet("font-size: 12px; color: #374151;")
        select_layout.addWidget(self._selected_count_label)
        select_layout.addStretch()

        layout.addLayout(select_layout)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["", "设备ID", "IP地址"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 32)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet(
            "QTableWidget { border: 1px solid #E5E7EB; border-radius: 6px; }"
            "QHeaderView::section { background: #F6F8FA; padding: 6px; font-weight: 600; }"
        )
        layout.addWidget(self._table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._connect_btn = QPushButton("批量连接")
        self._connect_btn.setFixedHeight(36)
        self._connect_btn.setStyleSheet(
            "QPushButton { background: #2DA44E; color: white; border-radius: 6px; font-weight: 500; }"
            "QPushButton:hover { background: #54AE76; }"
            "QPushButton:disabled { background: #94D3A2; }"
        )
        self._connect_btn.clicked.connect(lambda: self._execute("connect"))
        btn_layout.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("批量断开")
        self._disconnect_btn.setFixedHeight(36)
        self._disconnect_btn.setStyleSheet(
            "QPushButton { background: #F59E0B; color: white; border-radius: 6px; font-weight: 500; }"
            "QPushButton:hover { background: #FBBF24; }"
            "QPushButton:disabled { background: #FCD34D; }"
        )
        self._disconnect_btn.clicked.connect(lambda: self._execute("disconnect"))
        btn_layout.addWidget(self._disconnect_btn)

        self._delete_btn = QPushButton("批量删除")
        self._delete_btn.setFixedHeight(36)
        self._delete_btn.setStyleSheet(
            "QPushButton { background: #CF222E; color: white; border-radius: 6px; font-weight: 500; }"
            "QPushButton:hover { background: #E85B65; }"
            "QPushButton:disabled { background: #F0888E; }"
        )
        self._delete_btn.clicked.connect(lambda: self._execute("delete"))
        btn_layout.addWidget(self._delete_btn)

        btn_layout.addStretch()

        self._cancel_exec_btn = QPushButton("取消操作")
        self._cancel_exec_btn.setFixedHeight(36)
        self._cancel_exec_btn.setVisible(False)
        self._cancel_exec_btn.clicked.connect(self._cancel_execution)
        btn_layout.addWidget(self._cancel_exec_btn)

        self._close_btn = QPushButton("关闭")
        self._close_btn.setFixedHeight(36)
        self._close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._close_btn)

        layout.addLayout(btn_layout)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #E5E7EB; border-radius: 6px; text-align: center; }"
            "QProgressBar::chunk { background: #3B82F6; border-radius: 5px; }"
        )
        layout.addWidget(self._progress_bar)

        self._result_group = QGroupBox("操作结果")
        self._result_group.setVisible(False)
        result_layout = QVBoxLayout(self._result_group)

        self._result_summary_label = QLabel()
        self._result_summary_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #111827;")
        result_layout.addWidget(self._result_summary_label)

        self._result_detail_label = QLabel()
        self._result_detail_label.setStyleSheet("font-size: 12px; color: #6B7280;")
        self._result_detail_label.setWordWrap(True)
        result_layout.addWidget(self._result_detail_label)

        layout.addWidget(self._result_group)

    def _load_devices(self):
        if not self._controller:
            self._table.setRowCount(0)
            return

        try:
            device_ids = self._controller.list_devices()
        except Exception:
            device_ids = []

        self._table.setRowCount(len(device_ids))
        for row, device_id in enumerate(device_ids):
            cb = QCheckBox()
            cb.stateChanged.connect(self._update_selected_count)
            self._checkboxes[device_id] = cb
            self._table.setCellWidget(row, 0, cb)

            self._table.setItem(row, 1, QTableWidgetItem(device_id))

            try:
                reader = self._controller.get_reader()
                config = reader.get_device_config(device_id) if reader else {}
                ip = config.get("ip", "-") if config else "-"
            except Exception:
                ip = "-"

            self._table.setItem(row, 2, QTableWidgetItem(ip))

        if not device_ids:
            self._table.setRowCount(1)
            self._table.setItem(0, 0, QTableWidgetItem(""))
            self._table.setItem(0, 1, QTableWidgetItem("无设备"))
            self._table.setItem(0, 2, QTableWidgetItem("-"))

        self._update_selected_count()

    def _select_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(False)

    def _update_selected_count(self):
        count = sum(1 for cb in self._checkboxes.values() if cb.isChecked())
        self._selected_count_label.setText(f"已选: {count} 台")
        can_execute = count > 0 and self._worker is None
        self._connect_btn.setEnabled(can_execute)
        self._disconnect_btn.setEnabled(can_execute)
        self._delete_btn.setEnabled(can_execute)

    def _get_selected_ids(self) -> List[str]:
        return [did for did, cb in self._checkboxes.items() if cb.isChecked()]

    def _set_buttons_enabled(self, enabled: bool):
        self._connect_btn.setEnabled(enabled and len(self._get_selected_ids()) > 0)
        self._disconnect_btn.setEnabled(enabled and len(self._get_selected_ids()) > 0)
        self._delete_btn.setEnabled(enabled and len(self._get_selected_ids()) > 0)
        self._select_all_btn.setEnabled(enabled)
        self._deselect_all_btn.setEnabled(enabled)
        self._cancel_exec_btn.setVisible(not enabled)

    def _execute(self, operation: str):
        selected = self._get_selected_ids()
        if not selected:
            QMessageBox.information(self, "提示", "请先勾选要操作的设备")
            return

        if operation == "delete":
            reply = QMessageBox.warning(
                self,
                "确认批量删除",
                f"确定要删除 {len(selected)} 台设备吗？\n此操作不可撤销！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._results_success = 0
        self._results_failed = 0
        self._results_details: List[str] = []
        self._result_group.setVisible(False)

        self._progress_bar.setMaximum(len(selected))
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._set_buttons_enabled(False)

        self._worker = _BatchWorker(
            device_ids=selected,
            operation=operation,
            controller=self._controller,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.result.connect(self._on_result)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _on_progress(self, current: int, total: int):
        self._progress_bar.setValue(current)

    def _on_result(self, device_id: str, success: bool, message: str):
        if success:
            self._results_success += 1
        else:
            self._results_failed += 1
            self._results_details.append(f"{device_id}: {message}")

    def _on_all_done(self, success: int, failed: int, total: int):
        self._progress_bar.setVisible(False)
        self._set_buttons_enabled(True)
        self._worker = None

        self._result_group.setVisible(True)
        self._result_summary_label.setText(
            f"完成 {total} 台设备: [OK] 成功 {success} 台, [WARN] 失败 {failed} 台"
        )

        if self._results_details:
            self._result_detail_label.setText("\n".join(self._results_details[:10]))
            if len(self._results_details) > 10:
                self._result_detail_label.setText(
                    self._result_detail_label.text()
                    + f"\n... 还有 {len(self._results_details) - 10} 条失败记录"
                )
        else:
            self._result_detail_label.setText("所有操作均已成功完成。")

    def _cancel_execution(self):
        if self._worker:
            self._worker.cancel()
            self._worker.wait(2000)
        self._set_buttons_enabled(True)
        self._progress_bar.setVisible(False)