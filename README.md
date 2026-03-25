<div align="center">

# Comment-Vision-Claw

**抖音热评智能抓取 · 截图 · 分析 · 报告 一站式解决方案**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Playwright](https://img.shields.io/badge/Playwright-latest-brightgreen.svg)](https://playwright.dev/)
[![MediaCrawler](https://img.shields.io/badge/MediaCrawler-compatible-orange.svg)](https://github.com/NanmiCoder/MediaCrawler)

[快速开始](#快速开始) •
[使用方式](#使用方式) •
[配置说明](#配置说明) •
[常见问题](#常见问题)

</div>

---

## 核心功能

<table>
<tr>
<td width="50%">

### 抖音数据抓取
- 基于 MediaCrawler 引擎，稳定抓取抖音评论
- 关键词搜索 → 视频列表 → 评论数据，全链路自动化
- 渐进式抓取策略，智能累计热评达标后停止

</td>
<td width="50%">

### 热评精准截图
- 自定义筛选标准：点赞数 / 回复数阈值
- 内容前缀匹配 + 点赞数匹配，双重定位确保准确
- 每条热评独立截图，保留完整上下文

</td>
</tr>
<tr>
<td width="50%">

### 图文 PDF 报告
- 数据概览：点赞 Top 10 + 回复 Top 10
- 热评卡片：截图 + 分析 + 数据，一页一评
- AI 成因分析：解读评论走红原因（可选）

</td>
<td width="50%">

### 多种启动方式
- **Web UI**：`start.bat` 一键启动，零门槛
- **命令行**：`python main.py "关键词"`，脚本集成
- **MCP 协议**：接入 Claude / Cursor，AI 工具链扩展

</td>
</tr>
</table>

---

## 为什么选择我们

| 传统方式 | Comment-Vision-Claw |
|----------|---------------------|
| 手动翻阅评论，逐条筛选 | 自动抓取 + 智能筛选，一键完成 |
| 截图靠手动，容易遗漏 | 精准定位热评，自动截图保存 |
| 数据整理到 Excel，费时费力 | 直接生成专业 PDF 报告 |
| 分析全靠人脑，主观判断 | AI 解读走红原因，客观数据支撑 |
| 只能手动操作 | 支持脚本调用 + MCP 协议，可集成到工作流 |

---

## 快速开始

### 前置条件

1. **Python 3.9+**
2. **MediaCrawler**（抖音数据抓取引擎）

```bash
# 安装 MediaCrawler
git clone https://github.com/NanmiCoder/MediaCrawler.git D:\MediaCrawler
cd D:\MediaCrawler && pip install -r requirements.txt
playwright install chromium
```

3. **首次登录抖音**（扫码，只需一次）

```bash
cd D:\MediaCrawler
python main.py --platform dy --type search --lt qrcode --keywords "测试"
# 扫码登录后 Ctrl+C 退出，登录状态会自动保存
```

### 安装本项目

```bash
git clone https://github.com/wp-i/comment-vision-claw.git
cd comment-vision-claw
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # 按需修改配置
```

### 一条命令运行

```bash
python main.py "中医养生"     # 抓取、截图、分析、生成报告，一步到位
```

---

## 使用方式

### 方式一：Web 界面（推荐）

```bash
start.bat
# 或
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`，输入关键词点击"开始抓取"即可。

### 方式二：命令行

```bash
python main.py "中医养生"
python main.py "情感内容" --time-range 7days
python main.py "游戏" --min-likes 1000
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `keyword` | 搜索关键词（必需） | - |
| `--time-range` | 时间范围：`1day` / `7days` / `1month` | `1month` |
| `--min-likes` | 最小点赞数阈值 | `1000` |
| `--min-replies` | 最小回复数阈值 | `100` |

### 方式三：MCP 服务器

```bash
python server.py --server
```

在 Claude Desktop 或 Cursor 中添加配置：

```json
{
  "mcpServers": {
    "comment-vision-claw": {
      "command": "python",
      "args": ["path/to/comment-vision-claw/server.py", "--server"]
    }
  }
}
```

可用工具：`capture_hot_comments`、`generate_report`、`analyze_single_comment`

---

## 配置说明

复制 `.env.example` 为 `.env` 并修改：

```env
# MediaCrawler 路径（自动检测，通常无需修改）
MEDIACRAWLER_PATH=D:\MediaCrawler

# 热评筛选阈值
MIN_LIKE_COUNT=1000
MIN_REPLY_COUNT=100
MAX_VIDEOS=200
MAX_COMMENTS=20

# 截图浏览器配置
HEADLESS=false

# AI 分析（可选，留空则使用关键词分析）
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

### 热评规则

热评需满足以下条件之一：
- **点赞数 ≥ MIN_LIKE_COUNT**（默认 1000）
- **回复数 ≥ MIN_REPLY_COUNT**（默认 100）

### AI 分析配置

支持 OpenAI 兼容 API（DeepSeek、智谱等）：

```env
# DeepSeek 示例
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 智谱示例
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4-flash
```

---

## 输出说明

### PDF 报告包含

| 模块 | 内容 |
|------|------|
| 数据概览 | 点赞 Top 10、回复 Top 10 统计 |
| 热评卡片 | 每条热评的截图 + 评论内容 + 点赞/回复数 |
| 成因分析 | AI 解读评论走红原因（配置 API 后生效） |
| 爆款提炼 | 提取可复用的创作方向和传播策略 |

### 输出文件

```
data/
├── results.json              # 热评原始数据（JSON）
├── screenshots/
│   ├── comment_001.png       # 热评截图
│   ├── comment_002.png
│   └── ...
└── report_20260325_xxx.pdf   # 图文分析报告
```

---

## 项目结构

```
comment-vision-claw/
├── app.py                        # 启动方式①：Streamlit Web UI
├── main.py                       # 启动方式②：CLI（python main.py "关键词"）
├── server.py                     # 启动方式③：MCP 服务器
├── start.bat                     # Windows 一键启动脚本
├── quickstart.bat                # 首次安装脚本
├── requirements.txt              # Python 依赖
├── .env.example                  # 环境变量模板
├── AGENTS.md                     # AI 助手参考文档
├── data/                         # 运行时数据（gitignore）
│   ├── results.json              # 当次抓取的热评数据
│   ├── screenshots/              # 热评截图 PNG
│   ├── report_*.pdf              # 生成的 PDF 报告
│   └── capture_state.json        # 后台任务状态
└── engine/                       # 核心引擎
    ├── config.py                 # 所有配置（从 .env 读取）
    ├── mediacrawler_scraper.py   # 主抓取器（调用 MediaCrawler + 截图）
    ├── _screenshot_worker.py     # 截图子进程
    ├── pdf_report.py             # PDF 报告生成
    ├── comment_analyzer.py       # 评论分析（AI 或关键词）
    ├── cleanup.py                # 启动时数据清理
    └── utils.py                  # 通用工具
```

---

## 常见问题

<details>
<summary><b>Q: 启动时报错 "MediaCrawler not found"</b></summary>

需要安装 MediaCrawler：
```bash
git clone https://github.com/NanmiCoder/MediaCrawler.git D:\MediaCrawler
cd D:\MediaCrawler && pip install -r requirements.txt
```
或在 `.env` 中设置 `MEDIACRAWLER_PATH` 为实际安装路径。
</details>

<details>
<summary><b>Q: 抖音显示未登录 / 需要扫码</b></summary>

首次使用必须扫码登录一次，登录状态会保存在 MediaCrawler 的 `browser_data` 目录中，后续无需重复登录。

```bash
cd D:\MediaCrawler
python main.py --platform dy --type search --lt qrcode --keywords "测试"
# 扫码后 Ctrl+C 退出
```
</details>

<details>
<summary><b>Q: 截图功能不工作</b></summary>

截图使用 MediaCrawler 保存的登录状态自动打开浏览器，无需手动操作。如果截图失败，检查：
1. MediaCrawler 登录状态是否有效（重新扫码登录）
2. `MEDIACRAWLER_PATH/browser_data/dy_user_data_dir` 目录是否存在
</details>

<details>
<summary><b>Q: 热评数量太少</b></summary>

降低筛选阈值：
```bash
python main.py "关键词" --min-likes 500 --min-replies 50
```
或修改 `.env` 中的 `MIN_LIKE_COUNT` 和 `MIN_REPLY_COUNT`。
</details>

<details>
<summary><b>Q: 如何使用 AI 分析？</b></summary>

在 `.env` 中配置 `OPENAI_API_KEY`，支持 OpenAI 及兼容 API（DeepSeek、智谱等）。
不配置时自动使用关键词规则分析。
</details>

<details>
<summary><b>Q: 截图时浏览器会打开多个标签页？</b></summary>

这是正常现象。截图过程中会为每个视频打开新标签页，截图完成后会自动关闭。整个流程完全自动化，无需手动干预。
</details>

---

## 技术栈

- **Python 3.9+** — 主要开发语言
- **Playwright** — 浏览器自动化与截图
- **MediaCrawler** — 社交媒体数据抓取
- **Streamlit** — Web 界面
- **MCP** — Model Context Protocol 集成

---

## 许可证

[MIT License](LICENSE)

---

## 致谢

- [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) — 社交媒体数据抓取框架
- [Playwright](https://playwright.dev/) — 浏览器自动化工具

---

<div align="center">

**如果这个项目对你有帮助，请给个 Star 支持一下！**

</div>
