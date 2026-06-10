# ⚡ 众星 (ZhongXing) V4.0

### 端侧多模态高维折叠引擎 — 机机中间语 (Machine Interlingua)

> **"不是压缩文本，而是为机器设计原生语义空间。"**

---

## 🚀 核心理念

传统 LLM 处理长文本是一次性塞入数万 Token，受限于上下文窗口和注意力衰减。

众星走另一条路：**把人类语言翻译成机器原生语义空间**。

```
人类文本 → 🧠小脑折叠 → Crystal3D 机机中间语 → 👁️大脑推理 → 人类答案
              │                      │
         CPU毫秒级              文本化3D空间语言
         规则引擎              [E]节点 + [V]数值 + [R]关系
                              坐标/颜色/深度编码语义
```

### 三层信息界面

| 层级 | 方向 | 协议 | 对象 |
|------|------|------|------|
| 人→机 | 人类语言 → Crystal3D | 小脑规则引擎 | CPU |
| 机→机 | Crystal3D → 推理 | 文本化空间语言 | LLM |
| 机→人 | 推理 → 自然语言 | 中文回答 | 人类 |

---

## 🧠 Crystal3D — 机机中间语 v1

纯文本格式的3D空间语义语言。LLM无需OCR/VLM，原生可读。

```yaml
[LEGEND]
  GREEN=利好 RED=风险 BLUE=中性 GOLD=重点 GRAY=背景
  Z-tier: z<0.25=CORE  z<0.50=IMPORTANT  z<0.85=SUPPORT

[E] id=1 x=0.303 y=0.209 z=0.350 tier=IMPORTANT color=GREEN
    text="赵六的公司2025年营收500万元，净利润120万元，同比增长30%"

[E] id=2 x=0.135 y=0.509 z=0.525 tier=SUPPORT color=BLUE
    text="张三借给李四100万元，年利率5%，期限3年"

[V] id=1001 num=500 unit=万元
[V] id=1002 num=100 unit=万元

[R] from=1 to=2 type=NEXT
```

**设计原则**：
- **纯文本** — LLM 原生 Token 化，不需 OCR/VLM
- **坐标编码空间** — x/y/z (0~1)，空间距离=语义关联
- **颜色编码类型** — GREEN=利好, RED=风险, BLUE=中性
- **深度编码重要性** — z 越小越核心，CORE > IMPORTANT > SUPPORT > BACKGROUND
- **数字精确保留** — 独立 [V] 节点，带单位

### 为什么不用图片？

实验证明：llava:7b 从 2.5D 晶体图中读出 **0%** 的信息。视觉协议对当前模型不成立。

```
视觉通道 → 0% 准确 ❌ (llava不认识自定义视觉编码)
文字通道 → 100% 准确 ✅ (hermes3原生理解Crystal3D)
```

2.5D 晶体渲染保留为**可选的视觉层**（给人看），**通信协议本身是文本的**。

---

## 📦 项目结构

```
zhongxing/
├── crystal3d.py            # Crystal3D 机机中间语生成器
├── config.py               # 统一配置（环境变量可覆盖）
├── zhongxing.py            # CLI 入口
├── gradio_app.py           # Web UI · 双通道推理
├── diagnose_fidelity.py    # 语义保真度诊断工具
├── README.md
├── core/
│   ├── __init__.py
│   ├── models.py           # Crystal 数据模型 + 颜色映射
│   ├── text_folding.py     # 小脑：文本折叠引擎
│   └── crystal_renderer.py # 2.5D 晶体渲染器（可选视觉层）
├── demos/                  # 演示脚本
└── outputs/                # 输出图片
```

---

## 🛠️ 快速开始

### 环境要求

```bash
pip install pillow gradio ollama
```

### CLI

```bash
# 从文件
python zhongxing.py report.txt --title "财务分析" --output result.png

# 直接传文本
python zhongxing.py --direct "营收增长18% 利润创新高" --title "速览"

# 生成 Crystal3D 机机中间语
python crystal3d.py
```

### Web UI

```bash
python gradio_app.py
# → http://127.0.0.1:7861
```

### 语义保真度诊断

```bash
python diagnose_fidelity.py
# 输出：实体保留率 / 数字保留率 / 关系保留率
```

---

## 🎨 Crystal3D 颜色编码

| 颜色 | 类别 | 含义 |
|------|------|------|
| 🟢 GREEN | `positive` | 利好 / 增长 / 收益 |
| 🔴 RED | `risk` | 风险 / 警告 / 下降 |
| 🔵 BLUE | `neutral` | 中性 / 信息 / 数据 |
| 🟡 GOLD | `highlight` | 重点高亮 / 里程碑 |
| ⚫ GRAY | `dim` | 背景数据 / 次要信息 |

---

## 🧠 架构设计

### 小脑 (TextFolder)

```
原始文本 → 分句 → 关键词分类 → 权重打分 → 自动布局 → Crystal[]
                                                      ↓
                                              x/y/z坐标 + 颜色 + 文本
```

- 中英文关键词检测
- 5 类语义分类 (positive/risk/neutral/highlight/dim)
- Z 轴深度自动分配 (核心层→背景层)
- **纯 Python 规则引擎，CPU 毫秒级**

### Crystal3D 生成器

```
Crystal[] → 实体提取 → 数值提取 → 关系检测 → Crystal3D 文本
```

### 大脑 (双通道)

| 通道 | 模型 | 输入 | 适用场景 |
|------|------|------|---------|
| ⚡ 文字 | hermes3 | Crystal3D 文本 | 计数/统计/关系推理 |
| 🎨 视觉 | llava:7b | 2.5D 晶体图 | 空间模式/拓扑分析 |

---

## 📊 性能基准

| 指标 | 数值 |
|------|------|
| 小脑折叠 | < 0.01s (CPU) |
| Crystal3D 生成 | < 0.1s |
| 大脑推理 (hermes3) | ~2.8s (GPU, RTX 4060) |
| 实体保留率 | 100% |
| 数字保留率 | 92% |
| 关系保留率 | 100% |

测试文本：139 字金融关系短文，6 条事实。

---

## 🔧 配置

所有参数通过环境变量覆盖，无需改代码：

```bash
export ZX_TEXT_MODEL=hermes3        # 文字通道模型
export ZX_VISUAL_MODEL=llava:7b     # 视觉通道模型
export ZX_MAX_CHUNKS=20             # 最大晶体数
export ZX_GRADIO_PORT=7861          # Web UI 端口
```

详见 `config.py`。

---

## 🗺️ 路线图

- [x] **v1.0** — 小脑折叠 + 2.5D 渲染 + CLI
- [x] **v3.2** — 双通道推理 (Hermes 文字 + Llava 视觉) + Gradio
- [x] **v4.0** — Crystal3D 机机中间语 + 语义保真度诊断
- [ ] **v4.5** — CRC 语义校验层（事实提取+验证）
- [ ] **v5.0** — 端云协同（端侧 Crystal3D → 云端 256B 大脑）

---

## 📜 许可

MIT License — 开源，自由使用。

---

*⚡ 众星 — 不是堆算力，而是让机器用自己的语言思考。*
