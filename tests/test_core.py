"""
众星 · 单元测试
===============
测试核心功能：词频统计、问题路由、文本折叠、Crystal 模型
"""
import sys
import os
import pytest

# 加入项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    extract_word_freq, extract_targets, count_in_text,
    route, format_crystal_text, format_status,
)
from core.models import Crystal, COLOR_MAP
from core.text_folding import TextFolder


# ════════════════════════════════════════════
# 词频统计测试
# ════════════════════════════════════════════

class TestWordFreq:
    def test_basic_freq(self):
        """基本词频统计"""
        text = "萧炎萧炎萧炎"
        freq = extract_word_freq(text, top_n=5)
        assert len(freq) >= 1
        assert freq[0] == ("萧炎", 3)
    
    def test_sliding_window(self):
        """滑动窗口不会漏掉短词"""
        text = "的萧炎的萧炎的"  # "的萧" 和 "萧炎" 都应该被统计
        freq = extract_word_freq(text, top_n=10)
        freq_dict = dict(freq)
        assert "萧炎" in freq_dict
        assert freq_dict["萧炎"] == 2
    
    def test_stop_words_filtered(self):
        """停用词被过滤"""
        text = "的是在不是我他有这也为之"
        freq = extract_word_freq(text, top_n=20)
        words = [w for w, _ in freq]
        assert "的是" not in words
        assert "是在" not in words
    
    def test_empty_text(self):
        """空文本"""
        freq = extract_word_freq("", top_n=5)
        assert freq == []
    
    def test_no_chinese(self):
        """纯英文文本"""
        freq = extract_word_freq("hello world", top_n=5)
        assert freq == []


# ════════════════════════════════════════════
# 目标词提取测试
# ════════════════════════════════════════════

class TestExtractTargets:
    def test_sliding_window(self):
        """滑动窗口提取2-4字词"""
        targets = extract_targets("萧炎出现了几次")
        assert "萧炎" in targets
        assert "出现" in targets
    
    def test_full_phrases(self):
        """完整中文短语"""
        targets = extract_targets("花花更新出现了几次")
        assert "花花更新" in targets  # 4字短语
        assert "花花更新出现" in targets  # 6字短语
    
    def test_empty(self):
        """空问题"""
        targets = extract_targets("")
        assert len(targets) == 0


# ════════════════════════════════════════════
# 文本计数测试
# ════════════════════════════════════════════

class TestCountInText:
    def test_basic_count(self):
        """基本计数"""
        text = "萧炎很厉害，萧炎很强"
        targets = {"萧炎"}
        result = count_in_text(text, targets)
        assert result == {"萧炎": 2}
    
    def test_not_found(self):
        """目标词不存在"""
        text = "萧炎很厉害"
        targets = {"林动"}
        result = count_in_text(text, targets)
        assert result == {}
    
    def test_multiple_targets(self):
        """多个目标词"""
        text = "萧炎和林动都很厉害，萧炎更强"
        targets = {"萧炎", "林动"}
        result = count_in_text(text, targets)
        assert result["萧炎"] == 2
        assert result["林动"] == 1


# ════════════════════════════════════════════
# 问题路由测试
# ════════════════════════════════════════════

class TestRoute:
    def test_visual_keywords(self):
        """视觉关键词触发 VISUAL"""
        assert route("这张图怎么样") == "VISUAL"
        assert route("分析晶体") == "VISUAL"
        assert route("看看空间分布") == "VISUAL"
    
    def test_count_keywords(self):
        """计数关键词触发 TEXT"""
        assert route("萧炎出现了几次") == "TEXT"
        assert route("统计一下多少个") == "TEXT"
    
    def test_default_text(self):
        """默认走文字通道"""
        assert route("萧炎是谁") == "TEXT"
        assert route("分析一下这段话") == "TEXT"


# ════════════════════════════════════════════
# Crystal 模型测试
# ════════════════════════════════════════════

class TestCrystal:
    def test_default_values(self):
        """默认值"""
        c = Crystal(text="测试")
        assert c.category == "neutral"
        assert c.weight == 0.5
        assert c.depth == 0.0
    
    def test_invalid_category_fallback(self):
        """无效分类回退到 neutral"""
        c = Crystal(text="测试", category="invalid")
        assert c.category == "neutral"
    
    def test_color_map_complete(self):
        """颜色映射表完整"""
        expected = {"positive", "risk", "neutral", "highlight", "dim"}
        assert set(COLOR_MAP.keys()) == expected


# ════════════════════════════════════════════
# 文本折叠测试
# ════════════════════════════════════════════

class TestTextFolder:
    def test_fold_basic(self):
        """基本折叠"""
        folder = TextFolder(max_chunks=10)
        text = "营收增长18%。利润创新高。风险提示：市场竞争加剧。"
        crystals, title, subtitle = folder.fold(text, title="测试")
        assert len(crystals) > 0
        assert all(isinstance(c, Crystal) for c in crystals)
    
    def test_fold_empty(self):
        """空文本折叠"""
        folder = TextFolder(max_chunks=10)
        crystals, _, _ = folder.fold("")
        assert crystals == []
    
    def test_fold_max_chunks(self):
        """不超过最大块数"""
        folder = TextFolder(max_chunks=3)
        text = "。".join([f"句子{i}" for i in range(20)])
        crystals, _, _ = folder.fold(text)
        assert len(crystals) <= 3
    
    def test_fold_categories(self):
        """分类正确性"""
        folder = TextFolder(max_chunks=10)
        text = "利润大幅增长。市场份额下降。核心业务突破。"
        crystals, _, _ = folder.fold(text)
        cats = {c.category for c in crystals}
        # 至少应该有 positive 和 risk
        assert "positive" in cats or "highlight" in cats
    
    def test_fold_weights_in_range(self):
        """权重在 0~1 范围内"""
        folder = TextFolder(max_chunks=10)
        text = "营收增长18%。利润创新高。核心业务突破。"
        crystals, _, _ = folder.fold(text)
        for c in crystals:
            assert 0.0 <= c.weight <= 1.0
    
    def test_fold_depth_in_range(self):
        """深度在 0~1 范围内"""
        folder = TextFolder(max_chunks=10)
        text = "营收增长18%。利润创新高。核心业务突破。"
        crystals, _, _ = folder.fold(text)
        for c in crystals:
            assert 0.0 <= c.depth <= 1.0


# ════════════════════════════════════════════
# 格式化输出测试
# ════════════════════════════════════════════

class TestFormat:
    def test_format_status(self):
        """状态格式化"""
        crystals = [
            Crystal(text="a", category="positive"),
            Crystal(text="b", category="risk"),
            Crystal(text="c", category="positive"),
        ]
        status = format_status(crystals)
        assert "3晶体" in status
        assert "positive:2" in status
        assert "risk:1" in status
    
    def test_format_crystal_text(self):
        """Crystal 文本格式化"""
        crystals = [
            Crystal(text="测试内容", category="positive", depth=0.2),
        ]
        word_freq = [("测试", 5)]
        text = format_crystal_text(crystals, word_freq)
        assert "「测试」= 5次" in text
        assert "核心层" in text or "重要层" in text
