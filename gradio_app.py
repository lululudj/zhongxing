#!/usr/bin/env python3
"""
众星 V4.0 — M2M 机机协议 · 双通道推理引擎
====================================================
文字通道: hermes3 GPU ~2.8s  |  视觉通道: llava:7b GPU ~19s
智能路由: 规则引擎 0.001s     |  模型热切换: 按需装卸
"""
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
import ollama
from core import CrystalRenderer, TextFolder
from config import (
    TEXT_CHANNEL_MODEL, VISUAL_CHANNEL_MODEL,
    OLLAMA_GPU_LAYERS, OLLAMA_TEMPERATURE, OLLAMA_NUM_PREDICT,
    MAX_CHUNKS, RENDER_WIDTH, RENDER_HEIGHT, RENDER_FONT_SIZE,
    OUTPUT_DIR, CRYSTAL_IMAGE_PATH, GRADIO_HOST, GRADIO_PORT, GRADIO_SHARE,
)
from utils import (
    extract_word_freq, extract_targets, count_in_text,
    route, switch_model, ollama_chat_with_retry, format_crystal_text, format_status,
)
from PIL import Image, ImageDraw

# ── 日志配置 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("zhongxing.gradio")

# ── 会话状态 ──
_session_raw = ""
_session_crystal = ""
_crystal_image_path = ""

_TEXT_CHANNEL = TEXT_CHANNEL_MODEL
_VISUAL_CHANNEL = VISUAL_CHANNEL_MODEL
_current_gpu_model = None


def fold_and_render(text, title, subtitle):
    global _session_raw, _session_crystal, _crystal_image_path, _current_gpu_model

    if not text.strip():
        img = Image.new("RGBA", (800, 400), (10, 10, 30, 255))
        d = ImageDraw.Draw(img)
        d.text((150, 180), "请粘贴文本", fill=(100, 160, 200, 200))
        return img, ""

    _session_raw = text
    folder = TextFolder(max_chunks=MAX_CHUNKS)
    crystals, rt, rs = folder.fold(text, title=title, subtitle=subtitle)
    if not crystals:
        img = Image.new("RGBA", (800, 400), (10, 10, 30, 255))
        d = ImageDraw.Draw(img)
        d.text((150, 180), "未能提取", fill=(200, 80, 80, 200))
        return img, ""

    # 词频统计
    word_freq = extract_word_freq(text, top_n=20)
    _session_crystal = format_crystal_text(crystals, word_freq)

    # 渲染晶体图
    renderer = CrystalRenderer(width=RENDER_WIDTH, height=RENDER_HEIGHT)
    img = renderer.render(
        crystals,
        title=rt or title,
        subtitle=rs or subtitle,
        base_font_size=RENDER_FONT_SIZE,
    )
    _crystal_image_path = CRYSTAL_IMAGE_PATH
    os.makedirs(os.path.dirname(_crystal_image_path), exist_ok=True)
    img.save(_crystal_image_path)
    logger.info(f"晶体图已保存: {_crystal_image_path}")

    # 预热文字通道
    if _current_gpu_model != _TEXT_CHANNEL:
        if switch_model(_TEXT_CHANNEL, OLLAMA_GPU_LAYERS):
            _current_gpu_model = _TEXT_CHANNEL

    return img, format_status(crystals)


VISUAL_PROTOCOL_PROMPT = """你是众星大脑的视觉解码器。这张2.5D晶体图是机机视觉压缩协议——图中的每一个视觉属性都携带精确的语义信息：

## 视觉→语义 解码协议
### 深度层级 (Z轴 → 视觉清晰度 → 重要性)
整张图有4个深度层级，通过清晰度/阴影/模糊度来编码：
- **前层 (Z=0~0.25)**: 文字最清晰、颜色最亮、几乎无阴影 → 🔴核心信息/关键亮点，最重要
- **中前层 (Z=0.25~0.5)**: 文字清晰、轻微阴影 → 🟡重要数据/利好指标
- **中后层 (Z=0.5~0.85)**: 文字稍暗、明显阴影和模糊 → 🟠风险/警告/次要信息
- **后层 (Z=0.85~1.0)**: 文字暗沉、长阴影、高度模糊 → ⚫背景数据/辅助上下文

### 颜色→类型 编码
- 🟢 霓虹绿 = 利好/增长/收益 (positive)
- 🔴 赛博红 = 风险/警告/下降 (risk)
- 🔵 全息蓝 = 中性/数据/信息 (neutral)
- 🟡 晶金黄 = 核心亮点/里程碑 (highlight)
- 🟣 暗紫灰 = 背景数据 (dim)

### 空间→语义 编码
- 画面上方 = 正面/利好
- 画面下方 = 风险/负面
- 画面中心 = 最重要信息
- 边缘 = 次要/背景

### 字号→权重 编码
- 大字 = 高权重/高重要性
- 小字 = 低权重/次要

解码时请：
1. 优先关注前层清晰文字 — 这是最核心的信息
2. 根据颜色判断每条信息的性质
3. 回答时引用原图中看到的数字，不要猜测
4. 如果你不确定某条信息的类别，根据其清晰度和位置来判断"""


