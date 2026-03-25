"""
评论截图模块。

通过 _screenshot_worker.py 子进程完成截图，避免事件循环冲突。
实际截图逻辑见 engine/_screenshot_worker.py。
本模块保留辅助函数供其他模块复用。
"""

import re

from engine.config import min_like_count


def extract_like_count(full_text: str) -> int:
    """从评论文本中提取点赞数（支持"万"格式）。"""
    wan_matches = re.findall(r"(\d+\.?\d*)\s*万", full_text)
    if wan_matches:
        return int(float(wan_matches[0]) * 10000)
    numbers = re.findall(r"\b(\d{2,6})\b", full_text)
    best = 0
    for num_str in numbers:
        num = int(num_str)
        if num > best and num < 1_000_000:
            best = num
    return best


def extract_comment_content(full_text: str) -> str:
    """从评论文本中提取评论正文（跳过作者名、回复、展开等行）。"""
    lines = full_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if len(line) > 5 and not line.isdigit() and "回复" not in line and "展开" not in line:
            return line
    return ""
