"""
众星 V3.1 — 机机通信 2.5D 视觉压缩引擎
小脑(小模型) → 彩色字符晶体图 → 大脑(llava VLM 看图解读)
"""
import re, json, ollama, time, os
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from collections import Counter

# ── 颜色编码（机读优化：高对比度 + 语义绑定）──
CATEGORY_COLORS = {
    "character": (0, 255, 136),   # 霓虹绿 — 人物
    "location":  (51, 204, 255),  # 全息蓝 — 地点
    "event":     (255, 204, 0),   # 晶金黄 — 事件
    "item":      (255, 102, 255), # 霓虹紫 — 物品
    "skill":     (255, 80, 80),   # 赛博红 — 技能
    "stat":      (160, 160, 220), # 淡紫灰 — 统计数据
    "count":     (255, 255, 255), # 纯白 — 频次数据
}

FONT_PATHS = [
    "/c/Windows/Fonts/msyh.ttc",    # 微软雅黑
    "/c/Windows/Fonts/simhei.ttf",  # 黑体
    "/c/Windows/Fonts/arial.ttf",
]
def _load_font(size):
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()

def _text_size(text, font):
    d = ImageDraw.Draw(Image.new("RGBA", (1,1)))
    bbox = d.textbbox((0,0), text, font=font)
    return bbox[2]-bbox[0], bbox[3]-bbox[1]


