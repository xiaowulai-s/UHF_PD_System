## 程序问题清单（待解决）

> 审查日期: 2026-06-10 | 基准版本: v1.0.5
> 第一轮审查共 34 个问题，**29 个已解决**归档；第二轮全工程审查新增 **25 个问题**；v1.0.5 UI 审计新增 **26 个布局问题**。
> **当前待解决: 56 个**（上轮遗留 30 + 本轮UI审计新增 26）

---

## v1.0.5 已完成变更

| 变更类型 | 内容 | 位置 |
|---------|------|------|
| 新增 | 程序图标整理，`ems.png` 移至 `assets/icons/` 并设置相对路径 | `pd_main.py` |
| 新增 | "关于"对话框重构，QStackedWidget 单窗口切换关于/更新日志，底部切换按钮+关闭按钮 | `pd_main_window.py` |
| 新增 | CHANGELOG 结构化存储，颜色区分新增/优化/修复分类 | `pd_main_window.py` |
| 新增 | 关于页展示最新版本更新内容，更新日志页展示全部版本历史 | `pd_main_window.py` |
| 优化 | 分类置信度计算，移除 0.85 硬性上限，改为直接使用最高占比类型投票率 | `analysis_page.py` |
| 优化 | 冗余文档清理，删除 CHANGELOG.md、docs/ 下 16 个旧文档、issue_list.md 等，减少 12000+ 行 | 多文件 |
| 修复 | DT 常量引用错误（`DT.C.ACCENT`/`DT.C.BORDER` → 正确名称 `DT.C.ACCENT_PRIMARY`/`DT.C.BORDER_DEFAULT`） | `pd_main_window.py` |
| 审计 | 全面审计 PD 子系统所有 UI 文件，识别出 26 个布局问题（critical 2 / major 9 / minor 15）| 所有 UI 文件 |

---

## P0 — 必须立即修复（严重 Bug / 安全风险 / 运行时崩溃）

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 8 | **硬编码弱默认密码** | `permission_manager.py` L293-308 | 默认账户密码明文硬编码：`admin123`/`operator123`/`viewer123`。任何能访问代码仓库的人均可获取管理员权限。且 `_load_default_users()` 不检查是否已有数据库用户就直接添加。应改为环境变量或加密配置文件读取，首次启动强制修改。 |
| 9 | **SQL 注入风险 — 表名/列名拼入 SQL 字符串** | `data_archive_service.py` L168,171 | `cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {time_col} < ?", ...)` — 表名和列名直接 f-string 拼接。虽当前来源为内部常量，但违反防御性编程原则。应使用白名单校验或断言校验。 |
| 10 | **裸 `except: pass` 吞掉关键异常导致数据静默丢失** | `data_archive_service.py` L173 | 数据归档失败时完全静默（`except Exception: pass`），运维人员无法感知数据丢失。同模式出现在 `history_storage.py` 等多处。至少应记录 `logger.warning()`。 |
| — | ~~11 **`_show_about()` 引用不存在的 `_version` 属性，点击崩溃**~~ | ~~`pd_main_window.py`~~ | ✅ **已修复** (v1.0.5): `__init__` 中新增 `self._version = "1.0.5"`，同时完全重写了 `_show_about()` 方法。 |
| 12 | **DesignTokens 颜色值缺少 `#` 前缀** | `design_tokens.py` L65 | `DEVICE_WARNING = "D29922"` 缺少 `#` 号（其他颜色如 `DEVICE_ONLINE = "#2DA44E"` 格式正确）。使用该常量设置样式会导致 CSS 解析错误，设备警告状态颜色渲染异常。 |

---

