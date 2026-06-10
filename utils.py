"""
众星 · 公共工具库
================
提取 gradio_app.py 和 zhongxing.py 的重复逻辑：
- 词频统计（滑动窗口法）
- 问题路由
- 模型热切换
- Crystal 格式化输出

Author: Hermes Agent
"""
import re
import time
import logging
from collections import Counter
from typing import Optional

logger = logging.getLogger("zhongxing")


# ════════════════════════════════════════════
# 词频统计
# ════════════════════════════════════════════

# 中文停用词（单字 + 常见2字组合）
STOP_WORDS_1 = set("的了是在不我他有这也为之就都而及与么然但所那可以一个上下来去知道说")
STOP_WORDS_2 = {"的是", "是在", "在不", "不是", "是我", "我他", "他有", "也有", "这也是", 
                "为之", "就都", "都而", "而及", "及与", "可以", "一个", "上来", "下来", 
                "去说", "知道", "那是", "所以", "但是", "然而", "所那", "可以", "了是"}
STOP_WORDS = STOP_WORDS_1 | STOP_WORDS_2

def extract_word_freq(text: str, top_n: int = 20) -> list[tuple[str, int]]:
    """
    重叠滑动窗口提取2字中文词频。
    
    为什么用滑动窗口而不是正则？
    - re.findall(r'[\u4e00-\u9fff]{2,4}', text) 是贪心匹配，会优先吃掉4字长串
    - 导致2字短词（如"萧炎"）被吞掉
    - 滑动窗口保证所有相邻2字都被统计到
    """
    freq = Counter()
    chars = list(text)
    for i in range(len(chars) - 1):
        w = chars[i] + chars[i + 1]
        if '\u4e00' <= w[0] <= '\u9fff' and '\u4e00' <= w[1] <= '\u9fff':
            freq[w] += 1
    return [(w, c) for w, c in freq.most_common(top_n + len(STOP_WORDS)) 
            if w not in STOP_WORDS][:top_n]


def extract_targets(question: str) -> set[str]:
    """
    从问题中提取所有可能的搜索目标词。
    三种策略叠加：
    1. 滑动窗口：2-4字单/双词（覆盖人名、关键词）
    2. 完整中文短语：连续中文字符段
    3. 短语的所有2-6字子串（覆盖"花花更新"等组合词）
    """
    targets = set()
    # 策略1：滑动窗口
    for i in range(len(question)):
        for l in [2, 3, 4]:
            w = question[i:i + l]
            if len(w) == l and all('\u4e00' <= c <= '\u9fff' for c in w):
                targets.add(w)
    # 策略2+3：完整中文短语的所有子串
    for match in re.finditer(r'[\u4e00-\u9fff]{2,}', question):
        phrase = match.group()
        targets.add(phrase)
        # 提取所有2-6字子串
        for length in range(2, min(len(phrase) + 1, 7)):
            for i in range(len(phrase) - length + 1):
                targets.add(phrase[i:i + length])
    return targets


def count_in_text(text: str, targets: set[str]) -> dict[str, int]:
    """在文本中精确统计每个目标词的出现次数"""
    results = {}
    for t in targets:
        count = text.count(t)
        if count > 0:
            results[t] = count
    return results


# ════════════════════════════════════════════
# 问题路由
# ════════════════════════════════════════════

VISUAL_KEYWORDS = ["图", "晶体", "彩色", "空间", "分布", "拓扑", "阵营", "画", "视觉", "看图", "读取", "这张"]
COUNT_KEYWORDS = ["几次", "多少个", "出现", "提到", "次数", "频次", "统计", "多少", "TOP", "频率", "计数"]

def route(question: str) -> str:
    """
    规则路由器：0.001s 判断问题类型。
    返回 "VISUAL" 或 "TEXT"
    """
    if any(k in question for k in VISUAL_KEYWORDS):
        return "VISUAL"
    return "TEXT"


# ════════════════════════════════════════════
# Ollama 模型管理
# ════════════════════════════════════════════

def ollama_chat_with_retry(model: str, messages: list, options: dict, 
                           max_retries: int = 2) -> str:
    """调用 Ollama 并自动重试"""
    import ollama
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"重试第 {attempt} 次: {model}")
                time.sleep(1 * attempt)
            resp = ollama.chat(model=model, messages=messages, options=options)
            return resp['message']['content']
        except Exception as e:
            last_err = e
            logger.warning(f"Ollama 调用失败 (attempt {attempt+1}): {e}")
    raise last_err


def switch_model(target: str, gpu_layers: int = 99) -> bool:
    """热切换 GPU 模型（预热目标模型）"""
    try:
        import ollama
        # 预热目标模型
        ollama.chat(
            model=target,
            messages=[{"role": "user", "content": "ok"}],
            options={"num_predict": 5, "num_gpu": gpu_layers}
        )
        logger.info(f"模型已切换: {target}")
        return True
    except Exception as e:
        logger.error(f"模型切换失败 [{target}]: {e}")
        return False


# ════════════════════════════════════════════
# Crystal 数据格式化
# ════════════════════════════════════════════

def format_crystal_text(crystals: list, word_freq: list[tuple[str, int]]) -> str:
    """
    将 Crystal 列表格式化为可读文本（用于注入 LLM prompt）。
    """
    # Z轴深度分层
    def z_tier(d):
        if d < 0.25: return "🔴核心层"
        if d < 0.5:  return "🟡重要层"
        if d < 0.85: return "🟠中间层"
        return "⚫背景层"
    
    depth_groups = {}
    for c in crystals:
        tier = z_tier(c.depth)
        depth_groups.setdefault(tier, []).append(c)
    
    depth_sections = []
    for tier in ["🔴核心层", "🟡重要层", "🟠中间层", "⚫背景层"]:
        if tier in depth_groups:
            items = depth_groups[tier]
            depth_sections.append(f"\n### {tier} (Z深度 {items[0].depth:.2f}~{items[-1].depth:.2f}) ###")
            depth_sections.extend(f"  [{c.category}] (depth={c.depth:.2f}) {c.text[:60]}" for c in items)
    
    return (
        "【词频 Top20（精确）】\n" +
        "\n".join(f"  「{w}」= {c}次" for w, c in word_freq) +
        f"\n\n【晶体Z轴深度分层 ({len(crystals)}个晶体)】\n" +
        "注意：depth 越小越重要 — 核心层depth<0.25，重要层0.25~0.5，中间层0.5~0.85，背景层>0.85" +
        "\n".join(depth_sections)
    )


def format_status(crystals: list) -> str:
    """格式化晶体状态摘要"""
    cats = {}
    for c in crystals:
        cats[c.category] = cats.get(c.category, 0) + 1
    return f"✅ {len(crystals)}晶体 | " + " ".join(f"{k}:{v}" for k, v in sorted(cats.items()))