def dual_channel_infer(question):
    global _current_gpu_model, _crystal_image_path
    if not question.strip():
        return "⚠️ 请输入问题"
    if not _session_crystal:
        return "⚠️ 请先在「折叠渲染」生成晶体"

    channel = route(question)
    t0 = time.time()

    if channel == "VISUAL":
        if not _crystal_image_path or not os.path.exists(_crystal_image_path):
            return "⚠️ 视觉通道需要晶体图，请先生成"

        # 切换到视觉模型
        if _current_gpu_model != _VISUAL_CHANNEL:
            if not switch_model(_VISUAL_CHANNEL, OLLAMA_GPU_LAYERS):
                return "❌ 视觉模型加载失败"
            _current_gpu_model = _VISUAL_CHANNEL

        try:
            resp = ollama.chat(
                model=_VISUAL_CHANNEL,
                messages=[
                    {"role": "system", "content": VISUAL_PROTOCOL_PROMPT},
                    {"role": "user", "content": question, "images": [_crystal_image_path]},
                ],
                options={
                    "num_gpu": OLLAMA_GPU_LAYERS,
                    "temperature": OLLAMA_TEMPERATURE,
                    "num_predict": OLLAMA_NUM_PREDICT,
                },
            )
            elapsed = time.time() - t0
            return f"🎨 视觉通道 ({_VISUAL_CHANNEL} · {elapsed:.1f}s)\n\n{resp['message']['content']}"
        except Exception as e:
            logger.error(f"视觉通道推理失败: {e}")
            return f"❌ 视觉通道推理失败: {e}"

    else:
        # 文字通道
        if _current_gpu_model != _TEXT_CHANNEL:
            if not switch_model(_TEXT_CHANNEL, OLLAMA_GPU_LAYERS):
                return "❌ 文字模型加载失败"
            _current_gpu_model = _TEXT_CHANNEL

        # 精确计数
        extra = ""
        targets = extract_targets(question)
        if targets and _session_raw:
            counts = count_in_text(_session_raw, targets)
            if counts:
                extra = "\n【硬数据 — 原文精确搜索】\n" + "\n".join(
                    f"「{t}」= {c}次" for t, c in list(counts.items())[:10]
                )

        prompt = (
            f"晶体数据(按深度分层):\n{_session_crystal[:3000]}\n{extra}\n\n"
            f"问题:{question}\n\n"
            "注意：硬数据中的数字必须原样引用。depth值越小=越重要，核心层(depth<0.25)的信息优先级最高。不要猜测数字。"
        )

        try:
            content = ollama_chat_with_retry(
                model=_TEXT_CHANNEL,
                messages=[
                    {
                        "role": "system",
                        "content": "精准推理。晶体数据按Z轴深度分层：核心层=最关键信息，背景层=辅助上下文。优先基于核心层数据回答。硬数据的数字必须引用，不要猜测。",
                    },
                    {"role": "user", "content": prompt},
                ],
                options={
                    "num_gpu": OLLAMA_GPU_LAYERS,
                    "temperature": OLLAMA_TEMPERATURE,
                    "num_predict": OLLAMA_NUM_PREDICT,
                },
            )
            elapsed = time.time() - t0
            return f"⚡ 文字通道 ({_TEXT_CHANNEL} · {elapsed:.1f}s)\n\n{content}"
        except Exception as e:
            logger.error(f"文字通道推理失败 (已重试): {e}")
            return f"❌ 文字通道推理失败，请检查 Ollama 是否在运行: {e}"


# ── Gradio UI ──
with gr.Blocks(title="⚡ 众星 V4.0 M2M协议 双通道引擎") as demo:
    gr.Markdown(f"""
    # ⚡ 众星 (ZhongXing) V4.0 — M2M 双通道推理引擎
    **⚡ 文字通道 ({TEXT_CHANNEL_MODEL})** | **🎨 视觉通道 ({VISUAL_CHANNEL_MODEL})** | 智能路由
    """)

    with gr.Tabs():
        with gr.TabItem("🎨 折叠渲染"):
            with gr.Row():
                with gr.Column(scale=3):
                    text_input = gr.Textbox(label="📄 粘贴长文本", placeholder="粘贴要分析的文本…", lines=10)
                with gr.Column(scale=1):
                    gr.Markdown("**快速填充**")
                    gr.Button("📖 斗破苍穹", size="sm", elem_id="demo_dpcq")
            with gr.Row():
                title_input = gr.Textbox(label="标题", scale=2)
                subtitle_input = gr.Textbox(label="副标题", scale=2)
                fold_btn = gr.Button("🧠 折叠并渲染", variant="primary")
            status_text = gr.Markdown("")
            output_image = gr.Image(label="🎨 晶体图", type="pil")

        with gr.TabItem("🧠 双通道推理"):
            gr.Markdown("### 🧠 智能路由推理")
            gr.Markdown("> 计数/统计/频次 → ⚡文字通道(2.8s) | 空间/模式/看图 → 🎨视觉通道(19s)")
            question_input = gr.Textbox(
                label="💬 提问",
                placeholder="计数类：'萧炎出现了几次？'  视觉类：'请分析这张晶体图' …",
                lines=3,
            )
            ask_btn = gr.Button("🚀 智能推理", variant="primary", size="lg")
            answer_output = gr.Textbox(label="✨ 推理结果", lines=15)

    # 事件绑定
    fold_btn.click(
        fn=fold_and_render,
        inputs=[text_input, title_input, subtitle_input],
        outputs=[output_image, status_text],
    )
    ask_btn.click(fn=dual_channel_infer, inputs=question_input, outputs=answer_output)
    question_input.submit(fn=dual_channel_infer, inputs=question_input, outputs=answer_output)

if __name__ == "__main__":
    logger.info(f"启动 Gradio: {GRADIO_HOST}:{GRADIO_PORT}")
    demo.launch(
        server_name=GRADIO_HOST,
        server_port=GRADIO_PORT,
        share=GRADIO_SHARE,
        theme=gr.themes.Soft(primary_hue="cyan", neutral_hue="slate"),
    )
