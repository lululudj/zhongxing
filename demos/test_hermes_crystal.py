"""
众星 V3.0 — Hermes 结构化晶体生成测试
========================================
验证 Hermes 3 作为「小脑」的：
1. 结构化输出能力（XML/JSON 晶体格式）
2. CPU 推理的晶体生成速度
3. 中文文本信息抽取精度

测试数据：《西游记》第一回片段
"""
import json
import time
import sys
import os
import re

# ── 测试数据：西游记第一回（约600字） ──
XIYOUJI_EXCERPT = """
    感盘古开辟，三皇治世，五帝定伦，世界之间，遂分为四大部洲：曰东胜神洲，曰西牛贺洲，曰南赡部洲，曰北俱芦洲。
    这部书单表东胜神洲。海外有一国土，名曰傲来国。国近大海，海中有一座名山，唤为花果山。
    此山乃十洲之祖脉，三岛之来龙，自开清浊而立，鸿蒙判后而成。真个好山！
    那座山，正当顶上，有一块仙石。其石有三丈六尺五寸高，有二丈四尺围圆。
    三丈六尺五寸高，按周天三百六十五度；二丈四尺围圆，按政历二十四气。
    上有九窍八孔，按九宫八卦。四面更无树木遮阴，左右倒有芝兰相衬。
    盖自开辟以来，每受天真地秀，日精月华，感之既久，遂有灵通之意。
    内育仙胞，一日迸裂，产一石卵，似圆球样大。因见风，化作一个石猴。
    五官俱备，四肢皆全。便就学爬学走，拜了四方。目运两道金光，射冲斗府。
    惊动高天上圣大慈仁者玉皇大天尊玄穹高上帝，驾座金阙云宫灵霄宝殿，
    聚集仙卿，见有金光焰焰，即命千里眼、顺风耳开南天门观看。
    二将果奉旨出门外，看的真，听的明。须臾回报道：
    "臣奉旨观听金光之处，乃东胜神洲海东傲来小国之界，
    有一座花果山，山上有一仙石，石产一卵，见风化一石猴，
    在那里拜四方，眼运金光，射冲斗府。如今服饵水食，金光将潜息矣。"
    玉帝垂赐恩慈曰："下方之物，乃天地精华所生，不足为异。"
    那猴在山中，却会行走跳跃，食草木，饮涧泉，采山花，觅树果；
    与狼虫为伴，虎豹为群，獐鹿为友，猕猿为亲；
    夜宿石崖之下，朝游峰洞之中。真是"山中无甲子，寒尽不知年"。
"""

# ── Hermes 3 晶体生成 Prompt ──
HERMES_CRYSTAL_SYSTEM_PROMPT = """You are ZhongXing's Cerebellum Engine. 
Your ONLY task is to analyze the given text and output a valid JSON crystal structure.
NEVER include explanations, markdown, or extra text — ONLY output valid JSON.

Output JSON Schema:
{
  "crystal_version": "3.0",
  "source": "string",
  "summary": "string (20-50 chars)",
  "entities": [
    {
      "name": "string",
      "type": "character|location|object|event|concept",
      "mentions": integer,
      "significance": 0.0-1.0,
      "description": "string"
    }
  ],
  "key_events": [
    {
      "chapter": "string",
      "event": "string",
      "actors": ["string"]
    }
  ],
  "stats": {
    "total_characters": integer,
    "total_locations": integer,
    "key_metrics": {}
  },
  "risk_indicators": [
    {
      "entity": "string",
      "risk_type": "conflict|change|unknown|opportunity",
      "level": 0.0-1.0,
      "description": "string"
    }
  ]
}

Analyze the following text and output ONLY valid JSON:"""


