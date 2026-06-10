"""
众星 · 数据模型 — 机机(M2M)视觉压缩协议的核心数据结构
========================================================

Crystal 是整个系统的「通用语」：
  小脑(TextFolder) 输出 Crystal[]
  渲染器(CrystalRenderer) 接收 Crystal[] → 2.5D 晶体图
  大脑(llava/hermes3) 读取晶体图或 Crystal 数据进行推理

人类通道:
    text + category + weight → 理解内容
机器通道:
    depth → alpha/模糊/阴影 → llava通过视觉注意力感知重要性
    颜色(category) → 直接视觉信号 → llava识别语义
    字号(weight) → 视觉显眼度 → llava分配注意力

Z轴 (depth) 的视觉编码映射:
    depth 0.00~0.25: alpha 255→207, blur 0→1px, shadow 3→7px  — 核心层
    depth 0.25~0.50: alpha 207→159, blur 1→3px, shadow 7→12px — 重要层
    depth 0.50~0.85: alpha 159→93,  blur 3→5px, shadow 12→18px — 中间层
    depth 0.85~1.00: alpha 93→65,   blur 5→7px, shadow 18→21px — 背景层
"""
from dataclasses import dataclass

# ── 色彩方案：赛博朋克霓虹 palette ──
COLOR_MAP = {
    "positive":  (0x00, 0xFF, 0x88),   # 霓虹绿 — 收益/利好
    "risk":      (0xFF, 0x33, 0x33),   # 赛博红 — 风险/警告
    "neutral":   (0x33, 0xCC, 0xFF),   # 全息蓝 — 中性/信息
    "highlight": (0xFF, 0xCC, 0x00),   # 晶金黄 — 重点高亮
    "dim":       (0x44, 0x44, 0x66),   # 暗紫灰 — 背景数据
}


@dataclass
class Crystal:
    """单个文字晶体的参数 — 机机视觉压缩协议的核心数据单元"""
    text: str
    category: str = "neutral"          # positive / risk / neutral / highlight / dim
    weight: float = 0.5                # 重要性 (0~1) → 字号
    depth: float = 0.0                 # Z 轴深度 (0=最前, 1=最后) → alpha/模糊/阴影
    x_ratio: float = 0.5              # X 位置比例 (0~1)
    y_ratio: float = 0.5              # Y 位置比例 (0~1)
    rotation: float = 0.0             # 旋转角度（度）

    def __post_init__(self):
        if self.category not in COLOR_MAP:
            self.category = "neutral"
