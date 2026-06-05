# -*- coding: utf-8 -*-
"""
数据分析页面 - 导入 PRPD 实验数据并分析

支持:
- CSV/Excel/TXT 文件拖放和选择导入
- 自动识别数据格式和列名映射
- PRPD 图谱显示 (复用 PRPDWidget)
- 幅值分布直方图 + 相位分布柱状图
- 放电类型自动识别 + 置信度评估
- 幅值阈值过滤
- 报告导出 (JSON/Excel/Word)
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.design_tokens import DT

try:
    import pyqtgraph as pg

    pg.setConfigOptions(antialias=True, foreground="#333333")
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False


# ═══════════════════════════════════════════════════════
# 数据导入器
# ═══════════════════════════════════════════════════════


class DataImporter:
    """PRPD 实验数据导入器"""

    SUPPORTED_EXTENSIONS = [".csv", ".xlsx", ".xls", ".txt"]

    @staticmethod
    def load(path: str) -> Tuple[str, np.ndarray, np.ndarray, dict]:
        """
        加载数据文件

        Returns:
            (format_name, phases, amplitudes, metadata)
        """
        suffix = Path(path).suffix.lower()
        if suffix not in DataImporter.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {suffix}，支持: CSV/Excel/TXT")

        if suffix == ".csv":
            return DataImporter._load_csv(path)
        elif suffix in (".xlsx", ".xls"):
            return DataImporter._load_excel(path)
        else:
            return DataImporter._load_txt(path)

    @staticmethod
    def _load_csv(path: str) -> Tuple[str, np.ndarray, np.ndarray, dict]:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = [r for r in reader if r and not r[0].startswith(("#", "%", "//"))]

        header = [h.strip().lower() for h in rows[0]]
        data_rows = rows[1:]

        # 自动映射列
        phase_idx, amp_idx = None, None
        for i, h in enumerate(header):
            if h in ("phase_deg", "phase", "phi", "φ", "相位"):
                phase_idx = i
            if h in ("discharge", "amplitude", "amp", "magnitude", "幅值", "mv", "pc", "放电量"):
                amp_idx = i

        phases, amplitudes = [], []
        for row in data_rows:
            try:
                p = float(row[phase_idx]) if phase_idx is not None and len(row) > phase_idx else None
                a = float(row[amp_idx]) if amp_idx is not None and len(row) > amp_idx else None
                if p is not None and a is not None and 0 <= p <= 360 and a >= 0:
                    phases.append(p)
                    amplitudes.append(a)
            except (ValueError, IndexError, TypeError):
                continue

        if not phases:
            # 回退: 尝试前两列
            for row in data_rows:
                if len(row) >= 2:
                    try:
                        p, a = float(row[0]), float(row[1])
                        if 0 <= p <= 360 and a >= 0:
                            phases.append(p)
                            amplitudes.append(a)
                    except (ValueError, IndexError):
                        continue

        return (
            "phase_amplitude",
            np.array(phases),
            np.array(amplitudes),
            {
                "columns": header,
                "total_rows": len(data_rows),
                "file": path,
            },
        )

    @staticmethod
    def _load_excel(path: str) -> Tuple[str, np.ndarray, np.ndarray, dict]:
        try:
            import openpyxl
        except ImportError:
            raise ImportError("需要安装 openpyxl: pip install openpyxl")

        wb = openpyxl.load_workbook(path, read_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        header = [str(c).strip().lower() if c else "" for c in all_rows[0]]
        data_rows = all_rows[1:]
        wb.close()

        phase_idx, amp_idx = None, None
        for i, h in enumerate(header):
            if h in ("phase_deg", "phase", "phi", "φ", "相位"):
                phase_idx = i
            if h in ("discharge", "amplitude", "amp", "magnitude", "幅值", "mv", "pc"):
                amp_idx = i

        phases, amplitudes = [], []
        default_idx = 0
        for row in data_rows:
            try:
                p = (
                    float(row[phase_idx])
                    if phase_idx is not None and len(row) > phase_idx
                    else float(row[default_idx]) if row[default_idx] is not None else None
                )
                a = (
                    float(row[amp_idx])
                    if amp_idx is not None and len(row) > amp_idx
                    else (
                        float(row[default_idx + 1])
                        if len(row) > default_idx + 1 and row[default_idx + 1] is not None
                        else None
                    )
                )
                if p is not None and a is not None and 0 <= p <= 360 and a >= 0:
                    phases.append(p)
                    amplitudes.append(a)
            except (ValueError, IndexError, TypeError):
                continue

        return (
            "phase_amplitude",
            np.array(phases),
            np.array(amplitudes),
            {
                "columns": header,
                "total_rows": len(data_rows),
                "file": path,
            },
        )

    @staticmethod
    def _load_txt(path: str) -> Tuple[str, np.ndarray, np.ndarray, dict]:
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith(("#", "%"))]

        phases, amplitudes = [], []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    p, a = float(parts[0]), float(parts[1])
                    if 0 <= p <= 360:
                        phases.append(p)
                        amplitudes.append(a)
                except ValueError:
                    continue

        return (
            "phase_amplitude",
            np.array(phases),
            np.array(amplitudes),
            {
                "columns": ["col1", "col2"],
                "total_rows": len(lines),
                "file": path,
            },
        )


# ═══════════════════════════════════════════════════════
# 放电类型分类器
# ═══════════════════════════════════════════════════════


class DischargeClassifier:
    """基于 PRPD 统计特征的放电类型分类

    使用 6 扇区能量分布，通过明确规则+评分混合策略判断放电类型。

    扇区划分:
      S1 (0-60°),   S2 (60-120°),   S3 (120-180°)   — 正半周
      S4 (180-240°), S5 (240-300°), S6 (300-360°)   — 负半周

    各放电类型指纹:
      - 内部气隙: S1+S4 占主导(>50%)，对称，S2/S3/S5/S6 少
      - 电晕:     S6 占主导(>35%)，正半周极少(<15%)
      - 沿面:     S1 占主导(>30%)，正半周占比 >60%，不对称
      - 悬浮:     分布宽，无主导扇区，top2 集中度 <50%
    """

    PATTERNS = {
        "internal": {
            "name": "内部气隙放电",
            "name_en": "Internal Discharge",
            "desc": "绝缘介质内部气隙或杂质引起的放电。正负半周对称，集中在0°~60°和180°~240°（第一/三象限）。",
        },
        "corona": {
            "name": "电晕放电",
            "name_en": "Corona Discharge",
            "desc": "高压导体尖端产生的放电。集中在负半周270°~330°，幅值较稳定，正半周极少。",
        },
        "surface": {
            "name": "沿面放电",
            "name_en": "Surface Discharge",
            "desc": "绝缘表面爬电。正半周30°~90°集中，负半周分散或不对称。",
        },
        "floating": {
            "name": "悬浮颗粒放电",
            "name_en": "Floating Discharge",
            "desc": "金属悬浮电位体引起的放电。相位分布宽，无明显集中区间，幅值大且分散。",
        },
    }

    @classmethod
    def classify(cls, phases: np.ndarray, amplitudes: np.ndarray) -> dict:
        if len(phases) < 10:
            return {
                "type": "unknown",
                "name": "未知",
                "name_en": "Unknown",
                "confidence": 0,
                "severity": "normal",
                "symmetry": False,
                "pos_ratio": 0.5,
                "concentration": 0,
                "description": "数据不足",
            }

        n_all = len(phases)
        max_amp = float(np.max(amplitudes))
        p90 = float(np.percentile(amplitudes, 90))

        # ── 自适应去噪 ───────────────────────────────
        # 方法: 使用振幅中位数的倍数作为阈值, 但限制最低保留30%事件
        amp_median = float(np.median(amplitudes))
        p5 = float(np.percentile(amplitudes, 5))
        # 动态阈值: max(中位数*2, P5, 固定最小值避免过杀)
        noise_threshold = max(amp_median * 2.0, p5 * 1.5, 0.0)
        clean_mask = amplitudes >= noise_threshold
        p_clean = phases[clean_mask]
        a_clean = amplitudes[clean_mask]
        n_clean = len(p_clean)

        # 防止过滤过多: 保留至少 30% 事件数
        if n_clean < max(20, n_all * 0.3):
            p_clean, a_clean = phases, amplitudes
            n_clean = n_all
            noise_removed = 0
        else:
            noise_removed = n_all - n_clean

        # ── 双通道分析: 事件计数 + 幅值加权 ──────────
        # 幅值加权扇区 = 高幅值事件贡献更多权重，抑制噪声影响
        def calc_sectors(ph, amp=None):
            sec = np.zeros(6)
            for i in range(6):
                mask = (ph >= i * 60) & (ph < (i + 1) * 60)
                if amp is not None:
                    sec[i] = float(np.sum(amp[mask]))  # 幅值加权
                else:
                    sec[i] = float(np.sum(mask))  # 事件计数
            return sec / (np.sum(sec) + 1e-10)

        sectors_count = calc_sectors(p_clean)  # 计权扇区
        sectors_weighted = calc_sectors(p_clean, a_clean)  # 幅值加权扇区

        # 使用计权扇区做主判断，幅值加权做辅助验证
        S1, S2, S3, S4, S5, S6 = sectors_count
        W1, W2, W3, W4, W5, W6 = sectors_weighted

        # ── 特征提取 ──────────────────────────────────
        pos_ratio = S1 + S2 + S3  # 正半周占比
        quad13 = S1 + S4  # 第一+三象限
        neg_tail_count = S5 + S6  # 240-360° 计权
        neg_tail_weight = W5 + W6  # 240-360° 幅值加权
        s1_dominance = S1 / (S1 + S2 + S3 + 1e-10)  # S1 在正半周主导度
        symmetry = 1.0 - abs(S1 - S4) / (max(S1, S4) + 1e-10)  # S1↔S4 对称度
        spread = S2 + S3 + S5 + S6  # 签名区外扩散
        top2 = sum(sorted([S1, S2, S3, S4, S5, S6], reverse=True)[:2])

        # 不对称度: 正负半周能量差
        pos_energy_weight = W1 + W2 + W3
        neg_energy_weight = W4 + W5 + W6
        asymmetry_ratio = abs(pos_energy_weight - neg_energy_weight) / (pos_energy_weight + neg_energy_weight + 1e-10)
        # asymmetry_ratio: 0=完全对称, 1=完全不对称

        # ── 规则引擎 ──────────────────────────────────
        rules = []

        # 规则1: 电晕放电 — 负半周尾部(S5+S6)占绝对主导，正半周极少
        # 使用幅值加权(高幅值电晕脉冲贡献大) + 计权双验证
        corona_weight_dom = neg_tail_weight  # 幅值加权负尾部占比
        corona_count_dom = neg_tail_count  # 计权负尾部占比
        corona_pos_suppress = max(0, 1.0 - pos_ratio * 4)  # 正半周抑制
        # 幅值加权下 S5+S6 占绝对主导 → 强电晕证据
        corona_evidence = corona_weight_dom if corona_weight_dom > 0.5 else corona_count_dom
        corona_match = corona_evidence * 0.5 + corona_pos_suppress * 0.3 + max(corona_weight_dom - 0.3, 0) * 0.2
        corona_strong = (corona_weight_dom > 0.60 or corona_count_dom > 0.50) and pos_ratio < 0.25
        rules.append(("corona", corona_match, corona_strong))

        # 规则2: 沿面放电 — S1 主导正半周，正负半周不对称
        # 沿面典型特征: 正半周占优, S1/(S1+S4) > 0.6
        s1_ratio = S1 / (S1 + S4 + 1e-10)  # S1 在 quad13 中的占比 >0.6 偏向沿面
        surface_pos_bias = max(0, (s1_ratio - 0.5) * 2)  # 0~1, S1越主导越高
        surface_asym_bonus = asymmetry_ratio  # 不对称加分
        surface_neg_suppress = max(0, 1.0 - neg_tail_count * 3)  # 负半周抑制
        surface_match = surface_pos_bias * 0.4 + surface_asym_bonus * 0.3 + surface_neg_suppress * 0.3
        surface_strong = s1_ratio > 0.65 and asymmetry_ratio > 0.20 and pos_ratio > 0.55
        rules.append(("surface", surface_match, surface_strong))

        # 规则3: 内部气隙放电 — S1+S4 主导，对称，低扩散
        internal_match = quad13 * 0.5 + symmetry * 0.3 + max(0, 1.0 - spread / 0.55) * 0.2
        internal_strong = quad13 > 0.50 and symmetry > 0.60 and spread < 0.55
        rules.append(("internal", internal_match, internal_strong))

        # 规则4: 悬浮颗粒放电 — 低集中度，均匀分布
        uniformity = max(0, 1.0 - (top2 - 0.35) / 0.45)
        floating_match = uniformity * 0.5 + max(0, 1.0 - quad13 / 0.6) * 0.3 + max(0, spread / 0.6) * 0.2
        floating_strong = top2 < 0.50 and quad13 < 0.55
        rules.append(("floating", floating_match, floating_strong))

        # ── 决策 ──────────────────────────────────────
        strong_matches = [(t, s) for t, s, strong in rules if strong]
        if strong_matches:
            best_type = max(strong_matches, key=lambda x: x[1])[0]
            best_score = max(s for t, s in strong_matches if t == best_type)
            confidence = min(0.75 + best_score * 0.2, 0.95)
        else:
            best_type = max(rules, key=lambda x: x[1])[0]
            best_score = max(s for t, s, _ in rules if t == best_type)
            second_score = sorted([s for _, s, _ in rules], reverse=True)[1]
            margin = best_score - second_score
            confidence = max(0.35, min(0.5 + margin, 0.80))

        # 严重等级
        severity = "normal"
        if max_amp > 5000 or p90 > 3000:
            severity = "critical"
        elif max_amp > 2000 or p90 > 1000:
            severity = "warning"
        elif max_amp > 500:
            severity = "attention"

        pattern = cls.PATTERNS[best_type]
        return {
            "type": best_type,
            "name": pattern["name"],
            "name_en": pattern["name_en"],
            "description": pattern["desc"],
            "confidence": float(f"{confidence:.2f}"),
            "severity": severity,
            "symmetry": symmetry > 0.6,
            "pos_ratio": float(f"{pos_ratio:.2f}"),
            "concentration": float(f"{top2:.3f}"),
            "noise_removed": noise_removed,
            "clean_events": n_clean,
            "features": {
                "S1": float(f"{S1:.3f}"),
                "S2": float(f"{S2:.3f}"),
                "S3": float(f"{S3:.3f}"),
                "S4": float(f"{S4:.3f}"),
                "S5": float(f"{S5:.3f}"),
                "S6": float(f"{S6:.3f}"),
                "quad13": float(f"{quad13:.3f}"),
                "symmetry": float(f"{symmetry:.3f}"),
                "spread": float(f"{spread:.3f}"),
                "top2": float(f"{top2:.3f}"),
                "asymmetry_ratio": float(f"{asymmetry_ratio:.3f}"),
                "s1_ratio": float(f"{s1_ratio:.3f}"),
            },
            "scores": {t: float(f"{s:.3f}") for t, s, _ in rules},
        }


# ═══════════════════════════════════════════════════════
# 报告生成器
# ═══════════════════════════════════════════════════════


class ReportExporter:
    """报告导出"""

    @staticmethod
    def export_json(data: dict, path: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return path

    @staticmethod
    def export_excel(data: dict, path: str) -> str:
        try:
            import openpyxl
        except ImportError:
            raise ImportError("需要安装 openpyxl: pip install openpyxl")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "PRPD分析报告"

        # 标题
        ws.merge_cells("A1:E1")
        ws["A1"] = "PRPD 分析报告"
        ws["A1"].font = openpyxl.styles.Font(size=14, bold=True)

        # 基本信息
        ws["A3"] = "分析时间"
        ws["B3"] = data.get("analysis_time", "")
        ws["A4"] = "放电类型"
        dc = data.get("discharge_classification", {})
        ws["B4"] = dc.get("name", "")
        ws["A5"] = "置信度"
        ws["B5"] = f'{dc.get("confidence", 0):.0%}'
        ws["A6"] = "严重等级"
        ws["B6"] = dc.get("severity", "")

        # 统计
        stats = data.get("statistics", {})
        ws["A8"] = "统计指标"
        ws["A8"].font = openpyxl.styles.Font(bold=True)
        ws["A9"] = "总事件数"
        ws["B9"] = stats.get("total_events", 0)
        ws["A10"] = "最大幅值"
        ws["B10"] = stats.get("max_amplitude", 0)
        ws["A11"] = "平均幅值"
        ws["B11"] = stats.get("avg_amplitude", 0)
        ws["A12"] = "幅值中位数"
        ws["B12"] = stats.get("median_amplitude", 0)
        ws["A13"] = "幅值P90"
        ws["B13"] = stats.get("p90", 0)
        ws["A14"] = "相位集中度"
        ws["B14"] = stats.get("concentration", 0)

        # 相位分布
        ws["A16"] = "相位分布"
        ws["A16"].font = openpyxl.styles.Font(bold=True)
        phase_dist = data.get("phase_distribution", {})
        for i, (key, val) in enumerate(phase_dist.items()):
            ws[f"A{i+17}"] = key
            ws[f"B{i+17}"] = val

        wb.save(path)
        return path

    @staticmethod
    def export_word(data: dict, path: str, chart_path: Optional[str] = None) -> str:
        """导出 Word 报告（含 PRPD 截图）"""
        try:
            from docx import Document
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.shared import Cm, Inches, Pt, RGBColor
        except ImportError:
            raise ImportError("需要安装 python-docx: pip install python-docx")

        doc = Document()

        # 标题
        title = doc.add_heading("PRPD 局部放电分析报告", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 基本信息
        doc.add_heading("1. 基本信息", level=1)
        tbl = doc.add_table(rows=5, cols=2)
        tbl.style = "Light Shading Accent 1"
        items = [
            ("分析时间", data.get("analysis_time", "")),
            ("数据文件", data.get("file_name", "")),
            ("总事件数", str(data.get("statistics", {}).get("total_events", 0))),
            ("放电类型", data.get("discharge_classification", {}).get("name", "")),
            ("严重等级", data.get("discharge_classification", {}).get("severity", "")),
        ]
        for i, (k, v) in enumerate(items):
            tbl.cell(i, 0).text = k
            tbl.cell(i, 1).text = v

        # PRPD 图谱截图
        if chart_path and os.path.exists(chart_path):
            doc.add_heading("2. PRPD 图谱", level=1)
            doc.add_picture(chart_path, width=Inches(5.5))

        # 分类结果
        dc = data.get("discharge_classification", {})
        doc.add_heading("3. 放电类型分析", level=1)
        doc.add_paragraph(f"识别结果: {dc.get('name', '')} ({dc.get('name_en', '')})")
        doc.add_paragraph(f"置信度: {dc.get('confidence', 0):.0%}")
        doc.add_paragraph(f"严重等级: {dc.get('severity', 'normal')}")
        doc.add_paragraph(f"说明: {dc.get('description', '')}")

        # 统计指标
        stats = data.get("statistics", {})
        doc.add_heading("4. 统计指标", level=1)
        tbl2 = doc.add_table(rows=7, cols=2)
        tbl2.style = "Light Shading Accent 1"
        stat_items = [
            ("总事件数", str(stats.get("total_events", 0))),
            ("最大幅值", f'{stats.get("max_amplitude", 0):.1f}'),
            ("平均幅值", f'{stats.get("avg_amplitude", 0):.1f}'),
            ("幅值中位数", f'{stats.get("median_amplitude", 0):.1f}'),
            ("幅值P90", f'{stats.get("p90", 0):.1f}'),
            ("相位集中度", f'{stats.get("concentration", 0):.4f}'),
        ]
        for i, (k, v) in enumerate(stat_items):
            tbl2.cell(i, 0).text = k
            tbl2.cell(i, 1).text = v

        doc.save(path)
        return path


# ═══════════════════════════════════════════════════════
# 数据分析页面
# ═══════════════════════════════════════════════════════

# 等级颜色
LEVEL_COLORS = {
    "critical": "#CF222E",
    "warning": "#D29922",
    "attention": "#0969DA",
    "normal": "#1A7F37",
}
LEVEL_NAMES = {
    "critical": "严重",
    "warning": "警告",
    "attention": "注意",
    "normal": "正常",
}


class AnalysisPage(QWidget):
    """数据分析页面"""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("analysisPage")
        self.setAcceptDrops(True)

        self._phases: Optional[np.ndarray] = None
        self._amplitudes: Optional[np.ndarray] = None
        self._metadata: dict = {}
        self._analysis_result: dict = {}
        self._threshold_min = 0

        self._setup_ui()

    # ── UI 构建 ───────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(DT.S.XL, DT.S.LG, DT.S.XL, DT.S.LG)
        layout.setSpacing(DT.S.MD)

        self._build_header(layout)
        self._build_import_bar(layout)
        self._build_content(layout)

    def _build_header(self, layout: QVBoxLayout) -> None:
        h = QHBoxLayout()
        title = QLabel("数据分析")
        title.setFont(DT.T.get_font(*DT.T.TITLE_XLARGE[:2], "Bold"))
        title.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        h.addWidget(title)
        h.addStretch()
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 12px;")
        h.addWidget(self._status_label)
        layout.addLayout(h)

    def _build_import_bar(self, layout: QVBoxLayout) -> None:
        bar = QFrame()
        bar.setObjectName("cardContainer")
        bar.setStyleSheet(
            f"""
            QFrame#cardContainer {{
                background: {DT.C.BG_PRIMARY};
                border: 2px dashed {DT.C.BORDER_DEFAULT};
                border-radius: {DT.R.LG}px;
            }}
            QFrame#cardContainer:hover {{
                border-color: {DT.C.ACCENT_PRIMARY};
            }}
        """
        )
        bar.setFixedHeight(80)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(DT.S.LG, DT.S.MD, DT.S.LG, DT.S.MD)

        btn_import = QPushButton("选择文件")
        btn_import.setFixedHeight(32)
        btn_import.setStyleSheet(
            f"""
            QPushButton {{
                background: {DT.C.ACCENT_PRIMARY}; color: white; border: none;
                border-radius: 4px; padding: 6px 18px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {DT.C.ACCENT_HOVER}; }}
        """
        )
        btn_import.clicked.connect(self._on_import_click)
        bl.addWidget(btn_import)

        # 提示文字（无文件时显示）
        self._prompt_label = QLabel("选择文件或拖放 CSV/Excel/TXT 文件到此处")
        self._prompt_label.setStyleSheet(f"color: {DT.C.TEXT_TERTIARY}; font-size: 13px;")
        bl.addWidget(self._prompt_label)

        # 文件信息（有文件时显示）
        self._file_label = QLabel("")
        self._file_label.setStyleSheet(f"color: {DT.C.TEXT_SECONDARY}; font-size: 12px;")
        self._file_label.setVisible(False)
        bl.addWidget(self._file_label, 1)

        bl.addStretch()

        # 清除按钮
        self._clear_btn = QPushButton("清除")
        self._clear_btn.setFixedHeight(28)
        self._clear_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent; color: {DT.C.TEXT_SECONDARY};
                border: 1px solid {DT.C.BORDER_DEFAULT}; border-radius: 4px;
                padding: 4px 14px; font-size: 12px;
            }}
            QPushButton:hover {{ background: {DT.C.BG_HOVER}; }}
        """
        )
        self._clear_btn.clicked.connect(self._clear_analysis)
        self._clear_btn.setVisible(False)
        bl.addWidget(self._clear_btn)

        # 阈值过滤
        bl.addWidget(QLabel("最低幅值:", styleSheet=f"color: {DT.C.TEXT_TERTIARY}; font-size: 12px;"))
        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(0, 100000)
        self._threshold_spin.setValue(0)
        self._threshold_spin.setSuffix(" (过滤噪声)")
        self._threshold_spin.setFixedHeight(28)
        self._threshold_spin.setStyleSheet(
            f"""
            QSpinBox {{ background: {DT.C.BG_PRIMARY}; border: 1px solid {DT.C.BORDER_DEFAULT};
            border-radius: 4px; padding: 2px 6px; font-size: 12px; color: {DT.C.TEXT_PRIMARY}; }}
        """
        )
        self._threshold_spin.valueChanged.connect(self._on_threshold_changed)
        bl.addWidget(self._threshold_spin)

        layout.addWidget(bar)

    def _build_content(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        row.setSpacing(DT.S.MD)

        # 左: PRPD 图谱
        self._build_prpd_panel(row)
        # 右: 分析结果
        self._build_result_panel(row)

        layout.addLayout(row, 3)

        # 下: 相位+幅值分布
        self._build_distribution_panel(layout)

    def _build_prpd_panel(self, parent: QHBoxLayout) -> None:
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
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)

        if HAS_PYQTGRAPH:
            from ui.widgets import PRPDWidget

            self._prpd = PRPDWidget(title="PRPD 图谱")
            self._prpd._mode_combo.setCurrentIndex(0)  # 默认散点图
            fl.addWidget(self._prpd)
        else:
            self._prpd = None
            fl.addWidget(QLabel("需要 pyqtgraph 支持", alignment=Qt.AlignmentFlag.AlignCenter))

        parent.addWidget(frame, 3)

    def _build_result_panel(self, parent: QHBoxLayout) -> None:
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
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)

        lbl = QLabel("分析结果")
        lbl.setFont(DT.T.get_font(*DT.T.TITLE_MEDIUM[:2], "SemiBold"))
        lbl.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        fl.addWidget(lbl)

        # 放电类型
        self._type_card = self._make_result_card("放电类型", "—")
        fl.addWidget(self._type_card)
        self._conf_card = self._make_result_card("置信度", "—")
        fl.addWidget(self._conf_card)
        self._sev_card = self._make_result_card("严重等级", "—")
        fl.addWidget(self._sev_card)

        fl.addWidget(QLabel("", styleSheet=f"color: {DT.C.DIVIDER}; max-height: 1px;"))

        # 统计
        self._stat_table = QTableWidget()
        self._stat_table.setColumnCount(2)
        self._stat_table.setHorizontalHeaderLabels(["指标", "值"])
        self._stat_table.setAlternatingRowColors(True)
        self._stat_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._stat_table.verticalHeader().setVisible(False)
        self._stat_table.setStyleSheet(
            f"""
            QTableWidget {{
                background: transparent; border: none; font-size: 12px;
            }}
            QTableWidget::item {{ padding: 3px 6px; }}
            QHeaderView::section {{
                background: {DT.C.BG_SECONDARY}; color: {DT.C.TEXT_SECONDARY};
                border: none; font-size: 11px; font-weight: 600;
            }}
        """
        )
        self._stat_table.horizontalHeader().setStretchLastSection(True)
        fl.addWidget(self._stat_table, 1)

        # 导出按钮
        btn_row = QHBoxLayout()
        for text, slot in [
            ("导出 JSON", self._export_json),
            ("导出 Excel", self._export_excel),
            ("导出 Word", self._export_word),
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent; color: {DT.C.TEXT_SECONDARY};
                    border: 1px solid {DT.C.BORDER_DEFAULT}; border-radius: 4px;
                    padding: 3px 10px; font-size: 11px;
                }}
                QPushButton:hover {{ background: {DT.C.BG_HOVER}; }}
            """
            )
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        fl.addLayout(btn_row)

        parent.addWidget(frame, 2)

    def _build_distribution_panel(self, layout: QVBoxLayout) -> None:
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
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)

        lbl = QLabel("幅值分布")
        lbl.setFont(DT.T.get_font(*DT.T.TITLE_SMALL[:2], "SemiBold"))
        lbl.setStyleSheet(f"color: {DT.C.TEXT_PRIMARY};")
        fl.addWidget(lbl)

        if HAS_PYQTGRAPH:
            self._dist_plot = pg.PlotWidget()
            self._dist_plot.setMinimumHeight(100)
            self._dist_plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._dist_plot.showGrid(x=True, y=True, alpha=0.2)
            self._dist_plot.setLabel("left", "事件数")
            self._dist_plot.setLabel("bottom", "幅值")
            fl.addWidget(self._dist_plot)
        else:
            self._dist_plot = None

        layout.addWidget(frame, 1)

    @staticmethod
    def _make_result_card(title: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {DT.C.BG_SECONDARY}; border-radius: {DT.R.MD}px; }}")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(DT.S.MD, DT.S.SM, DT.S.MD, DT.S.SM)
        QLabel(title, styleSheet=f"color: {DT.C.TEXT_TERTIARY}; font-size: 11px;").setParent(card)
        cl.addWidget(QLabel(title, styleSheet=f"color: {DT.C.TEXT_TERTIARY}; font-size: 11px;"))
        cl.addWidget(QLabel(value, styleSheet=f"color: {DT.C.TEXT_PRIMARY}; font-size: 14px; font-weight: 600;"))
        return card

    # ── 导入 ─────────────────────────────────────────

    def _on_import_click(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 PRPD 数据文件",
            "",
            "数据文件 (*.csv *.xlsx *.xls *.txt);;CSV (*.csv);;Excel (*.xlsx *.xls);;TXT (*.txt)",
        )
        if path:
            self._import_file(path)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in DataImporter.SUPPORTED_EXTENSIONS:
                self._import_file(path)
                break

    def _import_file(self, path: str) -> None:
        try:
            fmt, phases, amplitudes, meta = DataImporter.load(path)
        except Exception as e:
            QMessageBox.warning(self, "导入失败", str(e))
            self._status_label.setText(f"导入失败: {e}")
            return

        if len(phases) == 0:
            QMessageBox.warning(
                self, "导入失败", "未能从文件中解析到有效数据。\n请确保文件包含相位(0-360°)和幅值两列数据。"
            )
            return

        self._raw_phases = phases
        self._raw_amplitudes = amplitudes
        self._metadata = meta
        self._file_path = path

        # 切换显示: 隐藏提示，显示文件信息
        self._prompt_label.setVisible(False)
        self._file_label.setText(f" {Path(path).name} — {len(phases)} 条")
        self._file_label.setVisible(True)
        self._clear_btn.setVisible(True)
        self._status_label.setText(f"已加载 {len(phases)} 条数据")

        # 自动设置阈值建议（P5 作为底噪估计）
        suggested = int(np.percentile(amplitudes, 5))
        self._threshold_spin.setValue(suggested)
        self._threshold_min = suggested

        self._run_analysis()

    def _on_threshold_changed(self, val: int) -> None:
        self._threshold_min = val
        if hasattr(self, "_raw_phases"):
            self._run_analysis()

    def _clear_analysis(self) -> None:
        """清除已加载的文件和分析结果，恢复到默认状态"""
        self._raw_phases = np.array([])
        self._raw_amplitudes = np.array([])
        self._metadata = {}
        self._analysis_result = {}
        self._file_path = ""
        self._threshold_spin.setValue(0)
        self._threshold_min = 0

        # 恢复提示文字，隐藏文件信息和清除按钮
        self._prompt_label.setVisible(True)
        self._file_label.setVisible(False)
        self._file_label.setText("")
        self._clear_btn.setVisible(False)

        # 清除 PRPD 图谱
        if HAS_PYQTGRAPH and self._prpd is not None:
            self._prpd._on_reset()

        # 清除分析结果卡片
        self._update_card(self._type_card, "放电类型", "—", DT.C.TEXT_PRIMARY)
        self._update_card(self._conf_card, "置信度", "—", DT.C.TEXT_PRIMARY)
        self._update_card(self._sev_card, "严重等级", "—", DT.C.TEXT_TERTIARY)
        self._stat_table.setRowCount(0)

        # 清除幅值分布图
        if HAS_PYQTGRAPH and self._dist_plot is not None:
            self._dist_plot.clear()

        self._status_label.setText("就绪")

    # ── 分析 ─────────────────────────────────────────

    def _run_analysis(self) -> None:
        phases = self._raw_phases
        amps = self._raw_amplitudes

        # 阈值过滤
        mask = amps >= self._threshold_min
        phases = phases[mask]
        amps = amps[mask]

        if len(phases) < 5:
            self._status_label.setText("过滤后数据不足，请降低阈值")
            return

        # 统计
        stats = {
            "total_events": int(len(phases)),
            "max_amplitude": float(np.max(amps)),
            "min_amplitude": float(np.min(amps)),
            "avg_amplitude": float(np.mean(amps)),
            "median_amplitude": float(np.median(amps)),
            "p90": float(np.percentile(amps, 90)),
            "concentration": float(np.max(np.histogram(phases, bins=36, range=(0, 360))[0]) / len(phases)),
        }

        # 放电类型分类
        dc = DischargeClassifier.classify(phases, amps)

        self._analysis_result = {
            "file_name": Path(self._file_path).name if hasattr(self, "_file_path") else "",
            "analysis_time": datetime.now().isoformat(),
            "statistics": stats,
            "discharge_classification": dc,
            "threshold": self._threshold_min,
        }

        # 更新 PRPD 图谱（热力图 + 散点数据）
        if HAS_PYQTGRAPH and self._prpd is not None:
            from core.processing import PRPDProcessor
            from core.processing.prpd_processor import PRPDMode

            prpd = PRPDProcessor(phase_bins=360, amplitude_bins=256, max_amplitude=stats["max_amplitude"] * 1.1)
            for p, a in zip(phases, amps):
                prpd.add_event(phase=float(p), amplitude=float(a))
            prpd_result = prpd.compute(mode=PRPDMode.HEATMAP)
            self._prpd.update_heatmap(prpd_result.matrix, 360, 256)
            # 同步更新散点数据，支持模式切换
            self._prpd.update_scatter(phases.tolist(), amps.tolist())

        # 更新分析结果面板
        self._update_result_display(dc, stats)

        # 更新幅值分布
        self._update_distribution(amps)

        self._status_label.setText(f"分析完成 — {len(phases)} 条事件 (阈值>{self._threshold_min})")

    def _update_result_display(self, dc: dict, stats: dict) -> None:
        """更新分析结果面板"""
        # 更新卡片
        self._update_card(self._type_card, "放电类型", dc.get("name", "—"), DT.C.ACCENT_PRIMARY)
        conf = dc.get("confidence", 0)
        self._update_card(
            self._conf_card, "置信度", f"{conf:.0%}", DT.C.STATUS_SUCCESS if conf > 0.7 else DT.C.STATUS_WARNING
        )
        sev = dc.get("severity", "normal")
        self._update_card(
            self._sev_card, "严重等级", LEVEL_NAMES.get(sev, "—"), LEVEL_COLORS.get(sev, DT.C.TEXT_SECONDARY)
        )

        # 更新统计表
        self._stat_table.setRowCount(6)
        items = [
            ("总事件数", str(stats["total_events"])),
            ("最大幅值", f'{stats["max_amplitude"]:.1f}'),
            ("最小幅值", f'{stats["min_amplitude"]:.1f}'),
            ("平均幅值", f'{stats["avg_amplitude"]:.1f}'),
            ("幅值中位数", f'{stats["median_amplitude"]:.1f}'),
            ("幅值 P90", f'{stats["p90"]:.1f}'),
        ]
        for i, (k, v) in enumerate(items):
            self._stat_table.setItem(i, 0, QTableWidgetItem(k))
            item = QTableWidgetItem(v)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._stat_table.setItem(i, 1, item)

    def _update_card(self, card: QFrame, title: str, value: str, color: str) -> None:
        cl = card.layout()
        # 删除旧标签重新添加
        while cl.count():
            item = cl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cl.addWidget(QLabel(title, styleSheet=f"color: {DT.C.TEXT_TERTIARY}; font-size: 11px;"))
        cl.addWidget(QLabel(value, styleSheet=f"color: {color}; font-size: 16px; font-weight: 700;"))

    def _update_distribution(self, amps: np.ndarray) -> None:
        if not HAS_PYQTGRAPH or self._dist_plot is None:
            return

        self._dist_plot.clear()
        if len(amps) < 2:
            return
        # 自动分箱
        n_bins = min(50, len(amps) // 10)
        n_bins = max(10, n_bins)
        y, x = np.histogram(amps, bins=n_bins)
        # 柱状图
        bg = pg.BarGraphItem(x0=x[:-1], height=y, width=(x[1] - x[0]) * 0.9, brush=QColor(DT.C.ACCENT_PRIMARY))
        self._dist_plot.addItem(bg)

    # ── 导出 ─────────────────────────────────────────

    def _export_json(self) -> None:
        if not self._analysis_result:
            QMessageBox.information(self, "提示", "请先导入数据并完成分析")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 JSON", "prpd_report.json", "JSON (*.json)")
        if path:
            ReportExporter.export_json(self._analysis_result, path)
            self._status_label.setText(f"报告已导出: {path}")

    def _export_excel(self) -> None:
        if not self._analysis_result:
            QMessageBox.information(self, "提示", "请先导入数据并完成分析")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 Excel", "prpd_report.xlsx", "Excel (*.xlsx)")
        if path:
            try:
                ReportExporter.export_excel(self._analysis_result, path)
                self._status_label.setText(f"Excel 已导出: {path}")
            except ImportError as e:
                QMessageBox.warning(self, "导出失败", str(e))

    def _export_word(self) -> None:
        if not self._analysis_result:
            QMessageBox.information(self, "提示", "请先导入数据并完成分析")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 Word", "prpd_report.docx", "Word (*.docx)")
        if path:
            try:
                # 先尝试截图 PRPD 图谱
                chart_path = None
                if HAS_PYQTGRAPH and self._prpd is not None:
                    try:
                        import io

                        from PIL import ImageGrab

                        # 保存 PRPD 控件截图
                        pixmap = self._prpd.grab()
                        chart_dir = Path(path).parent / ".charts"
                        chart_dir.mkdir(exist_ok=True)
                        chart_path = str(chart_dir / "prpd_chart.png")
                        pixmap.save(chart_path)
                    except Exception:
                        chart_path = None

                ReportExporter.export_word(self._analysis_result, path, chart_path)
                self._status_label.setText(f"Word 已导出: {path}")
            except ImportError as e:
                QMessageBox.warning(self, "导出失败", str(e))
            except Exception as e:
                QMessageBox.warning(self, "导出失败", f"报告导出异常: {e}")
