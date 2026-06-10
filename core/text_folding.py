"""
众星 · 小脑 — 文本折叠引擎
============================
核心功能：将原始长文本解析、分类、打分，生成 Crystal 结构化数据。

架构设计：
  1. 文本分块与关键词提取
  2. 语义分类（positive/risk/neutral/highlight/dim）
  3. 重要性权重打分
  4. 自动布局（根据语义关系分配 X/Y 位置和 Z 深度）
  5. 输出 Crystal 对象列表，供渲染器使用

Author: Hermes Agent @ CTO 指令
"""
import re
import math
import json
import random
from typing import Optional
from dataclasses import dataclass, field
from .models import Crystal
from .crystal_renderer import CrystalRenderer


# ── 关键词映射表（可扩展） ──
KEYWORD_CATEGORIES = {
    "positive": [
        "增长", "盈利", "突破", "创新", "领先", "增长", "创纪录",
        "新高", "利好", "收益", "利润", "提升", "优化", "成功",
        "优势", "里程碑", "扩张", "市占率", "增速", "翻倍",
        "growth", "profit", "record", "breakthrough", "lead",
        "revenue", "gain", "surge", "bullish", "positive",
    ],
    "risk": [
        "风险", "下降", "亏损", "关税", "制裁", "调查", "诉讼",
        "跌", "减少", "放缓", "危机", "警告", "挑战", "威胁",
        "竞争", "不稳定", "波动", "下滑", "拖累", "压力",
        "risk", "decline", "loss", "tariff", "lawsuit", "threat",
        "volatile", "downturn", "bearish", "warning",
    ],
    "highlight": [
        "核心", "重点", "关键", "最大", "首次", "独家",
        "重磅", "颠覆", "里程碑", "史无前例", "革命性",
        "核心亮点", "值得关注",
        "key", "core", "milestone", "first", "breakthrough",
        "revolutionary", "flagship",
    ],
}

# 数字模式 (用于提取数据点)
NUM_PATTERN = re.compile(r"[+-]?\d+[\.\d]*(?:\s*[万亿亿百万千%美元亿元]|%)?")
PERCENT_PATTERN = re.compile(r"[+-]?\d+\.?\d*%")


@dataclass
class FoldedChunk:
    """文本折叠后的一个信息块"""
    text: str
    category: str = "neutral"
    weight: float = 0.5       # 0~1 重要性
    has_number: bool = False   # 是否包含数值
    depth_hint: Optional[float] = None  # 可选深度建议


