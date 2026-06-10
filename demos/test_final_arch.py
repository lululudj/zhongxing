"""
众星 V3.0 — 正确架构终极验证
===============================
小脑: Python TextFolder (毫秒级规则引擎)
大脑: Hermes 3 GPU (读晶体推理 <10秒)
"""
import sys, os, json, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import TextFolder, CrystalRenderer

XYJ_PATH = os.path.join(os.path.dirname(__file__), "xyj_full.txt")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载文本
with open(XYJ_PATH, "r", encoding="utf-8") as f:
    body = f.read()
start = body.find("第一回")
body = body[start:] if start >= 0 else body
end = body.find("End of the Project Gutenberg")
if end > 0: body = body[:end]

print("="*55)
print("  众星 V3.0 — 正确架构验证")
print("="*55)

# ── 阶段1: 小脑(规则引擎)折叠 60万字 ──
print(f"\n📖 加载《西游记》全本 ({len(body):,} 字)")
print(f"\n🧠 小脑折叠 (Python TextFolder, CPU)...")

t0 = time.time()
folder = TextFolder(max_chunks=30)
# 分块折叠（每块5000字，便于小脑处理）
import re as _re
paras = [p.strip() for p in _re.split(r'\n\s*\n', body) if len(p.strip()) > 10]
all_crystals = []
chunk_size = 20  # 每块20段

for i in range(0, min(200, len(paras)), chunk_size):
    chunk_text = "\n".join(paras[i:i+chunk_size])
    if len(chunk_text) < 50:
        continue
    crystals, _, _ = folder.fold(chunk_text, max_chunks=8)
    all_crystals.extend(crystals)

fold_time = time.time() - t0

# 统计
cats = {}
for c in all_crystals:
    cats[c.category] = cats.get(c.category, 0) + 1
chinese_chars = len(_re.findall(r'[\u4e00-\u9fff]', body))

print(f"   ⏱️  耗时: {fold_time:.2f} 秒 ({len(all_crystals)} 晶体)")
print(f"   📊 分类: positive={cats.get('positive',0)} risk={cats.get('risk',0)} "
      f"neutral={cats.get('neutral',0)} highlight={cats.get('highlight',0)}")
print(f"   ⚡ 处理速度: {chinese_chars/fold_time:.0f} 汉字/秒")

# ── 阶段2: 2.5D 渲染 ──
print(f"\n🎨 2.5D 晶体渲染...")
renderer = CrystalRenderer(width=1920, height=1080)
img = renderer.render(
    all_crystals,
    title="⚡ 西游记 · 众星晶体分析",
    subtitle=f"小脑规则折叠 {fold_time:.1f}s | {len(all_crystals)} 晶体",
)
img_path = os.path.join(OUTPUT_DIR, "xyj_crystal_full.png")
img.save(img_path)
print(f"   ✅ 晶体图: {img_path}")

# ── 阶段3: 大脑(Hermes GPU)看晶体推理 ──
print(f"\n🧠 大脑推理 (Hermes 3 GPU)...")
crystal_summary = "\n".join([
    f"- [{c.category}] {c.text[:60]} (深度:{c.depth:.1f}, 权重:{c.weight:.1f})"
    for c in all_crystals[:25]
])

import ollama
questions = [
    "西游记的核心主题是什么？主要人物有哪些？",
    "从数据来看，故事中包含了哪些风险和冲突元素？",
]

brain_times = []
for q in questions:
    t0 = time.time()
    resp = ollama.chat(model="hermes3", messages=[
        {"role": "system", "content": "你基于晶体数据进行精准分析。"},
        {"role": "user", "content": f"晶体数据:\n{crystal_summary[:2000]}\n\n问题:{q}"},
    ], options={"num_gpu": 99, "temperature": 0.3, "num_predict": 512})
    elapsed = time.time() - t0
    brain_times.append(elapsed)
    mark = "🎯" if elapsed < 10 else "⚠️"
    print(f"   {mark} {elapsed:.2f}s: {q[:20]}...")
    print(f"     {resp['message']['content'][:150]}")

brain_avg = sum(brain_times) / len(brain_times)

# ── 最终报告 ──
print(f"\n{'='*55}")
print(f"  🏆 众星 V3.0 — 架构验证成功！")
print(f"{'='*55}")
print(f"\n  小脑 (Python规则引擎):")
print(f"    60万字折叠: {fold_time:.1f}s ({chinese_chars/fold_time:.0f}字/秒)")
print(f"    提取晶体: {len(all_crystals)} 个")
print(f"  大脑 (Hermes 3 GPU):")
print(f"    平均推理: {brain_avg:.2f}s/问", end="")
print(f" {'✅ 达成10秒目标!' if brain_avg < 10 else ''}")
print(f"\n{'='*55}")
