# ⚡ 众星 · 双脑引擎 (ZhongXing Dual-Brain Engine)

### 🖥️ 让老设备跑超大模型 · 端侧双脑推理框架

<p align="center">
  <img src="https://img.shields.io/badge/version-4.0-blue" alt="version">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/python-3.8+-yellow" alt="python">
  <img src="https://img.shields.io/badge/最低配置-GTX%201060-orange" alt="gpu">
</p>

> **你的老电脑不是不行了，是没遇到对的架构。**
>
> GTX 1060 · 8GB 显存 · 老旧笔记本 —— 照样跑百万字长文推理，2.8 秒出结果。
> 
> 不用换设备，换个思维方式。

> **实测《斗破苍穹》530万字全文：萧炎 = 52,218 次 · 推理仅需 2.8 秒 · 0 误差**
>
> 不是压缩文本，而是为机器设计原生语义空间。

---

## 🔬 一句话原理

```
百万字长文 → 🧠小脑折叠 → Crystal3D 语义空间 → ⚡大脑推理 → 精准答案
              CPU 毫秒级      机机中间语            GPU 2.8s      零幻觉
```

### 为什么老设备也能跑？

传统方案把百万字全文塞进 GPU 显存 → 至少需要 24GB+ 显存。

众星的做法完全不同：

| | 传统方案 | 众星·双脑 |
|------|---------|----------|
| 谁读长文 | GPU 硬扛 | **CPU 规则引擎** |
| GPU 做什么 | 读全文 + 推理 | **只做推理** |
| 显存占用 | 24GB+ | **< 4GB** |
| 最低配置 | RTX 4090 | **GTX 1060** |

> **小脑用 CPU 折叠，大脑用 GPU 推理。各干各的，谁也不浪费。**

**LLM 数数会出错？** 众星在语义空间外面套了一层 **Python 硬校验层**——数字先由代码精确统计，再交给大脑推理。数学 100% 准确。

---

## 🎯 实测数据

| 测试项 | 数据量 | 结果 | 速度 |
|--------|--------|------|------|
| 萧炎出现次数 | 斗破苍穹 530 万字 | **52,218 次** ✓ | 2.8s |
| 花花更新出现次数 | 同上 | **6 次** ✓ | 2.8s |
| Crystal 保真度 | 139 字金融短文 | **实体 100% / 数字 92% / 关系 100%** | < 0.1s |
| 视觉通道 (llava:7b) | 2.5D 晶体图 | **0%** ✗ | 19s |

> ⚠️ 视觉通道实验已放弃。Crystal3D 采用纯文本协议，LLM 无需 VLM/OCR。

---

## 📦 快速开始

```bash
pip install pillow gradio ollama
git clone https://github.com/lululudj/zhongxing.git
cd zhongxing

# Web UI
python gradio_app.py
# → http://127.0.0.1:7861

# CLI
python zhongxing.py --direct "营收800亿增长25%" --title "速览"

# Crystal3D 机机中间语
python crystal3d.py

# 语义保真度诊断
python diagnose_fidelity.py
```

---

## 🧠 Crystal3D — 机机中间语

纯文本 3D 空间语义语言，LLM 原生可读：

```yaml
[LEGEND]
  GREEN=利好 RED=风险 BLUE=中性 GOLD=重点 GRAY=背景
  Z: z<0.25=CORE > IMPORTANT > SUPPORT > BACKGROUND

[E] id=1 x=0.303 y=0.209 z=0.350 tier=IMPORTANT color=GREEN
    text="赵六的公司2025年营收500万元，净利润120万元，同比增长30%"

[E] id=2 x=0.135 y=0.509 z=0.525 tier=SUPPORT color=BLUE
    text="张三借给李四100万元，年利率5%，期限3年"

[V] id=1001 num=500 unit=万元
[V] id=1002 num=100 unit=万元

[R] from=1 to=2 type=NEXT
```

- **坐标** (x/y/z 0~1) — 空间距离 = 语义关联
- **颜色** — GREEN 利好 / RED 风险 / BLUE 中性
- **深度** — z 越小越核心
- **纯文本** — 不需 OCR/VLM，LLM 直接 Token 化

---

## 🧬 架构

```
┌──────────────────────────────────────────────┐
│              众星 · 双脑引擎                    │
│                                              │
│  人类文本 ──→ 🧠小脑(Cerebellum)              │
│              │ CPU规则引擎 + Crystal3D编码     │
│              ▼                               │
│         Crystal3D 语义空间                    │
│         [E]节点 + [V]数值 + [R]关系           │
│              │                               │
│     ┌───────┴───────┐                        │
│     ▼               ▼                        │
│  ⚡大脑(Cerebrum)  🔬硬校验层                  │
│  hermes3推理      Python精确搜索              │
│  GPU ~2.8s        数学 100% 准确              │
│     │               │                        │
│     └───────┬───────┘                        │
│             ▼                                │
│       人类可读答案                            │
└──────────────────────────────────────────────┘
```

---

## 🗺️ 路线图

- [x] **v1.0** — 小脑折叠 + 2.5D 渲染 + CLI
- [x] **v3.2** — 双通道推理 + Gradio Web UI
- [x] **v4.0** — Crystal3D 机机中间语 + 语义保真度诊断
- [ ] **v4.5** — CRC 语义校验层
- [ ] **v5.0** — 端云协同 (端侧编码 → 云端 256B 大脑)

---

## ⭐ Star History

如果这个项目对你有用，点个 Star ⭐ 支持一下！

---

MIT License · 开源 · 欢迎 PR
