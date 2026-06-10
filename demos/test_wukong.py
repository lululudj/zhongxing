"""
众星 V3.0 — test_wukong.py
=============================
《西游记》全本结构化折叠压测

架构：
  1. 小脑 (CPU)：分块折叠 60 万字 → 子晶体列表
  2. 晶体合并：子晶体 → 主晶体（JSON）
  3. 大脑 (GPU)：读主晶体 → 深度推理问答（冲击 10 秒）

Usage:
  python test_wukong.py [--chapters N] [--chunk-size N]
"""
import json
import re
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 小脑 Crystal Schema（Hermes 3 结构化输出） ──
CRYSTAL_SYSTEM_PROMPT = """You are ZhongXing's Cerebellum Engine v3.0.
Analyze the given Chinese classical text chunk and output ONLY valid JSON.
NEVER include explanations, markdown, or any text outside the JSON.

Output JSON Schema:
{
  "crystal_version": "3.0",
  "chunk_id": "string",
  "summary": "string",
  "entities": [
    {
      "name": "string",
      "type": "character|location|object|event|concept|deity|creature",
      "mentions": integer,
      "significance": 0.0-1.0,
      "description": "string",
      "first_appearance": "string (optional)"
    }
  ],
  "key_events": [{"chapter": "string", "event": "string", "actors": ["string"]}],
  "objects_artifacts": [{"name": "string", "description": "string", "owner": "string"}],
  "locations": [{"name": "string", "description": "string", "chapter": "string"}],
  "relationships": [{"entity_a": "string", "entity_b": "string", "type": "ally|enemy|family|master|servant|unknown", "description": "string"}],
  "quotes": [{"speaker": "string", "quote": "string", "chapter": "string"}],
  "stats": {"chinese_chars": integer, "total_entities": integer, "key_events_count": integer}
}"""


def load_xyj(filepath: str, max_chapters: int = None) -> str:
    """加载西游记并提取指定章回数"""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # 提取正文（跳过 Gutenberg 头尾）
    start = text.find("第一回")
    if start < 0:
        start = 0
    end = text.find("End of the Project Gutenberg")
    if end < 0:
        end = len(text)

    body = text[start:end]

    if max_chapters:
        # 按章回分割，取前 N 回
        chapters = re.split(r'(第[一二三四五六七八九十百千]+回)', body)
        # 重建包含章回标题的文本
        result = []
        count = 0
        for i, part in enumerate(chapters):
            if re.match(r'第[一二三四五六七八九十百千]+回', part):
                count += 1
                if count > max_chapters:
                    break
            if count <= max_chapters:
                result.append(part)
        body = "".join(result)

    return body.strip()


def chunk_text(text: str, chunk_size: int = 2000) -> list[tuple[str, int]]:
    """将文本分割为固定大小的块，返回 (块内容, 块序号)"""
    # 按段落分割
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current = []
    current_len = 0
    chunk_id = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if current_len + len(para) > chunk_size and current:
            chunks.append(("\n".join(current), chunk_id))
            chunk_id += 1
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para)

    if current:
        chunks.append(("\n".join(current), chunk_id))

    return chunks


def fold_chunk(chunk_text: str, chunk_id: int, model: str = "hermes3") -> dict:
    """小脑：使用 Hermes 3 折叠一个文本块为晶体"""
    import ollama
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": CRYSTAL_SYSTEM_PROMPT},
            {"role": "user", "content": f"Chunk {chunk_id}:\n\n{chunk_text[:1800]}"},
        ],
        options={
            "num_gpu": 0,       # CPU 推理
            "temperature": 0.1,
            "num_predict": 1024,
        },
    )
    content = response["message"]["content"]
    # 提取 JSON
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return {"error": "JSON parse failed", "raw": content[:200]}
    return {"error": "No JSON found", "raw": content[:200]}


def merge_crystals(sub_crystals: list[dict], source: str = "西游记") -> dict:
    """合并多个子晶体为主晶体"""
    master = {
        "crystal_version": "3.0",
        "source": source,
        "summary": "",
        "entities": [],
        "key_events": [],
        "objects_artifacts": [],
        "locations": [],
        "relationships": [],
        "quotes": [],
        "stats": {
            "total_chunks_processed": len(sub_crystals),
            "total_entities": 0,
            "total_events": 0,
            "total_locations": 0,
        },
    }

    seen_entities = set()

    for sc in sub_crystals:
        if "error" in sc:
            continue

        # 实体去重
        for e in sc.get("entities", []):
            name = e.get("name", "")
            if name and name not in seen_entities:
                seen_entities.add(name)
                master["entities"].append(e)

        master["key_events"].extend(sc.get("key_events", []))
        master["objects_artifacts"].extend(sc.get("objects_artifacts", []))
        master["locations"].extend(sc.get("locations", []))
        master["relationships"].extend(sc.get("relationships", []))
        master["quotes"].extend(sc.get("quotes", []))

    master["stats"]["total_entities"] = len(master["entities"])
    master["stats"]["total_events"] = len(master["key_events"])
    master["stats"]["total_locations"] = len(master["locations"])
    master["summary"] = f"共处理 {master['stats']['total_chunks_processed']} 个文本块，提取 {master['stats']['total_entities']} 个实体，{master['stats']['total_events']} 个事件"

    return master