## P1 — 应当修复（线程安全 / 资源泄漏 / 潜在崩溃 / 数据质量）

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 13 | **`pd_controller.py` 中 6+ 处裸 `except: pass` 吞掉 UI 异常** | `pd_controller.py` L205,214,243,250,267,273,300 | 波形/FFT/PRPD/PRPS 更新回调全部 `except Exception: pass`，数据处理管线任何异常都被静默忽略，UI 卡死或显示陈旧数据时无法排查。应替换为 `logger.debug()` 或 `logger.exception()`。 |
| 14 | **`PRPDProcessor.add_waveform()` 每帧新建 PeakDetector 实例** | `prpd_processor.py` L169 | 20 FPS 场景下每秒创建 20 个临时 `PeakDetector` 对象，造成不必要的 GC 压力。应将 detector 作为成员变量在 `__init__` 中创建一次并复用。 |
| 15 | **`RingBuffer.get_range()` 全量复制再切片** | `ring_buffer.py` L65-75 | `list(self._buffer)[start:end]` — 缓冲区接近 1,000,000 点时即使只取 1000 点也先复制整个 deque。应改用 `itertools.islice()`。 |
| 16 | **UDPDriver 统计字段无线程保护** | `udp_driver.py` L231-242 | `_packets_received`/`_bytes_received` 在接收线程写入、主线程读取，无原子性保证。应加锁或用 `threading.Event` 保护。 |
| 17 | **`PDSimulator.stop()` 不等待线程退出** | `pd_simulator.py` L191-194 | 仅设 `_is_running = False` 标志位，无 `thread.join()`。快速 restart 可能导致双线程同时运行，数据总线收到双倍事件。应添加 `join(timeout=2.0)`。 |
| 18 | **`FFTWidget.clear()` 可能抛 AttributeError** | `fft_widget.py` L326-332 | `self._peak_table.setRowCount(0)` — 当 `show_peak_list=False` 时 `_peak_table` 未创建，调用 `.clear()` 会崩溃。应改为 `hasattr` 判断或在 `__init__` 中始终创建控件仅隐藏。 |
| 19 | **趋势数据幅值/能量字段写死为 0** | `pd_acquisition_service.py` L177-189 | `store_trend_data(...)` 中 `max_amplitude=0, avg_amplitude=0, total_energy=0, noise_level=0` 全部硬编码零。趋势图表永远显示平坦线，失去监控价值。应从波形或峰值检测结果提取真实值。 |
| 20 | **SerialDriver 接收循环 use-after-free 竞态** | `serial_driver.py` L153-172 | 获取 `local_serial` 引用后释放锁，后续操作可能在已关闭串口上执行。`disconnect()` 可在 `is_open` 检查后关闭串口。应捕获 `SerialException` 区分正常关闭与异常。 |
| 21 | **`history_storage.py` 大量 f-string 动态拼接 SQL** | `history_storage.py` L108,126,146,189 | 表名和列名全部 f-string 拼入 SQL，与项目 ORM 风格不一致，维护风险高。应迁移到 SQLAlchemy 或参数化白名单校验。 |

---

## P2 — 建议优化（代码质量 / 架构改进 / 性能）

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 22 | **多个 Widget 重复调用 `pg.setConfigOptions()` 覆盖全局配置** | `prpd_widget.py` L38, `prps_widget.py` L26, `waveform_widget.py` L28, `fft_widget.py` L37 | 每个控件文件模块加载时都调用全局配置，后面的覆盖前面的（如 waveform 设了 background 但 prpd 没有）。应在入口统一调用一次。 |
| 23 | **`_waveform_frame_count` 使用 `getattr` 惰性初始化** | `pd_controller.py` L211 | `getattr(self, "_waveform_frame_count", 0)` 而非在 `__init__` 中声明，降低可读性且 IDE 无法推断类型。 |
| 24 | **PRPS 前 5 周期 autoLevels 导致色阶跳变闪烁** | `prps_widget.py` L140-143 | `autoLevels=(self._cycle_count < 5)` — 前 5 周期自动调整色阶后固定，初始阶段亮度/对比度突然变化产生视觉"闪烁"。应用首帧基线色阶后固定。 |
| 25 | **DatabaseManager 单例缓存无过期/清理机制** | `models.py` L410-420 | 类变量级全局字典缓存所有实例，测试间可能互相污染，多数据库路径场景内存持续增长。考虑 `WeakValueDictionary` 或 LRU 淘汰。 |
| 26 | **内联 `__import__("time")` 替代正常 import** | `pd_main_window.py` L194,204; `pd_data_bus.py` L72 | 为获取时间戳/线程锁使用 `__import__()` 而非文件顶部 import，影响可读性和调试。应移至文件顶部正常导入。 |
| 27 | **pyproject.toml coverage 配置指向不存在的 `src/` 路径** | `pyproject.toml` L83-84 | `source = ["src"]` 但项目无 `src/` 目录，coverage 报告 0% 覆盖率。应改为 `source = ["core", "ui"]`。 |
| 28 | **AsyncDatabaseLogHandler 队列满时 ERROR 级别日志也可能被丢弃** | `logger.py` L93-101 | LIFO 式丢弃策略（丢最旧换最新）不区分日志级别，CRITICAL 日志也可能被丢弃。应对高优先级日志采用阻塞 put 或独立队列。 |
| 29 | **FpgaProtocol 帧头搜索 O(n) 逐字节扫描** | `fpga_protocol.py` L239-244 | Python 循环逐字节找 `0xA5A5`，高速 UDP 场景下缓冲区大时性能差。应改用 `buf.find(b'\xA5\xA5')`（C 层实现快数十倍）。 |
| 30 | **main.py 与 pd_main.py 功能重叠但无代码复用** | `main.py` vs `pd_main.py` | 两入口初始化流程几乎相同但实现细节不一致（窗口类不同、功能集不同）。维护时易遗漏同步更新。应抽取公共初始化库。 |
| 31 | **TCPDriver 心跳定时器跨线程延迟启动** | `tcp_driver.py` L128-133 | 非 main_thread 调用 connect() 时心跳定时器延迟到下一事件循环才启动，期间无保活可能导致连接断开。应要求 connect() 必须在主线程调用或用 invokeMethod 安全启动。 |

