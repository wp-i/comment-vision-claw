"""
Configuration settings for the Comment-Vision-Claw engine.

This module contains platform-specific selectors, URLs, and other configuration
parameters needed for the scraper to function properly.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# General settings
DATA_DIR = os.getenv("DATA_DIR", "./data")
SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "./data/screenshots")
USER_DATA_DIR = os.getenv("USER_DATA_DIR", "./data/user_data")
PLATFORM = os.getenv("PLATFORM", "douyin")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

# Hot comment thresholds (OR condition: likes >= MIN_LIKE_COUNT OR replies >= MIN_REPLY_COUNT)
MIN_LIKE_COUNT = int(os.getenv("MIN_LIKE_COUNT", "1000"))
MIN_REPLY_COUNT = int(os.getenv("MIN_REPLY_COUNT", "100"))
MAX_VIDEOS = int(os.getenv("MAX_VIDEOS", "200"))
MAX_COMMENTS = int(os.getenv("MAX_COMMENTS", "20"))
MAX_SCREENSHOTS = int(os.getenv("MAX_SCREENSHOTS", "10"))


# Dynamic configuration accessors
def min_like_count() -> int:
    """Return the current minimum like count from environment (dynamic).

    Reads MIN_LIKE_COUNT from env every time it is called to reflect
    runtime changes without restarting the process.
    """
    try:
        # Reload .env to reflect live changes without restarting the process
        from dotenv import load_dotenv

        load_dotenv()
        return int(os.getenv("MIN_LIKE_COUNT", "1000"))
    except Exception:
        return 1000


def min_reply_count() -> int:
    """Return the current minimum reply count from environment (dynamic)."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
        return int(os.getenv("MIN_REPLY_COUNT", "100"))
    except Exception:
        return 100


def max_videos() -> int:
    """Return the current max videos from environment (dynamic)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
        return int(os.getenv("MAX_VIDEOS", "200"))
    except Exception:
        return 200


def max_comments() -> int:
    """Return the current MAX_COMMENTS from environment (dynamic)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
        return int(os.getenv("MAX_COMMENTS", "20"))
    except Exception:
        return 20


# External tools
def _detect_mediapcrawler_path():
    """自动检测MediaCrawler安装位置"""
    # 优先使用环境变量
    env_path = os.getenv("MEDIACRAWLER_PATH")
    if env_path and os.path.exists(os.path.join(env_path, "main.py")):
        return env_path

    # 常见安装位置（项目旁边优先）
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(script_dir, "MediaCrawler"),  # 项目旁边
        "D:/MediaCrawler",
        "C:/MediaCrawler",
        "../MediaCrawler",
        "./MediaCrawler",
        os.path.expanduser("~/MediaCrawler"),
    ]

    for path in candidates:
        if os.path.exists(os.path.join(path, "main.py")):
            return os.path.abspath(path)

    # 默认返回项目旁边
    return os.path.join(script_dir, "MediaCrawler")


MEDIACRAWLER_PATH = _detect_mediapcrawler_path()
CDP_URL = os.getenv("CDP_URL", "http://127.0.0.1:9222")

# AI Analysis (optional)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Platform URLs
PLATFORM_URLS = {
    "douyin": "https://www.douyin.com/",
    "xiaohongshu": "https://www.xiaohongshu.com/",
}

# Selectors for Douyin
# Using XPath with fuzzy matching for better robustness against frontend changes
DOUYIN_SELECTORS = {
    # Search related selectors
    "search_input": "//input[contains(@placeholder, '搜索')]",
    "search_button": "//button[contains(@class, 'search') or .//span[contains(text(), '搜索')]]",
    "filter_by_time_1day": "//span[contains(text(), '1天内') or contains(text(), '最近24小时')]",
    "filter_by_time_7days": "//span[contains(text(), '7天内') or contains(text(), '最近一周')]",
    "sort_by_likes": "//span[contains(text(), '点赞最多') or contains(text(), '热门')]",
    "video_items": "//div[contains(@class, 'video-card') or contains(@class, 'feed-item')]",
    # Comment related selectors
    "comment_section": "//div[contains(@class, 'comment') or contains(@class, 'reply')]",
    "comment_items": "//div[contains(@class, 'comment-item') or contains(@class, 'reply-item')]",
    "comment_like_count": ".//span[contains(@class, 'like') or contains(@class, 'digg')]/span[contains(text(), 'w') or contains(text(), 'W') or contains(text(), '万') or contains(text(), '点赞')]",
    "comment_content": ".//p[contains(@class, 'content') or contains(@class, 'text')]",
    "comment_author": ".//span[contains(@class, 'author') or contains(@class, 'user-name')]",
    "comment_with_image": ".//div[contains(@class, 'image') or .//img]",
    # Navigation and interaction
    "load_more_comments": "//div[contains(text(), '查看更多') or contains(text(), '加载更多')]",
    "video_title": "//h1[contains(@class, 'title')]",
    "video_author": "//span[contains(@class, 'author') or contains(@class, 'creator')]",
}

# Selectors for Xiaohongshu
XIAOHONGSHU_SELECTORS = {
    # Search related selectors
    "search_input": "//input[contains(@placeholder, '搜索')]",
    "search_button": "//button[contains(@class, 'search') or .//span[contains(text(), '搜索')]]",
    "filter_by_time_recent": "//span[contains(text(), '最新') or contains(text(), '最近')]",
    "sort_by_likes": "//span[contains(text(), '最热') or contains(text(), '热门')]",
    "note_items": "//div[contains(@class, 'note-item') or contains(@class, 'feed-item')]",
    # Comment related selectors
    "comment_section": "//div[contains(@class, 'comment') or contains(@class, 'reply')]",
    "comment_items": "//div[contains(@class, 'comment-item') or contains(@class, 'reply-item')]",
    "comment_like_count": ".//span[contains(@class, 'like') or contains(@class, 'digg')]/span[contains(text(), '万') or contains(text(), 'w') or contains(text(), 'W') or contains(text(), '点赞')]",
    "comment_content": ".//p[contains(@class, 'content') or contains(@class, 'text')]",
    "comment_author": ".//span[contains(@class, 'author') or contains(@class, 'user-name')]",
    "comment_with_image": ".//div[contains(@class, 'image') or .//img]",
    # Navigation and interaction
    "load_more_comments": "//div[contains(text(), '查看更多') or contains(text(), '加载更多')]",
    "note_title": "//h1[contains(@class, 'title')]",
    "note_author": "//span[contains(@class, 'author') or contains(@class, 'creator')]",
}


# Get the appropriate selectors based on the platform
def get_selectors():
    """
    Returns the appropriate selectors based on the configured platform.

    Returns:
        dict: A dictionary of selectors for the configured platform.
    """
    if PLATFORM.lower() == "xiaohongshu":
        return XIAOHONGSHU_SELECTORS
    return DOUYIN_SELECTORS


# Get the base URL for the configured platform
def get_platform_url():
    """
    Returns the base URL for the configured platform.

    Returns:
        str: The base URL for the configured platform.
    """
    return PLATFORM_URLS.get(PLATFORM.lower(), PLATFORM_URLS["douyin"])