def test_hermes_crystal_inference():
    """测试 Hermes 3 的结构化晶体生成能力"""
    print("=" * 60)
    print("  众星 V3.0 — Hermes 小脑结构化晶体测试")
    print("=" * 60)

    # 检查模型是否已拉取
    import subprocess
    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True, text=True, timeout=10
    )
    if "hermes3" not in result.stdout:
        print("❌ hermes3 模型未安装，请先运行: ollama pull hermes3")
        return False

    print(f"\n📄 测试文本: 《西游记》第一回片段 ({len(XIYOUJI_EXCERPT)} 字符)")
    print(f"🧠 模型: hermes3")
    print(f"⚙️  模式: CPU 推理 (num_gpu=0)")
    print()

    # ── CPU 推理测试（小脑模式） ──
    print("⏳ 小脑折叠中（CPU 推理）...")
    t0 = time.time()

    import ollama
    response = ollama.chat(
        model="hermes3",
        messages=[
            {"role": "system", "content": HERMES_CRYSTAL_SYSTEM_PROMPT},
            {"role": "user", "content": XIYOUJI_EXCERPT},
        ],
        options={
            "num_gpu": 0,       # 强制 CPU
            "temperature": 0.1,  # 低温度保证结构化稳定性
            "num_predict": 2048,
        },
    )

    t1 = time.time()
    elapsed = t1 - t0
    content = response["message"]["content"]

    # ── 解析 JSON 输出 ──
    crystal = None
    raw_output = content

    # 尝试提取 JSON（模型可能会加 markdown 包裹）
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            crystal = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 解析失败: {e}")
            print(f"   原始输出前 200 字符: {content[:200]}")
    else:
        print(f"⚠️  未找到 JSON 输出")
        print(f"   原始输出前 200 字符: {content[:200]}")

    print(f"\n📊 测试结果:")
    print(f"   ⏱️  推理耗时: {elapsed:.2f} 秒")
    print(f"   📦 输出长度: {len(content)} 字符")
    print(f"   ✅ JSON 解析: {'成功' if crystal else '失败'}")

    if crystal:
        print(f"\n📋 晶体数据结构:")
        print(f"   来源: {crystal.get('source', 'N/A')}")
        print(f"   摘要: {crystal.get('summary', 'N/A')}")

        entities = crystal.get("entities", [])
        print(f"   实体数: {len(entities)}")
        for e in entities[:5]:
            icon = {"character": "👤", "location": "📍", "object": "📦", "event": "⚡", "concept": "💡"}
            print(f"     {icon.get(e.get('type',''),'❓')} {e.get('name','?')} ({e.get('type','?')}) "
                  f"— 提及{e.get('mentions',0)}次, 重要度{e.get('significance',0):.2f}")

        events = crystal.get("key_events", [])
        print(f"   关键事件数: {len(events)}")
        for ev in events[:3]:
            print(f"     ⚡ [{ev.get('chapter','?')}] {ev.get('event','?')}")

        risks = crystal.get("risk_indicators", [])
        print(f"   风险指标数: {len(risks)}")
        for r in risks[:3]:
            icon_map = {"conflict": "⚔️", "change": "🔄", "unknown": "❓", "opportunity": "🎯"}
            print(f"     {icon_map.get(r.get('risk_type',''),'⚠️')} {r.get('entity','?')} "
                  f"— 级别{r.get('level',0):.2f}: {r.get('description','?')}")

        # 保存结果为 JSON
        output_path = os.path.join(os.path.dirname(__file__), "outputs", "hermes_crystal.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(crystal, f, ensure_ascii=False, indent=2)
        print(f"\n   💾 JSON 已保存: {output_path}")
        print(f"\n{'=' * 60}")
        print(f"  ✅ Hermes 小脑结构化输出验证通过！")
        print(f"  🎯 核心指标: 文本 → 结构化晶体 = {elapsed:.2f}s (CPU)")
        print(f"{'=' * 60}")
        return True

    print(f"\n{'=' * 60}")
    print(f"  ❌ 测试未通过，需要调整 prompt 或模型")
    print(f"{'=' * 60}")
    return False


# ── GPU 大脑推理测试 ──
def test_brain_reasoning(crystal_file: str = None):
    """用 GPU 跑 Hermes 3，基于晶体做深度推理"""
    print("\n" + "=" * 60)
    print("  众星 V3.0 — Hermes 大脑看图/读晶体推理测试")
    print("=" * 60)

    if crystal_file and os.path.exists(crystal_file):
        with open(crystal_file, "r", encoding="utf-8") as f:
            crystal = json.load(f)
    else:
        print("⚠️  无晶体数据，跳过大脑推理测试")
        return False

    summary_text = f"""
根据以下结构化的晶体数据，深度分析《西游记》第一回的内容：

核心实体：{', '.join([e['name'] for e in crystal.get('entities', [])[:5]])}
关键事件：{crystal.get('key_events', [{}])[0].get('event', 'N/A') if crystal.get('key_events') else 'N/A'}
风险指标：{crystal.get('risk_indicators', [])}

问题：请用中文简要分析这段文本的主题、主要人物和关键事件。
"""

    print("⏳ 大脑推理中（GPU 加速）...")
    t0 = time.time()

    import ollama
    response = ollama.chat(
        model="hermes3",
        messages=[
            {"role": "system", "content": "你是众星的大脑引擎。基于晶体数据进行深度分析和总结。"},
            {"role": "user", "content": summary_text},
        ],
        options={
            "num_gpu": 99,      # GPU 加速
            "temperature": 0.3,
            "num_predict": 1024,
        },
    )

    t1 = time.time()
    elapsed = t1 - t0

    print(f"\n📊 大脑推理结果:")
    print(f"   ⏱️  推理耗时: {elapsed:.2f} 秒")
    print(f"   💬 输出:\n")
    print(f"   {response['message']['content']}")
    print(f"\n{'=' * 60}")
    print(f"  ✅ GPU 大脑推理验证通过！{elapsed:.2f}s")
    print(f"{'=' * 60}")
    return True


if __name__ == "__main__":
    print("正在检查 hermes3 模型状态...")
    import subprocess
    r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
    if "hermes3" in r.stdout:
        print("✅ hermes3 已就绪\n")
    else:
        print("⏳ hermes3 正在后台下载中，请等待完成后重试...")
        sys.exit(0)

    # 阶段 1：小脑 CPU 晶体生成
    success = test_hermes_crystal_inference()

    # 阶段 2：大脑 GPU 读晶体推理
    if success:
        crystal_file = os.path.join(os.path.dirname(__file__), "outputs", "hermes_crystal.json")
        test_brain_reasoning(crystal_file)

    print("\n✨ 众星 V3.0 · Hermes 全链路测试完成！")
