# Auto Lab

> AI 驱动的大学实验报告自动填写工具。给 AI agent 一份需求文档 + 一个 Word 模板，它帮你把报告写好、截图配好、图表插好、格式调好，直接交。

## 它能做什么

大学生写实验报告 / 课程设计报告时，最耗时的不是思考，而是：

- 按模板格式一点点填内容
- 截图（终端截图、运行截图、配置截图）
- 画图（流程图、ER 图、数据流图、功能结构图）
- 排版（图例对齐、目录更新、占位符清理）

**Auto Lab 把这些全部自动化。** 你只需要提供：

1. 一份需求文档（老师给的作业要求）
2. 一个 Word 模板（学校给的报告模板）

剩下的交给 agent。

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

## 三条截图路线

| 路线 | 用在哪 | 举例 |
|------|--------|------|
| `ai_simulated` | 终端、命令输出、软件配置、IDE 界面 | MySQL 命令行截图、VS Code 编辑器截图、服务器配置面板 |
| `browser_capture` | 你自己写的前端页面 / App | React 登录页截图、小程序运行效果截图 |
| `diagram_assets` | 流程图、ER 图、数据流图、功能结构图 | 系统架构图、数据库 ER 图、业务流程图 |

**关键规则**：需求说"真实截图"= AI 生成逼真的截图（不是本地截屏）。只有需求明确说"自己的页面"时才走浏览器截图。

## 安装

```bash
# 克隆仓库
git clone <repo-url>
cd auto-lab

# 安装依赖（agent 会自动做这一步）
pip install requests python-docx Pillow

# 如果需要浏览器截图
pip install playwright
playwright install chromium

# 如果需要视频处理
pip install av opencv-python numpy mss
```

## 快速开始

```bash
# 1. 环境检查
powershell -ExecutionPolicy Bypass -File scripts/env_check.ps1

# 2. 初始化工作目录
python scripts/init_run.py \
  --requirements 作业要求.txt \
  --template 实验报告模板.docx \
  --output-dir ./run01 \
  --output-docx-name 实验报告.docx

# 3. Agent 自动完成后续步骤：
#    - 分析需求 → 规划截图路线 → 生成图片 → 填写模板 → 交付
```

详细步骤见 `SKILL.md` 的 Execution steps 章节。

## 文档验收标准

Auto Lab 内置 7 大类 40+ 检查项，交付前自动验证：

| 检查项 | 内容 |
|--------|------|
| 模板完整性 | 封面保留、标题层级、表格结构、页面布局 |
| 目录 | TOC 存在、页码正确、与正文标题匹配 |
| 正文质量 | 无占位符、无模板指令、无格式提醒、学生口吻 |
| 图与图例 | 一一对应、不堆叠、编号连续、有引导句和分析段 |
| 图片内容 | 时间真实、代码匹配、无 localhost、图表无重叠 |
| 交付包 | submit/ 文件夹 + submit.zip 同时存在、命名规范 |
| 运行元数据 | delivery_review.json 已写、checklist 一致 |

## 项目结构

```
auto-lab/
├── SKILL.md                    # Agent 执行指南（完整工作流 + 决策框架）
├── README.md                   # 本文件
├── requirements.txt            # Python 依赖
├── .env.example                # API 配置模板
├── scripts/
│   ├── env_check.ps1           # 环境检查
│   ├── init_run.py             # 初始化工作目录
│   ├── run_workflow.py         # 工作流引擎 + 6 道门禁检查
│   ├── generate_images.py      # AI 截图批量生成
│   ├── capture_frontend_screenshots.py  # 浏览器截图
│   ├── generate_diagram_assets.py       # 图表生成
│   ├── video_process.py        # 视频处理
│   ├── package_submission.py   # 交付打包
│   ├── prepare_blank_template.py        # 模板清理
│   ├── test_image_concurrency.py        # 并发测试
│   └── template_adapter.py     # DOCX 模板操作库
├── docs/prompts/               # 各环节详细规则
├── examples/                   # 配置文件示例
└── vendor/                     # 附属 skills
```

## 为什么不用通用 AI 直接写

通用 AI 写实验报告的常见问题：

- 不按模板格式，字号行距全乱
- 截图造假明显（时间不对、代码不匹配）
- 图例堆在一起，图和说明对不上
- 保留了模板里的"请在此处填写"等提示文字
- 用 agent 口吻写（"我已生成以下截图"）

**Auto Lab 逐一解决这些问题**，并内置 40+ 项验收检查确保交付质量。

## License

MIT
