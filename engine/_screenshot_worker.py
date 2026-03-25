"""
Screenshot worker script - runs in subprocess to avoid event loop conflicts.

通过 CDP 连接主抓取阶段的浏览器（端口 9222），浏览器由外层统一清理。
"""

import json
import os
import sys
import re
import random
import time
from datetime import datetime


def _get_debug_log_enabled() -> bool:
    return os.getenv("DEBUG_SCREENSHOT_WORKER", "0") == "1"


def _dbg(msg: str):
    if _get_debug_log_enabled():
        print(msg, flush=True)


def _check_login_status(page) -> bool:
    """检测页面是否处于已登录状态（无登录弹窗）。

    Returns:
        True 如果已登录（无弹窗），False 如果检测到登录弹窗。
    """
    try:
        # 等待页面加载
        time.sleep(3)

        # 检测常见的登录弹窗选择器
        login_selectors = [
            # 抖音登录弹窗
            "div.login-guide-container",
            "div[class*='login-guide']",
            "div[class*='loginGuide']",
            "div[class*='login-modal']",
            "div[class*='loginModal']",
            # 扫码登录
            "div[class*='qrcode-login']",
            "div[class*='qrcodeLogin']",
            # 通用登录提示
            "div:has-text('扫码登录')",
            "div:has-text('请先登录')",
        ]

        for selector in login_selectors:
            try:
                elem = page.query_selector(selector)
                if elem and elem.is_visible():
                    print(f"[worker] 检测到登录弹窗: {selector}")
                    return False
            except Exception:
                continue

        # 额外检查：页面内容是否包含登录相关文字
        try:
            body_text = page.inner_text("body")
            login_keywords = ["扫码登录", "请先登录", "登录后查看", "请使用抖音App扫码"]
            for kw in login_keywords:
                if kw in body_text:
                    print(f"[worker] 页面包含登录提示: '{kw}'")
                    return False
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"[worker] 登录状态检测异常: {e}")
        return True  # 异常时假设已登录，继续尝试


