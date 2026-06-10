"""
众星 · 2.5D 晶体渲染引擎
=========================
将结构化文本数据渲染为赛博朋克风「伪 3D 晶体信息图」
支持：颜色映射 / Z 轴景深 / 霓虹辉光 / 阴影层级 / 中文排版

Author: Hermes Agent @ CTO 指令
"""
import math
import random
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from dataclasses import dataclass, field
from typing import Optional

from .models import Crystal, COLOR_MAP


class CrystalRenderer:
    """
    2.5D 晶体渲染器
    ─────────────────
    把一批 Crystal 对象渲染成一张赛博朋克风图片。
    支持中英文混排，自动检测系统可用中文字体。
    """

    # 候选字体路径（Windows 常见路径）
    _FONT_CANDIDATES = [
        # 中文优先
        "/c/Windows/Fonts/msyh.ttc",          # 微软雅黑
        "/c/Windows/Fonts/msyhbd.ttc",        # 微软雅黑 Bold
        "/c/Windows/Fonts/simhei.ttf",        # 黑体
        "/c/Windows/Fonts/simsun.ttc",        # 宋体
        "/c/Windows/Fonts/STXINGKA.TTF",      # 华文行楷
        "/c/Windows/Fonts/STHUPO.TTF",        # 华文琥珀
        "/c/Windows/Fonts/DENG.TTF",          # 等线
        "/c/Windows/Fonts/DENGLB.TTF",        # 等线 Light Bold
        # 英文 fallback
        "/c/Windows/Fonts/arial.ttf",
        "/c/Windows/Fonts/arialbd.ttf",
        "/c/Windows/Fonts/ARLRDBD.TTF",
    ]

    def __init__(self, width: int = 1920, height: int = 1080, bg_color="#0a0a1a"):
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.img = Image.new("RGBA", (width, height), bg_color)
        self.draw = ImageDraw.Draw(self.img)
        # 自动检测可用字体
        self._fonts = {}
        self._detected_fonts = self._detect_fonts()

    def _detect_fonts(self) -> dict:
        """扫描系统字体，返回 {name: path} 映射"""
        found = {}
        for fp in self._FONT_CANDIDATES:
            name = os.path.basename(fp).split(".")[0]
            if os.path.exists(fp):
                found[name] = fp
        if not found:
            # 实在找不到就用默认
            found["default"] = None
        return found

    def _list_available_fonts(self) -> str:
        """列出找到的字体（调试用）"""
        return ", ".join(self._detected_fonts.keys())

    def _get_font(self, size: int, bold: bool = False) -> ImageFont:
        """获取指定大小的字体，优先用中文粗体"""
        key = f"{'bold' if bold else 'normal'}_{size}"
        if key in self._fonts:
            return self._fonts[key]

        # 优先选择
        if bold:
            preferred = ["msyhbd", "arialbd", "denlgb"]
        else:
            preferred = ["msyh", "simhei", "arial", "deng"]

        for name in preferred:
            if name in self._detected_fonts:
                path = self._detected_fonts[name]
                try:
                    f = ImageFont.truetype(path, size)
                    self._fonts[key] = f
                    return f
                except (IOError, OSError):
                    continue

        # fallback: 用第一个可用字体
        for name, path in self._detected_fonts.items():
            if name == "default":
                f = ImageFont.load_default()
                self._fonts[key] = f
                return f
            try:
                f = ImageFont.truetype(path, size)
                self._fonts[key] = f
                return f
            except (IOError, OSError):
                continue

        f = ImageFont.load_default()
        self._fonts[key] = f
        return f

    def _text_size(self, text: str, font) -> tuple:
        """测量文字尺寸，兼容 PIL 不同版本"""
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = d.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    # ── 背景层 ──────────────────────────────────
    def _draw_background(self):
        """绘制深空科技感背景"""
        w, h = self.width, self.height
        pixels = self.img.load()

        cx, cy = w // 2, h // 2
        max_r = math.hypot(w, h) / 2
        for y in range(h):
            for x in range(w):
                dx, dy = x - cx, y - cy
                r = math.hypot(dx, dy) / max_r
                rr = int(10 * (1 - r) + 5)
                rg = int(10 * (1 - r) + 5)
                rb = int(26 * (1 - r) + 10)
                pixels[x, y] = (rr, rg, rb, 255)

        # 网格线
        grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grid)
        gc = (30, 120, 255, 15)
        step = 60
        for x in range(0, w, step):
            gd.line([(x, 0), (x, h)], fill=gc, width=1)
        for y in range(0, h, step):
            gd.line([(0, y), (w, y)], fill=gc, width=1)
        self.img = Image.alpha_composite(self.img, grid)

        # 扫描线
        scan = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(scan)
        for y in range(0, h, 3):
            sd.rectangle([(0, y), (w, y)], fill=(0, 0, 0, 6))
        self.img = Image.alpha_composite(self.img, scan)
        self.draw = ImageDraw.Draw(self.img)

    # ── 晶体渲染核心 ────────────────────────────
    def _render_crystal(self, crystal: Crystal, base_font_size: int = 36):
        """
        渲染单个晶体：文字 + 4 层叠加（远阴影→近阴影→辉光→主文字）
        返回 (RGBA Image, x, y)
        """
        c = crystal
        color = COLOR_MAP.get(c.category, COLOR_MAP["neutral"])
        size = max(14, int(base_font_size * (0.3 + c.weight * 0.9)))

        font = self._get_font(size, bold=(c.weight > 0.6))
        tw, th = self._text_size(c.text, font)

        # 画布位置（居中）
        px = int(self.width * c.x_ratio - tw / 2)
        py = int(self.height * c.y_ratio - th / 2)

        # 景深参数 — 机机视觉压缩协议的Z轴编码
        # 4个深度层级必须在视觉上可区分，让llava通过清晰度感知重要性
        # Tier1 (Z<0.25): 核心层 — 清晰锐利
        # Tier2 (Z 0.25~0.5): 重要层 — 轻微柔化
        # Tier3 (Z 0.5~0.85): 中间层 — 明显模糊+阴影
        # Tier4 (Z>0.85): 背景层 — 高度模糊，仅余轮廓
        alpha = max(40, int(255 * (1 - c.depth * 0.75)))  # 更激进衰减: 背景只剩40
        blur_r = max(0, int(c.depth * 7))                  # 更多模糊: 最深7px高斯
        shadow_offset = int(3 + c.depth * 18)               # 阴影更长: 最深21px偏移
        shadow_alpha = max(15, int(100 * (1 - c.depth * 0.7)))  # 阴影也逐层变淡

        pad = shadow_offset + blur_r + 20
        lw, lh = tw + pad * 2, th + pad * 2
        layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)

        tx, ty = pad, pad

        # 第1层：远阴影
        s1 = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        s1d = ImageDraw.Draw(s1)
        so = shadow_offset
        s1d.text((tx + so, ty + so), c.text, font=font, fill=(0, 0, 0, shadow_alpha))
        if blur_r > 0:
            s1 = s1.filter(ImageFilter.GaussianBlur(radius=blur_r * 1.5))
        layer = Image.alpha_composite(layer, s1)

        # 第2层：近阴影
        s2 = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        s2d = ImageDraw.Draw(s2)
        s2d.text((tx + max(2, so // 2), ty + max(2, so // 2)), c.text, font=font,
                 fill=(color[0] // 3, color[1] // 3, color[2] // 3, shadow_alpha + 20))
        if blur_r > 0:
            s2 = s2.filter(ImageFilter.GaussianBlur(radius=max(1, blur_r // 2)))
        layer = Image.alpha_composite(layer, s2)

        # 第3层：外辉光
        glow = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        ga = min(100, int(alpha * 0.3))
        gd.text((tx, ty), c.text, font=font, fill=(color[0], color[1], color[2], ga))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=max(3, blur_r + 2)))
        layer = Image.alpha_composite(layer, glow)

        # 第4层：主文字
        ld.text((tx, ty), c.text, font=font, fill=(color[0], color[1], color[2], alpha))

        # 浅层晶体加内亮边
        if c.depth < 0.3:
            hl = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
            hd = ImageDraw.Draw(hl)
            hd.text((tx - 1, ty - 1), c.text, font=font,
                    fill=(255, 255, 255, min(60, alpha // 4)))
            layer = Image.alpha_composite(layer, hl)

        # α 衰减
        if alpha < 255:
            r, g, b, a = layer.split()
            a = a.point(lambda x: int(x * alpha / 255))
            layer = Image.merge("RGBA", (r, g, b, a))

        # 旋转
        if c.rotation != 0:
            layer = layer.rotate(c.rotation, expand=True,
                                 center=(lw // 2, lh // 2),
                                 fillcolor=(0, 0, 0, 0), resample=Image.BICUBIC)

        return layer, px, py

    # ── 装饰粒子 ────────────────────────────────
    def _draw_particles(self, count: int = 60):
        pl = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pl)
        for _ in range(count):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            r = random.randint(1, 3)
            c = random.choice([
                (0, 200, 255, random.randint(20, 60)),
                (0, 255, 136, random.randint(10, 40)),
                (255, 51, 51, random.randint(10, 30)),
            ])
            pd.ellipse([(x - r, y - r), (x + r, y + r)], fill=c)
        self.img = Image.alpha_composite(self.img, pl)

    # ── 数据流装饰线 ────────────────────────────
    def _draw_data_streams(self, count: int = 8):
        sl = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sl)
        chars = "01011010アイウエオ"
        for _ in range(count):
            x = random.randint(0, self.width)
            y0 = random.randint(0, self.height)
            length = random.randint(10, 30)
            a = random.randint(8, 25)
            for i in range(length):
                ch = random.choice(chars)
                sd.text((x + random.randint(-2, 2), y0 + i * 14), ch,
                        fill=(0, 255, 180, a), font=self._get_font(10))
        self.img = Image.alpha_composite(self.img, sl)

    # ── 主渲染入口 ──────────────────────────────
    def render(self, crystals: list[Crystal],
               title: str = "",
               subtitle: str = "",
               base_font_size: int = 38,
               particle_count: int = 50,
               data_streams: bool = True) -> Image.Image:
        """
        渲染全部晶体到一张图片
        """
        self._draw_background()
        self._draw_particles(particle_count)
        if data_streams:
            self._draw_data_streams()
        # 4. 逐层渲染 — 按深度排序，远→近
        for c in sorted(crystals, key=lambda x: x.depth):
            layer, px, py = self._render_crystal(c, base_font_size)
            font = self._get_font(max(14, int(base_font_size * (0.3 + c.weight * 0.9))),
                                  bold=(c.weight > 0.6))
            tw, th = self._text_size(c.text, font)
            pad_x = (layer.width - tw) // 2
            pad_y = (layer.height - th) // 2
            self.img.paste(layer, (px - pad_x, py - pad_y), layer)
        self.draw = ImageDraw.Draw(self.img)

        # 标题
        if title:
            tf = self._get_font(42, bold=True)
            self.draw.text((40, 30), title, fill=(200, 220, 255, 220), font=tf)
        if subtitle:
            sf = self._get_font(20)
            self.draw.text((40, 80), subtitle, fill=(120, 160, 200, 160), font=sf)

        # 水印
        wf = self._get_font(14)
        self.draw.text((self.width - 280, self.height - 35),
                       "⚡ 众星 · 2.5D 晶体引擎 v1.0",
                       fill=(60, 100, 140, 100), font=wf)

        return self.img
