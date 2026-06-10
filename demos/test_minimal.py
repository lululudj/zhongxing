"""超简验证：跳过 Ollama 小脑，直接用 Python TextFolder + Hermes CPU 大脑"""
import sys, os, json, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import TextFolder, CrystalRenderer

XYJ_PATH = os.path.join(os.path.dirname(__file__), "xyj_full.txt")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(XYJ_PATH, "r", encoding="utf-8") as f:
    body = f.read()
body = body[body.find("第一回"):body.find("End of the Project Gutenberg")] if "第一回" in body else body
print(f"📖 {len(body):,}字")

# 小脑：纯Python规则引擎，秒级
t0 = time.time()
folder = TextFolder(max_chunks=25)
paras = [p.strip() for p in re.split(r'\n\s*\n', body) if len(p.strip()) > 10]
crystals = []
for i in range(0, min(250, len(paras)), 20):
    cs, _, _ = folder.fold("\n".join(paras[i:i+20]), max_chunks=8)
    crystals.extend(cs)
fold_time = time.time() - t0
print(f"🧠 小脑: {fold_time:.1f}s → {len(crystals)}晶体")

# 渲染
renderer = CrystalRenderer()
img = renderer.render(crystals, title="⚡ 西游记 · 晶体折叠",
    subtitle=f"Python规则引擎 {fold_time:.1f}s | {len(crystals)}晶体")
img.save(os.path.join(OUTPUT_DIR, "xyj_final.png"))
print(f"🎨 晶体图已保存")

# 大脑：Hermes 3 CPU 推理（GPU暂不可用就用CPU）
crystal_summary = "\n".join(f"[{c.category}] {c.text[:50]}" for c in crystals[:20])
print(f"🧠 大脑推理...")
import ollama
t0 = time.time()
r = ollama.chat(model="hermes3", messages=[
    {"role": "system", "content": "基于数据回答。"},
    {"role": "user", "content": f"晶体:\n{crystal_summary[:1500]}\n\n问:西游记核心主题和人物?"},
], options={"num_predict": 256})
print(f"⏱️ {time.time()-t0:.1f}s: {r['message']['content'][:150]}")
print(f"✨ 完成!")