def main():
    if len(sys.argv) != 3:
        print("Usage: python _screenshot_worker.py <input.json> <output.json>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    print(f"[worker] 启动截图 worker")
    print(f"[worker] 输入文件: {input_file}")
    print(f"[worker] 输出文件: {output_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    comments = data["comments"]
    screenshots_dir = data["screenshots_dir"]
    min_like_count = data.get("min_like_count", 1000)

    os.makedirs(screenshots_dir, exist_ok=True)

    # 将项目根目录加入 sys.path，以便导入 engine.config
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from playwright.sync_api import sync_playwright

    video_captured_contents = {}
    results = []

    try:
        with sync_playwright() as p:
            _dbg("[worker] playwright started")

            # 通过 CDP 连接主抓取阶段的浏览器
            cdp_url = "http://localhost:9222"
            print(f"[worker] 尝试连接 CDP: {cdp_url}")

            # 检查端口是否可用
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            conn_result = sock.connect_ex(("localhost", 9222))
            sock.close()
            if conn_result != 0:
                print(f"[worker] 错误: CDP 端口 9222 不可用 (conn_result={conn_result})")
                print("[worker] 浏览器可能已被 MediaCrawler 清理")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump([{"screenshot_path": ""} for _ in comments], f)
                return

            print(f"[worker] CDP 端口 9222 可用，尝试连接...")
            cdp_browser = p.chromium.connect_over_cdp(cdp_url)
            print(f"[worker] CDP 连接成功: is_connected={cdp_browser.is_connected()}")
            contexts = cdp_browser.contexts
            context = contexts[0] if contexts else cdp_browser.new_context()
            print(f"[worker] 已连接 CDP 浏览器; contexts={len(cdp_browser.contexts)}")

            # ── 登录状态检测（仅在第一个视频时检测）──
            login_checked = False
            is_logged_in = True
            _dbg(f"[worker] begin loop, total_comments={len(comments)}")

            # ── 截图循环 ──
            print(f"[worker] 开始截图循环，共 {len(comments)} 条评论")
            for i, comment in enumerate(comments, 1):
                video_url = comment.get("video_url", "")
                like_count = comment.get("like_count", 0)
                comment_content = comment.get("comment_content", "")

                print(f"[worker] ({i}/{len(comments)}) 处理视频: {video_url[:50]}...")

                result = {"screenshot_path": ""}

                if not video_url:
                    results.append(result)
                    continue

                # 如果已确认未登录，跳过所有截图
                if not is_logged_in:
                    print(f"[worker] ({i}/{len(comments)}) 跳过（未登录）")
                    results.append(result)
                    continue

                    _dbg(f"[worker] ({i}/{len(comments)}) open page: {video_url}")

                page = None
                try:
                    start_time = time.time()
                    timeout_seconds = 90

                    print(f"[worker] ({i}/{len(comments)}) 创建新页面...")
                    page = context.new_page()

                    try:
                        print(f"[worker] ({i}/{len(comments)}) 导航到: {video_url[:50]}...")
                        page.goto(video_url, wait_until="domcontentloaded", timeout=60000)
                        print(f"[worker] ({i}/{len(comments)}) 页面加载成功")
                    except Exception as e:
                        print(f"[worker] ({i}/{len(comments)}) 页面加载失败: {str(e)[:100]}")
                        try:
                            page.close()
                        except Exception:
                            pass
                        page = None
                        results.append(result)
                        continue

                    time.sleep(5)

                    # 首次访问时检测登录状态
                    if not login_checked:
                        login_checked = True
                        is_logged_in = _check_login_status(page)
                        _dbg(f"[worker] login_checked={login_checked}, is_logged_in={is_logged_in}")
                        if not is_logged_in:
                            print("[worker] 未登录抖音，无法截图评论")
                            print("[worker] 请先通过 MediaCrawler 扫码登录抖音")
                            try:
                                page.close()
                            except Exception:
                                pass
                            page = None
                            results.append(result)
                            continue

                    if time.time() - start_time > timeout_seconds:
                        print(f"[worker] ({i}/{len(comments)}) 超时 (goto)")
                        try:
                            page.close()
                        except Exception:
                            pass
                        page = None
                        results.append(result)
                        continue

                    # 滚动到评论区
                    for _ in range(10):
                        page.evaluate("window.scrollBy(0, 300)")
                        time.sleep(0.3)
                    time.sleep(2)

                    if time.time() - start_time > timeout_seconds:
                        print(f"[worker] ({i}/{len(comments)}) 超时 (scroll)")
                        try:
                            page.close()
                        except Exception:
                            pass
                        page = None
                        results.append(result)
                        continue

                    # 点击"最热"排序
                    for sel in ["span:text-is('最热')", "span:has-text('最热')", "div:text-is('最热')"]:
                        try:
                            btn = page.query_selector(sel)
                            if btn and btn.is_visible():
                                btn.click()
                                print(f"[worker] 已点击'最热'")
                                break
                        except Exception:
                            continue

                    time.sleep(3)
                    page.evaluate("window.scrollBy(0, 100)")
                    time.sleep(1)

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"comment_{like_count}likes_{timestamp}_{i}.png"
                    filepath = os.path.join(screenshots_dir, filename)

                    if time.time() - start_time > timeout_seconds:
                        print(f"[worker] ({i}/{len(comments)}) 超时 (before extract)")
                        try:
                            page.close()
                        except Exception:
                            pass
                        page = None
                        results.append(result)
                        continue

                    # 提取页面评论
                    page_comments = []
                    comment_items = page.query_selector_all("div[data-e2e='comment-item']")
                    for elem in comment_items:
                        try:
                            if not elem.is_visible():
                                continue
                            bbox = elem.bounding_box()
                            if not bbox or bbox["height"] < 40:
                                continue
                            full_text = elem.inner_text()
                            likes = 0
                            wan_matches = re.findall(r"(\d+\.?\d*)\s*万", full_text)
                            if wan_matches:
                                likes = int(float(wan_matches[0]) * 10000)
                            else:
                                numbers = re.findall(r"\b(\d{2,6})\b", full_text)
                                for num_str in numbers:
                                    num = int(num_str)
                                    if num > likes and num < 1_000_000:
                                        likes = num
                            lines = full_text.strip().split("\n")
                            content = ""
                            for line in lines:
                                line = line.strip()
                                if len(line) > 5 and not line.isdigit() and "回复" not in line and "展开" not in line:
                                    content = line
                                    break
                            page_comments.append(
                                {
                                    "element": elem,
                                    "content": content,
                                    "likes": likes,
                                    "bbox": bbox,
                                }
                            )
                        except Exception:
                            continue

                    _dbg(f"[worker] 提取到 {len(page_comments)} 条评论")

                    if time.time() - start_time > timeout_seconds:
                        print(f"[worker] ({i}/{len(comments)}) 超时 (before match)")
                        try:
                            page.close()
                        except Exception:
                            pass
                        page = None
                        results.append(result)
                        continue

                    # 匹配目标评论
                    content_prefix = comment_content[:20] if len(comment_content) > 20 else comment_content
                    exclude_contents = video_captured_contents.get(video_url, set())

                    matched = None

                    # 优先内容匹配
                    if content_prefix:
                        for pc in page_comments:
                            if content_prefix in pc["content"]:
                                pc_prefix = pc["content"][:30]
                                if pc_prefix not in exclude_contents:
                                    matched = pc
                                    print(f"[worker] 内容匹配: {pc['content'][:30]}")
                                    break

                    # 点赞数匹配（±10%）
                    if not matched and like_count >= min_like_count:
                        for pc in page_comments:
                            if abs(pc["likes"] - like_count) <= like_count * 0.1:
                                pc_prefix = pc["content"][:30]
                                if pc_prefix not in exclude_contents:
                                    matched = pc
                                    print(f"[worker] 点赞数匹配: {pc['likes']} vs {like_count}")
                                    break

                    # 兜底：取最高赞且未截过的
                    if not matched:
                        valid = [pc for pc in page_comments if pc["likes"] >= min_like_count]
                        valid.sort(key=lambda x: x["likes"], reverse=True)
                        for pc in valid:
                            pc_prefix = pc["content"][:30]
                            if pc_prefix not in exclude_contents:
                                matched = pc
                                print(f"[worker] 最高赞兜底: {pc['likes']}")
                                break

                    if matched:
                        if time.time() - start_time > timeout_seconds:
                            print(f"[worker] ({i}/{len(comments)}) 超时 (before screenshot)")
                            try:
                                page.close()
                            except Exception:
                                pass
                            page = None
                            results.append(result)
                            continue

                        elem = matched["element"]
                        elem.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        bbox = elem.bounding_box()
                        if bbox:
                            padding = 10
                            clip_x = max(0, bbox["x"] - padding)
                            clip_y = max(0, bbox["y"] - padding)
                            clip_width = min(1280 - clip_x, bbox["width"] + 2 * padding)
                            clip_height = min(900 - clip_y, bbox["height"] + 2 * padding)
                            if clip_width > 0 and clip_height > 0:
                                page.screenshot(
                                    path=filepath,
                                    clip={"x": clip_x, "y": clip_y, "width": clip_width, "height": clip_height},
                                )
                                result["screenshot_path"] = filepath
                                captured_prefix = matched["content"][:20]
                                if video_url not in video_captured_contents:
                                    video_captured_contents[video_url] = set()
                                video_captured_contents[video_url].add(captured_prefix)
                                print(f"[worker] ({i}/{len(comments)}) 截图已保存")
                            else:
                                print(f"[worker] ({i}/{len(comments)}) clip 区域无效")
                        else:
                            print(f"[worker] ({i}/{len(comments)}) 无法获取 bbox")
                    else:
                        print(f"[worker] ({i}/{len(comments)}) 未找到匹配评论")

                    page.close()
                    page = None
                    time.sleep(random.uniform(1, 2))

                except Exception as e:
                    print(f"[worker] ({i}/{len(comments)}) 失败: {str(e)[:80]}")
                    if page:
                        try:
                            page.close()
                        except Exception:
                            pass
                        page = None

                results.append(result)

            # 浏览器由外层统一关闭，这里不关闭
            print(f"[worker] 截图完成，共处理 {len(results)} 条评论")
            print("[worker] 完成！")

    except Exception as e:
        print(f"[worker] 启动失败: {str(e)}")
        import traceback

        traceback.print_exc()

    # 确保结果数量与输入一致
    while len(results) < len(comments):
        results.append({"screenshot_path": ""})

    # 写出结果
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)


if __name__ == "__main__":
    main()
