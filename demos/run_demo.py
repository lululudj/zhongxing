"""
众星 1.0 — 演示脚本
====================
快速演示全链路：小脑折叠 + 渲染输出
"""
import sys, os
# 添加项目根目录到路径
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from core import CrystalRenderer, TextFolder, Crystal

# ════════════════════════════════════════════
# 演示 1：特斯拉财报数据（预定义晶体）
# ════════════════════════════════════════════
def demo_tesla(output_path: str = "outputs/tesla_crystal.png"):
    """演示数据：特斯拉 2025 年度财务报告关键数据"""
    crystals = [
        # 顶层 — 核心指标
        Crystal("营收 1,234 亿美元 ↑18%", "positive", 0.95, 0.00, 0.30, 0.25),
        Crystal("净利润 152 亿美元", "positive", 0.80, 0.05, 0.55, 0.20),
        Crystal("毛利率 22.8% 超预期", "highlight", 0.85, 0.10, 0.45, 0.35),

        # 中层 — 关键信息
        Crystal("全球市占率 22.5%", "neutral", 0.65, 0.20, 0.75, 0.30),
        Crystal("Cybertruck 年交付 12 万辆", "neutral", 0.55, 0.25, 0.20, 0.45),
        Crystal("FSD V13 测试进展顺利", "highlight", 0.70, 0.30, 0.65, 0.55),
        Crystal("上海超级工厂产能 +25%", "positive", 0.60, 0.35, 0.35, 0.50),
        Crystal("4680 电池良率 92%", "neutral", 0.50, 0.40, 0.78, 0.48),
        Crystal("能源业务收入 +67% YoY", "positive", 0.60, 0.38, 0.15, 0.55),

        # 底层 — 风险信息
        Crystal("⚠ 美中关税摩擦影响供应链", "risk", 0.75, 0.60, 0.40, 0.72),
        Crystal("⚠ 铝材采购成本 +12%", "risk", 0.60, 0.65, 0.65, 0.75),
        Crystal("⚠ 欧盟反补贴调查进行中", "risk", 0.55, 0.70, 0.25, 0.78),
        Crystal("⚠ 柏林工厂产能利用率 68%", "risk", 0.50, 0.75, 0.55, 0.80),
        Crystal("⚠ 墨西哥超级工厂审批延迟", "risk", 0.45, 0.80, 0.75, 0.78),

        # 最深背景层
        Crystal("Dojo 超算训练进度 78%", "dim", 0.30, 0.92, 0.12, 0.62),
        Crystal("Q4 自由现金流 35 亿美元", "dim", 0.28, 0.94, 0.85, 0.58),
        Crystal("车辆软件订阅收入 +45%", "dim", 0.25, 0.96, 0.50, 0.45),
        Crystal("全球超充站 6,500 座", "dim", 0.22, 0.97, 0.18, 0.35),
        Crystal("Robotaxi 计划 2026 年启动", "dim", 0.20, 0.98, 0.78, 0.35),
    ]

    title = "⚡ Tesla 2025 年度财报 · 2.5D 晶体分析"
    subtitle = "霓虹绿=利好 | 赛博红=风险 | 全息蓝=中性 | 晶金黄=亮点"

    renderer = CrystalRenderer()
    img = renderer.render(crystals, title=title, subtitle=subtitle)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    print(f"✅ [演示 1] 特斯拉财报晶体图: {output_path}")
    return img


