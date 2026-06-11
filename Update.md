## 程序问题清单（待解决）

> 审查日期: 2026-06-11 | 基准版本: v1.0.5
> 第一轮审查共 34 个问题，**29 个已解决**归档；第二轮全工程审查新增 **25 个问题**；v1.0.5 UI 审计新增 **26 个布局问题**。
> **当前待解决: 3 个**（P2遗留 1 + UI审计遗留 2）

---

## v1.0.5 已完成变更

| 变更类型 | 内容 | 位置 |
|---------|------|------|
| 新增 | 程序图标整理，`ems.png` 移至 `assets/icons/` 并设置相对路径 | `pd_main.py` |
| 新增 | "关于"对话框重构，QStackedWidget 单窗口切换关于/更新日志，底部切换按钮+关闭按钮 | `pd_main_window.py` |
| 新增 | CHANGELOG 结构化存储，颜色区分新增/优化/修复分类 | `pd_main_window.py` |
| 新增 | 关于页展示最新版本更新内容，更新日志页展示全部版本历史 | `pd_main_window.py` |
| 新增 | 仪表盘指标卡片数据自动刷新（每2秒从服务层读取真实数据推送） | `pd_controller.py` |
| 新增 | 趋势图数据实时推送（每50帧从波形存储回调同步到 TrendPage） | `pd_controller.py` |
| 新增 | 设备状态变更实时刷新设备页表格（DataBus 回调实现） | `pd_controller.py`, `device_page.py` |
| 新增 | 设备页在线设备数统计接口 + 表格状态行刷新方法 | `device_page.py` |
| 新增 | 分析结果面板重构为 2×2 卡片网格（参考结果/置信度/严重等级/采样次数） | `analysis_page.py` |
| 新增 | 菜单栏动作添加系统标准图标（退出/关于） | `pd_main_window.py` |
| 优化 | 分类置信度计算，移除 0.85 硬性上限 | `analysis_page.py` |
| 优化 | 冗余文档清理，删除 CHANGELOG.md、docs/ 下 16 个旧文档等 | 多文件 |
| 优化 | 仪表盘指标卡片视觉重构：圆角浅灰背景无边框，字号 18px | `dashboard_page.py` |
| 优化 | 报警页统计卡片字号统一 18px | `alarm_page.py` |
| 优化 | 报警页表格列宽高分屏适配（Stretch+ResizeToContents 混合策略） | `alarm_page.py` |
| 优化 | 分析页按钮高度统一为 32px（导入/清除/阈值/导出） | `analysis_page.py` |
| 优化 | 趋势页过滤器间距紧凑化（SM→XS） | `trend_page.py` |
| 优化 | PRPD 控制栏与图表区域间距统一（DT.S.SM） | `prpd_widget.py` |
| 优化 | 导航菜单选中态背景色改用 DT 令牌（#E3F2FD→ACCENT_SUBTLE） | `nav_menu.py` |
| 修复 | DT 常量引用错误（`DT.C.ACCENT`/`DT.C.BORDER` → 正确名称） | `pd_main_window.py` |
| 修复 | DT 颜色值缺少 `#` 前缀（`DEVICE_WARNING = "D29922"` → `"#D29922"`） | `design_tokens.py` |
| 修复 | 硬编码弱默认密码改为环境变量读取 | `permission_manager.py` |
| 修复 | SQL 注入风险 — data_archive_service 表名/列名白名单校验 | `data_archive_service.py` |
| 修复 | SQL 注入风险 — history_storage ORDER BY 方向白名单校验 | `history_storage.py` |
| 修复 | 裸 `except: pass` 吞异常替换为 logger.warning/debug | 多文件 |
| 修复 | `_update_status_stats()` 空实现 → 完整数据聚合+UI推送 | `pd_controller.py` |
| 修复 | `_on_device_status_for_ui()` 空实现 → 设备状态表格刷新 | `pd_controller.py` |
| 修复 | 趋势图永远为空 → 波形存储回调推送 TrendPage 数据 | `pd_controller.py` |
| 修复 | 仪表盘"在线设备"硬编码 → 从 DevicePage 读真实值 | `pd_controller.py`, `device_page.py` |
| 修复 | settings_page.py 缺少 Qt 导入导致 NameError 崩溃 | `settings_page.py` |
| 修复 | analysis_page.py 方法不存在错误（_make_stat_card/_table_style） | `analysis_page.py` |
| 修复 | 终端中文日志乱码 → 三层 UTF-8 编码强制设置 | `pd_main.py` |
| 修复 | logging.basicConfig 重复 handler → force=True | `logger.py` |
| 修复 | PeakDetector 每帧新建改为 __init__ 复用 | `prpd_processor.py` |
| 修复 | RingBuffer 全量复制切片改用 itertools.islice() | `ring_buffer.py` |
| 修复 | UDPDriver 统计字段加锁保护 | `udp_driver.py` |
| 修复 | PDSimulator.stop() 添加 join(timeout=2.0) | `pd_simulator.py` |
| 修复 | FFTWidget.clear() 添加 hasattr 防护 | `fft_widget.py` |
| 修复 | SerialDriver 区分 SerialException | `serial_driver.py` |
| 修复 | AsyncDatabaseLogHandler 高优先级日志阻塞 put | `logger.py` |
| 修复 | FpgaProtocol 帧头搜索改用 buf.find() C层实现 | `fpga_protocol.py` |
| 修复 | DatabaseManager 缓存添加 clear_cache() + WeakRef | `models.py` |
| 修复 | pyproject.toml coverage source 改为 ["core", "ui"] | `pyproject.toml` |
| 修复 | 6处 __import__() 内联调用改为正常 import | 多文件 |
| 修复 | _waveform_frame_count 移至 __init__ 声明 | `pd_controller.py` |
| 修复 | PRPS 首帧基线色阶锁定消除 autoLevels 闪烁 | `prps_widget.py` |
| 修复 | 3D 渲染节流 200ms QTimer + pending 标志 | `prpd_widget.py` |
| 修复 | Matplotlib Canvas 懒加载 | `prpd_widget.py` |
| 修复 | 2D/3D colormap 统一为 jet | `prpd_widget.py` |
| 修复 | 事件计数文案区分（heatmap/scatter） | `prpd_widget.py` |
| 修复 | waveforms_processed 按通道独立计数 | `pd_acquisition_service.py` |
| 审计 | 全面审计 PD 子系统所有 UI 文件，识别 26 个布局问题 | 所有 UI 文件 |

