#!/usr/bin/env python
"""
Comment-Vision-Claw CLI

Command-line interface for the Comment-Vision-Claw tool.
Searches for and captures high-engagement comments from Douyin,
then generates a PDF analysis report.

Usage:
    python main.py "关键词"
    python main.py "关键词" --time-range 7days
    python main.py "关键词" --min-likes 1000 --min-replies 100
"""

import os
import sys
import argparse
import json
from datetime import datetime

from dotenv import load_dotenv

from engine.config import PLATFORM, MAX_SCREENSHOTS
from engine.utils import log_progress, setup_directories

load_dotenv()


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Comment-Vision-Claw: Capture high-engagement comments from Douyin.")

    parser.add_argument("keyword", type=str, help="搜索关键词，例如 'AI方向'、'情感内容'")

    parser.add_argument(
        "--time-range",
        type=str,
        choices=["1day", "7days", "1month"],
        default="1month",
        help="时间范围 (default: 1month)",
    )

    parser.add_argument(
        "--platform",
        type=str,
        choices=["douyin", "xiaohongshu"],
        default=PLATFORM,
        help=f"目标平台 (default: {PLATFORM})",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="./data/results.json",
        help="结果 JSON 保存路径 (default: ./data/results.json)",
    )

    parser.add_argument(
        "--mediacrawler-path",
        type=str,
        default=None,
        help="MediaCrawler 安装路径（默认自动检测）",
    )

    return parser.parse_args()


def detect_time_range(keyword: str) -> str:
    """从关键词中自动推断时间范围。"""
    time_mapping = {
        "今日": "1day",
        "今天": "1day",
        "当日": "1day",
        "当天": "1day",
        "这周": "7days",
        "本周": "7days",
        "近一周": "7days",
        "最近一周": "7days",
        "一周": "7days",
        "本月": "1month",
        "这个月": "1month",
        "近一个月": "1month",
        "最近": "1month",
        "近来": "1month",
    }
    for key, value in time_mapping.items():
        if key in keyword:
            return value

    current_year = datetime.now().year
    for year in range(current_year, current_year - 5, -1):
        if str(year) in keyword or f"{year}年" in keyword:
            return "1month"

    return "1month"


def main():
    """CLI 主入口。"""
    args = parse_arguments()

    # 从关键词自动推断时间范围
    detected_time_range = detect_time_range(args.keyword)
    if detected_time_range != args.time_range:
        log_progress(f"从关键词自动推断时间范围: {detected_time_range}")
        args.time_range = detected_time_range

    # 确保输出目录存在
    output_dir = os.path.dirname(args.output)
    setup_directories([output_dir, os.path.join(output_dir, "screenshots")])

    # 清理旧数据（保留 PDF 和 MediaCrawler 登录状态）
    log_progress("清理旧数据...")
    if os.path.exists(args.output):
        os.remove(args.output)

    screenshots_dir = os.path.join(output_dir, "screenshots")
    if os.path.exists(screenshots_dir):
        for f in os.listdir(screenshots_dir):
            if f.endswith(".png"):
                os.remove(os.path.join(screenshots_dir, f))

    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            filepath = os.path.join(output_dir, f)
            if os.path.isfile(filepath) and not f.endswith(".pdf"):
                os.remove(filepath)

    log_progress("旧数据已清理")

    # 检查 MediaCrawler
    if args.mediacrawler_path:
        os.environ["MEDIACRAWLER_PATH"] = args.mediacrawler_path

    from engine.mediacrawler_scraper import (
        MediaCrawlerDouyinScraper,
        check_mediacrawler_installed,
        MEDIACRAWLER_PATH,
    )

    if not check_mediacrawler_installed():
        log_progress(f"MediaCrawler 未找到: {MEDIACRAWLER_PATH}", level="ERROR")
        log_progress("请先安装 MediaCrawler:", level="ERROR")
        log_progress("  git clone https://github.com/NanmiCoder/MediaCrawler.git D:\\MediaCrawler", level="ERROR")
        log_progress("  cd D:\\MediaCrawler && pip install -r requirements.txt", level="ERROR")
        sys.exit(1)

    log_progress(f"开始抓取，关键词: '{args.keyword}'")
    log_progress(f"平台: {args.platform}，时间范围: {args.time_range}")

    scraper = MediaCrawlerDouyinScraper()

    try:
        with scraper:
            # 第一步：抓取热评（含截图）
            print("\n[1/2] 正在抓取热评和截图...")
            comments = scraper.capture_hot_comments(args.keyword, args.time_range)

            if not comments:
                log_progress("未找到符合条件的热评。", level="WARNING")
                return 1

            # 保存结果
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(comments, f, ensure_ascii=False, indent=2)

            # 打印摘要
            print("\n===== 已抓取热评 =====")
            for i, comment in enumerate(comments, 1):
                has_ss = "[截图OK]" if comment.get("screenshot_path") else "[无截图]"
                content_preview = comment["comment_content"][:40]
                print(f"{i}. {has_ss} {comment['like_count']:,}赞/{comment['reply_count']}回复 - {content_preview}...")

            # 第二步：生成 PDF 报告
            print("\n[2/2] 正在生成 PDF 报告...")
            from engine.pdf_report import generate_pdf_report

            report_path = generate_pdf_report(
                comments=comments,
                keyword=args.keyword,
                platform=args.platform,
                time_range=args.time_range,
                output_dir=output_dir,
            )
            print(f"\n[报告] 已生成: {report_path}")

    except Exception as e:
        log_progress(f"错误: {str(e)}", level="ERROR")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    from engine.cleanup import clear_app_data

    clear_app_data()

    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        log_progress(f"未预期的错误: {str(e)}", level="ERROR")
        import traceback

        traceback.print_exc()
        sys.exit(1)
