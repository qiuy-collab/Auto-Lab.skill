# Auto Lab

**给 AI agent 一份需求文档 + 一个 Word 模板，它帮你把报告写好、截图配好、图表插好、格式调好，直接交。**

受 [darwin-skill](https://github.com/alchaincyf/darwin-skill) 启发，将 Agent Skills 应用于大学实验报告自动化。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0-blue.svg)](#whats-new-in-20)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Standard-blueviolet)](https://skills.sh)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## What's New in 2.0

**v2.0** 是一次结构性升级，核心变化：

**1. 三条截图路线**
- `ai_simulated`: AI 生成逼真的终端、IDE、配置截图
- `browser_capture`: 本地浏览器截图（自己的前端页面）
- `diagram_assets`: 流程图、ER 图、数据流图自动生成

**2. 预任务支持**
- 自动检测是否需要先完成代码、数据等预任务
- 完成后自动记录到 `pre_task_plan.json`

**3. 40+ 验收检查**
- 模板完整性、目录、正文质量、图例、交付包
- 交付前自动验证，确保质量

**4. Agent Skills Standard 兼容**
- 支持 Claude Code、Codex、Cursor、OpenClaw 等 50+ runtime
- 标准化 `SKILL.md` 格式

---

## 工作流程

```
需求文档 + Word 模板
       ↓
  自动安装依赖 + 环境检查
       ↓
  分析需求 → 规划截图和图表路线
       ↓
  🔴 确认分析结果（agent 停下来等你）
       ↓
  生成 AI 截图 / 浏览器截图 / 流程图
       ↓
  填写模板 → 清理占位符 → 插入图片
       ↓
  🔴 检查输出文档（agent 停下来等你）
       ↓
  打包交付（submit/ 文件夹 + submit.zip）
```

---

## 为什么需要这个

大学生写实验报告 / 课程设计报告时，最耗时的不是思考，而是：

| 痛点 | Auto Lab 的解决方案 |
|------|---------------------|
| 按模板格式一点点填内容 | 自动填充模板，保留结构，清理占位符 |
| 截图（终端、运行、配置） | AI 生成逼真截图，或本地浏览器截图 |
| 画图（流程图、ER 图） | 自动生成图表，防止重叠和碰撞 |
| 排版（图例对齐、目录更新） | 自动对齐图例，清理格式指令 |
| 用 agent 口吻写报告 | 自动用学生口吻重写内容 |

---

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/qiuy-collab/Auto-Lab.skill.git
cd Auto-Lab.skill

# 环境检查
powershell -ExecutionPolicy Bypass -File scripts/env_check.ps1

# 初始化工作目录
python scripts/init_run.py \
  --requirements 作业要求.txt \
  --template 实验报告模板.docx \
  --output-dir ./run01 \
  --output-docx-name 实验报告.docx

# Agent 自动完成后续步骤
```

---

## 示例

查看 `examples/big-data-processing-report/` 获取一个完整的运行实例：

### 输入
- 需求文档：《大数据处理技术》课程大作业

### 输出
- 12 张 AI 生成的终端/IDE 截图
- 完整的 PySpark 代码
- 数据分析结果（CSV + 图表）
- 填好的 Word 报告
- 一键打包交付（submit.zip）

### 效果图

| 封面 | 目录 | 正文 |
|------|------|------|
| ![封面](examples/big-data-processing-report/效果图/提交文件.png) | ![目录](examples/big-data-processing-report/效果图/生成的文档预览.png) | AI 截图 + 学生口吻 |

---

## 项目结构

```
Auto-Lab.skill/
├── SKILL.md                    # Agent 执行指南
├── README.md                   # 本文件
├── .env.example                # API 配置模板
├── scripts/
│   ├── env_check.ps1           # 环境检查
│   ├── init_run.py             # 初始化工作目录
│   ├── run_workflow.py         # 工作流引擎
│   ├── generate_images.py      # AI 截图生成
│   ├── generate_diagram_assets.py  # 图表生成
│   └── package_submission.py   # 交付打包
├── docs/
│   ├── index.html              # GitHub Pages
│   └── prompts/                # 各环节详细规则
├── examples/
│   └── big-data-processing-report/  # 完整示例
└── vendor/                     # 附属 skills
    ├── baseline-ui/
    ├── frontend-design/
    ├── minimax-docx/
    └── webapp-testing/
```

---

## 安装方式

### 方式一：Agent Skills Standard（推荐）

```bash
# Claude Code
npx skills add qiuy-collab/Auto-Lab.skill

# Codex
npx skills add qiuy-collab/Auto-Lab.skill

# 手动安装
git clone https://github.com/qiuy-collab/Auto-Lab.skill.git
cp -r Auto-Lab.skill ~/.claude/skills/auto-lab
```

### 方式二：直接使用

```bash
git clone https://github.com/qiuy-collab/Auto-Lab.skill.git
cd Auto-Lab.skill
pip install requests python-docx Pillow
```

---

## 技术栈

- **Python**: 核心脚本语言
- **python-docx**: Word 文档操作
- **Playwright**: 浏览器截图
- **Pillow**: 图像处理
- **PowerShell**: 环境检查

---

## 设计原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **Agent 友好** | 标准化工作流，支持多种 runtime |
| 2 | **模板安全** | 保留模板结构，清理占位符 |
| 3 | **质量优先** | 40+ 验收检查，确保交付质量 |
| 4 | **人在回路** | 关键节点暂停，等用户确认 |
| 5 | **可扩展** | 模块化设计，易于添加新路线 |

---

## 参考项目

- [darwin-skill](https://github.com/alchaincyf/darwin-skill) - Agent Skills 优化系统
- [Agent Skills Standard](https://skills.sh) - Skills 标准化规范
- [minimax-docx](https://github.com/MiniMaxAI/minimax-docx) - Word 文档操作库

---

## 许可证

MIT License © [qiuy-collab](https://github.com/qiuy-collab)

---

**Auto Lab** — 让 AI agent 帮你写实验报告。

*给它需求文档和模板，它还你一份完整的报告。*
