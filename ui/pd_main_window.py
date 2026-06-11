# -*- coding: utf-8 -*-
"""
UHF PD Monitor 主窗口

基于现有 MCGS_EMS 主窗口架构重构，保留 Fluent Design 风格：
- 左侧导航菜单（可折叠）
- 右侧页面栈
- 统一的状态栏和菜单栏
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

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

    CHANGELOG = [
        {
            "version": "v1.0.5",
            "date": "2026-06-10",
            "changes": [
                "新增：关于对话框重构，Tab式版本日志（关于页+更新日志页）",
                "新增：更新日志内嵌，CHANGELOG结构化存储，支持新增/优化/修复标签颜色区分",
                "新增：关于页展示最新版本更新内容",
                "优化：分类置信度计算，移除0.85硬性上限，改为直接使用最高占比类型投票率",
                "优化：冗余文档清理，删除CHANGELOG.md、docs/下16个旧文档等，减少12000+行冗余内容",
            ],
        },
        {
            "version": "v1.0.4",
            "date": "2026-06-10",
            "changes": [
                "新增：放电类型分类策略重设计（Profile Matching 替代规则引擎），8维特征+高斯核相似度+Softmax归一化",
                "新增：幅值分布特征（变异系数/双峰性/正半周能量比），增强类型区分能力",
                "新增：分析结果面板重构，参考结果卡片+类型统计表+幅值统计表，标记为参考结果",
                "新增：Bootstrap多次采样统计，50次有放回采样，各类型出现次数和占比",
                "新增：随机噪声(noise)识别与UI灰色显示",
                "优化：分析页面布局，幅值分布宽度与PRPD一致，分析结果高度扩展至底部",
                "优化：统一分类路径，移除classify_by_cycles，统一使用Bootstrap classify_cycles",
                "修复：DataImporter解包缺少cycles的ValueError",
            ],
        },
        {
            "version": "v1.0.3",
            "date": "2026-06-09",
            "changes": [
                "修复：热力图/密度图团簇方向错误，手动构建2D直方图+flipud修正ImageItem Y轴反转",
                "修复：Jet颜色映射注册，PyQtGraph无内置jet，改为模块级直接引用",
                "修复：_version崩溃，_show_about引用不存在的self._version",
                "修复：动态幅值范围扩展，峰值超80%时自动扩展至peak×1.2并重建矩阵",
                "修复：分析页面数据同步，添加缺失的set_max_amplitude调用",
                "优化：调用顺序修正，先update_scatter后update_heatmap",
                "优化：PRPS 3D散点图重构，替换为Matplotlib 3D懒加载+脏标记优化",
                "优化：完整坐标轴系统、ColorBar集成、视觉比例优化",
            ],
        },
        {
            "version": "v1.0.2",
            "date": "2026-06-05",
            "changes": [
                "新增：数据分析页面，导入CSV/Excel/TXT实验数据，PRPD图谱显示",
                "新增：放电类型自动分类（内部气隙/电晕/沿面/悬浮颗粒）",
                "新增：分类报告导出（JSON/Excel/Word）",
                "新增：PRPD三种显示模式（散点图/热力图/密度图）",
                "新增：文件拖放导入，自适应去噪和阈值过滤",
                "优化：系统设置页重构、报警管理页按钮重新排布、设备管理页布局调整",
                "修复：导航页索引偏移导致数据分析页不显示",
            ],
        },
        {
            "version": "v1.0.1",
            "date": "2026-06-03",
            "changes": [
                "新增：实时监测设备/通道切换下拉框",
                "新增：设备列表持久化（JSON保存/加载）",
                "优化：设置变更实时推送到运行中服务",
                "优化：PRPD/趋势list→deque、PRPS原地切片",
                "修复：报警统计卡片遮挡、报警数据同步",
            ],
        },
        {
            "version": "v1.0.0",
            "date": "2026-06-02",
            "changes": [
                "初始版本发布",
                "核心功能：实时波形20FPS、PRPD/FFT/PRPS分析",
                "核心功能：趋势分析(1h/24h/7d/30d)、三级报警管理",
                "核心功能：FPGA通信协议(TCP+UDP)、数据模拟器",
                "核心功能：Fluent Design界面、6个功能页面",
                "25个集成测试、PyInstaller打包",
            ],
        },
    ]

    def __init__(self, db_manager=None):
        super().__init__()

        self._db_manager = db_manager
        self._version = "1.0.5"
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
        """显示关于对话框（含切换更新日志）"""
        dialog = QDialog(self)
        dialog.setWindowTitle("关于")
        dialog.setMinimumSize(560, 500)
        dialog.setStyleSheet(
            f"QDialog {{ background: {DT.C.BG_PRIMARY}; }}"
            f"QLabel {{ color: {DT.C.TEXT_PRIMARY}; }}"
        )

        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(12)

        # ---------- 关于页内容 ----------
        about_widget = QWidget()
        about_layout = QVBoxLayout(about_widget)
        about_layout.setContentsMargins(0, 0, 0, 0)
        about_layout.setSpacing(12)

        # 图标 + 标题行
        header_row = QHBoxLayout()
        icon_label = QLabel()
        icon_path = "assets/icons/ems.png"
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            icon_label.setText("[ICON]")
        icon_label.setFixedSize(72, 72)
        header_row.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_label = QLabel(f"{self.APP_NAME}")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {DT.C.ACCENT_PRIMARY};")
        title_col.addWidget(title_label)

        version_label = QLabel(f"版本 {self._version}")
        version_label.setStyleSheet(f"color: {DT.C.TEXT_SECONDARY}; font-size: 13px;")
        title_col.addWidget(version_label)

        date_label = QLabel(f"构建日期: {self.CHANGELOG[0]['date']}")
        date_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 12px;")
        title_col.addWidget(date_label)

        header_row.addLayout(title_col)
        header_row.addStretch()
        about_layout.addLayout(header_row)

        # 分隔线
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {DT.C.BORDER_DEFAULT};")
        about_layout.addWidget(sep)

        # 描述
        desc_label = QLabel(
            "<p style='line-height:1.6;'>"
            "超高频（UHF）局部放电在线监测系统，"
            "实现电力设备局部放电信号的实时采集、图谱分析、趋势追踪与智能报警。"
            "</p>"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY}; font-size: 13px;")
        about_layout.addWidget(desc_label)

        # 最新版本更新日志
        latest = self.CHANGELOG[0]
        latest_html_parts = [
            f"<h4 style='margin:12px 0 4px 0; color:{DT.C.TEXT_PRIMARY};'>"
            f"{latest['version']} 更新内容"
            f"<span style='font-weight:normal;font-size:12px;color:{DT.C.TEXT_TERTIARY};margin-left:8px;'>{latest['date']}</span></h4>"
        ]
        latest_html_parts.append('<ul style="margin:4px 0 0 0;">')
        for change in latest["changes"]:
            if change.startswith("新增"):
                tag_color = "#34a853"
            elif change.startswith("优化"):
                tag_color = "#fbbc04"
            elif change.startswith("修复"):
                tag_color = "#ea4335"
            else:
                tag_color = DT.C.TEXT_SECONDARY
            tag, _, detail = change.partition("：")
            latest_html_parts.append(
                f'<li style="line-height:1.5;margin:2px 0;">'
                f'<span style="color:{tag_color};font-weight:bold;font-size:11px;">[{tag}]</span> '
                f'{detail}</li>'
            )
        latest_html_parts.append("</ul>")

        latest_label = QLabel("".join(latest_html_parts))
        latest_label.setWordWrap(True)
        latest_label.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY}; font-size: 12px;")
        about_layout.addWidget(latest_label)

        about_layout.addStretch()

        # ---------- 更新日志页内容 ----------
        changelog_widget = QWidget()
        changelog_layout = QVBoxLayout(changelog_widget)
        changelog_layout.setContentsMargins(0, 0, 0, 0)

        changelog_text = QTextEdit()
        changelog_text.setReadOnly(True)
        changelog_text.setStyleSheet(
            f"QTextEdit {{"
            f"  background: {DT.C.BG_SECONDARY};"
            f"  border: none;"
            f"  border-radius: {DT.R.SM}px;"
            f"  padding: 8px;"
            f"  color: {DT.C.TEXT_PRIMARY};"
            f"  font-size: 13px;"
            f"}}"
        )

        # 构建 HTML 格式更新日志
        html_parts = []
        for entry in self.CHANGELOG:
            html_parts.append(
                f"<h3 style='margin:16px 0 4px 0; color:{DT.C.TEXT_PRIMARY};'>{entry['version']}"
                f"<span style='font-weight:normal;font-size:12px;color:{DT.C.TEXT_TERTIARY};margin-left:8px;'>{entry['date']}</span></h3>"
            )
            html_parts.append('<ul style="margin:4px 0 8px 0;">')
            for change in entry["changes"]:
                if change.startswith("新增"):
                    tag_color = "#34a853"
                elif change.startswith("优化"):
                    tag_color = "#fbbc04"
                elif change.startswith("修复"):
                    tag_color = "#ea4335"
                else:
                    tag_color = DT.C.TEXT_SECONDARY
                tag, _, detail = change.partition("：")
                html_parts.append(
                    f'<li style="line-height:1.5;margin:2px 0;">'
                    f'<span style="color:{tag_color};font-weight:bold;font-size:11px;">[{tag}]</span> '
                    f'{detail}</li>'
                )
            html_parts.append("</ul>")

        changelog_text.setHtml("".join(html_parts))
        changelog_layout.addWidget(changelog_text)

        # ---------- 使用 QStackedWidget 切换 ----------
        stacked = QStackedWidget()
        stacked.addWidget(about_widget)       # index 0
        stacked.addWidget(changelog_widget)   # index 1
        main_layout.addWidget(stacked)

        # 底部按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        toggle_btn = QPushButton("更新日志")
        toggle_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; color: {DT.C.ACCENT_PRIMARY}; border: 1px solid {DT.C.ACCENT_PRIMARY};"
            f"  border-radius: {DT.R.SM}px; padding: 8px 24px; font-size: 13px;"
            f"}}"
            f"QPushButton:hover {{ background: {DT.C.BG_SECONDARY}; }}"
        )

        def _toggle_page():
            if stacked.currentIndex() == 0:
                stacked.setCurrentIndex(1)
                toggle_btn.setText("关于")
                dialog.setWindowTitle("更新日志")
            else:
                stacked.setCurrentIndex(0)
                toggle_btn.setText("更新日志")
                dialog.setWindowTitle("关于")

        toggle_btn.clicked.connect(_toggle_page)
        btn_row.addWidget(toggle_btn)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {DT.C.ACCENT_PRIMARY}; color: white; border: none;"
            f"  border-radius: {DT.R.SM}px; padding: 8px 24px; font-size: 13px;"
            f"}}"
            f"QPushButton:hover {{ background: {DT.C.ACCENT_HOVER}; }}"
        )
        close_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(close_btn)

        main_layout.addLayout(btn_row)

        dialog.exec()

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
