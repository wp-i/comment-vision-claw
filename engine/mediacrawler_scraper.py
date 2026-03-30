"""
Douyin scraper using MediaCrawler backend.

This implementation uses MediaCrawler for robust Douyin scraping,
avoiding Playwright's anti-detection issues.
"""

import os
import json
import time
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from engine.config import (
    DATA_DIR,
    SCREENSHOTS_DIR,
    MAX_VIDEOS,
    MAX_COMMENTS,
    MEDIACRAWLER_PATH,
    min_like_count,
    min_reply_count,
    max_comments,
    max_videos,
)
from engine.utils import log_progress, setup_directories


def update_status_file(status: str, is_error: bool = False):
    """更新状态文件供前端读取"""
    state_file = "./data/capture_state.json"
    state = {
        "status": status,
        "is_error": is_error,
        "timestamp": datetime.now().isoformat(),
    }
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except:
        pass


class MediaCrawlerDouyinScraper:
    """Douyin scraper using MediaCrawler as backend."""

    def __init__(self):
        self.mediapath = Path(MEDIACRAWLER_PATH)
        self.crawler_running = False
        self._stop_signal_sent = False
        setup_directories([DATA_DIR, SCREENSHOTS_DIR])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _monitor_hot_comments(self, target_count: int = 10):
        """监控热评数量，达到目标时发送停止信号"""
        while self.crawler_running:
            try:
                # 加载当前的评论数据
                comments_data = self._load_comments_results()

                # 统计符合条件的热评数量
                hot_count = 0
                for comment in comments_data:
                    like_count = comment.get("like_count", 0) or comment.get("digg_count", 0)
                    if isinstance(like_count, str):
                        like_count = int(like_count) if like_count.isdigit() else 0

                    reply_count = comment.get("sub_comment_count", 0) or comment.get("reply_comment_total", 0)
                    if isinstance(reply_count, str):
                        reply_count = int(reply_count) if reply_count.isdigit() else 0

                    if like_count >= min_like_count() or reply_count >= min_reply_count():
                        hot_count += 1

                # 如果达到目标，发送停止信号
                if hot_count >= target_count:
                    log_progress(f"已找到 {hot_count} 条热评，发送停止信号")
                    self._write_stop_signal()
                    break

                log_progress(f"当前热评数量: {hot_count}/{target_count}")
            except Exception as e:
                log_progress(f"监控异常: {e}", level="WARNING")

            time.sleep(3)  # 每3秒检查一次

    def _write_stop_signal(self):
        if self._stop_signal_sent:
            return
        with open("./data/stop_crawler.signal", "w", encoding="utf-8") as f:
            f.write("stop")
        self._stop_signal_sent = True

    def _estimate_hot_count_from_comments(self, comments_data: list) -> int:
        hot_count = 0
        for comment in comments_data:
            like_count = comment.get("like_count", 0) or comment.get("digg_count", 0)
            if isinstance(like_count, str):
                like_count = int(like_count) if like_count.isdigit() else 0

            reply_count = comment.get("sub_comment_count", 0) or comment.get("reply_comment_total", 0)
            if isinstance(reply_count, str):
                reply_count = int(reply_count) if reply_count.isdigit() else 0

            if like_count >= min_like_count() or reply_count >= min_reply_count():
                hot_count += 1
        return hot_count

    def _wait_for_hot_comments(self, target_count: int, timeout: int = 900, poll_interval: int = 3) -> bool:
        start = time.time()
        previous_total = -1
        stable_rounds = 0
        stable_limit = 3
        while time.time() - start < timeout:
            comments_data = self._load_comments_results()
            hot_count = self._estimate_hot_count_from_comments(comments_data)
            total_comments = len(comments_data)
            log_progress(f"当前热评数量: {hot_count}/{target_count}")
            if hot_count >= target_count:
                self._write_stop_signal()
                return True

            max_total_comments = max_videos() * max_comments()
            if total_comments >= max_total_comments:
                log_progress(
                    f"已达到抓取上限（评论数 {total_comments}/{max_total_comments}），停止继续等待热评",
                    level="INFO",
                )
                self._write_stop_signal()
                return False

            if total_comments == previous_total:
                stable_rounds += 1
            else:
                stable_rounds = 0
                previous_total = total_comments

            if stable_rounds >= stable_limit:
                log_progress(
                    f"评论数据连续 {stable_limit} 轮无增长（当前 {total_comments} 条），停止继续等待",
                    level="INFO",
                )
                self._write_stop_signal()
                return False
            time.sleep(poll_interval)
        return False

    def _run_mediapcrawler(self, args: list, timeout: int = 900) -> subprocess.CompletedProcess:
        """Run MediaCrawler command with real-time output."""
        cmd = ["python", "main.py"] + args
        log_progress(f"Running: python main.py {' '.join(args)}")

        # Run with real-time output so user can see login prompt
        # Don't capture output to allow real-time display
        import sys

        env = os.environ.copy()
        env.setdefault("PLAYWRIGHT_TIMEOUT", "120000")
        env.setdefault("ENABLE_CDP_MODE", "true")
        env.setdefault("CDP_HEADLESS", "false")
        env["AUTO_CLOSE_BROWSER"] = "false"
        env["MEDIACRAWLER_PRESERVE_BROWSER"] = "true"
        env["CRAWLER_MAX_NOTES_COUNT"] = str(max_videos())
        env["CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES"] = str(max_comments())
        log_progress(
            "MediaCrawler limits: "
            f"MAX_VIDEOS={env['CRAWLER_MAX_NOTES_COUNT']}, "
            f"MAX_COMMENTS={env['CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES']}"
        )
        log_progress(
            "Browser env: "
            f"AUTO_CLOSE_BROWSER={env['AUTO_CLOSE_BROWSER']}, "
            f"MEDIACRAWLER_PRESERVE_BROWSER={env['MEDIACRAWLER_PRESERVE_BROWSER']}"
        )

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.mediapath),
                timeout=timeout,
                env=env,
            )
            return result
        except subprocess.TimeoutExpired as e:
            log_progress(f"MediaCrawler 子进程超时: {e}", level="WARNING")
            raise

    def _load_search_results(self) -> list:
        """Load search results from MediaCrawler output."""
        data_dir = self.mediapath / "data" / "douyin" / "json"

        if not data_dir.exists():
            return []

        # Find search result files - MediaCrawler generates search_contents_*.json
        json_files = list(data_dir.glob("search_contents_*.json"))
        if not json_files:
            json_files = list(data_dir.glob("search_*.json"))
        if not json_files:
            return []

        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)

        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            log_progress(f"Error loading search results: {e}", level="ERROR")
            return []

    def _load_comments_results(self) -> list:
        """Load comments results from MediaCrawler output."""
        data_dir = self.mediapath / "data" / "douyin" / "json"

        if not data_dir.exists():
            return []

        # Find comments result files
        json_files = list(data_dir.glob("search_comments_*.json"))
        if not json_files:
            return []

        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)

        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            log_progress(f"Error loading comments: {e}", level="ERROR")
            return []

    def _wait_for_browser_release(self, user_data_dir: str, max_wait: int = 30):
        """等待 MediaCrawler 的 Chromium 进程完全释放 user_data_dir 文件锁。

        通过检测 SingletonLock 文件是否可重命名来判断锁状态，
        比固定 time.sleep(5) 更可靠。

        Args:
            user_data_dir: Chromium user data 目录路径
            max_wait: 最大等待秒数
        """
        if not os.path.exists(user_data_dir):
            log_progress(f"user_data_dir 不存在，跳过等待: {user_data_dir}")
            return

        lock_file = os.path.join(user_data_dir, "SingletonLock")

        for i in range(max_wait):
            if not os.path.exists(lock_file):
                if i > 0:
                    log_progress(f"浏览器资源已释放 (等待了 {i} 秒)")
                else:
                    log_progress("浏览器资源已释放")
                # 额外等待 2 秒确保文件句柄完全关闭
                time.sleep(2)
                return

            try:
                # 尝试重命名来检测锁
                temp_name = lock_file + ".test"
                os.rename(lock_file, temp_name)
                os.rename(temp_name, lock_file)
                # 重命名成功说明未被锁定
                if i > 0:
                    log_progress(f"浏览器资源已释放 (等待了 {i} 秒)")
                else:
                    log_progress("浏览器资源已释放")
                time.sleep(2)
                return
            except (OSError, PermissionError):
                if i == 0:
                    log_progress("等待 MediaCrawler 浏览器释放文件锁...")
                time.sleep(1)

        log_progress(f"警告: 等待 {max_wait} 秒后浏览器仍未释放，继续执行...", level="WARNING")
        # 最后兜底等待
        time.sleep(3)

    def _check_cdp_ports(self):
        """检查 CDP 端口状态，用于诊断浏览器是否还在运行"""
        import socket

        for port in range(9222, 9227):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            conn_result = sock.connect_ex(("localhost", port))
            sock.close()
            if conn_result == 0:
                log_progress(f"CDP 端口 {port} 可用")
            else:
                log_progress(f"CDP 端口 {port} 不可用", level="DEBUG")

    def _cleanup_browser(self):
        """截图完成后统一关闭 CDP 浏览器。

        通过 CDP 协议连接浏览器并关闭，适用于 MEDIACRAWLER_PRESERVE_BROWSER=true 场景。
        """
        log_progress("正在关闭浏览器...")
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                for port in range(9222, 9227):
                    try:
                        import socket

                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        conn_result = sock.connect_ex(("localhost", port))
                        sock.close()
                        if conn_result != 0:
                            continue

                        browser = p.chromium.connect_over_cdp(f"http://localhost:{port}")
                        browser.close()
                        log_progress(f"已关闭端口 {port} 的浏览器")
                        return
                    except Exception:
                        continue
                log_progress("未找到需要关闭的浏览器进程")
        except Exception as e:
            log_progress(f"关闭浏览器时出错: {e}", level="WARNING")

    def _clear_old_data(self):
        """Clear captured data but PRESERVE login session (browser cache)."""
        import os

        # Clear MediaCrawler data (JSON files only - NOT login session)
        data_dir = self.mediapath / "data" / "douyin" / "json"
        if data_dir.exists():
            for f in data_dir.glob("*.json"):
                try:
                    f.unlink()
                    log_progress(f"Cleared: {f.name}")
                except Exception:
                    pass

        # DO NOT clear browser_data - login session must be preserved!
        # Browser cache clearing should only happen at system startup via cleanup.py

        # Clear local results
        local_files = ["./data/results.json", "./data/capture_state.json"]
        for f in local_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    log_progress(f"Cleared: {f}")
                except Exception:
                    pass

        # Clear screenshots
        screenshots_dir = "./data/screenshots"
        if os.path.exists(screenshots_dir):
            for f in os.listdir(screenshots_dir):
                if f.endswith(".png"):
                    try:
                        os.remove(os.path.join(screenshots_dir, f))
                        log_progress(f"Cleared screenshot: {f}")
                    except Exception:
                        pass

        # Clear old PDF reports
        for f in os.listdir("./data"):
            if f.startswith("report_") and f.endswith(".pdf"):
                try:
                    os.remove(os.path.join("./data", f))
                    log_progress(f"Cleared report: {f}")
                except Exception:
                    pass

    def capture_hot_comments(self, keyword: str, time_range: str = "1day") -> list:
        """
        Main method to capture hot comments for a keyword.
        Always fetches fresh data for the given keyword.

        Args:
            keyword: Search keyword
            time_range: Time range filter (1day, 1week, 1month, 1year)

        Returns:
            List of captured comment data with screenshots
        """
        # 检查是否有正在进行的抓取任务
        lock_file = "./data/capture.lock"
        if os.path.exists(lock_file):
            log_progress("Another capture is already running, skipping", level="WARNING")
            return []

        # 创建锁文件
        try:
            with open(lock_file, "w", encoding="utf-8") as f:
                f.write(f"Started at {datetime.now().isoformat()}")
        except Exception as e:
            log_progress(f"Failed to create lock file: {e}", level="ERROR")
            return []

        try:
            log_progress(f"Starting capture for keyword: {keyword}")
            update_status_file("正在抓取，请稍候...")
            return self._do_capture_hot_comments(keyword, time_range)
        finally:
            # 确保删除锁文件
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except Exception:
                    pass

    def _do_capture_hot_comments(self, keyword: str, time_range: str = "1day") -> list:
        # Check if we already have data (use cache if available)
        data_dir = self.mediapath / "data" / "douyin" / "json"
        existing_files = list(data_dir.glob("search_contents_*.json")) if data_dir.exists() else []

        skip_crawler = False
        if existing_files:
            latest_file = max(existing_files, key=lambda p: p.stat().st_mtime)
            file_age = time.time() - latest_file.stat().st_mtime
            log_progress(f"Using existing data from {latest_file.name} (age: {int(file_age)}s)")
            skip_crawler = True

        search_failed = False
        expected_comment_cap = max_videos() * max_comments()

        if not skip_crawler:
            # Clear old search data
            self._clear_old_data()

            # 清除旧的停止信号文件
            stop_signal_file = "./data/stop_crawler.signal"
            self._stop_signal_sent = False
            if os.path.exists(stop_signal_file):
                try:
                    os.remove(stop_signal_file)
                except:
                    pass

            # 启动监控线程
            self.crawler_running = True
            monitor_thread = threading.Thread(target=self._monitor_hot_comments, args=(max_comments(),), daemon=True)
            monitor_thread.start()
            log_progress("已启动热评监控线程")

            hot_ready = False

            # Build crawler arguments based on whether keyword is provided
            crawler_args = [
                "--platform",
                "dy",
                "--type",
                "search",
                "--lt",
                "qrcode",
                "--save_data_option",
                "json",
            ]

            # If keyword is provided, add it; otherwise search all videos (without keyword)
            search_keyword = keyword.strip() if keyword else ""
            if search_keyword:
                crawler_args.extend(["--keywords", search_keyword])
                log_progress(f"使用关键词搜索: {search_keyword}")
            else:
                log_progress("关键词为空，搜索全部视频")

            # Run MediaCrawler search
            try:
                search_result = self._run_mediapcrawler(crawler_args)
                hot_ready = self._wait_for_hot_comments(max_comments(), timeout=900, poll_interval=3)
                if getattr(search_result, "returncode", 0) not in (0, None):
                    search_failed = True
                    log_progress(f"MediaCrawler 退出码异常: {search_result.returncode}", level="WARNING")
                    if not existing_files:
                        return []
                else:
                    log_progress("MediaCrawler 子进程正常结束", level="INFO")
            finally:
                # 停止监控线程
                self.crawler_running = False
                log_progress("已停止热评监控线程")

                # 清除停止信号文件
                if os.path.exists(stop_signal_file):
                    try:
                        os.remove(stop_signal_file)
                    except:
                        pass

            if not hot_ready:
                current_comments = self._load_comments_results()
                current_hot_count = self._estimate_hot_count_from_comments(current_comments)
                current_total_comments = len(current_comments)
                if current_total_comments >= expected_comment_cap:
                    log_progress(
                        f"已达到抓取上限（评论数 {current_total_comments}/{expected_comment_cap}），使用当前结果继续处理",
                        level="INFO",
                    )
                else:
                    log_progress(
                        f"热评未达目标，当前热评 {current_hot_count}/{max_comments()}，使用当前结果继续处理",
                        level="WARNING",
                    )

        # Load results after search
        videos = self._load_search_results()
        comments_data = self._load_comments_results()

        if not videos:
            if search_failed:
                log_progress("MediaCrawler 未成功返回搜索数据，可能是未登录或搜索失败", level="WARNING")
            else:
                log_progress("No videos found", level="WARNING")
            return []

        if comments_data == []:
            log_progress("MediaCrawler search 已返回视频，但评论数据为空", level="WARNING")
            return []

        log_progress(f"Found {len(videos)} videos and {len(comments_data)} comments")

        comments_data = self._load_comments_results()

        # Build video lookup map
        video_map = {}
        for video in videos:
            aweme_id = video.get("aweme_id")
            if aweme_id:
                video_map[str(aweme_id)] = video

        # Process comments and filter hot ones
        # Track comments per video (max 2 per video for diversity)
        video_comments = {}  # aweme_id -> list of comments (max 2)
        seen_contents = set()  # Track seen comment content to avoid duplicates

        for comment in comments_data:
            # Get like count
            like_count = comment.get("like_count", 0) or comment.get("digg_count", 0)
            if isinstance(like_count, str):
                like_count = int(like_count) if like_count.isdigit() else 0

            # Get reply count
            reply_count = comment.get("sub_comment_count", 0) or comment.get("reply_comment_total", 0)
            if isinstance(reply_count, str):
                reply_count = int(reply_count) if reply_count.isdigit() else 0

            # Filter: 5000赞以上 OR 400回复以上
            if like_count < min_like_count() and reply_count < min_reply_count():
                continue

            # Get video info
            aweme_id = str(comment.get("aweme_id", ""))
            video_info = video_map.get(aweme_id, {})

            # Skip if video info not found
            if not video_info:
                continue

            # Get comment content and skip duplicates
            content = comment.get("content", "")
            if not content or len(content) < 5:
                continue
            if content in seen_contents:
                continue
            seen_contents.add(content)

            hot_comment = {
                "platform": "douyin",
                "video_title": video_info.get("desc", "Unknown Title")[:100],
                "video_author": video_info.get("nickname", "Unknown Author"),
                "video_url": video_info.get("aweme_url", f"https://www.douyin.com/video/{aweme_id}"),
                "comment_author": comment.get("nickname", "Unknown"),
                "comment_content": content,
                "like_count": like_count,
                "reply_count": reply_count,
                "has_image": bool(comment.get("pictures")),
                "screenshot_path": "",
                "timestamp": datetime.now().isoformat(),
            }

            # Keep max 2 comments per video (sorted by likes later)
            if aweme_id not in video_comments:
                video_comments[aweme_id] = []

            if len(video_comments[aweme_id]) < 2:
                video_comments[aweme_id].append(hot_comment)
            else:
                # Replace the lower one if this is higher
                video_comments[aweme_id].sort(key=lambda x: x["like_count"])
                if like_count > video_comments[aweme_id][0]["like_count"]:
                    video_comments[aweme_id][0] = hot_comment

        # Flatten and sort by like count
        hot_comments = []
        for comments in video_comments.values():
            hot_comments.extend(comments)

        hot_comments.sort(key=lambda x: x["like_count"], reverse=True)
        hot_comments = hot_comments[: max_comments()]

        # Count unique videos
        unique_videos = len(set(c["video_url"] for c in hot_comments))
        log_progress(f"Captured {len(hot_comments)} hot comments from {unique_videos} videos")

        # 保存数据
        import json

        with open("./data/results.json", "w", encoding="utf-8") as f:
            json.dump(hot_comments, f, ensure_ascii=False, indent=2)

        # MediaCrawler 退出后，CDP 浏览器仍由 MEDIACRAWLER_PRESERVE_BROWSER 保活，直接截图。
        log_progress("MediaCrawler 子进程已退出，检查 CDP 端口状态...")
        self._check_cdp_ports()

        if hot_comments:
            log_progress(f"开始统一截图，共 {len(hot_comments)} 条热评...")
            update_status_file(f"正在生成热评截图（{len(hot_comments)} 条）...")
            hot_comments = self._capture_screenshots(hot_comments)
        else:
            log_progress("没有可截图的热评，跳过截图步骤。")

        # 截图完成后统一关闭浏览器
        self._cleanup_browser()

        return hot_comments

    def _capture_screenshots(self, hot_comments: list) -> list:
        """Capture screenshots for a single comment using Playwright built-in browser."""
        import subprocess
        import sys

        # Capture screenshots using Playwright built-in browser with timeout
        try:
            # 使用 subprocess 运行截图，设置 90 秒超时
            input_data = {
                "comments": hot_comments,
                "screenshots_dir": "./data/screenshots",
                "min_like_count": min_like_count(),
            }

            temp_input = "./data/screenshot_input.json"
            temp_output = "./data/screenshot_output.json"

            with open(temp_input, "w", encoding="utf-8") as f:
                json.dump(input_data, f, ensure_ascii=False, default=str)

            script_path = os.path.join(os.path.dirname(__file__), "_screenshot_worker.py")
            env = os.environ.copy()
            env.setdefault("DEBUG_SCREENSHOT_WORKER", "1")
            result = subprocess.run(
                [sys.executable, script_path, temp_input, temp_output],
                timeout=300,  # 5 minutes timeout for all screenshots
                env=env,
            )

            log_progress(f"Screenshot worker return code: {result.returncode}")

            # 读取结果
            if os.path.exists(temp_output):
                with open(temp_output, "r", encoding="utf-8") as f:
                    screenshot_results = json.load(f)
                # 更新截图路径
                success_count = 0
                for i, comment in enumerate(hot_comments):
                    if i < len(screenshot_results):
                        path = screenshot_results[i].get("screenshot_path", "")
                        if path and os.path.exists(path):
                            comment["screenshot_path"] = path
                            success_count += 1
                log_progress(f"截图完成: {success_count}/{len(hot_comments)}")
            else:
                log_progress("截图结果文件未生成，所有截图视为失败", level="WARNING")

            # 清理临时文件
            for f in [temp_input, temp_output]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

        except subprocess.TimeoutExpired:
            log_progress("Screenshot timed out, skipping", level="WARNING")
        except Exception as e:
            log_progress(f"Screenshot failed: {e}", level="WARNING")

        return hot_comments


def check_mediacrawler_installed() -> bool:
    """Check if MediaCrawler is installed."""
    path = Path(MEDIACRAWLER_PATH)
    return path.exists() and (path / "main.py").exists()
