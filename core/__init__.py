"""
众星 (ZhongXing) — 端侧多模态高维折叠引擎
===========================================
Version: 4.0.0 — M2M 机机协议
"""
from .models import Crystal, COLOR_MAP
from .crystal_renderer import CrystalRenderer
from .text_folding import TextFolder

__all__ = ["Crystal", "COLOR_MAP", "CrystalRenderer", "TextFolder"]
