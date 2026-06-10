"""
众星 V3.0 — 正确架构压测
========================
小脑: qwen2.5:1.5b CPU (几百MB，秒级)
大脑: hermes3 GPU (<10秒)

验证 10 秒极限：小脑3秒/块 × N块 + 大脑 <10秒
"""
import sys, os, json, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

XYJ_PATH = os.path.join(os.path.dirname(__file__), "xyj_full.txt")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载文本（前3回 = 约 6-8 块）
with open(XYJ_PATH, "r", encoding="utf-8") as f:
    body = f.read()
start = body.find("第一回")
body = body[start:] if start >= 0 else body
end = body.find("End of the Project Gutenberg")
if end > 0: body = body[:end]

# 分块
paras = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
chunks = []
for i in range(0, min(30, len(paras)), 8):
    chunk = "\n".join(paras[i:i+8])
    if len(chunk) > 100:
        chunks.append(chunk)

print(f"📊 西游记 — 正确架构压测")
print(f"   文本: {sum(len(c) for c in chunks)} 字, {len(chunks)} 块\n")

CRYSTAL_PROMPT = """Extract structured data as JSON only. No extra text.
{"entities":[{"name":"str","type":"character|location|deity|creature|object"}],
 "key_events":[{"event":"str","actors":["str"]}],
 "locations":[{"name":"str"}]}"""

import ollama

# ── 测试不同模型的 CPU 推理速度 ──
models_to_test = [
    ("qwen2.5:1.5b", "🧠 小脑(1.5B)"),
    ("qwen2.5:3b",   "🧠 小脑(3B)"),
]

results = {}

for model_name, label in models_to_test:
    print(f"\n{label} CPU 测试 (num_gpu=0)...")
    total_time = 0
    chunk_times = []
    entity_counts = []
    
    for i, chunk in enumerate(chunks[:4]):  # 各测4块
        t0 = time.time()
        resp = ollama.chat(model=model_name, messages=[
            {"role": "system", "content": CRYSTAL_PROMPT},
            {"role": "user", "content": chunk},
        ], options={"num_gpu": 0, "temperature": 0.1, "num_predict": 512})
        elapsed = time.time() - t0
        j = re.search(r'\{.*\}', resp["message"]["content"], re.DOTALL)
        ents = 0
        if j:
            try:
                data = json.loads(j.group())
                ents = len(data.get("entities", []))
            except: pass
        total_time += elapsed
        chunk_times.append(elapsed)
        entity_counts.append(ents)
        print(f"   块{i+1}: {elapsed:.1f}s → {ents}实体")
    
    avg = total_time / len(chunk_times)
    print(f"   📊 平均: {avg:.1f}s/块 | 总{len(chunks)}块预计: {avg*len(chunks):.0f}s")
    results[model_name] = {"avg": avg, "chunks": chunk_times, "entities": entity_counts}

# ── 大脑 GPU 测试 ──
print(f"\n🧠 大脑 GPU 测试 (hermes3, num_gpu=99)...")
# 先小脑用1.5b跑完整第1回，给大脑喂晶体
crp = ollama.chat(model="qwen2.5:1.5b", messages=[
    {"role": "system", "content": CRYSTAL_PROMPT},
    {"role": "user", "content": chunks[0]},
], options={"num_gpu": 0, "temperature": 0.1, "num_predict": 512})

crp_json = {}
j = re.search(r'\{.*\}', crp["message"]["content"], re.DOTALL)
if j:
    crp_json = json.loads(j.group())

crystal_text = json.dumps(crp_json, ensure_ascii=False, indent=2)

questions = [
    "西游记第一回讲述的核心事件是什么？提到了哪些主要角色和地点？",
    "从提取的信息来看，故事中有哪些神话元素或超自然现象？",
]

brain_times = []
for q in questions:
    t0 = time.time()
    resp = ollama.chat(model="hermes3", messages=[
        {"role": "system", "content": "你是众星的大脑引擎。基于晶体数据推理，语言简洁。"},
        {"role": "user", "content": f"晶体:\n{crystal_text[:1500]}\n\n问题:{q}"},
    ], options={"num_gpu": 99, "temperature": 0.3, "num_predict": 512})
    elapsed = time.time() - t0
    brain_times.append(elapsed)
    mark = "🎯" if elapsed < 10 else "⚠️"
    print(f"   {mark} {elapsed:.2f}s: {q[:25]}...")
    print(f"     → {resp['message']['content'][:120]}...")

brain_avg = sum(brain_times) / len(brain_times)

# ── 最终报告 ──
print(f"\n{'='*55}")
print(f"  🏆 众星 V3.0 — 架构压测报告")
print(f"{'='*55}")
print(f"\n📦 模型部署:")
print(f"   小脑(CPU): qwen2.5:1.5b ({results['qwen2.5:1.5b']['avg']:.1f}s/块)")
if 'qwen2.5:3b' in results:
    print(f"   小脑(CPU): qwen2.5:3b   ({results['qwen2.5:3b']['avg']:.1f}s/块)")
print(f"   大脑(GPU): hermes3       ({brain_avg:.2f}s/问)")

print(f"\n📐 全链路预估:")
print(f"   60万字全本 ≈ {len(body)//2000}块 × {results['qwen2.5:1.5b']['avg']:.0f}s/块")
total_est = (len(body) // 2000) * results['qwen2.5:1.5b']['avg']
print(f"   → 小脑折叠: {total_est:.0f}s = {total_est/60:.1f} 分钟")
print(f"   → 大脑推理: {brain_avg:.2f}s/问 {'✅ 达成10秒目标' if brain_avg < 10 else '❌'}")

# 保存报告
report_path = os.path.join(OUTPUT_DIR, "benchmark_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump({
        "cerebellum_models": {k: {"avg_s_per_chunk": v["avg"]} for k,v in results.items()},
        "brain_model": "hermes3",
        "brain_avg_s": brain_avg,
        "brain_10s_target": brain_avg < 10,
        "full_book_estimate_minutes": round(total_est/60, 1),
    }, f, ensure_ascii=False, indent=2)

print(f"\n📋 报告保存: {report_path}")
print(f"\n✨ 架构验证完成！")
