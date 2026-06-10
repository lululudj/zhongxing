"""GPU大脑极速压测 — hermes3 独占 RTX 4060"""
import time, ollama

# 先预热（第一次加载慢）
print("🔥 GPU 预热...")
ollama.chat(model="hermes3", messages=[
    {"role": "user", "content": "say ok"}
], options={"num_gpu": 99, "num_predict": 10})
print("   预热完成\n")

# 正式测试
questions = [
    "西游记讲述了什么故事？核心人物有哪些？",
    "取经团队经历的磨难本质是什么？",
    "分析孙悟空性格中的矛盾与成长。",
]

print(f"🚀 GPU 大脑推理基准 (hermes3 + RTX 4060)")
print(f"{'='*50}")
times = []
for q in questions:
    t0 = time.time()
    r = ollama.chat(model="hermes3", messages=[
        {"role": "system", "content": "你基于数据推理，语言简洁。"},
        {"role": "user", "content": f"问题: {q}"},
    ], options={"num_gpu": 99, "num_predict": 256, "temperature": 0.3})
    elapsed = time.time() - t0
    times.append(elapsed)
    mark = "⚡" if elapsed < 10 else "⚠️"
    print(f"  {mark} {elapsed:.2f}s | {q[:25]}...")

avg = sum(times) / len(times)
print(f"\n{'='*50}")
print(f"  📊 平均: {avg:.2f}s")
print(f"  🎯 10秒目标: {'✅ 达成!' if avg < 10 else f'❌ 差{avg-10:.1f}s'}")
print(f"  🏆 最快: {min(times):.2f}s")
print(f"{'='*50}")
