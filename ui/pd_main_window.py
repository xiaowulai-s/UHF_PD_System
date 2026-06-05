# -*- coding: utf-8 -*-
"""
UHF PD Monitor 主窗口

基于现有 MCGS_EMS 主窗口架构重构，保留 Fluent Design 风格：
- 左侧导航菜单（可折叠）
- 右侧页面栈
- 统一的状态栏和菜单栏
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from core.utils.logger import get_logger
from ui.design_tokens import DT
from ui.pages import AlarmPage, AnalysisPage, DashboardPage, DevicePage, RealtimeMonitorPage, SettingsPage, TrendPage
from ui.widgets.nav_menu import NavMenu

logger = get_logger("pd_main_window")


class PDMainWindow(QMainWindow):
    """UHF 局部放电在线监测系统主窗口"""

    APP_NAME = "UHF-PD-Monitor"
    WINDOW_TITLE = "超高频局部放电在线监测系统"

    PAGE_KEYS = ["dashboard", "monitor", "analysis", "trend", "alarm", "device", "settings"]
    PAGE_TITLES = [
        "系统仪表板",
        "实时监测",
        "数据分析",
        "趋势分析",
        "报警管理",
        "设备管理",
        "系统设置",
    ]

    def __init__(self, db_manager=None):
        super().__init__()

        self._db_manager = db_manager
        self._pages: dict[str, QWidget] = {}
        self._controller = None

        self._setup_window()
        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()

        # 默认选中首页
        self._nav_menu.select_item("dashboard")
        self._stack_widget.setCurrentIndex(0)

        self._update_status_bar()

        logger.info("UHF PD Monitor 主窗口初始化完成")

    def _setup_window(self) -> None:
        """配置主窗口属性"""
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(1280, 720)
        self.resize(1440, 900)
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {DT.C.BG_SECONDARY};
            }}
        """
        )

    def _setup_menu_bar(self) -> None:
        """创建菜单栏"""
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet(
            f"""
            QMenuBar {{
                background: {DT.C.BG_PRIMARY};
                border-bottom: 1px solid {DT.C.BORDER_DEFAULT};
                padding: 2px 0;
                font-size: 13px;
            }}
            QMenuBar::item {{
                padding: 6px 16px;
                background: transparent;
                border-radius: 4px;
                margin: 2px 2px;
            }}
            QMenuBar::item:selected {{
                background: {DT.C.BG_HOVER};
            }}
            QMenu {{
                background: {DT.C.BG_PRIMARY};
                border: 1px solid {DT.C.BORDER_DEFAULT};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 32px 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }}
            QMenu::item:selected {{
                background: {DT.C.BG_HOVER};
            }}
            QMenu::separator {{
                height: 1px;
                background: {DT.C.DIVIDER};
                margin: 4px 8px;
            }}
        """
        )

        # 文件菜单
        file_menu = menu_bar.addMenu("文件(&F)")
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助(&H)")
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_central_widget(self) -> None:
        """创建中央部件：导航菜单 + 页面栈"""
        central = QWidget()
        central.setStyleSheet(f"background: {DT.C.BG_SECONDARY};")
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧导航
        self._nav_menu = NavMenu(self)
        self._nav_menu.item_selected.connect(self._on_nav_item_selected)
        layout.addWidget(self._nav_menu)

        # 右侧页面栈
        page_container = QWidget()
        page_container.setStyleSheet(f"background: {DT.C.BG_SECONDARY};")
        page_layout = QVBoxLayout(page_container)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        self._stack_widget = QStackedWidget()
        self._stack_widget.setStyleSheet(
            f"""
            QStackedWidget {{
                background: {DT.C.BG_SECONDARY};
                border: none;
            }}
        """
        )
        self._init_pages()
        page_layout.addWidget(self._stack_widget)

        layout.addWidget(page_container, 1)

    def _init_pages(self) -> None:
        """初始化所有页面"""
        page_classes = [
            DashboardPage,
            RealtimeMonitorPage,
            AnalysisPage,
            TrendPage,
            AlarmPage,
            DevicePage,
            SettingsPage,
        ]

        for key, cls in zip(self.PAGE_KEYS, page_classes):
            page = cls(self)
            self._pages[key] = page
            self._stack_widget.addWidget(page)

        # 页面后初始化
        self._pages["device"].add_sample_devices()

        alarm_desc = "局放超限 - 幅值 85.3mV (85%), 等级: 严重报警"
        self._pages["alarm"].add_alarm(
            {
                "device_id": "DEV-001",
                "alarm_type": "pd_over_limit",
                "level": "critical",
                "amplitude": 85.3,
                "description": alarm_desc,
                "timestamp": __import__("time").time(),
            }
        )
        self._pages["alarm"].add_alarm(
            {
                "device_id": "DEV-002",
                "alarm_type": "device_offline",
                "level": "warning",
                "amplitude": 0,
                "description": "设备离线 - 设备状态异常",
                "timestamp": __import__("time").time() - 300,
            }
        )
        # 同步更新首页报警栏
        if "dashboard" in self._pages:
            self._pages["dashboard"].set_latest_alarm(alarm_desc)

    def _setup_status_bar(self) -> None:
        """创建状态栏"""
        status_bar = self.statusBar()
        status_bar.setStyleSheet(
            f"""
            QStatusBar {{
                background: {DT.C.BG_PRIMARY};
                border-top: 1px solid {DT.C.BORDER_DEFAULT};
                font-size: 12px;
                color: {DT.C.TEXT_TERTIARY};
                padding: 2px 8px;
            }}
        """
        )

        self._status_label = QLabel("系统就绪")
        self._status_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 12px;")
        status_bar.addWidget(self._status_label)

        self._page_label = QLabel("首页")
        self._page_label.setStyleSheet(f"color: {DT.C.TEXT_SECONDARY}; font-size: 12px; padding: 0 12px;")
        status_bar.addPermanentWidget(self._page_label)

        self._time_label = QLabel("")
        self._time_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 12px; padding: 0 8px;")
        status_bar.addPermanentWidget(self._time_label)

        # 时钟更新
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def _update_clock(self) -> None:
        """更新状态栏时钟"""
        from datetime import datetime

        self._time_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _update_status_bar(self) -> None:
        """更新状态栏信息"""
        from datetime import datetime

        self._status_label.setText(f"系统就绪 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def _on_nav_item_selected(self, key: str) -> None:
        """导航项选中处理"""
        self._navigate_to(key)

    def _navigate_to(self, key: str) -> None:
        """导航到指定页面"""
        if key in self._pages:
            idx = self.PAGE_KEYS.index(key)
            self._stack_widget.setCurrentIndex(idx)
            self._nav_menu.select_item(key)
            title = self.PAGE_TITLES[idx]
            self._page_label.setText(title)
            self._status_label.setText(f"当前页面: {title}")

    def _show_about(self) -> None:
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            f"<h3>{self.APP_NAME} v{self._version}</h3>"
            "<p>超高频（UHF）局部放电在线监测系统</p>"
            "<hr>"
            "<p><b>开发架构:</b> Python 全栈架构</p>"
            "<p><b>技术栈:</b> PySide6 · PyQtGraph · NumPy · SciPy · SQLAlchemy</p>"
            "<p><b>功能特性:</b></p>"
            "<ul>"
            "<li>实时波形监测 (20 FPS)</li>"
            "<li>PRPD / PRPS 图谱分析</li>"
            "<li>FFT 频谱分析</li>"
            "<li>趋势分析 (1h/24h/7d/30d)</li>"
            "<li>三级报警管理</li>"
            "<li>报表生成 (PDF/Excel)</li>"
            "</ul>"
            "<hr>"
            f"<p>© 2026 UHF-PD-Monitor Team</p>",
        )

    def closeEvent(self, event) -> None:
        """关闭时保存窗口状态"""
        from PySide6.QtCore import QSettings

        settings = QSettings("UHF-PD-Monitor", "PDMainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        logger.info("窗口状态已保存")
        super().closeEvent(event)

    @property
    def pages(self) -> dict:
        """获取页面字典（供控制器使用）"""
        return self._pages

    def set_controller(self, controller) -> None:
        """设置系统控制器"""
        self._controller = controller