def cerebellum_compress(text: str, model: str = "qwen2.5:1.5b") -> dict:
    """
    小脑（小模型 CPU）压缩文本为结构化数据
    输出格式专门为 2.5D 视觉编码设计
    """
    prompt = """Extract from the Chinese text. Output ONLY valid JSON:
{
  "entities": [
    {"name":"Chinese_name","type":"character|location|event|item|skill","frequency":int,"importance":0.0-1.0}
  ],
  "relationships": [{"a":"str","b":"str","type":"str"}],
  "frequency_stats": [{"word":"str","count":int} for top 15 frequent Chinese words],
  "summary": "1-sentence summary in Chinese"
}"""

    resp = ollama.chat(model=model, messages=[
        {"role":"system","content": prompt},
        {"role":"user","content": text[:3000]},
    ], options={"num_gpu":0, "temperature":0.1, "num_predict":1024})

    content = resp["message"]["content"]
    # 提取 JSON — 小模型格式可能不稳，多重尝试
    data = {"entities":[], "frequency_stats":[], "summary":"提取失败"}
    m = re.search(r'\{.*\}', content, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
        except json.JSONDecodeError:
            # 尝试修复常见 JSON 错误
            raw = m.group()
            raw = re.sub(r',\s*}', '}', raw)     # 尾部多余逗号
            raw = re.sub(r',\s*]', ']', raw)     # 数组尾部多余逗号
            try:
                data = json.loads(raw)
            except:
                pass

    # Python 兜底：直接用原文做精确词频统计
    freq = Counter()
    for w in re.findall(r'[\u4e00-\u9fff]{2,4}', text):
        freq[w] += 1
    # 过滤停用词
    stops = set("的了是在不我他有这也为之就都而及与么然但所那可以一个上下来去说知道")
    top_words = [(w,c) for w,c in freq.most_common(30) if w not in stops][:15]
    data["frequency_stats"] = data.get("frequency_stats", []) or [
        {"word": w, "count": c} for w, c in top_words
    ]
    # 确保 entities 中的 frequency 字段有值
    for e in data.get("entities", []):
        if not e.get("frequency"):
            name = e.get("name","")
            if name:
                e["frequency"] = len(re.findall(re.escape(name), text))

    return data


def render_machine_crystal(data: dict, width=1600, height=1200) -> Image.Image:
    """
    渲染机读 2.5D 彩色字符晶体图
    设计原则：高对比度 / 色彩语义绑定 / 频次直接印字 / 空间分层
    """
    img = Image.new("RGB", (width, height), (8, 8, 22))
    draw = ImageDraw.Draw(img)

    # 背景网格（辅助视觉定位）
    for x in range(0, width, 80):
        draw.line([(x,0),(x,height)], fill=(20,20,40), width=1)
    for y in range(0, height, 80):
        draw.line([(0,y),(width,y)], fill=(20,20,40), width=1)

    entities = data.get("entities", [])
    freq_stats = data.get("frequency_stats", [])
    summary = data.get("summary", "")

    # ── 左上：标题 ──
    title_font = _load_font(36)
    draw.text((30, 20), "⚡ 众星 · 视觉压缩晶体 (机读格式)", fill=(200,220,255), font=title_font)
    if summary:
        sf = _load_font(20)
        draw.text((30, 65), summary[:80], fill=(120,160,200), font=sf)

    # ── 右上：词频统计（白字 — 机读最重要区域）──
    freq_font = _load_font(16)
    freq_x, freq_y = width - 320, 30
    draw.text((freq_x, freq_y), "【词频统计 — 精确值】", fill=(255,255,255), font=_load_font(18))
    for i, (w, c) in enumerate(freq_stats[:15]):
        y = freq_y + 28 + i * 22
        draw.text((freq_x, y), f"{w}: {c}", fill=(255,255,255), font=freq_font)

    # ── 中左：实体卡片（带颜色编码）──
    if entities:
        draw.text((30, 110), "【实体 — 颜色=类型】", fill=(180,200,230), font=_load_font(18))

    sorted_ents = sorted(entities, key=lambda e: e.get("importance",0), reverse=True)[:20]
    card_w, card_h = 280, 70
    cols = 4
    for i, ent in enumerate(sorted_ents):
        col, row = i % cols, i // cols
        cx, cy = 30 + col * (card_w + 15), 140 + row * (card_h + 12)

        # 卡片背景
        color = CATEGORY_COLORS.get(ent.get("type",""), (100,120,140))
        bg = tuple(max(5, c//6) for c in color)
        draw.rectangle([cx, cy, cx+card_w, cy+card_h], fill=bg, outline=color, width=2)

        # 实体名
        name_font = _load_font(22)
        name = ent.get("name","?")[:10]
        draw.text((cx+8, cy+6), name, fill=color, font=name_font)

        # 频次（白字醒目）
        freq = ent.get("frequency", "?")
        freq_str = f"×{freq}" if isinstance(freq, int) else str(freq)
        draw.text((cx+card_w-60, cy+6), freq_str, fill=(255,255,255), font=_load_font(18))

        # 类型标签
        etype = ent.get("type","?")
        draw.text((cx+8, cy+38), etype, fill=(120,140,160), font=_load_font(13))

        # 重要度条形
        imp = ent.get("importance", 0.5)
        bar_w = int(card_w * 0.7 * imp)
        draw.rectangle([cx+8, cy+56, cx+8+bar_w, cy+62], fill=color)

        # 频次再标记（纯数字，方便 VLM OCR）
        if isinstance(freq, int) and freq > 1:
            cnt_font = _load_font(48)
            tw, th = _text_size(str(freq), cnt_font)
            # 卡片右侧大数字
            alpha_color = tuple(min(255, c//3 + 30) for c in color)
            draw.text((cx+card_w-tw-5, cy+card_h-th-2), str(freq),
                      fill=alpha_color, font=cnt_font)

    # ── 底栏：关系连线 ──
    rels = data.get("relationships", [])[:8]
    if rels:
        rel_y = height - 120
        draw.text((30, rel_y), "【关系】", fill=(180,200,230), font=_load_font(18))
        rel_font = _load_font(15)
        for i, rel in enumerate(rels):
            rx, ry = 30 + (i % 4) * 350, rel_y + 28 + (i // 4) * 22
            rel_text = f"{rel.get('a','?')} → {rel.get('b','?')} [{rel.get('type','?')}]"
            draw.text((rx, ry), rel_text, fill=(140,160,200), font=rel_font)

    # ── 右下水印 ──
    draw.text((width-250, height-30), "众星 · 视觉压缩 v3.1",
              fill=(50,70,100), font=_load_font(14))

    return img


def brain_vision_read(image_path: str, question: str) -> dict:
    """大脑 (llava VLM) 读取彩色晶体图并回答问题"""
    t0 = time.time()
    resp = ollama.chat(model="llava:7b", messages=[
        {"role":"system","content":"你是视觉大脑。读取这张彩色编码的晶体图。图中颜色、位置、数字均有语义。白色数字=精确频次。"},
        {"role":"user","content": question, "images": [image_path]},
    ], options={"num_gpu":99, "temperature":0.3, "num_predict":512})
    elapsed = time.time() - t0
    return {"answer": resp["message"]["content"], "time": round(elapsed,2)}


# ═══════════════════════════════════
# 快速测试
# ═══════════════════════════════════
if __name__ == "__main__":
    text = """
    萧炎，斗之气，三段！望着测验魔石碑上刺眼的五个大字，少年面无表情。
    三年前，他是乌坦城最耀眼的天才，四岁练气，十岁九段斗之气，十一岁突破十段。
    萧媚远远望着那个曾经意气风发的少年，心中五味杂陈。萧薰儿静静站在人群外。
    纳兰嫣然来到萧家退婚，引发轩然大波。药老从戒指中苏醒，传授萧炎焚诀。
    斗气大陆，强者为尊。萧炎历经磨难，从斗者到斗师，从大斗师到斗灵、斗王、斗皇。
    美杜莎女王、云韵、小医仙，萧炎的旅途上出现了越来越多的人。
    萧炎萧炎萧炎，整个大陆都在传颂这个名字。三十年河东三十年河西，莫欺少年穷！
    """

    print("🧠 小脑压缩中 (qwen2.5:1.5b CPU)...")
    t0 = time.time()
    data = cerebellum_compress(text)
    print(f"   耗时: {time.time()-t0:.1f}s")
    print(f"   实体: {len(data.get('entities',[]))}")
    print(f"   词频: {len(data.get('frequency_stats',[]))}")

    print("\n🎨 渲染机读晶体图...")
    img = render_machine_crystal(data)
    out = "D:/zhongxing/outputs/machine_crystal.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print(f"   已保存: {out}")

    print("\n🧠 大脑视觉读取 (llava:7b)...")
    result = brain_vision_read(out, "这张图中萧炎出现了多少次？请精确回答数字。")
    print(f"   ⏱️ {result['time']}s")
    print(f"   💬 {result['answer'][:300]}")