# ════════════════════════════════════════════
# 演示 2：小脑折叠 — 从文本自动生成晶体
# ════════════════════════════════════════════
def demo_folding(output_path: str = "outputs/folding_demo.png"):
    """演示小脑自动折叠能力"""
    sample_text = """
    公司2025年上半年业绩表现强劲，营收突破800亿元大关，同比增长25.3%。
    净利润达到98亿元，创历史新高。核心产品市场份额提升至35%。
    研发投入同比增长40%，在AI和量子计算领域取得多项突破。
    海外市场收入增长迅速，欧洲市场增长45%，东南亚市场翻倍。
    但公司也面临多重风险挑战。全球供应链成本上升12%，
    部分原材料价格波动较大。地缘政治风险加剧，贸易摩擦影响出口业务。
    新监管政策可能增加合规成本。市场竞争日益激烈，
    主要竞争对手在低价市场发起价格战。公司需要警惕毛利率下滑风险。
    此外，人才流失率上升至15%，核心团队稳定性值得关注。
    总体来看，公司基本面稳健，短期风险可控，长期增长逻辑未变。
    管理层表示将加大研发投入，保持技术领先优势。
    """

    folder = TextFolder(max_chunks=18)
    crystals, title, subtitle = folder.fold(
        sample_text,
        title="📊 2025 半年报 · 小脑自动折叠",
        subtitle="AI 自动分类/打分/布局 | 无需人工干预",
    )

    if not crystals:
        print("❌ 折叠失败")
        return

    renderer = CrystalRenderer()
    img = renderer.render(crystals, title=title, subtitle=subtitle)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    print(f"✅ [演示 2] 小脑自动折叠晶体图: {output_path}")

    # 打印分类统计
    cats = {}
    for c in crystals:
        cats[c.category] = cats.get(c.category, 0) + 1
    print(f"   📊 晶体分类: {cats}")
    print(f"   🧠 小脑自动折叠完成！")

    return img


# ════════════════════════════════════════════
# 演示 3：纯中文财报分析
# ════════════════════════════════════════════
def demo_chinese_finance(output_path: str = "outputs/chinese_finance.png"):
    """中文金融文本折叠演示"""
    text = """
    贵州茅台 2024 年年度报告摘要

    一、主要财务指标
    公司实现营业总收入 1741.44 亿元，同比增长 15.66%；
    归属于上市公司股东的净利润 862.28 亿元，同比增长 16.36%。
    基本每股收益 68.63 元，同比增长 16.37%。

    二、主营业务分析
    茅台酒销售收入 1458.28 亿元，同比增长 15.81%；
    系列酒销售收入 246.14 亿元，同比增长 19.65%。
    直销渠道收入 765.28 亿元，同比增长 23.45%；
    批发渠道收入 939.14 亿元，同比增长 10.31%。

    三、核心风险提示
    宏观经济下行风险：消费需求可能受到经济增速放缓的影响。
    产能限制风险：茅台酒核心产能受限于赤水河流域生态环境。
    政策监管风险：白酒行业消费税政策可能调整。
    市场竞争加剧风险：高端白酒市场竞争日趋激烈。
    原材料价格波动风险：高粱等原材料价格存在波动。

    四、分红方案
    每 10 股派发现金红利 315.81 元（含税），
    合计分红金额 396.61 亿元，分红比例 46.00%。

    五、2025 年经营计划
    公司计划实现营收增长 15% 左右，
    重点推进茅台酒产能扩建项目，
    加大数字化转型和 i 茅台平台建设。
    """

    folder = TextFolder(max_chunks=20)
    crystals, title, subtitle = folder.fold(
        text,
        title="🏮 贵州茅台 2024 年报 · 晶体折叠",
        subtitle="小脑自动分类：利润↑ | 风险↓ | 数据纯度 100%",
    )

    renderer = CrystalRenderer()
    img = renderer.render(crystals, title=title, subtitle=subtitle)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    print(f"✅ [演示 3] 中文财报晶体图: {output_path}")

    cats = {}
    for c in crystals:
        cats[c.category] = cats.get(c.category, 0) + 1
    print(f"   📊 晶体分类: {cats}")
    return img


# ════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  众星 (ZhongXing) — 端侧多模态高维折叠引擎")
    print("  DEMO 演示脚本 v1.0")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("\n🎯 演示 1: 特斯拉财报 2.5D 晶体图（预定义数据）")
    demo_tesla(os.path.join(base_dir, "outputs", "tesla_crystal.png"))

    print("\n🎯 演示 2: 小脑自动折叠（文本→晶体）")
    demo_folding(os.path.join(base_dir, "outputs", "folding_demo.png"))

    print("\n🎯 演示 3: 中文金融财报分析")
    demo_chinese_finance(os.path.join(base_dir, "outputs", "chinese_finance.png"))

    print("\n" + "=" * 60)
    print("  ✅ 三个演示全部完成！图片保存在 outputs/ 目录")
    print("=" * 60)