---

## 上轮遗留问题（第一轮审查发现，尚未解决）

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 1 | **`waveforms_processed` 全局计数器跨通道** | `pd_acquisition_service.py` L287 | PRPD 发布触发条件使用全局计数器，多设备/多通道场景下某通道发布频率受其他通道影响。应改为按通道独立计数触发发布。 |
| 2 | **PRPS 相位映射过于简单** | `pd_acquisition_service.py` L299-301 | 将峰值位置线性映射到相位，实际波形可能跨越多个工频周期，需外部同步信号辅助对齐。 |
| 3 | **3D 渲染在主线程执行** | `prpd_widget.py` L394 | Matplotlib 3D 渲染在主线程，>5000 点时可能短暂卡顿。可考虑工作线程渲染后交换 buffer。 |
| 4 | **Matplotlib Canvas 启动即创建** | `prpd_widget.py` L195-197 | 即使从未切换到 3D 模式也占用资源。可改为首次切换时懒加载。 |
| 5 | **2D 散点模式下不缓存 3D 数据** | `prpd_widget.py` L244-246 | 非 3D 模式下不更新 3D 缓存数据，切换到 3D 后需等下次数据更新才显示。建议任何模式都更新缓存。 |
| 6 | **2D/3D 颜色映射不一致** | `prpd_widget.py` L78-79 | 2D 用 viridis，3D 用 jet，同一控件视觉跳跃大。建议统一 colormap。 |
| 7 | **事件计数语义不一致** | `prpd_widget.py` L227 vs L242 | heatmap 显示矩阵总和，scatter 显示事件数，共用同一 label 切换时数字跳变。建议区分文案。 |

---

## 已解决的问题归档（27/34）

> 以下问题已在 v1.0.3 版本中修复，留档备查。

### 3D 散点图渲染核心（11 项已修复）

| # | 原问题 | 修复方式 |
|---|--------|----------|
| ~~1~~ | 每次 `fig.clear()` 全量重建 axes/colorbar | 改为增量更新：首次 `_setup_3d_axes()` 初始化，后续仅 `scatter.remove()` + 重绘散点 + `colorbar.update_normal()` |
| ~~2~~ | 散点周期是人为模拟的（无真实周期号） | 新增 `_scatter_cycles` 字段，`update_scatter(cycles=)` 接受真实周期；有真实周期时使用与 plot_PRPS.py 一致的公式 |
| ~~3~~ | 热力图回退双路径幅值计算混乱 | 统一为单路径：从 `self._heatmap_data > 0` 取非零 bin 中心坐标 + 抖动 |
| ~~5~~ | `subplots_adjust()` 与 `tight_layout()` 冲突 | 移除 `tight_layout()`，仅保留 `subplots_adjust(left=0.08, right=0.92, ...)` |
| ~~6~~ | ColorBar `shrink=0.88` 偏大 | 改为 `shrink=0.74`，与 plot_PRPS.py 一致 |
| ~~7~~ | ColorBar 标签英文 "Discharge (a.u.)" | 改为中文 `"放电量"` |
| ~~8~~ | 散点大小 `s=25` 过大 | 改为 `s=18`，与 plot_PRPS.py 一致 |
| ~~9~~ | Z轴 `set_rotation(90)` 无效操作 | 移除此行代码 |
| ~~10~~ | `print()` 调试语句残留 | 替换为 `logger.debug()` |
| ~~35~~ | **ImageItem axisOrder 默认 col-major 导致热力图/密度图 axes 颠倒** | `pg.ImageItem(axisOrder='row-major')` 使 `img[幅值][相位]` → `(Y, X)`，团簇方向与散点图一致 |
| ~~36~~ | **`np.flipud` 残留导致 Y 轴二次反转** | 移除 `update_heatmap` 中两处 `np.flipud`（axisOrder='col-major' 时期的补偿，'row-major' 下无需反转） |

