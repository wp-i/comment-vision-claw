# Comment-Vision-Claw — AI 参考文档

> 本文件供 AI 助手（Claude、Cursor、Copilot 等）阅读，快速理解项目架构、数据流和关键约定。

---

## 项目概述

**Comment-Vision-Claw** 是一个抖音热评抓取与分析工具。

核心流程：
1. 用 **MediaCrawler** 搜索抖音视频并抓取评论数据（JSON）
2. 筛选高赞（≥ MIN_LIKE_COUNT）或高回复（≥ MIN_REPLY_COUNT）的热评
3. 以**渐进式抓取**方式持续累计热评：每轮抓取一批视频，达到热评目标后停止
4. 对最终热评集合统一截图，并生成包含截图和 AI/关键词分析的 **PDF 报告**

---

## 目录结构

```
comment-vision-claw/
├── app.py                        # 启动方式①：Streamlit Web UI
├── main.py                       # 启动方式②：CLI（python main.py "关键词"）
├── server.py                     # 启动方式③：MCP 服务器（python server.py --server）
├── start.bat                     # Windows 一键启动脚本（调用 app.py）
├── quickstart.bat                # 首次安装脚本
├── requirements.txt              # Python 依赖
├── pyproject.toml                # 项目元数据
├── .env.example                  # 环境变量模板（复制为 .env 使用）
├── AGENTS.md                     # 本文件：AI 助手参考文档
├── data/                         # 运行时数据（gitignore）
│   ├── results.json              # 当次抓取的热评数据
│   ├── screenshots/              # 热评截图 PNG
│   ├── report_*.pdf              # 生成的 PDF 报告
│   ├── capture_state.json        # 后台任务状态（供 Streamlit 轮询）
│   └── capture.lock              # 防并发锁文件
└── engine/                       # 核心引擎
    ├── __init__.py
    ├── config.py                 # 所有配置（从 .env 读取）
    ├── mediacrawler_scraper.py   # 主抓取器（调用 MediaCrawler + 截图）
    ├── _screenshot_worker.py     # 截图子进程（被 mediacrawler_scraper 调用）
    ├── screenshot.py             # 截图辅助函数（extract_like_count 等）
    ├── pdf_report.py             # PDF 报告生成
    ├── comment_analyzer.py       # 评论分析（AI 或关键词）
    ├── cleanup.py                # 启动时数据清理（保留登录状态）
    ├── stealth.py                # Playwright 反检测脚本（备用，未在主流程中调用）
    └── utils.py                  # 通用工具（log_progress、setup_directories）
```

---

## 三种启动方式

| 方式 | 命令 | 说明 |
|------|------|------|
| Web UI | `start.bat` 或 `streamlit run app.py` | 推荐，有图形界面 |
| CLI | `python main.py "关键词"` | 命令行，适合脚本调用 |
| MCP | `python server.py --server` | 供 Claude/Cursor 等 AI 工具调用 |

三种方式的**核心逻辑完全一致**，均调用 `MediaCrawlerDouyinScraper.capture_hot_comments()`。

---

## 关键模块说明

### `start.bat`
- 先 `cd /d "%~dp0"` 切换到脚本所在目录，确保后续命令在正确路径执行
- **启动前检查**：Python 是否可用 → Streamlit 是否安装 → `app.py` 和 `engine/` 是否存在 → MediaCrawler 是否安装
- 每个检查失败时都有 `pause` 和明确错误提示，**防止窗口闪退**
- 清理上次数据（`clear_app_data()`），清理失败不阻塞启动
- **杀掉残留进程**：启动前检测并杀掉占用 8501 端口的旧 Streamlit 进程
- 用 PowerShell `Invoke-WebRequest` 后台轮询端口 8501，**等到 Streamlit 真正响应 HTTP 200 后**再打开浏览器（避免空白页）
- `start.bat` 强制切到 UTF-8，并在退出时恢复原始代码页，减少 Windows 控制台中文乱码
- 最后启动 `streamlit run app.py --server.headless=true --server.port=8501`
- Streamlit 异常退出时 `pause` 显示错误信息

### `app.py`
- Streamlit Web UI，模块顶层只调用 `setup_directories()`（无副作用，可安全重复执行）
- 点击"开始抓取"时才调用 `clear_app_data()` 清理上次数据
- 后台线程执行 `run_capture()`，主线程通过 `st.rerun()` 非阻塞轮询 `capture_state.json`
- **使用用户在 UI 中选择的 `time_range`**，不再用 `detect_time_range()` 自动推断覆盖
- **不在 `__main__` 块调用 `clear_app_data()`**（避免 Streamlit 热重载时误清数据）

### `engine/config.py`
- 所有配置从 `.env` 读取，提供模块级常量和动态函数（`min_like_count()`、`min_reply_count()` 等）
- `HEADLESS`：控制截图浏览器是否无头模式（`true`=无头，`false`=显示窗口），默认 `false`
- `MEDIACRAWLER_PATH`：自动检测 MediaCrawler 安装位置，优先使用环境变量

