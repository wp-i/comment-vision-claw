"""
Douyin scraper using MediaCrawler backend.

This implementation uses MediaCrawler for robust Douyin scraping,
avoiding Playwright's anti-detection issues.
"""

import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

from engine.config import (
    DATA_DIR,
    SCREENSHOTS_DIR,
    MIN_LIKE_COUNT,
    MAX_VIDEOS,
    MAX_COMMENTS,
    MIN_REPLY_COUNT,
    MEDIACRAWLER_PATH,
)
from engine.utils import log_progress, setup_directories
from engine.screenshot import capture_screenshots_sync


class MediaCrawlerDouyinScraper:
    """Douyin scraper using MediaCrawler as backend."""

    def __init__(self):
        self.mediapath = Path(MEDIACRAWLER_PATH)
        setup_directories([DATA_DIR, SCREENSHOTS_DIR])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _run_mediapcrawler(self, args: list, timeout: int = 600) -> subprocess.CompletedProcess:
        """Run MediaCrawler command."""
        cmd = ["python", "main.py"] + args
        log_progress(f"Running: python main.py {' '.join(args)}")

        result = subprocess.run(
            cmd,
            cwd=str(self.mediapath),
            capture_output=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return result

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

    def _clear_old_data(self):
        """Clear old MediaCrawler search data (preserve login state)."""
        data_dir = self.mediapath / "data" / "douyin" / "json"
        if data_dir.exists():
            for f in data_dir.glob("*.json"):
                try:
                    f.unlink()
                    log_progress(f"Cleared: {f.name}")
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
        log_progress(f"Starting capture for keyword: {keyword}")

        # Check if we already have data (use cache if available)
        data_dir = self.mediapath / "data" / "douyin" / "json"
        existing_files = list(data_dir.glob("search_contents_*.json")) if data_dir.exists() else []

        skip_crawler = False
        if existing_files:
            latest_file = max(existing_files, key=lambda p: p.stat().st_mtime)
            file_age = time.time() - latest_file.stat().st_mtime
            log_progress(f"Using existing data from {latest_file.name} (age: {int(file_age)}s)")
            skip_crawler = True

        if not skip_crawler:
            # Clear old search data (preserve login state in browser_data)
            self._clear_old_data()

            # Run MediaCrawler search
            search_result = self._run_mediapcrawler(
                [
                    "--platform",
                    "dy",
                    "--type",
                    "search",
                    "--lt",
                    "qrcode",
                    "--keywords",
                    keyword,
                    "--save_data_option",
                    "json",
                ]
            )

        # Load results after search
        videos = self._load_search_results()
        comments_data = self._load_comments_results()

        if not videos:
            log_progress("No videos found", level="WARNING")
            return []

        log_progress(f"Found {len(videos)} videos and {len(comments_data)} comments")

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
            if like_count < MIN_LIKE_COUNT and reply_count < MIN_REPLY_COUNT:
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
        hot_comments = hot_comments[:MAX_COMMENTS]

        # Count unique videos
        unique_videos = len(set(c["video_url"] for c in hot_comments))
        log_progress(f"Captured {len(hot_comments)} hot comments from {unique_videos} videos")

        # Save data first before starting Chrome (to avoid timeout)
        import json

        with open("./data/results.json", "w", encoding="utf-8") as f:
            json.dump(hot_comments, f, ensure_ascii=False, indent=2)

        # Now capture screenshots
        log_progress("Starting screenshot capture...")
        hot_comments = self._capture_screenshots(hot_comments)

        return hot_comments

    def _capture_screenshots(self, hot_comments: list) -> list:
        """Capture screenshots by launching Chrome with CDP."""
        import subprocess

        # Kill any existing Chrome processes
        try:
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
            time.sleep(2)
        except:
            pass

        # Start Chrome with CDP
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        user_data = r"D:\MediaCrawler\browser_data\cdp_dy_user_data_dir"

        try:
            subprocess.Popen([chrome_path, "--remote-debugging-port=9222", f"--user-data-dir={user_data}"])
            log_progress("Chrome started, waiting for it to be ready...")
            time.sleep(5)  # Wait for Chrome to start
        except Exception as e:
            log_progress(f"Failed to start Chrome: {e}", level="WARNING")
            return hot_comments

        # Capture screenshots
        try:
            from engine.screenshot import capture_screenshots_sync

            hot_comments = capture_screenshots_sync(hot_comments, max_screenshots=len(hot_comments))

            # Kill Chrome after screenshots
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
        except Exception as e:
            log_progress(f"Screenshot capture failed: {e}", level="WARNING")

        return hot_comments


def check_mediacrawler_installed() -> bool:
    """Check if MediaCrawler is installed."""
    path = Path(MEDIACRAWLER_PATH)
    return path.exists() and (path / "main.py").exists()