### 数据管线问题（4 项已修复）

| # | 原问题 | 修复方式 |
|---|--------|----------|
| ~~11~~ | PRPD 散点数据未传递到 UI（3D 无真实数据） | pd_controller 新增 `update_scatter(evt_phases, evt_amps, evt_cycles)` 调用 |
| ~~12~~ | PRPS 数据错误发给 PRPD 控件 | 改为检查 `_prps` 控件存在性，调用 `update_from_prps_processor()` |
| ~~13~~ | PRPS 每帧发布无节流 | 新增 `_prps_publish_interval=10` + 按通道 `_prps_frame_count` 节流 |
| ~~14~~ | 外部直接访问 `_matrix` 做衰减 | 改为调用 `prpd_proc.decay(factor)` 公开方法 |

### 架构与设计问题（5 项已修复）

| # | 原问题 | 修复方式 |
|---|--------|----------|
| ~~19~~ | 枚举值与 `_display_mode` 字符串不一致 | 统一使用 `mode.value`（小写字符串），比较逻辑一致 |
| ~~21~~ | `_on_reset` 不重置 3D 状态 | 新增清除 `_scatter_cycles`、`_mpl_ax.clear()`、`_3d_initialized=False`、`_mpl_scatter=None`、`_mpl_colorbar=None` |
| ~~22~~ | PRPDProcessor 淘汰事件浮点索引漂移 | 移除手动减 1 逻辑，统一由 `decay()` 指数衰减处理过期数据 |
| ~~23~~ | 3D 视角每次数据更新被重置 | 连接鼠标 release 事件保存 `elev`/`azim`，后续更新使用保存值 |
| ~~28~~ | `_view_stack` 重复初始化 None | 移除 `__init__` 中的冗余赋值 |

### UI/交互问题（4 项已修复）

| # | 原问题 | 修复方式 |
|---|--------|----------|
| ~~24~~ | 切换到 3D 模式时数据延迟 | 通过 #11 修复（散点数据实时传递），heatmap 回退路径也可用 |
| ~~27~~ | 模式 combo 默认选中索引可能错位 | 改用 `findData(HEATMAP.value)` 精确查找索引 |
| ~~29~~ | `_image_transform` 声明未使用 | 已移除该变量 |
| ~~34~~ | cycle_local 计算与 plot_PRPS.py 不一致 | 有真实周期时采用 `((cycles - 1) % 50) + 1` 公式，完全一致 |

### 代码质量 / 小问题（4 项已修复）

| # | 原问题 | 修复方式 |
|---|--------|----------|
| ~~30~~ | analysis_page.py 导入 ImageGrab 未使用 | 已移除该导入 |
| ~~31~~ | _make_result_card 孤儿 QLabel | 两处 QLabel 均通过 `cl.addWidget()` 加入布局 |
| ~~32~~ | append_cycle_data 每次 autoLevels=True | 改为 `autoLevels=(self._cycle_count < 5)`，前 5 次后固定色阶 |
| ~~33~~ | DischargeClassifier 噪声阈值可能为 0 | 新增 `min_noise_threshold = max(1.0, ...)` 保底值 |

---

## UI 布局审计（v1.0.5 新增，26 个问题）

> 审查日期: 2026-06-10 | 审计范围: PD 子系统所有 UI 文件（16 个）
> 问题按严重程度分类：critical（2）/ major（9）/ minor（15），用户要求暂不修复。

### Critical（2 个 — 界面功能异常）

| # | 问题 | 位置 |
|---|------|------|
| C1 | `dashboard_page.py` 中 `c.addWidget(lbl)` 重复调用两次，导致卡片统计标签被添加两次 | `pages/dashboard_page.py` |
| C2 | `device_page.py` 编辑设备对话框缺少输入验证，空字符串保存导致界面异常 | `pages/device_page.py` |

### Major（9 个 — 布局结构 / 响应式 / 一致性）