def brain_ask(master_crystal: dict, question: str, model: str = "hermes3") -> dict:
    """大脑：基于主晶体回答问题"""
    import ollama

    crystal_summary = json.dumps(master_crystal, ensure_ascii=False, indent=2)[:3000]

    prompt = f"""基于以下《西游记》结构化晶体数据，回答用户问题。

晶体数据摘要：
{crystal_summary}

用户问题：{question}

请用中文回答，基于晶体数据中的实体、事件和关系进行推理分析。"""

    t0 = time.time()
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": "你是众星的大脑引擎。基于晶体数据进行精准推理。"},
            {"role": "user", "content": prompt},
        ],
        options={
            "num_gpu": 99,       # GPU 加速
            "temperature": 0.3,
            "num_predict": 1024,
        },
    )
    elapsed = time.time() - t0

    return {
        "answer": response["message"]["content"],
        "time_seconds": round(elapsed, 2),
    }


# ══════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="众星 — 西游记全本折叠压测")
    parser.add_argument("--chapters", type=int, default=3,
                        help="测试的章回数（默认3回，全本100回）")
    parser.add_argument("--chunk-size", type=int, default=2000,
                        help="每块字符数（默认2000）")
    parser.add_argument("--full", action="store_true",
                        help="全本测试（100回，可能数小时）")
    args = parser.parse_args()

    xyj_path = os.path.join(os.path.dirname(__file__), "xyj_full.txt")
    if not os.path.exists(xyj_path):
        print(f"❌ 找不到 {xyj_path}")
        sys.exit(1)

    chapters = 0 if args.full else args.chapters
    label = "全本100回" if args.full else f"前{chapters}回"

    print("=" * 65)
    print(f"  众星 V3.0 × Hermes 3 — {label}压测")
    print("=" * 65)

    # ── 1. 加载文本 ──
    print(f"\n📖 加载《西游记》...")
    body = load_xyj(xyj_path, max_chapters=None if args.full else chapters)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', body))
    print(f"   中文汉字: {chinese_chars:,} 字")

    # ── 2. 分块 ──
    chunks = chunk_text(body, chunk_size=args.chunk_size)
    print(f"   分块: {len(chunks)} 块 (每块 ~{args.chunk_size} 字)")

    # ── 3. 小脑折叠 ──
    print(f"\n🧠 小脑折叠中 (CPU, hermes3)...")
    print(f"   {'=' * 50}")
    sub_crystals = []
    total_t0 = time.time()

    for i, (chunk_data, cid) in enumerate(chunks):
        print(f"   [{i+1}/{len(chunks)}] 块 {cid} ({len(chunk_data)} 字)...", end=" ", flush=True)
        t0 = time.time()
        crystal = fold_chunk(chunk_data, cid)
        t1 = time.time()
        status = "✅" if "error" not in crystal else "⚠️"
        print(f"{status} {t1-t0:.1f}s")

        if "error" not in crystal:
            sub_crystals.append(crystal)

        # 每块之间休息一下避免 CPU 过热
        if i < len(chunks) - 1:
            time.sleep(1)

    total_t1 = time.time()
    total_fold_time = total_t1 - total_t0

    # ── 4. 合并晶体 ──
    print(f"\n🔗 合并 {len(sub_crystals)} 个子晶体 → 主晶体...")
    master = merge_crystals(sub_crystals)

    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    master_path = os.path.join(output_dir, "xyj_master_crystal.json")
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)

    print(f"   ✅ 主晶体已保存: {master_path}")
    print(f"   📊 实体: {master['stats']['total_entities']}")
    print(f"   📊 事件: {master['stats']['total_events']}")
    print(f"   📊 地点: {master['stats']['total_locations']}")

    # ── 5. 大脑推理（冲击 10 秒） ──
    print(f"\n🧠 大脑推理测试 (GPU, hermes3)...")

    questions = [
        "《西游记》前几回的主要人物有哪些？他们之间的关系是什么？",
        "花果山在故事中扮演了什么角色？有哪些关键事件发生在这里？",
        "请分析故事中的主要冲突和风险因素。",
    ]

    for q in questions:
        result = brain_ask(master, q)
        status = "🎯" if result["time_seconds"] < 10 else "⚠️"
        print(f"\n   Q: {q[:30]}...")
        print(f"   {status} 耗时: {result['time_seconds']}s {'✅ 冲击10秒成功!' if result['time_seconds'] < 10 else ''}")
        print(f"   A: {result['answer'][:100]}...")

    # ── 6. 最终报告 ──
    print(f"\n" + "=" * 65)
    print(f"  📊 {label} 压测报告")
    print(f"  {'=' * 65}")
    print(f"  文本量: {chinese_chars:,} 汉字 | {len(chunks)} 块")
    print(f"  小脑折叠: {total_fold_time:.1f}s ({total_fold_time/len(chunks):.1f}s/块)")
    print(f"  实体抽取: {master['stats']['total_entities']} 个")
    print(f"  事件抽取: {master['stats']['total_events']} 个")

    # 平均大脑推理时间
    brain_times = [brain_ask(master, q)["time_seconds"] for q in questions]
    print(f"  大脑推理: avg {sum(brain_times)/len(brain_times):.2f}s (目标: <10s)")
    print(f"  {'=' * 65}")

    # 保存报告
    report = {
        "test": f"西游记{label}",
        "chinese_chars": chinese_chars,
        "chunks": len(chunks),
        "cerebellum_time_seconds": round(total_fold_time, 1),
        "brain_avg_seconds": round(sum(brain_times)/len(brain_times), 2),
        "brain_10s_target_achieved": all(t < 10 for t in brain_times),
        "total_entities": master["stats"]["total_entities"],
        "total_events": master["stats"]["total_events"],
    }
    report_path = os.path.join(output_dir, "xyj_benchmark_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n   📋 压测报告: {report_path}")
    print(f"\n✨ 众星 V3.0 · 西游记压测完成！")


if __name__ == "__main__":
    main()
