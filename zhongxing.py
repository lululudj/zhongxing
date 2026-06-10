#!/usr/bin/env python3
"""
众星 (ZhongXing) — 端侧多模态高维折叠引擎
===========================================
CLI 入口：文本折叠 → 2.5D 晶体渲染 → 输出图片

用法：
  python zhongxing.py <文本文件> [选项]

选项：
  --title TITLE      图片标题
  --subtitle TEXT    图片副标题
  --output PATH      输出图片路径
  --max-chunks N     最大晶体数 (默认 20)
  --width W          图片宽度 (默认 1920)
  --height H         图片高度 (默认 1080)
  --show             渲染后自动打开图片
  --json             同时输出 Crystal 数据为 JSON
  --direct TEXT      直接传入文本（而非文件）
  --fontsize N       基准字号 (默认 38)

示例：
  python zhongxing.py report.txt --title "财务分析报告" --output crystal.png
  python zhongxing.py --direct "营收增长18% 利润创新高" --title "速览"
"""
import sys
import os
import json
import argparse

# 加入项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import CrystalRenderer, TextFolder


def main():
    parser = argparse.ArgumentParser(
        description="众星 (ZhongXing) — 端侧多模态高维折叠引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s report.txt --title "财务分析" --output result.png
  %(prog)s --direct "营收增长18%% 利润创新高" --title "速览" --show
        """,
    )

    # 输入
    parser.add_argument("file", nargs="?", default=None,
                        help="输入文本文件路径")
    parser.add_argument("--direct", type=str, default=None,
                        help="直接传入文本内容（而非文件）")
    parser.add_argument("--encoding", type=str, default="utf-8",
                        help="文件编码 (默认 utf-8)")

    # 输出
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="输出图片路径")
    parser.add_argument("--show", action="store_true",
                        help="渲染后自动打开图片")
    parser.add_argument("--json", action="store_true",
                        help="同时输出 Crystal JSON 数据")

    # 渲染参数
    parser.add_argument("--title", type=str, default="",
                        help="图片标题")
    parser.add_argument("--subtitle", type=str, default="",
                        help="图片副标题")
    parser.add_argument("--width", type=int, default=1920,
                        help="图片宽度 (默认 1920)")
    parser.add_argument("--height", type=int, default=1080,
                        help="图片高度 (默认 1080)")
    parser.add_argument("--max-chunks", type=int, default=20,
                        help="最大晶体数 (默认 20)")
    parser.add_argument("--fontsize", type=int, default=38,
                        help="基准字号 (默认 38)")
    parser.add_argument("--no-streams", action="store_true",
                        help="不画数据流装饰线")

    args = parser.parse_args()

    # ── 读取文本 ──
    text = ""
    if args.direct:
        text = args.direct
    elif args.file:
        if not os.path.exists(args.file):
            print(f"❌ 文件不存在: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding=args.encoding) as f:
            text = f.read()
    else:
        # 从 stdin 读取
        print("📄 请在下面粘贴文本（Ctrl+Z / Ctrl+D 结束）：")
        try:
            text = sys.stdin.read()
        except KeyboardInterrupt:
            print("\n⚠️  已取消")
            sys.exit(0)

    if not text.strip():
        print("❌ 未读取到文本内容")
        sys.exit(1)

    # ── 小脑：折叠文本 ──
    print(f"🧠 小脑折叠中... ({len(text)} 字符)")
    folder = TextFolder(max_chunks=args.max_chunks)
    crystals, title, subtitle = folder.fold(
        text,
        title=args.title,
        subtitle=args.subtitle,
    )

    if not crystals:
        print("❌ 未能从文本中提取到有效信息块")
        sys.exit(1)

    print(f"   → 提取 {len(crystals)} 个晶体")

    # 统计分类
    cats = {}
    for c in crystals:
        cats[c.category] = cats.get(c.category, 0) + 1
    cat_desc = " | ".join(f"{k}: {v}" for k, v in sorted(cats.items()))
    print(f"   → 分类: {cat_desc}")

    # ── 渲染 ──
    print(f"🎨 渲染 2.5D 晶体图... ({args.width}x{args.height})")
    renderer = CrystalRenderer(width=args.width, height=args.height)
    img = renderer.render(
        crystals,
        title=title,
        subtitle=subtitle,
        base_font_size=args.fontsize,
        data_streams=not args.no_streams,
    )

    # ── 输出 ──
    output_path = args.output
    if not output_path:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "crystal_output.png")

    img.save(output_path)
    print(f"✅ 晶体图已保存: {output_path}")
    print(f"   尺寸: {img.width} × {img.height}")

    # JSON 输出
    if args.json:
        json_path = output_path.rsplit(".", 1)[0] + ".json"
        data = {
            "title": title,
            "subtitle": subtitle,
            "crystals": [
                {
                    "text": c.text,
                    "category": c.category,
                    "weight": c.weight,
                    "depth": c.depth,
                    "x_ratio": c.x_ratio,
                    "y_ratio": c.y_ratio,
                }
                for c in crystals
            ],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   JSON 数据: {json_path}")

    # 打开图片
    if args.show:
        try:
            import subprocess
            subprocess.Popen(["start", output_path], shell=True)
            print("   🖼️  图片已打开")
        except Exception:
            pass

    print("✨ 众星折叠完成！")


if __name__ == "__main__":
    main()
