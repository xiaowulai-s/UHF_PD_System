# 工业设备监控与局放监测系统

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-green.svg)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

本工程包含两套独立的工业上位机系统，共用同一套 UI 组件库和基础架构：

| 系统 | 版本 | 入口 | 说明 |
|------|------|------|------|
| **MCGS 设备管理系统** | v2.1.0 | `main.py` | Modbus TCP/RTU 工业设备监控 |
| **UHF 局放监测系统** | v1.0.3 | `pd_main.py` | 超高频局部放电在线监测 |

---

# MCGS 设备管理系统 (Equipment Management System)

[![MCGS](https://img.shields.io/badge/MCGS-Modbus_TCP-integrationred.svg)](MCGS.md)

基于 **PySide6** 和 **Modbus 协议** 的工业设备上位机监控软件，采用 **四层解耦 + 服务化架构**，支持 **MCGS 触摸屏集成**、多设备并发管理、实时数据可视化和智能故障恢复。

> **v2.1.0** — 日志系统重构 (structlog 中文完美显示)、编码安全加固、连接失败日志去重、PBKDF2 密码升级、冗余文件清理

## 核心特性

### Modbus 通信

| 特性 | 说明 |
|------|------|
| **Modbus TCP** | 上位机作为 Client，MCGS 触摸屏作为 Server（Slave），端口 502 |
| **Modbus RTU** | 串口通信（RS485/RS232），TOCTOU 安全读取，CRC-16 校验 |
| **Modbus ASCII** | ASCII 编码串口通信，LRC 校验 |
| **批量寄存器读取** | 单次请求读取全部变量，高性能低延迟 |
| **4 种字节序** | ABCD（大端）/ BADC / CDAB / DCBA |
| **7 种数据类型** | uint16 / int16 / uint32 / int32 / float32 / bool / coil |

### 设备管理

- 多设备并发管理（支持 100+ 设备、20000+ 寄存器）
- 设备增删改查 + 搜索 + 批量操作
- JSON 配置持久化，端口信息完整保存
- 可配置自动重连（全局/设备级控制）
- 设备分组管理与分组轮询
- 设备模板管理（快速创建/克隆设备）
- 配置导入/导出（含版本兼容性检查）
- 协议插件注册表（运行时扩展新协议）

### 智能故障恢复

- **FaultRecoveryService** — 多模式故障恢复（指数退避 / 固定间隔 / 即时重试）
- 随机抖动防惊群（Jitter）
- 故障检测与诊断
- 恢复状态查询与统计分析

### 通信驱动

- **TCPDriver** — FC08 Modbus 诊断心跳（10s 间隔），TCP KeepAlive（10s/5s/3次），线程安全
- **SerialDriver** — TOCTOU 安全读取，混合/阻塞/非阻塞三种模式，自适应波特率超时
- **BaseDriver** — QMutex 缓冲区保护，统一信号接口

### 数据可视化

- **DataCard** — 数据卡片，实时值 + 状态 + 趋势
- **Gauge** — Canvas 仪表盘，弧形进度条
- **RealTimeChart** — pyqtgraph 高性能实时曲线图
- **DynamicMonitorPanel** — 动态监控面板，支持卡片布局自由编排
- **HistoryChartWidget** — 历史数据趋势图

### 报警系统

- 四级报警：信息 / 警告 / 错误 / 严重
- 四类阈值：高高(HH) / 高(H) / 低(L) / 低低(LL)
- 死区控制 + 冷却机制，防止报警风暴
- 8 种错误智能分类
- 报警确认 + 历史记录 + 统计分析

### UI 组件库

- **按钮系统**：PrimaryButton / SecondaryButton / SuccessButton / DangerButton / GhostButton
- **输入控件**：LineEdit / ComboBox / InputWithLabel / Checkbox
- **卡片组件**：DataCard / InfoCard / ActionCard
- **表格组件**：DeviceTree / DataTable / DeviceTable
- **状态组件**：StatusBadge / AnimatedStatusBadge
- **主题管理**：ThemeManager（Fluent Design 风格浅色主题）+ DesignTokens 设计令牌系统
- **动画调度**：AnimationScheduler（全局单定时器，CPU 占用降低 80%+）

## MCGS 系统架构

```
UI 层 (PySide6 Widgets)
    MainWindow + Controllers + Panels + Dialogs
    ├─ MCGSController (MCGS触摸屏通信)
    └─ MonitorPageController (监控页)
        ↓
设备管理层 (DeviceManagerFacade v4.0)
    Registry + Scheduler + Recovery + Configuration
    GroupManager + Lifecycle + DataPersistence
        ↓
通信驱动层
    TCPDriver / SerialDriver / BaseDriver
        ↓
协议层 (Modbus Protocol)
    TCP + RTU + ASCII + CRC-16 / LRC
    ByteOrderConfig + ProtocolRegistry
        ↓
数据总线 (DataBus v2.0) — 发布/订阅模式
        ↓
数据持久化层 (SQLite WAL)
    DatabaseManager + Repository + Services
    7 ORM Models + 5 Repositories
```

## 项目结构

```
├── main.py                     # MCGS 系统入口
├── config.json                 # MCGS 系统配置
├── config/devices.json         # MCGS 设备配置
├── core/
│   ├── communication/          # TCP/串口驱动
│   ├── protocols/              # Modbus 协议栈
│   ├── device/                 # 设备管理层 (v4.0)
│   │   ├── device_manager_facade.py
│   │   ├── polling_scheduler.py
│   │   ├── fault_recovery_service.py
│   │   └── ...
│   ├── engine/                 # 网关引擎
│   ├── data/                   # 数据库模型 + Repository
│   ├── services/               # MCGS 业务服务
│   ├── foundation/             # DataBus 事件总线
│   ├── plugins/                # 协议插件
│   └── utils/                  # 报警/权限/日志/导出
├── ui/
│   ├── main_window.py          # MCGS 主窗口
│   ├── controllers/            # 页面控制器
│   ├── dialogs/                # MCGS 配置对话框
│   ├── widgets/                # 组件库
│   └── panels/                 # 监控面板
└── tests/
```

## 安装与运行

```bash
pip install -e .

# 运行 MCGS 系统
python main.py
```

---

# UHF 局部放电在线监测系统 (UHF-PD-Monitor)

[![PyQtGraph](https://img.shields.io/badge/PyQtGraph-0.14%2B-green.svg)](https://pypi.org/project/pyqtgraph/)
[![NumPy](https://img.shields.io/badge/NumPy-1.24%2B-blue.svg)](https://numpy.org/)

基于 **PySide6 + PyQtGraph + NumPy** 的工业级超高频局部放电在线监测上位机软件。

> **v1.0.3** — 热力图/密度图团簇方向修复（手动直方图+flipud修正ImageItem Y轴反转）、Jet颜色映射注册、_version崩溃修复、动态幅值范围扩展、分析页面数据同步修复

## 核心特性

### 信号分析

| 模块 | 功能 | 性能 |
|------|------|------|
| **实时波形** | 缩放/拖拽/游标测量/自动量程/触发标记 | ≥20 FPS |
| **PRPD 图谱** | 散点图/热力图/密度图三种模式、相位分布分析 | ≥10 FPS |
| **FFT 频谱** | 峰值检测(含谐波识别)、频段统计(UHF四频段)、噪声估计、SNR | ≥10 FPS |
| **PRPS 图谱** | 3D 散点图（Matplotlib）、512×360 周期脉冲序列、完整坐标轴+ColorBar | 实时 |
| **趋势分析** | 1h/24h/7d/30d 多时间维度、多指标叠加 | 实时 |

### 报警管理

- **三级报警体系**：严重(≥80%) / 一般(≥50%) / 提示(≥30%)
- **六种报警类型**：局放超限 / 设备离线 / 光模块异常 / ADC异常 / 同步异常 / 存储不足
- **防抖机制**：连续 N 次触发确认报警，消除误报
- 报警事件列表 + 统计 + 规则配置 + 确认
- 报警持久化到 SQLite 数据库

### FPGA 通信协议

```
数据帧格式:
┌──────┬──────┬────────┬────────┬──────────┬────────┬──────────┬──────┐
│ 帧头 │ 长度 │ 设备ID │ 通道ID │ 时间戳   │数据类型│ 数据内容 │ CRC  │
│ 2Byte│ 2Byte│ 2Byte  │ 2Byte  │ 8Byte    │ 1Byte  │ N Byte   │ 2Byte│
└──────┴──────┴────────┴────────┴──────────┴────────┴──────────┴──────┘

数据类型:
0x01 WAVEFORM    波形数据      TCP 端口 5000: 控制通道
0x02 PD_EVENT    局放事件      UDP 端口 6000: 数据通道
0x03 FFT_RESULT  FFT 频谱      CRC-16/MODBUS 校验
0x04 PRPD_RESULT PRPD 图谱
0x05 PRPS_RESULT PRPS 图谱
0x06 DEVICE_STATUS 设备状态
```

### 数据处理 Pipeline

```
UDP 接收 → FpgaProtocol.feed() → 波形数据
                                    ↓
                          ┌─ 峰值检测 → DataBus(PD事件)
                          ├─ FFT计算  → DataBus(FFT)
                          ├─ PRPD更新 → DataBus(PRPD)  (指数衰减)
                          └─ PRPS更新 → DataBus(PRPS)
```

### 信号处理算法

| 模块 | 算法 | 说明 |
|------|------|------|
| **FFTProcessor** | numpy.rfft + scipy.signal.find_peaks | 频谱计算、峰值检测、频段统计、SNR |
| **PRPDProcessor** | 360×256 相位-幅值矩阵 | 散点/热力/密度、指数衰减、统计特征 |
| **PRPSProcessor** | 512×360 滚动矩阵 | 周期脉冲序列、滑动平均 PRPD |
| **PeakDetector** | scipy 自适应阈值 / 简化模式 | 脉冲参数(幅值/宽度/面积/能量/SNR) |
| **RingBuffer** | collections.deque | 1,000,000 点线程安全环形缓冲 |

### 模拟器（无需 FPGA）

内置四种局放类型的波形模拟器，支持可调参数：

```bash
# 电晕放电 (270°~330° 负半周集中)
python pd_main.py --simulator --pd-type corona

# 沿面放电 (30°~90° 正半周集中)
python pd_main.py --simulator --pd-type surface

# 内部放电 (0°~60° 正半周初期)
python pd_main.py --simulator --pd-type internal

# 悬浮放电 (0°~360° 全相位分布)
python pd_main.py --simulator --pd-type floating
```

### 系统架构

```
┌─────────────────────────────────────────────────┐
│                  UI 层 (PySide6)                  │
│  ┌──────────┬──────────┬──────────┬──────────┐   │
│  │ 仪表板   │ 实时监测  │ 趋势分析  │ 报警管理  │   │
│  ├──────────┼──────────┼──────────┼──────────┤   │
│  │ 设备管理  │ 系统设置  │          │          │   │
│  └──────────┴──────────┴──────────┴──────────┘   │
├─────────────────────────────────────────────────┤
│               控制器层 (Coordinator)              │
│          PDSystemController                      │
│    ┌──────────────────────────────────────┐      │
│    │          PDDataBus 事件总线           │      │
│    └──────────────────────────────────────┘      │
├─────────────────────────────────────────────────┤
│              服务层 (Services)                    │
│  AcquisitionService  PDAlarmService              │
│  PDStorageService                                │
├─────────────────────────────────────────────────┤
│              通信层 (Communication)               │
│  FpgaProtocol  UDPDriver  TCPDriver              │
├─────────────────────────────────────────────────┤
│              信号处理 (Processing)                │
│  RingBuffer  FFTProcessor  PRPDProcessor         │
│  PRPSProcessor  PeakDetector                     │
└─────────────────────────────────────────────────┘
```

### 项目结构

```
├── pd_main.py                     # PD 系统入口
├── pd_build.spec                  # PyInstaller 打包配置
├── core/
│   ├── processing/                # 信号处理核心
│   │   ├── fft_processor.py       # FFT 频谱分析
│   │   ├── prpd_processor.py      # PRPD 图谱
│   │   ├── prps_processor.py      # PRPS 图谱
│   │   ├── peak_detector.py       # 峰值检测
│   │   └── ring_buffer.py         # 环形缓冲区
│   ├── communication/             # FPGA 通信
│   │   ├── fpga_protocol.py       # 协议解析器
│   │   └── udp_driver.py          # UDP 数据通道
│   ├── services/                  # PD 业务服务
│   │   ├── pd_acquisition_service.py  # 采集服务
│   │   ├── pd_alarm_service.py       # 报警服务
│   │   └── pd_storage_service.py     # 存储服务
│   ├── data/pd_models.py          # PD 数据库模型
│   └── foundation/pd_data_bus.py  # PD 事件总线
├── ui/
│   ├── pd_main_window.py          # PD 主窗口
│   ├── pd_controller.py           # 系统总控制器
│   ├── pages/                     # 6 个功能页面
│   │   ├── dashboard_page.py      # 系统仪表板
│   │   ├── realtime_monitor_page.py # 实时监测
│   │   ├── trend_page.py          # 趋势分析
│   │   ├── alarm_page.py          # 报警管理
│   │   ├── device_page.py         # 设备管理
│   │   └── settings_page.py       # 系统设置
│   └── widgets/                   # 分析控件
│       ├── waveform_widget.py     # 实时波形控件
│       ├── prpd_widget.py         # PRPD 图谱控件
│       ├── prps_widget.py         # PRPS 图谱控件
│       ├── fft_widget.py          # FFT 频谱控件
│       └── trend_chart_widget.py  # 趋势曲线控件
├── config/pd_default_config.json  # PD 系统配置
└── tests/test_pd_integration.py   # 25 个集成测试
```

## 安装与运行

```bash
# 安装基础依赖
pip install -e .

# 安装可选依赖（推荐: scipy+OpenGL）
pip install -e ".[full]"

# 运行 PD 监测系统（需 FPGA 硬件）
python pd_main.py

# 模拟器模式（自动生成局放数据，无需硬件）
python pd_main.py --simulator
```

---

# 共同基础架构

## 设计令牌系统 (DesignTokens)

Fluent Design 风格统一 UI 规范：

| 令牌 | 值 | 用途 |
|------|-----|------|
| 主色 | `#0969DA` | 按钮/选中态/链接 |
| 成功 | `#1A7F37` | 在线/正常 |
| 警告 | `#D29922` | 一般报警 |
| 错误 | `#CF222E` | 严重报警/错误 |
| 字体 | Segoe UI Variable | Windows 11 默认 |
| 间距 | 4px 基数的 8pt 栅格 | 统一间距 |
| 圆角 | 8px (标准) / 12px (卡片) | 统一圆角 |

## 数据库

| 系统 | 数据库 | 表数量 | ORM |
|------|--------|--------|-----|
| MCGS | `data/equipment_management.db` | 7 表 | SQLAlchemy |
| PD | `data/pd_monitor.db` | 5 表 | SQLAlchemy |

## 测试

```bash
# MCGS 测试
pytest tests/ -v

# PD 集成测试（25 个用例）
pytest tests/test_pd_integration.py -v
```

---

# 版本历史

## MCGS 系统

### v2.1.0 (2026-05-19)
- 日志系统重构 (structlog 中文完美显示)
- 编码安全加固、连接失败日志去重
- PBKDF2 密码升级、冗余文件清理

## PD 系统

### v1.0.3 (2026-06-09)
- **热力图/密度图 axes 修复**：`ImageItem(axisOrder='row-major')` 解决团簇横向展开问题，与散点图方向一致
- **PRPS 3D 散点图重构**：移除 pyqtgraph.opengl 实现（~500 行），替换为 Matplotlib 3D
- **完整坐标轴系统**：X(相位°)/Y(工频周期n)/Z(放电量) 三轴标签+刻度+网格
- **ColorBar 集成**：Matplotlib 原生 colorbar（Jet 色图，Discharge a.u.）
- **视觉比例优化**：`box_aspect=(1.45, 1.15, 1.20)`，视角 `elev=36°, azim=-122°`
- **布局优化**：散点放大(s=25)、色条填充(shrink=0.88)、边距自适应防截断
- **Z 轴标签纵向显示**：沿坐标轴方向旋转 90°
- **ColorBar 叠加 bug 修复**：`fig.clear()` 替代 `ax.clear()`
- 移除冗余标题 "PRPS Pattern"
- 代码量精简：949 行 → 456 行（减少 52%）

### v1.0.2 (2026-06-05)
- 新增数据分析页面：导入 CSV/Excel/TXT 实验数据，PRPD 图谱显示
- 新增放电类型自动分类：内部气隙/电晕/沿面/悬浮颗粒（基于 6 扇区能量分布+规则引擎）
- 新增分类报告导出：JSON/Excel/Word
- 新增 PRPD 三种显示模式（散点图/热力图/密度图）并修复模式切换问题
- 新增文件拖放导入，自适应去噪和阈值过滤
- UI 布局优化：系统设置页重构、报警管理页按钮重新排布、设备管理页布局调整
- 修复导航页索引偏移导致数据分析页不显示的问题

### v1.0.1 (2026-06-03)
- 实时监测新增设备/通道切换下拉框
- 报警统计卡片遮挡修复、报警数据同步修复
- 设备列表持久化（JSON 保存/加载）
- 设置变更实时推送到运行中服务
- 性能优化：PRPD/趋势 list → deque、PRPS 原地切片
- OpenGL 加速、窗口状态持久化

### v1.0.0 (2026-06-02)
- 初始版本：实时波形 20FPS、PRPD/FFT/PRPS 分析
- 趋势分析 (1h/24h/7d/30d)、三级报警管理
- FPGA 通信协议 (TCP+UDP)、数据模拟器
- Fluent Design 界面、6 个功能页面
- 25 个集成测试、PyInstaller 打包

---

## License

MIT License

---

**MCGS 系统**: v2.1.0 | **PD 系统**: v1.0.3 | **更新**: 2026-06-09