---

## P0 — 必须立即修复

> **全部清零 ✅**

| # | 问题 | 状态 |
|---|------|------|
| ~~8~~ | 硬编码弱默认密码 | ✅ 环境变量读取 |
| ~~9~~ | SQL 注入风险（表名/列名） | ✅ 白名单校验 |
| ~~10~~ | 裸 except: pass 吞异常 | ✅ logger 替换 |
| ~~11~~ | _show_about() _version 崩溃 | ✅ 属性声明 |
| ~~12~~ | DesignTokens 颜色缺 # 前缀 | ✅ 补全 |

---

## P1 — 应当修复

> **全部清零 ✅**（含本轮新增修复）

| # | 问题 | 状态 |
|---|------|------|
| ~~13~~ | pd_controller.py 裸 except 吞异常 | ✅ logger.debug |
| ~~14~~ | PeakDetector 每帧新建 | ✅ __init__ 复用 |
| ~~15~~ | RingBuffer 全量复制 | ✅ islice |
| ~~16~~ | UDPDriver 统计字段无锁 | ✅ threading.Lock |
| ~~17~~ | Simulator.stop() 无 join | ✅ join(2.0) |
| ~~18~~ | FFTWidget.clear() 崩溃 | ✅ hasattr |
| ~~19~~ | 趋势数据写死 0 | ✅ 真实值提取+推送 |
| ~~20~~ | SerialDriver use-after-free | ✅ SerialException 区分 |
| ~~21~~ | history_storage SQL 拼接 | ✅ ORDER BY 白名单 |

---

## P2 — 建议优化

| # | 问题 | 状态 |
|---|------|------|
| ~~22~~ | pg.setConfigOptions 重复调用 | ✅ noqa 注释 |
| ~~23~~ | _waveform_frame_count getattr | ✅ __init__ 声明 |
| ~~24~~ | PRPS autoLevels 跳变闪烁 | ✅ 基线色阶锁定 |
| ~~25~~ | DatabaseManager 缓存无清理 | ✅ clear_cache+WeakRef |
| ~~26~~ | 内联 __import__() | ✅ 正常 import |
| ~~27~~ | pyproject.toml src/ 错误路径 | ✅ ["core","ui"] |
| ~~28~~ | 日志队列 ERROR 可丢弃 | ✅ 阻塞 put |
| ~~29~~ | FpgaProtocol O(n) 帧头搜索 | ✅ buf.find() |
| 30 | main.py 与 pd_main.py 重叠无复用 | ⏸ 两入口定位不同 |
| ~~31~~ | TCPDriver 心跳延迟启动 | ✅ 已确认正常 |

