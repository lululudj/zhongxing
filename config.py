"""
众星 · 配置系统
===============
集中管理所有可配置项：模型名、渲染参数、分类关键词等。
通过环境变量或直接修改此文件来调整。
"""
import os

# ════════════════════════════════════════════
# 大脑模型配置
# ════════════════════════════════════════════
TEXT_CHANNEL_MODEL = os.getenv("ZX_TEXT_MODEL", "hermes3")
VISUAL_CHANNEL_MODEL = os.getenv("ZX_VISUAL_MODEL", "llava:7b")

# Ollama 选项
OLLAMA_GPU_LAYERS = int(os.getenv("ZX_GPU_LAYERS", "99"))
OLLAMA_TEMPERATURE = float(os.getenv("ZX_TEMPERATURE", "0.3"))
OLLAMA_NUM_PREDICT = int(os.getenv("ZX_NUM_PREDICT", "512"))

# ════════════════════════════════════════════
# 小脑折叠配置
# ════════════════════════════════════════════
MAX_CHUNKS = int(os.getenv("ZX_MAX_CHUNKS", "20"))

# ════════════════════════════════════════════
# 渲染配置
# ════════════════════════════════════════════
RENDER_WIDTH = int(os.getenv("ZX_RENDER_WIDTH", "1440"))
RENDER_HEIGHT = int(os.getenv("ZX_RENDER_HEIGHT", "900"))
RENDER_FONT_SIZE = int(os.getenv("ZX_FONT_SIZE", "36"))

# ════════════════════════════════════════════
# 输出路径
# ════════════════════════════════════════════
OUTPUT_DIR = os.getenv("ZX_OUTPUT_DIR", "D:/zhongxing/outputs")
CRYSTAL_IMAGE_PATH = os.getenv("ZX_CRYSTAL_PATH", f"{OUTPUT_DIR}/crystal_latest.png")

# ════════════════════════════════════════════
# Gradio 配置
# ════════════════════════════════════════════
GRADIO_HOST = os.getenv("ZX_GRADIO_HOST", "127.0.0.1")
GRADIO_PORT = int(os.getenv("ZX_GRADIO_PORT", "7861"))
GRADIO_SHARE = os.getenv("ZX_GRADIO_SHARE", "").lower() == "true"