| # | 问题 | 位置 |
|---|------|------|
| M1 | 实时监测页波形/PRPD/PRPS/FFT 四个卡片无统一最小高度约束，窗口缩小时比例失调 | `pages/realtime_monitor_page.py` |
| M2 | 趋势分析页图表区域无弹性伸缩策略，全屏时图表不跟随扩展 | `pages/trend_page.py` |
| M3 | 分析页面左右面板比例固定（60:40），无 QSplitter 可拖拽分割 | `pages/analysis_page.py` |
| M4 | 导航菜单折叠状态下 ToolTip 缺失，用户无法识别折叠后的图标对应页面 | `widgets/nav_menu.py` |
| M5 | 设置页采用 QScrollArea 包裹但内部控件宽度未设 100%，右侧出现空白 | `pages/settings_page.py` |
| M6 | 报警页表格列宽固定为绝对值（px），高分屏下列宽过窄 | `pages/alarm_page.py` |
| M7 | 设备管理页设备卡片网格无响应式列数（固定 3 列），窄屏下卡片挤压 | `pages/device_page.py` |
| M8 | 仪表板首页卡片布局使用硬编码 `setFixedSize`，不同分辨率视觉效果不一致 | `pages/dashboard_page.py` |
| M9 | 多个页面使用 `setMinimumSize` 硬编码最小尺寸，未适配 1366×768 低分屏 | 多个页面 |

### Minor（15 个 — 对齐 / 间距 / 视觉细节）

| # | 问题 | 位置 |
|---|------|------|
| m1 | PRPD 控制栏（模式切换/色阶等）与图表区域间距不一致 | `widgets/prpd_widget.py` |
| m2 | 波形图控件 Y 轴标签未设置固定宽度，数值变化时水平抖动 | `widgets/waveform_widget.py` |
| m3 | FFT 频谱图 X 轴刻度标签过于密集（默认自适应），高频段标签重叠 | `widgets/fft_widget.py` |
| m4 | PRPS 相位图 ColorBar 标签字号固定，与图表区域比例不协调 | `widgets/prps_widget.py` |
| m5 | 趋势图表 X 轴时间格式在不同时间跨度下未动态调整（如天/时/分） | `widgets/trend_chart_widget.py` |
| m6 | 状态栏设备信息文字无 Elide 模式，长设备名溢出遮挡 | `pd_main_window.py` |
| m7 | 菜单栏动作无图标（纯文字），视觉重量偏轻 | `pd_main_window.py` |
| m8 | 各页面顶部标题栏风格不统一（部分用 QLabel，部分无标题） | 多个页面 |
| m9 | 报警确认/重置按钮尺寸不统一，与表格行高不匹配 | `pages/alarm_page.py` |
| m10 | 设置页面 switch/toggle 控件与标签未在同一基线对齐 | `pages/settings_page.py` |
| m11 | 分析页面导入按钮与下拉选择器高度不一致 | `pages/analysis_page.py` |
| m12 | 仪表板卡片使用纯色背景，无阴影/边框层次感 | `pages/dashboard_page.py` |
| m13 | 趋势分析页过滤器区域控件间距过大，浪费纵向空间 | `pages/trend_page.py` |
| m14 | 实时监测页信息栏标签/数值未使用等宽字体，数值变化时整行抖动 | `pages/realtime_monitor_page.py` |
| m15 | 多个控件 `setStyleSheet` 内联颜色值而非使用 DT 设计令牌 | 多个文件 |

---

## 统计总览

| 严重程度 | 数量 | 主要类别 |
|---------|------|---------|
| **P0 必须立即修复** | 4 | 安全风险(2)、运行时崩溃(0→含#11已修复)、UI缺陷(1→DEVICE_WARNING) |
| **P1 应当修复** | 9 | 线程安全(3)、资源泄漏(1)、潜在崩溃(2)、代码质量(1)、数据质量(1)、SQL安全(1) |
| **P2 建议优化** | 10 | 性能(2)、架构(2)、代码质量(4)、兼容性(1)、配置(1) |
| **上轮遗留** | 7 | 数据管线(2)、架构(3)、UI(2) |
| **UI审计新增 (v1.0.5)** | 26 | Critical(2)、Major(9)、Minor(15) |
| **合计待解决** | **56** | |
| **已解决归档** | **30** | (+1: #11 _version 崩溃修复) |
| **累计发现问题** | **86** | |