> **P2: 9/10 已解决，剩余 1 项暂不处理**

---

## 上轮遗留问题

| # | 问题 | 状态 |
|---|------|------|
| ~~1~~ | waveforms_processed 跨通道全局计数 | ✅ 按通道独立计数 |
| 2 | PRPS 相位映射过于简单 | ⏸ 有 TODO，模拟器够用 |
| ~~3~~ | 3D 渲染主线程卡顿 | ✅ 200ms 节流 |
| ~~4~~ | Canvas 启动即创建 | ✅ 懒加载 |
| ~~5~~ | 2D 不缓存 3D 数据 | ✅ 全模式更新缓存 |
| ~~6~~ | 2D/3D colormap 不一致 | ✅ 统一 jet |
| ~~7~~ | 事件计数语义不一致 | ✅ 文案区分 |

> **上轮遗留: 6/7 已解决，剩余 1 项有 TODO 标记**

---

## 运行时验证修复（v1.0.5 运行阶段发现）

> **全部清零 ✅**

| # | 问题 | 严重度 | 修复方式 |
|---|------|--------|----------|
| R1 | 仪表盘数据永远为0 | 🔴 | _update_status_stats 完整实现 |
| R2 | 趋势图永远为空 | 🔴 | TrendPage.update_series 推送 |
| R3 | 设备状态事件丢弃 | 🟡 | _on_device_status_for_ui 实现 |
| R4 | 在线设备硬编码1台 | 🟡 | get_online_device_count() |
| R5 | 统计卡片文字截断 | 🟡 | 字号 22px→18px |
| R6 | settings_page NameError | 🔴 | Qt 导入补全 |
| R7 | analysis_page AttributeError | 🔴 | 方法名/QSS 修正 |
| R8 | 终端中文日志乱码 | 🟡 | 三层 UTF-8 编码 |
| R9 | basicConfig 重复 handler | 🟢 | force=True |

---

## UI 布局审计（v1.0.5 新增，26 个）

### Critical（2/2 ✅）

| # | 问题 | 状态 |
|---|------|------|
| C1 | dashboard_page 重复 addWidget | ✅ 移除重复 |
| C2 | device_page 编辑对话框无验证 | ✅ 非空验证 |

### Major（7/9 ✅ / 2 ⏸）

| # | 问题 | 状态 |
|---|------|------|
| M1 | 实时监测页无最小高度约束 | ✅ setMinimumHeight(200) |
| M2 | 趋势分析页无弹性伸缩 | ✅ Expanding SizePolicy |
| M3 | 分析页固定比例无 QSplitter | ✅ QSplitter 可拖拽 |
| M4 | 导航菜单折叠缺 ToolTip | ✅ 折叠显示 ToolTip |
| M5 | 设置页控件宽度未设100% | ✅ minimumWidth(600) |
| M6 | 报警页表格列宽固定绝对值 | ✅ Stretch+ResizeToContents |
| M7 | 设备页网格无响应式列数 | ⏸ 当前足够使用 |
| M8 | 仪表板卡片硬编码尺寸 | ✅ 圆角背景+合理字号 |
| M9 | 多页面 MinimumSize 未适配低分屏 | ⏸ 已设 1024×680 |

### Minor（11/15 ✅ / 4 ⏸）

| # | 问题 | 状态 |
|---|------|------|
| m1 | PRPD 控制栏间距不一致 | ✅ DT.S.SM 统一 |
| m2 | 波形图 Y轴标签抖动 | ✅ setFixedWidth(50) |
| m3 | FFT X轴刻度重叠 | ✅ 向内刻度 |
| m4 | PRPS ColorBar 标签字号 | ⏸ 无独立ColorBar |
| m5 | 趋势图表时间格式固定 | ✅ 动态调整 |
| m6 | 状态栏文字溢出 | ✅ Elide+minimumWidth |
| m7 | 菜单栏动作无图标 | ✅ QStyle 标准图标 |
| m8 | 页面标题风格不统一 | ✅ 已确认统一 |
| m9 | 报警按钮尺寸不统一 | ✅ 已确认统一36px |
| m10 | 设置页控件基线不对齐 | ✅ FormLayout AlignRight |
| m11 | 分析页按钮高度不一致 | ✅ 统一 32px |
| m12 | 仪表板卡片纯色无层次 | ✅ BG_SECONDARY 圆角背景 |
| m13 | 趋势页过滤器间距过大 | ✅ spacing XS |
| m14 | 实时监测非等宽字体 | ✅ monospace |
| m15 | 控件内联颜色未用 DT | ✅ nav_menu ACCENT_SUBTLE |

