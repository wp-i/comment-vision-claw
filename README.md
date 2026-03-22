<div align="center">

# 🔥 Comment-Vision-Claw

**抖音热评智能抓取与分析工具**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Playwright](https://img.shields.io/badge/Playwright-latest-brightgreen.svg)](https://playwright.dev/)
[![MediaCrawler](https://img.shields.io/badge/MediaCrawler-compatible-orange.svg)](https://github.com/NanmiCoder/MediaCrawler)

自动捕获高赞/高回复评论 · 智能截图 · 深度分析 · 生成专业 PDF 报告

[功能特点](#-功能特点) •
[快速开始](#-快速开始) •
[使用指南](#-使用指南) •
[配置说明](#-配置说明) •
[FAQ](#-常见问题)

</div>

---

## ✨ 功能特点

| 功能 | 说明 |
|------|------|
| 🔍 **智能抓取** | 基于关键词搜索抖音视频，自动筛选高赞(≥5000)或高回复(≥400)的热评 |
| 📸 **精准截图** | 自动定位评论区域，支持内容匹配和点赞数匹配，确保截取正确评论 |
| 📊 **数据统计** | 展示评论点赞数 Top 10、回复数 Top 10，去重展示 |
| 📄 **PDF 报告** | 生成专业分析报告，包含数据概览、热评截图、成因分析 |
| 🤖 **AI 增强** | 支持 OpenAI/DeepSeek 等 API，生成更精准的分析（可选） |
| 🔌 **MCP 集成** | 支持 Model Context Protocol，可作为 AI 工具集成到 Claude/Cursor |

## 📸 效果展示

```
┌─────────────────────────────────────────────────┐
│             抖音热评分析报告                      │
│ 关键词：xxx | 平台：douyin | 共2条热评            │
├─────────────────────────────────────────────────┤
│  共抓取 28 个视频 | 848 条评论（去重后）           │
├─────────────────────────────────────────────────┤
│  评论点赞数 Top 10                               │
│  # | 评论内容 | 作者 | 点赞                       │
├─────────────────────────────────────────────────┤
│  评论回复数 Top 10                               │
│  # | 评论内容 | 作者 | 回复                       │
├─────────────────────────────────────────────────┤
│  ─── 热评详情 ───                                │
│  #1 热评卡片（截图 + 分析）                       │
│  #2 热评卡片（截图 + 分析）                       │
└─────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/comment-vision-claw.git
cd comment-vision-claw
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. 安装 MediaCrawler

```bash
git clone https://github.com/NanmiCoder/MediaCrawler.git ../MediaCrawler
cd ../MediaCrawler && pip install -r requirements.txt
```

### 4. 首次登录（扫码）

```bash
cd ../MediaCrawler
python main.py --platform dy --type search --lt qrcode --keywords "测试"
# 扫码登录后 Ctrl+C 退出
```

### 5. 开始使用

```bash
cd ../comment-vision-claw
python main.py "你感兴趣的关键词"
```

## 📖 使用指南

### CLI 命令

```bash
# 基本用法
python main.py "AI视频生成"

# 指定时间范围
python main.py "情感内容" --time-range 7days

# 自定义阈值
python main.py "游戏" --min-likes 3000 --min-replies 200

# 限制抓取数量
python main.py "美食" --max-videos 50
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `keyword` | 搜索关键词（必需） | - |
| `--time-range` | 时间范围：`1day` / `7days` / `1month` | `1day` |
| `--min-likes` | 最小点赞数阈值 | `5000` |
| `--min-replies` | 最小回复数阈值 | `400` |
| `--max-videos` | 最大抓取视频数 | `200` |

### 输出文件

```
data/
├── results.json          # 热评数据（JSON格式）
├── report_*.pdf          # 分析报告（PDF格式）
└── screenshots/          # 热评截图
    └── comment_*.png
```

## 🔌 MCP 服务器

支持 Model Context Protocol，可集成到 Claude Desktop、Cursor 等 AI 应用。

### 启动服务器

```bash
python server.py --server
```

### 配置客户端

在 Claude Desktop 或 Cursor 中添加配置：

```json
{
  "mcpServers": {
    "comment-vision-claw": {
      "command": "python",
      "args": ["path/to/comment-vision-claw/server.py", "--server"],
      "env": {
        "MEDIACRAWLER_PATH": "path/to/MediaCrawler"
      }
    }
  }
}
```

### 可用工具

| 工具 | 说明 |
|------|------|
| `capture_hot_comments` | 抓取指定关键词的热评 |
| `generate_report` | 生成 PDF 分析报告 |
| `analyze_single_comment` | AI 分析单条评论 |

## ⚙️ 配置说明

复制 `.env.example` 为 `.env` 并修改：

```bash
cp .env.example .env
```

### 主要配置

```env
# 数据目录
DATA_DIR=./data
SCREENSHOTS_DIR=./data/screenshots

# 热评筛选阈值
MIN_LIKE_COUNT=5000
MIN_REPLY_COUNT=400

# 浏览器设置
HEADLESS=false
```

### AI 分析（可选）

```env
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

支持兼容 OpenAI API 的服务（DeepSeek、智谱等）：

```env
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

## 📁 项目结构

```
comment-vision-claw/
├── engine/
│   ├── config.py               # 配置管理
│   ├── mediacrawler_scraper.py # MediaCrawler 集成
│   ├── screenshot.py           # 截图功能
│   ├── pdf_report.py           # PDF 报告生成
│   ├── comment_analyzer.py     # 评论分析
│   └── utils.py                # 工具函数
├── main.py                     # CLI 入口
├── server.py                   # MCP 服务器
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## ❓ 常见问题

<details>
<summary><b>Q: 启动时报错 "MediaCrawler not found"</b></summary>

需要安装 MediaCrawler 到上级目录：
```bash
git clone https://github.com/NanmiCoder/MediaCrawler.git ../MediaCrawler
```
</details>

<details>
<summary><b>Q: 截图功能不工作</b></summary>

确保 Chrome 已启动并开启远程调试：
```bash
# Windows
chrome.exe --remote-debugging-port=9222

# macOS
open -a "Google Chrome" --args --remote-debugging-port=9222
```
</details>

<details>
<summary><b>Q: 登录失败</b></summary>

首次使用需要扫码登录：
1. 运行 `cd ../MediaCrawler && python main.py --platform dy --type search --lt qrcode --keywords "测试"`
2. 扫码登录
3. Ctrl+C 退出
4. 重新运行本工具
</details>

<details>
<summary><b>Q: 热评数量太少</b></summary>

降低筛选阈值：
```bash
python main.py "关键词" --min-likes 1000 --min-replies 100
```
</details>

<details>
<summary><b>Q: 如何使用 AI 分析？</b></summary>

在 `.env` 中配置 `OPENAI_API_KEY`，支持 OpenAI 及兼容 API。
</details>

## 🛠️ 技术栈

- **Python 3.9+** - 主要开发语言
- **Playwright** - 浏览器自动化与截图
- **MediaCrawler** - 社交媒体数据抓取
- **MCP** - Model Context Protocol 集成

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

```bash
# Fork 项目后
git clone https://github.com/your-fork/comment-vision-claw.git
cd comment-vision-claw

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check .
```

## 📄 许可证

[MIT License](LICENSE)

## 🔗 致谢

- [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) - 社交媒体数据抓取框架
- [Playwright](https://playwright.dev/) - 浏览器自动化工具

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

</div>
