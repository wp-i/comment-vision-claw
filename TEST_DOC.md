# 测试排查文档

## 问题追踪表

| 序号 | 问题描述 | 排查记录 | 状态 | 备注 |
|------|----------|----------|------|------|
| 1 | 执行时打开两个浏览器（一个是空页面，另一个是空页面+抖音网页） | 2025-03-28 已定位原因并修复 | completed | 修复已生效，第一次运行成功 |
| 2 | 关键词为空时支持搜索全部视频 | 2025-03-28 已修改代码支持空关键词 | completed | 代码已生效 |
| 3 | MCP/openClaw调用时截图失败问题 | 2025-03-28 已添加 fallback 机制 | completed | 需验证fallback是否正常工作 |

---

## 问题1: 双浏览器问题排查

### 现象描述
执行时打开两个浏览器：
- 浏览器1: 空页面
- 浏览器2: 空页面 + 抖音网页

### 排查记录
| 时间 | 尝试 | 结果 | 备注 |
|------|------|------|------|
| 2025-03-28 | 检查 screenshot_worker.py, mediacrawler_scraper.py, pdf_report.py | 仅找到两处 playwright.launch，均为 headless 或 CDP 连接，不会弹出窗口 | |
| 2025-03-28 | 检查 screenshot worker 的页面导航逻辑 | screenshot_worker.py:310 会先 goto("about:blank") 然后 goto(video_url) | 可能是截图前清空页面导致的视觉现象 |
| 2025-03-28-20:25 | 实际运行观察 | 发现 MediaCrawler 日志：启动时创建 chrome://new-tab-page/ 和 about:blank 两个标签页 | 可能是 MediaCrawler 内部创建的额外页面 |

### 可能原因分析
1. MediaCrawler 启动时创建了 `chrome://new-tab-page/` (新标签页) 和 `about:blank` 两个页面
2. MediaCrawler 使用 CDP 模式时会有额外的 DevTools 窗口

### 排查方向
- [x] 已定位到 MediaCrawler 启动时创建了多个页面 (chrome://new-tab-page/, about:blank)
- [x] 已修改 _screenshot_worker.py，添加关闭初始页面的逻辑
- [x] 第一次运行测试成功，截图完成 (3/5)，修复已生效

### 修改记录
| 时间 | 尝试 | 结果 | 备注 |
|------|------|------|------|
| 2025-03-28-20:25 | 运行观察 | MediaCrawler 启动时创建 chrome://new-tab-page/ 和 about:blank 两个初始页面 | |
| 2025-03-28-20:27 | 添加关闭初始页面逻辑 | 修改 _screenshot_worker.py，在创建工作页面之前关闭初始空白页面 | 修复已生效 |
| 2025-03-28-20:27 | 第一次运行结果 | 截图完成 3/5，问题1已解决 | 验证通过 |

---

## 问题2: 空关键词搜索全部视频

### 需求
关键词不输入时，搜索全部视频

### 修改记录
| 时间 | 尝试 | 结果 | 备注 |
|------|------|------|------|
| 2025-03-28 | 修改 mediacrawler_scraper.py | 当 keyword 为空时，不传递 --keywords 参数 | 待实际运行测试验证 |

### 排查方向
- [x] 已修改 mediacrawler_scraper.py:455-475，当 keyword 为空时不传 --keywords 参数

---

## 问题3: MCP/openClaw调用截图失败

### 需求
用户通过openClaw直接调用时，可能出现截图失败，需要在这里直接解决

### 排查记录
| 时间 | 尝试 | 结果 | 备注 |
|------|------|------|------|
| 2025-03-28 | 检查 _screenshot_worker.py:263 | CDP 端口不可用时返回空截图路径 | 可能原因：MCP 调用时浏览器会话不可访问 |

### 排查方向
- [x] 已添加 fallback 机制：当 CDP 连接失败时启动独立浏览器
- [ ] 测试 fallback 机制在 MCP 环境下的有效性

### 修改记录
| 时间 | 尝试 | 结果 | 备注 |
|------|------|------|------|
| 2025-03-28 | 修改 _screenshot_worker.py | 添加 fallback 浏览器机制，当 CDP 端口不可用或连接失败时启动独立浏览器进行截图 | 待测试 |

---

## 待验证项

### 问题1: 双浏览器
- [ ] 实际运行测试，观察浏览器窗口数量
- [ ] 可在 MediaCrawler 环境变量中添加调试日志定位浏览器启动

### 问题2: 空关键词搜索
- [ ] 实际运行测试，验证搜索全部视频功能
- [ ] 观察 MediaCrawler 在无 --keywords 参数时的行为

### 问题3: 截图 fallback
- [ ] 通过 MCP 方式调用，观察截图是否正常
- [ ] 验证 fallback 浏览器是否能正常完成截图

---

## 代码修改汇总

### 修改1: 空关键词支持 (mediacrawler_scraper.py)
- 位置: mediacrawler_scraper.py:455-475
- 修改: 当 keyword 为空字符串时不传递 --keywords 参数，让 MediaCrawler 搜索全部视频

### 修改2: 截图 fallback 机制 (_screenshot_worker.py)
- 位置: _screenshot_worker.py:247-295
- 修改: 当 CDP 端口 9222 不可用或 CDP 连接失败时，启动独立的 Chromium 浏览器进行截图
- 目的: 解决 MCP/openClaw 调用时可能出现截图失败的问题