class TextFolder:
    """
    小脑 — 文本折叠引擎
    ───────────────────
    接收原始文本 → 分块 → 分类 → 打分 → 自动布局 → 输出 Crystal[]
    """

    def __init__(self, max_chunks: int = 30):
        self.max_chunks = max_chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """将文本分割为句子"""
        # 按中文/英文句号、感叹号、问号、换行分割
        raw = re.split(r"[。！？\n!?]+", text)
        return [s.strip() for s in raw if len(s.strip()) > 3]

    def _categorize(self, sentence: str) -> str:
        """对单句进行语义分类"""
        s_lower = sentence.lower()
        scores = {"positive": 0, "risk": 0, "highlight": 0}

        for cat, keywords in KEYWORD_CATEGORIES.items():
            for kw in keywords:
                if kw.lower() in s_lower:
                    scores[cat] += 1

        # 如果包含数字且是正面的关键词匹配，加强 positive
        if NUM_PATTERN.search(sentence) and scores["positive"] > 0:
            scores["positive"] += 1

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "neutral"
        return best

    def _score_weight(self, sentence: str, category: str) -> float:
        """评估句子重要性权重 (0~1)"""
        w = 0.3  # 基础权重

        # 数字 → 加权重
        nums = NUM_PATTERN.findall(sentence)
        if nums:
            w += 0.15 * min(len(nums) / 3, 1.0)
            # 百分比额外加分
            pcts = PERCENT_PATTERN.findall(sentence)
            if pcts:
                w += 0.1 * min(len(pcts) / 2, 1.0)

        # 关键词 → 加权重
        for cat, keywords in KEYWORD_CATEGORIES.items():
            for kw in keywords:
                if kw.lower() in sentence.lower():
                    w += 0.05
                    break

        # 长度惩罚（太短的不重要）
        if len(sentence) < 10:
            w -= 0.1
        # 太长也惩罚（可能太啰嗦）
        if len(sentence) > 100:
            w -= 0.05

        # 高亮类别额外加权
        if category == "highlight":
            w += 0.15
        elif category == "positive":
            w += 0.05
        elif category == "risk":
            w += 0.08  # 风险信息在财报中很重要

        return max(0.1, min(1.0, w))

    def _auto_layout(self, chunks: list[FoldedChunk]) -> list[Crystal]:
        """
        自动布局：根据分类和权重分配 X/Y/Z 位置
        
        机机视觉压缩协议的布局策略:
        - 顶层 (depth 0~0.25): highlight / 高权重 positive → 画面中心附近，llava看到最清晰文字
        - 中层 (depth 0.25~0.5): positive / neutral → 中上区域，轻微柔化
        - 后层 (depth 0.5~0.85): risk → 中下区域，明显模糊+阴影
        - 背景层 (depth 0.85~1.0): dim / 低权重 → 边缘，高度模糊
        
        深度不仅控制渲染效果，也是 llava 的视觉注意力引导信号。
        """
        # 按类别分组并排序
        groups = {"highlight": [], "positive": [], "neutral": [], "risk": [], "dim": []}

        for ch in chunks:
            cat = ch.category if ch.category in groups else "neutral"
            groups[cat].append(ch)

        # 每组内按权重排序
        for cat in groups:
            groups[cat].sort(key=lambda x: x.weight, reverse=True)

        crystals = []
        # 预定义布局位置（从中心向外扩散）
        layout_template = {
            "highlight": [
                (0.50, 0.22), (0.50, 0.38), (0.50, 0.15),
                (0.30, 0.28), (0.70, 0.28),
            ],
            "positive": [
                (0.30, 0.22), (0.70, 0.22), (0.20, 0.40), (0.80, 0.40),
                (0.35, 0.52), (0.65, 0.52), (0.15, 0.30), (0.85, 0.30),
            ],
            "neutral": [
                (0.15, 0.50), (0.85, 0.50), (0.25, 0.62), (0.75, 0.62),
                (0.10, 0.40), (0.90, 0.40), (0.35, 0.70), (0.65, 0.70),
            ],
            "risk": [
                (0.50, 0.65), (0.40, 0.72), (0.60, 0.72),
                (0.30, 0.78), (0.70, 0.78), (0.20, 0.82), (0.80, 0.82),
            ],
            "dim": [
                (0.10, 0.65), (0.90, 0.65), (0.05, 0.50), (0.95, 0.50),
                (0.12, 0.78), (0.88, 0.78), (0.08, 0.30), (0.92, 0.30),
            ],
        }

        depth_ranges = {
            "highlight": (0.00, 0.25),
            "positive":  (0.25, 0.50),
            "neutral":   (0.40, 0.65),
            "risk":      (0.55, 0.85),
            "dim":       (0.85, 1.00),
        }

        for cat, chunk_list in groups.items():
            template = layout_template.get(cat, layout_template["neutral"])
            d_min, d_max = depth_ranges.get(cat, (0.5, 0.7))

            for i, ch in enumerate(chunk_list):
                # 位置：循环使用模板，超出则随机
                if i < len(template):
                    xr, yr = template[i]
                else:
                    xr = 0.1 + random.uniform(0, 0.8)
                    yr = 0.1 + random.uniform(0, 0.8)

                # 深度：权重越高越靠前
                if ch.depth_hint is not None:
                    depth = ch.depth_hint
                else:
                    depth = d_max - (d_max - d_min) * ch.weight

                # 小随机偏移避免完全对齐
                xr += random.uniform(-0.02, 0.02)
                yr += random.uniform(-0.02, 0.02)
                xr = max(0.02, min(0.98, xr))
                yr = max(0.02, min(0.98, yr))

                crystal = Crystal(
                    text=ch.text[:80],  # 截断过长文本
                    category=cat,
                    weight=ch.weight,
                    depth=depth,
                    x_ratio=xr,
                    y_ratio=yr,
                    rotation=random.uniform(-2, 2),  # 轻微旋转增加自然感
                )
                crystals.append(crystal)

        return crystals

    def fold(self, text: str, title: str = "", subtitle: str = "",
             max_chunks: Optional[int] = None) -> tuple[list[Crystal], str, str]:
        """
        主入口：折叠文本 → Crystal 列表

        Parameters
        ----------
        text : str
            原始长文本
        title : str
            结果图片标题
        subtitle : str
            结果图片副标题
        max_chunks : int, optional
            最大晶体块数

        Returns
        -------
        (crystals, title, subtitle)
        """
        max_c = max_chunks or self.max_chunks

        # 1. 分句
        sentences = self._split_into_sentences(text)
        if not sentences:
            return [], title, subtitle

        # 2. 分类 + 打分
        chunks = []
        for s in sentences[:max_c * 2]:  # 多取一些以便筛选
            cat = self._categorize(s)
            w = self._score_weight(s, cat)
            chunks.append(FoldedChunk(
                text=s,
                category=cat,
                weight=w,
                has_number=bool(NUM_PATTERN.search(s)),
            ))

        # 3. 按权重排序，取 top N
        chunks.sort(key=lambda x: x.weight, reverse=True)
        chunks = chunks[:max_c]

        # 4. 自动布局
        crystals = self._auto_layout(chunks)

        return crystals, title, subtitle

    def fold_from_file(self, filepath: str, encoding: str = "utf-8",
                       title: str = "", subtitle: str = "",
                       max_chunks: Optional[int] = None) -> tuple[list[Crystal], str, str]:
        """从文件读取文本并折叠"""
        with open(filepath, "r", encoding=encoding) as f:
            text = f.read()
        return self.fold(text, title=title, subtitle=subtitle, max_chunks=max_chunks)
