"""
Utility functions for the Comment-Vision-Claw engine.

This module contains helper functions for common tasks such as:
- Formatting and validating data
- Handling file operations
- Processing text and images
- Implementing human-like behavior
"""

import os
import time
import random
import logging
import re
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("comment_vision_claw.log")],
)

logger = logging.getLogger("comment-vision-claw")


def setup_directories(dirs):
    """
    Ensure all required directories exist.

    Args:
        dirs (list): List of directory paths to create if they don't exist.
    """
    for dir_path in dirs:
        path_obj = Path(dir_path)
        existed = path_obj.exists()
        path_obj.mkdir(parents=True, exist_ok=True)
        if not existed:
            logger.info(f"Ensured directory exists: {dir_path}")


def human_delay(min_seconds=1, max_seconds=3):
    """
    Introduce a random delay to simulate human behavior.

    Args:
        min_seconds (float): Minimum delay in seconds.
        max_seconds (float): Maximum delay in seconds.
    """
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay


def extract_number_from_text(text):
    """
    Extract a number from text, handling formats like '1.2w', '1,200', etc.

    Args:
        text (str): Text containing a number.

    Returns:
        int: Extracted number, or 0 if no number found.
    """
    if not text:
        return 0

    # Remove commas and spaces
    text = text.replace(",", "").strip()

    # Handle 'w' or 'W' suffix (10,000 in Chinese social media)
    if "w" in text.lower() or "W" in text or "万" in text:
        # Extract the number before 'w'/'W'/'万'
        match = re.search(r"(\d+\.?\d*)[wW万]", text)
        if match:
            number = float(match.group(1)) * 10000
            return int(number)

    # Try to extract any number
    match = re.search(r"(\d+\.?\d*)", text)
    if match:
        return int(float(match.group(1)))

    return 0


def generate_filename(platform, author, like_count):
    """
    Generate a filename for a screenshot based on metadata.

    Args:
        platform (str): Platform name (e.g., 'douyin', 'xiaohongshu').
        author (str): Author/username of the comment.
        like_count (int): Number of likes.

    Returns:
        str: Generated filename.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Remove invalid filename characters
    author = re.sub(r'[\\/*?:"<>|]', "", author)
    # Limit author length
    author = author[:20]

    return f"{platform}_{author}_{like_count}_{timestamp}.png"


def log_progress(message, level=logging.INFO):
    """
    Log a progress message.

    Args:
        message (str): Message to log.
        level (int or str): Logging level as integer or string (e.g., "INFO", "ERROR").
    """
    # Convert string level to integer if needed
    if isinstance(level, str):
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        level = level_map.get(level.upper(), logging.INFO)

    logger.log(level, message)
    # Also print to console for immediate feedback
    print(message)


def is_high_value_comment(like_count, min_threshold=10000):
    """
    Determine if a comment is high-value based on like count.

    Args:
        like_count (int): Number of likes.
        min_threshold (int): Minimum threshold to be considered high-value.

    Returns:
        bool: True if the comment is high-value, False otherwise.
    """
    return like_count >= min_threshold
