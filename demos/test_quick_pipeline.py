"""
众星 V3.0 — 快速全链路验证
============================
取西游记前 2 块做端到端演示：小脑折叠 → 晶体合并 → 大脑推理
预期总耗时 < 5 分钟
"""
import sys, os, json, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

XYJ_PATH = os.path.join(os.path.dirname(__file__), "xyj_full.txt")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载
with open(XYJ_PATH, "r", encoding="utf-8") as f:
    text = f.read()
start = text.find("第一回")
body = text[start:] if start >= 0 else text
end = body.find("End of the Project Gutenberg")
if end > 0:
    body = body[:end]

# 取前 2 块
paras = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
chunk1 = "\n".join(paras[:8])   # ~2000 chars
chunk2 = "\n".join(paras[8:16]) # ~2000 chars

print(f"📄 西游记第1回 ({len(body[:8000])} 字)")
print(f"   块1: {len(chunk1)} 字符")
print(f"   块2: {len(chunk2)} 字符\n")

# ── 小脑 CPU 折叠 ──
import ollama

CRYSTAL_PROMPT = """You are ZhongXing's Cerebellum Engine v3.0.
Analyze the text and output ONLY valid JSON with no extra text.

{
  "entities": [{"name": "str", "type": "character|location|deity|creature|object", "mentions": int, "significance": 0.0-1.0}],
  "key_events": [{"event": "str", "actors": ["str"]}],
  "locations": [{"name": "str", "description": "str"}],
  "relationships": [{"entity_a": "str", "entity_b": "str", "type": "str"}]
}"""

results = []
for i, chunk in enumerate([chunk1, chunk2]):
    t0 = time.time()
    print(f"⏳ 小脑折叠块{i+1} (CPU)...", end=" ", flush=True)
    resp = ollama.chat(model="hermes3", messages=[
        {"role": "system", "content": CRYSTAL_PROMPT},
        {"role": "user", "content": chunk},
    ], options={"num_gpu": 0, "temperature": 0.1, "num_predict": 1024})
    elapsed = time.time() - t0
    j = re.search(r'\{.*\}', resp["message"]["content"], re.DOTALL)
    if j:
        data = json.loads(j.group())
        results.append(data)
        print(f"✅ {elapsed:.0f}s → {len(data.get('entities',[]))}实体 {len(data.get('key_events',[]))}事件")
    else:
        print(f"⚠️ {elapsed:.0f}s → JSON解析失败")

# ── 合并晶体 ──
master = {"source": "西游记", "entities": [], "key_events": [], "locations": [], "relationships": []}
seen = set()
for r in results:
    for e in r.get("entities",[]):
        if e.get("name","") not in seen:
            seen.add(e["name"])
            master["entities"].append(e)
    master["key_events"].extend(r.get("key_events",[]))
    master["locations"].extend(r.get("locations",[]))
    master["relationships"].extend(r.get("relationships",[]))

master_path = os.path.join(OUTPUT_DIR, "xyj_quick_crystal.json")
with open(master_path, "w", encoding="utf-8") as f:
    json.dump(master, f, ensure_ascii=False, indent=2)

print(f"\n🔗 合并完成: {master_path}")
print(f"   实体: {len(master['entities'])} | 事件: {len(master['key_events'])}")
print(f"   地点: {len(master['locations'])} | 关系: {len(master['relationships'])}")

# ── 大脑 GPU 推理 ──
print(f"\n🧠 大脑推理 (GPU, hermes3)...")
crystal_summary = json.dumps(master, ensure_ascii=False, indent=2)[:2000]

questions = [
    "西游记开篇讲了什么故事？提到了哪些主要人物和地点？",
    "故事中出现了哪些具有神奇能力的人物或生物？",
]

for q in questions:
    t0 = time.time()
    resp = ollama.chat(model="hermes3", messages=[
        {"role": "system", "content": "你是众星的大脑引擎。基于晶体数据进行精准推理。"},
        {"role": "user", "content": f"晶体数据：\n{crystal_summary}\n\n问题：{q}"},
    ], options={"num_gpu": 99, "temperature": 0.3, "num_predict": 1024})
    elapsed = time.time() - t0
    mark = "🎯" if elapsed < 10 else "⚠️"
    print(f"\n   Q: {q}")
    print(f"   {mark} {elapsed:.2f}s {'(达成10秒目标!)' if elapsed < 10 else '(未达标)'}")
    print(f"   A: {resp['message']['content'][:200]}...")

# ── 也跑一下 xiaonao:qwen2.5 对比（如果存在） ──
print(f"\n📊 对比测试: xiaonao:qwen2.5 (Qwen2.5专用小脑)...")
try:
    t0 = time.time()
    resp = ollama.chat(model="xiaonao:qwen2.5", messages=[
        {"role": "system", "content": CRYSTAL_PROMPT},
        {"role": "user", "content": chunk1},
    ], options={"num_gpu": 0, "temperature": 0.1, "num_predict": 1024})
    elapsed = time.time() - t0
    j = re.search(r'\{.*\}', resp["message"]["content"], re.DOTALL)
    if j:
        data = json.loads(j.group())
        print(f"   ✅ xiaonao:qwen2.5 CPU: {elapsed:.0f}s → {len(data.get('entities',[]))}实体 {len(data.get('key_events',[]))}事件")
    else:
        print(f"   ⚠️ xiaonao:qwen2.5 CPU: {elapsed:.0f}s → JSON解析失败")
except Exception as e:
    print(f"   ⚠️ xiaonao:qwen2.5 不可用: {e}")

print(f"\n✨ 全链路验证完成！")
print(f"   主晶体: {master_path}")
