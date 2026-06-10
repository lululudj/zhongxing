"""
众星 · Crystal3D — 机机中间语 (Machine Interlingua) v1
========================================================
从 Crystal[] 直接转换为文本化3D空间语言，LLM原生可读。

格式:
  [E] id=N x=X y=Y z=Z cat=CATEGORY text="..."
  [V] id=N num=VALUE
  [R] from=N to=M type=T

颜色=类别编码:
  GREEN = positive (利好)
  RED   = risk     (风险)  
  BLUE  = neutral  (中性)
  GOLD  = highlight(重点)
  GRAY  = dim      (背景)

Z轴=深度=重要性:
  z<0.25 = CORE      (核心)
  z<0.50 = IMPORTANT (重要)
  z<0.85 = SUPPORT   (支撑)
  z>0.85 = BACKGROUND(背景)
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import TextFolder
from core.models import COLOR_MAP

CAT_TO_COLOR = {
    "positive":  "GREEN",
    "risk":      "RED",
    "neutral":   "BLUE",
    "highlight": "GOLD",
    "dim":       "GRAY",
}

def z_tier(depth: float) -> str:
    if depth < 0.25: return "CORE"
    if depth < 0.50: return "IMPORTANT"
    if depth < 0.85: return "SUPPORT"
    return "BACKGROUND"

def generate(text: str, title: str = "", max_chunks: int = 20) -> str:
    """从原文生成 Crystal3D 机机中间语"""
    folder = TextFolder(max_chunks=max_chunks)
    crystals, _, _ = folder.fold(text)
    
    lines = []
    if title:
        lines.append(f"// {title}")
    lines.append(f"// Crystal3D v1 · {len(crystals)} nodes")
    lines.append("")
    
    # 图例
    lines.append("[LEGEND]")
    lines.append("  GREEN=positive RED=risk BLUE=neutral GOLD=highlight GRAY=dim")
    lines.append("  Z-tier: z<0.25=CORE  z<0.50=IMPORTANT  z<0.85=SUPPORT  z>0.85=BACKGROUND")
    lines.append("")
    
    # 提取所有数值
    value_id = 1000
    values = []  # (value_id, x, y, z, num_str)
    
    # 实体节点
    for i, c in enumerate(crystals):
        color = CAT_TO_COLOR.get(c.category, "BLUE")
        tier = z_tier(c.depth)
        # 清理文本中的特殊字符
        clean_text = c.text.replace('"', "'").replace('\n', ' ')
        lines.append(
            f"[E] id={i+1} x={c.x_ratio:.3f} y={c.y_ratio:.3f} "
            f"z={c.depth:.3f} tier={tier} color={color} "
            f'text="{clean_text}"'
        )
        
        # 提取数值
        for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(万元?|亿元?|％|%|元|次|个|年|月|天)?', c.text):
            value_id += 1
            num = m.group(1)
            unit = m.group(2) or ""
            values.append((value_id, c.x_ratio, c.y_ratio, c.depth, num, unit))
    
    if crystals:
        lines.append("")
    
    # 数值节点
    for vid, x, y, z, num, unit in values:
        unit_str = f" unit={unit}" if unit else ""
        lines.append(f"[V] id={vid} x={x:.3f} y={y:.3f} z={z:.3f} num={num}{unit_str}")
    
    if values:
        lines.append("")
    
    # 关系：同一 Z 层级的实体间建立相邻关系
    for i in range(len(crystals) - 1):
        c1, c2 = crystals[i], crystals[i+1]
        # 如果 Z 层级相同，建立上下文关系
        if abs(c1.depth - c2.depth) < 0.15:
            lines.append(f"[R] from={i+1} to={i+2} type=NEXT")
    
    return "\n".join(lines)


# ════════════════════════════════════════════
if __name__ == "__main__":
    test = """张三借给李四100万元，年利率5%，期限3年。
王五投资200万元给赵六的公司，占股15%。
李四欠张三80万元，至今未还。
赵六的公司2025年营收500万元，净利润120万元，同比增长30%。
王五与张三合作开发新项目，各出资50万元。
李四将欠款中的30万元转给了王五。"""
    
    print(generate(test, title="金融关系测试"))