### `engine/mediacrawler_scraper.py`
- `MediaCrawlerDouyinScraper`：主抓取类，实现 context manager
- `capture_hot_comments(keyword, time_range)` → `list[dict]`：完整流程入口
- 内部调用 `_run_mediapcrawler()` 启动 MediaCrawler 子进程（`--lt qrcode` 扫码登录）
- **浏览器保活**：启动 MediaCrawler 时设置 `AUTO_CLOSE_BROWSER=false` + `MEDIACRAWLER_PRESERVE_BROWSER=true`，确保浏览器进程不被清理
- MediaCrawler 退出后，CDP 端口（9222）仍可用，截图 worker 直接复用
- 抓取：采用渐进式累计策略，优先满足目标热评数量，避免一次性大抓取
- 截图：只对最终热评集合执行一次，不与抓取阶段耦合
- 子进程启动时会把外层 `.env` 的 `MAX_VIDEOS` 映射到 MediaCrawler 的 `CRAWLER_MAX_NOTES_COUNT`，并同步 `MAX_COMMENTS` 到 `CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES`
- 使用 `./data/capture.lock` 防止并发抓取
- **`_cleanup_browser()`**：截图完成后通过 CDP 连接并关闭浏览器

### `engine/_screenshot_worker.py`
- 独立子进程，避免与 Streamlit/asyncio 的事件循环冲突
- **浏览器连接策略**：通过 CDP 连接主抓取阶段的浏览器（端口 9222），浏览器由外层统一清理
- **CDP 模式**：`p.chromium.connect_over_cdp("http://localhost:9222")` → 返回 `Browser` 对象，从中取 `contexts[0]` 得到 `BrowserContext`
- **复用单个标签页**：创建一个页面，循环内使用 `page.goto()` 导航到不同视频 URL，避免打开多个浏览器窗口
- **页面状态清空**：每次导航前先 `page.goto("about:blank")` 清空 SPA 页面状态，避免残留状态导致截图超时
- **登录状态检测**：打开第一个视频页面后检测是否出现登录弹窗（扫码登录、请先登录等），若未登录则**跳过所有截图**并输出提示，避免浏览器闪退
- **结果数量保证**：确保输出结果数量与输入评论数量一致（不足时补空结果）
- 匹配策略：内容前缀匹配 → 点赞数匹配（±10%）→ 最高赞评论
- **去重规则**：每条视频只保留最多两条热评，按点赞数排序保留较高的
  - **截图会话策略**：截图阶段优先复用主抓取期间的 CDP 浏览器会话；不要为了截图提前关闭抓取浏览器，也不要在截图前重启整个 Chrome 进程
  - **浏览器保活开关**：当需要让截图 worker 连接仍在工作的 CDP 浏览器时，使用环境变量 `MEDIACRAWLER_PRESERVE_BROWSER=true` 禁止 MediaCrawler 的 atexit/signal 清理过早关闭浏览器；截图完成后再由外层统一清理
  - **渐进式抓取**：每轮抓取后先累计热评，热评达标后再停止，之后统一处理截图与报告

### `engine/pdf_report.py`
- 生成 HTML 后用 Playwright 子进程转 PDF（避免事件循环冲突）
- 包含：数据概览（Top10 点赞/回复）+ 每条热评卡片（截图 + 分析）

### `engine/comment_analyzer.py`
- 若配置了 `OPENAI_API_KEY`：调用 OpenAI 兼容 API 分析
- 否则：关键词规则分析（fallback）
- 输出格式：`{"reasons": [...], "viral_points": [...], "directions": [...]}`

### `engine/cleanup.py`
- `clear_app_data()`：清理 results.json、截图、锁文件、临时文件、MediaCrawler JSON 数据
- **不清除** `browser_data`（MediaCrawler 登录状态）
- MediaCrawler 路径从 `engine/config.MEDIACRAWLER_PATH` 读取（不硬编码）

---

## 数据流

```
用户输入关键词
    │
    ▼
MediaCrawlerDouyinScraper.capture_hot_comments()
    │
    ├─► MediaCrawler 子进程（python main.py --platform dy --type search --lt qrcode）
    │       └─► 输出: {MEDIACRAWLER_PATH}/data/douyin/json/search_contents_*.json
    │                                                       search_comments_*.json
    │       └─► MediaCrawler 的 Playwright 浏览器会弹出（正常现象，用于扫码/抓取）
    │       └─► 环境变量 AUTO_CLOSE_BROWSER=false + MEDIACRAWLER_PRESERVE_BROWSER=true
    │
    ├─► 加载 JSON → 筛选热评（likes ≥ MIN_LIKE_COUNT OR replies ≥ MIN_REPLY_COUNT）
    │
    ├─► _screenshot_worker.py 子进程（一次性处理所有评论截图）
    │       ├─► 通过 CDP 连接主抓取阶段的浏览器（端口 9222）
    │       ├─► 打开第一个视频页面后检测登录状态
    │       └─► 输出: ./data/screenshots/comment_*.png
    │
    ├─► _cleanup_browser()：通过 CDP 连接并关闭浏览器
    │
    └─► 返回 list[dict]（含 screenshot_path）
            │
            ▼
        generate_pdf_report() → ./data/report_*.pdf
```

---

## 热评数据结构