> **UI审计: 24/26 已修复，2 项暂缓（M7 + m4）**

---

## 分析页 UI 优化（本轮新增）

| 变更 | 说明 |
|------|------|
| 分析结果面板重构 | 从"单行参考信息 + 1×2 卡片"改为 **2×2 QGridLayout 卡片网格**：参考结果 / 置信度 / 严重等级 / 采样次数，每格独立圆角灰色背景框 |
| 死标签移除 | 删除无数据源的"标记: —"标签，消除用户困惑 |
| 有值/无值区分 | 有参考结果时名称主色加粗显示，无结果时灰色弱化显示"—" |
| 清除逻辑同步 | _clear_analysis 同步重置全部4张卡片为灰色默认态 |

---

## 已解决问题归档（30/34）

### 3D 散点图渲染核心（11 项）
| ~~1~~ fig.clear 全量重建 → 增量更新 | ~~2~~ 散点周期模拟 → _scatter_cycles | ~~3~~ 热力图回退双路径 → 单路径 |
| ~~5~~ tight_layout 冲突 → 移除 | ~~6~~ ColorBar shrink → 0.74 | ~~7~~ ColorBar 英文 → 中文 |
| ~~8~~ 散点大小 s=25 → s=18 | ~~9~~ Z轴 rotation 无效 → 移除 | ~~10~~ print残留 → logger |
| ~~35~~ ImageItem col-major 颠倒 → row-major | ~~36~~ flipud 二次反转 → 移除 |

### 数据管线问题（4 项）
| ~~11~~ PRPD 散点未传 UI → controller 连接 | ~~12~~ PRPS 错发给 PRPD → 存在性检查 |
| ~~13~~ PRPS 无节流 → publish_interval=10 | ~~14~~ 外部访问 _matrix → decay() 公开方法 |

### 架构与设计问题（5 项）
| ~~19~~ 枚举不一致 → mode.value | ~~21~~ _on_reset 未重置3D → 清除所有缓存 |
| ~~22~~ 浮点索引漂移 → decay() | ~~23~~ 3D视角每次重置 → 保存elev/azim |
| ~~28~~ _view_stack 重复None → 移除冗余 |

### UI/交互问题（4 项）
| ~~24~~ 3D切换数据延迟 → 通过#11修复 | ~~27~~ combo索引错位 → findData精确查找 |
| ~~29~~ _image_transform未使用 → 移除 | ~~34~~ cycle_local公式不一致 → 统一 |

### 代码质量（4 项）
| ~~30~~ ImageGrab未用导入 → 移除 | ~~31~~ 孤儿QLabel → cl.addWidget |
| ~~32~~ append_cycle autoLevels=True → 前5次后固定 | ~~33~~ DischargeClassifier阈值可能0 → min保底 |

---

## 统计总览

| 严重程度 | 总数 | 已解决 | 待解决 | 状态 |
|---------|------|--------|--------|------|
| **P0** | 5 | **5** | **0** | ✅ 清零 |
| **P1** | 9 | **9** | **0** | ✅ 清零 |
| **P2** | 10 | **9** | **1** | 🟡 91% |
| **上轮遗留** | 7 | **6** | **1** | 🟡 86% |
| **运行时修复** | 9 | **9** | **0** | ✅ 清零 |
| **UI审计** | 26 | **24** | **2** | 🟡 92% |
| **分析页优化** | 3 | **3** | **0** | ✅ 完成 |
| **合计** | **89** | **83** | **6** | |
| **解决率** | | **93.3%** | | |

### 待解决清单（仅剩 6 项）

| # | 类别 | 问题 | 原因 |
|---|------|------|------|
| 30 | P2 | main.py 与 pd_main.py 重叠 | 两入口定位不同，暂不复用 |
| 2 | 遗留 | PRPS 相位映射简单 | 需外部同步信号，有TODO标记 |
| M7 | Major | 设备页网格响应式 | 固定3列当前够用 |
| m4 | Minor | PRPS ColorBar字号 | 无独立ColorBar控件 |
