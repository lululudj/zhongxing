"""
众星 · 语义保真度诊断工具
===========================
测量压缩链路中每一层的信息损失：
  原始文本 → Crystal[] → 文字通道复述 → 视觉通道复述
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import TextFolder, CrystalRenderer
from collections import Counter

# ════════════════════════════════════════════
# 1. 加载原文 + 定义基准事实
# ════════════════════════════════════════════
with open("test_semantic_fidelity.txt", "r", encoding="utf-8") as f:
    original = f.read()

GROUND_TRUTH = {
    "entities": {
        "张三": {"mentions": 2, "roles": ["借款人", "合作方"]},
        "李四": {"mentions": 3, "roles": ["欠款人", "债权人"]},
        "王五": {"mentions": 3, "roles": ["投资人", "合作方"]},
        "赵六": {"mentions": 2, "roles": ["公司创始人"]},
    },
    "numbers": {
        "100": 2,  # 100万 出现2次
        "200": 1,  # 200万
        "80": 1,
        "500": 1,
        "120": 1,
        "50": 1,
        "5": 1,
        "3": 1,
        "15": 1,
        "30": 2,  # 30万 + 30%
    },
    "relationships": [
        ("张三", "李四", "借款", "100万"),
        ("王五", "赵六", "投资", "200万"),
        ("李四", "张三", "欠款", "80万"),
        ("王五", "张三", "合作", "各50万"),
        ("李四", "王五", "转款", "30万"),
    ],
}

print("=" * 60)
print("  众星 · 语义保真度诊断")
print("=" * 60)

# ════════════════════════════════════════════
# 2. 小脑压缩 → Crystal[] 
# ════════════════════════════════════════════
folder = TextFolder(max_chunks=20)
crystals, _, _ = folder.fold(original)

print(f"\n📦 原文: {len(original)} 字符")
print(f"📦 Crystal: {len(crystals)} 个晶体块")

# 统计 Crystal 中保留了哪些信息
crystal_text = " ".join(c.text for c in crystals)
print(f"\n--- Crystal 层信息保留 ---")

# 实体保留率
for name, info in GROUND_TRUTH["entities"].items():
    in_original = original.count(name)
    in_crystal = crystal_text.count(name)
    rate = in_crystal / in_original * 100 if in_original else 0
    status = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
    print(f"  {status} {name}: 原文{in_original}次 → Crystal{in_crystal}次 ({rate:.0f}%)")

# 数字保留率
print(f"\n  数字保留:")
num_total, num_found = 0, 0
for num, count in GROUND_TRUTH["numbers"].items():
    in_crystal = crystal_text.count(num)  # 中文环境用简单计数
    found = min(in_crystal, count)
    num_total += count
    num_found += found
    rate = in_crystal / count * 100 if count else 100
    status = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
    print(f"  {status} 数字「{num}」: 原文{count}次 → Crystal{in_crystal}次 ({rate:.0f}%)")
num_rate = num_found / num_total * 100 if num_total else 0
print(f"  {'✅' if num_rate >= 80 else '⚠️' if num_rate >= 50 else '❌'} 关键数字保留率: {num_found}/{num_total} ({num_rate:.0f}%)")

# 关系保留率
print(f"\n  关系保留:")
rel_count = 0
for a, b, rel_type, amount in GROUND_TRUTH["relationships"]:
    # 检查 Crystal 中是否同时出现两个实体
    has_a = a in crystal_text
    has_b = b in crystal_text
    # 金额中的数字是否在 Crystal 中出现
    amount_digits = re.sub(r'[^0-9]', '', amount)
    has_amount = amount_digits and amount_digits in crystal_text
    ok = has_a and has_b and (has_amount or amount in crystal_text)
    rel_count += 1 if ok else 0
    print(f"  {'✅' if ok else '❌'} {a}→{b} [{rel_type} {amount}]")

rel_rate = rel_count / len(GROUND_TRUTH["relationships"]) * 100
print(f"\n  关系保留率: {rel_count}/{len(GROUND_TRUTH['relationships'])} ({rel_rate:.0f}%)")

# ════════════════════════════════════════════
# 3. 汇总
# ════════════════════════════════════════════
print(f"\n{'=' * 60}")
print(f"  压缩层保真度汇总")
print(f"{'=' * 60}")
print(f"  实体保留率: {sum(1 for n in GROUND_TRUTH['entities'] if len(re.findall(re.escape(n), crystal_text)) / max(1, len(re.findall(re.escape(n), original))) >= 0.5)}/{len(GROUND_TRUTH['entities'])}")
print(f"  数字保留率: {num_found}/{num_total} ({num_rate:.0f}%)")
print(f"  关系保留率: {rel_count}/{len(GROUND_TRUTH['relationships'])} ({rel_rate:.0f}%)")

# 整体评分
total_score = (num_rate + rel_rate + sum(
    min(100, len(re.findall(re.escape(n), crystal_text)) / max(1, len(re.findall(re.escape(n), original))) * 100)
    for n in GROUND_TRUTH["entities"]
) / len(GROUND_TRUTH["entities"])) / 3

print(f"\n  📊 压缩层综合保真度: {total_score:.0f}%")
print(f"  {'🟢 保真度良好' if total_score >= 80 else '🟡 有信息损失' if total_score >= 60 else '🔴 损失严重'}")