```python
{
    "platform": "douyin",
    "video_title": str,          # 视频标题（截断至100字）
    "video_author": str,         # 视频博主昵称
    "video_url": str,            # 视频链接
    "comment_author": str,       # 评论者昵称
    "comment_content": str,      # 评论正文
    "like_count": int,           # 点赞数
    "reply_count": int,          # 回复数
    "has_image": bool,           # 评论是否含图片
    "screenshot_path": str,      # 截图本地路径（空字符串表示截图失败）
    "timestamp": str,            # ISO 格式时间戳
}
```

---

## 环境变量（`.env`）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MEDIACRAWLER_PATH` | 自动检测 | MediaCrawler 安装路径 |
| `MIN_LIKE_COUNT` | `1000` | 热评最小点赞数 |
| `MIN_REPLY_COUNT` | `100` | 热评最小回复数 |
| `MAX_COMMENTS` | `20` | 每个视频评论抓取上限 / 最多保留热评数 |
| `MAX_VIDEOS` | `10` | 最多抓取视频数 |
| `HEADLESS` | `false` | 截图浏览器是否无头模式（`true`=不显示窗口） |
| `OPENAI_API_KEY` | 空 | AI 分析 API Key（可选） |
| `OPENAI_BASE_URL` | OpenAI | 兼容 API 地址（DeepSeek 等） |
| `OPENAI_MODEL` | `gpt-4o-mini` | 模型名称 |

---

## 外部依赖

- **MediaCrawler**：需单独安装到 `MEDIACRAWLER_PATH`（默认 `D:\MediaCrawler`）
  - 首次使用需扫码登录抖音（`--lt qrcode`），登录状态保存在 `browser_data/dy_user_data_dir`
  - 项目地址：https://github.com/NanmiCoder/MediaCrawler
- **Playwright Chromium**：`playwright install chromium`

---

## 常见问题与约定

1. **登录状态**：MediaCrawler 的登录 Cookie 存储在 `MEDIACRAWLER_PATH/browser_data/dy_user_data_dir`，任何清理操作都**不能**删除此目录

2. **并发保护**：`./data/capture.lock` 存在时拒绝新的抓取任务

3. **截图子进程**：截图必须在独立子进程中运行，不能在 Streamlit 主线程或 asyncio 事件循环中直接调用 Playwright

4. **PDF 生成**：同样通过子进程调用 Playwright，避免事件循环冲突

5. **数据缓存**：`mediacrawler_scraper.py` 会检测 MediaCrawler JSON 文件是否已存在，存在则跳过重新抓取（`skip_crawler = True`）

6. **时间范围**：用户在 Web UI 中选择的时间范围直接传入 `run_capture()`，不再被 `detect_time_range()` 覆盖。MediaCrawler 的 `--time-filter` 参数目前未传入，时间范围仅用于报告展示

7. **`BrowserContext` vs `Browser`**：`launch_persistent_context()` 返回 `BrowserContext`（无 `is_connected()` 方法），`connect_over_cdp()` 返回 `Browser`。两者不可混用，`_screenshot_worker.py` 用 `context` 统一操作页面

8. **user_data_dir 文件锁**：不再需要 `_wait_for_browser_release()`，因为 `MEDIACRAWLER_PRESERVE_BROWSER=true` 会保留浏览器进程，CDP 端口直接可用

9. **start.bat 防闪退**：
   - 启动前依次检查 Python、Streamlit、项目文件、MediaCrawler，每步失败都 `pause` 显示错误
   - 启动前杀掉占用 8501 端口的残留进程
   - Streamlit 异常退出时 `pause` 显示错误信息
   - 用 `Invoke-WebRequest` 轮询端口 8501，等到 HTTP 200 响应后再打开浏览器
   - 运行前切换为 UTF-8，退出时恢复原始代码页，减少中文乱码

10. **截图浏览器空白标签页**：CDP 连接模式下不再需要清理空白标签页

11. **登录状态检测**：截图 worker 打开第一个视频页面后检测是否出现登录弹窗，若未登录则跳过所有截图并输出提示，避免浏览器闪退崩溃

12. **HEADLESS 配置**：CDP 连接模式下，headless 由 MediaCrawler 的 `CDP_HEADLESS` 控制

 13. **浏览器重复打开修复**：截图流程只通过 CDP 连接已打开浏览器，不再启动持久化浏览器

 14. **截图保活约定**：若截图需要连接到主抓取期间的 CDP 浏览器，必须在截图完成前保留该浏览器进程；外层通过 `MEDIACRAWLER_PRESERVE_BROWSER=true` 触发保活，避免 MediaCrawler 的 atexit 清理提前关闭会话

 15. **视频/评论数量映射**：外层项目的 `MAX_VIDEOS`、`MAX_COMMENTS` 会在启动 MediaCrawler 子进程时同步映射到 `CRAWLER_MAX_NOTES_COUNT`、`CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES`，以保证 `.env` 配置生效一致

 16. **截图标签页复用**：CDP 模式下，截图 worker 复用单个标签页进行截图，每次导航前先 `goto("about:blank")` 清空页面状态，避免 SPA 残留导致截图超时
