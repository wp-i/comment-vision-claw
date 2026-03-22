#!/usr/bin/env python
"""
Comment-Vision-Claw CLI

Command-line interface for testing the Comment-Vision-Claw tool.
This script allows users to search for and capture high-engagement comments
from social media platforms.

Supports two backends:
- playwright: Original Playwright-based scraper (may be detected by Douyin)
- mediacrawler: MediaCrawler-based scraper (recommended for Douyin)
"""

import os
import sys
import argparse
import json
import subprocess
import platform
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from engine.config import PLATFORM, MAX_SCREENSHOTS
from engine.utils import log_progress, setup_directories

# Load environment variables
load_dotenv()


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Comment-Vision-Claw: Capture high-engagement comments from social media."
    )

    parser.add_argument("keyword", type=str, help="Keyword to search for (e.g., 'AI方向', '情感内容')")

    parser.add_argument(
        "--time-range",
        type=str,
        choices=["1day", "7days"],
        default="1day",
        help="Time range filter (default: 1day)",
    )

    parser.add_argument(
        "--platform",
        type=str,
        choices=["douyin", "xiaohongshu"],
        default=PLATFORM,
        help=f"Platform to search on (default: {PLATFORM})",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="./data/results.json",
        help="Path to save results JSON (default: ./data/results.json)",
    )

    parser.add_argument(
        "--backend",
        type=str,
        choices=["playwright", "mediacrawler"],
        default="mediacrawler",
        help="Backend to use (default: mediacrawler, recommended for Douyin)",
    )

    parser.add_argument(
        "--mediacrawler-path",
        type=str,
        default=None,
        help="Path to MediaCrawler installation (default: D:\\MediaCrawler)",
    )

    return parser.parse_args()


def get_scraper(
    backend: str = "mediacrawler",
    platform_name: str = "douyin",
    mediacrawler_path: str = None,
):
    """
    Get the appropriate scraper for the specified backend.

    Args:
        backend: Backend to use ('playwright' or 'mediacrawler')
        platform_name: Platform name ('douyin' or 'xiaohongshu')
        mediacrawler_path: Path to MediaCrawler installation

    Returns:
        Scraper instance
    """
    if backend == "mediacrawler":
        from engine.mediacrawler_scraper import (
            MediaCrawlerDouyinScraper,
            check_mediacrawler_installed,
            MEDIACRAWLER_PATH,
        )

        # Check if MediaCrawler is installed
        if mediacrawler_path:
            os.environ["MEDIACRAWLER_PATH"] = mediacrawler_path

        if not check_mediacrawler_installed():
            log_progress(
                f"MediaCrawler not found at: {mediacrawler_path or MEDIACRAWLER_PATH}",
                level="ERROR",
            )
            log_progress("Please install MediaCrawler first:", level="ERROR")
            log_progress(
                "  1. git clone https://github.com/NanmiCoder/MediaCrawler.git D:\\MediaCrawler",
                level="ERROR",
            )
            log_progress(
                "  2. cd D:\\MediaCrawler && pip install -r requirements.txt",
                level="ERROR",
            )
            log_progress("  3. playwright install", level="ERROR")
            sys.exit(1)

        return MediaCrawlerDouyinScraper()
    else:
        from engine.scraper import get_scraper as get_playwright_scraper

        return get_playwright_scraper(platform_name)


def detect_time_range(keyword: str) -> str:
    """
    Detect time range from keyword.

    Args:
        keyword: Search keyword

    Returns:
        Time range string: "1month", "1year", etc.
    """
    keyword_lower = keyword.lower()

    # Check for year indicators
    current_year = datetime.now().year
    for year in range(current_year, current_year - 5, -1):
        if str(year) in keyword or f"{year}年" in keyword:
            return "1year"

    # Check for time keywords
    if any(k in keyword for k in ["今年", "本年"]):
        return "1year"
    if any(k in keyword for k in ["本月", "这个月", "近一个月", "最近"]):
        return "1month"
    if any(k in keyword for k in ["本周", "这周", "近一周"]):
        return "1week"
    if any(k in keyword for k in ["今天", "今日", "当天"]):
        return "1day"
    if any(k in keyword for k in ["去年", "上一年"]):
        return "1year"

    # Default: 1 month
    return "1month"


def main():
    """Main entry point for the CLI."""
    # Parse command-line arguments
    args = parse_arguments()

    # Auto-detect time range from keyword
    detected_time_range = detect_time_range(args.keyword)
    if detected_time_range != args.time_range:
        log_progress(f"Auto-detected time range: {detected_time_range} (from keyword: '{args.keyword}')")
        args.time_range = detected_time_range

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    setup_directories([output_dir, os.path.join(output_dir, "screenshots")])

    # Clear old data on startup (preserve PDF files and MediaCrawler data)
    log_progress("Clearing old data...")

    # Clear results.json
    if os.path.exists(args.output):
        os.remove(args.output)

    # Clear screenshots
    screenshots_dir = os.path.join(output_dir, "screenshots")
    if os.path.exists(screenshots_dir):
        for f in os.listdir(screenshots_dir):
            if f.endswith(".png"):
                os.remove(os.path.join(screenshots_dir, f))

    # Clear old HTML/temp files but keep PDFs
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            filepath = os.path.join(output_dir, f)
            if os.path.isfile(filepath):
                # Keep PDF files, delete others
                if not f.endswith(".pdf"):
                    os.remove(filepath)

    # Note: Do NOT clear MediaCrawler data - it contains login state
    log_progress("Old data cleared")

    # Log start of execution
    log_progress(f"Starting Comment-Vision-Claw with keyword: '{args.keyword}'")
    log_progress(f"Platform: {args.platform}, Time range: {args.time_range}, Backend: {args.backend}")

    # Get the appropriate scraper
    scraper = get_scraper(args.backend, args.platform, args.mediacrawler_path)

    try:
        # Use context manager to ensure proper cleanup
        with scraper:
            # Capture hot comments (includes screenshot capture)
            print("\n[Step 1/2] Capturing hot comments and screenshots...")
            comments = scraper.capture_hot_comments(args.keyword, args.time_range)

            if not comments:
                log_progress("No comments were captured.", level="WARNING")
                return 1

            # Save results to JSON
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(comments, f, ensure_ascii=False, indent=2)

            # Print summary
            print("\n===== CAPTURED COMMENTS =====")
            for i, comment in enumerate(comments, 1):
                has_ss = "[OK]" if comment.get("screenshot_path") else "[NO]"
                content_preview = comment["comment_content"][:40].encode("utf-8", errors="replace").decode("utf-8")
                print(f"{i}. {has_ss} {comment['like_count']:,}赞/{comment['reply_count']}回复 - {content_preview}...")

            # Generate PDF report
            print("\n[Step 2/2] Generating PDF report...")
            from engine.pdf_report import generate_pdf_report

            report_path = generate_pdf_report(
                comments=comments,
                keyword=args.keyword,
                platform=args.platform,
                time_range=args.time_range,
                output_dir=output_dir,
            )

            # Generate PDF report
            from engine.pdf_report import generate_pdf_report

            report_path = generate_pdf_report(
                comments=comments,
                keyword=args.keyword,
                platform=args.platform,
                time_range=args.time_range,
                output_dir=output_dir,
            )
            print(f"\n[REPORT] Generated: {report_path}")

    except Exception as e:
        log_progress(f"Error: {str(e)}", level="ERROR")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    # Run the main function
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        log_progress(f"Unexpected error: {str(e)}", level="ERROR")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def check_playwright_installation():
    """Check if Playwright is properly installed."""
    try:
        # Try to run a simple Playwright command
        result = subprocess.run(["playwright", "--version"], capture_output=True, text=True, check=False)

        if result.returncode != 0:
            log_progress(
                "Playwright CLI not found. Please install it with: playwright install",
                level="ERROR",
            )
            return False

        return True
    except FileNotFoundError:
        log_progress(
            "Playwright CLI not found. Please install it with: playwright install",
            level="ERROR",
        )
        return False


def main():
    """Main entry point for the CLI."""
    # Parse command-line arguments
    args = parse_arguments()

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    setup_directories([output_dir])

    # Log start of execution
    log_progress(f"Starting Comment-Vision-Claw with keyword: '{args.keyword}'")
    log_progress(f"Platform: {args.platform}, Time range: {args.time_range}")

    # Check Playwright installation
    if not check_playwright_installation():
        log_progress("Please install Playwright browsers with: playwright install", level="ERROR")
        return 1

    # Get the appropriate scraper
    scraper = get_scraper(args.platform)

    try:
        # Use context manager to ensure proper cleanup
        with scraper:
            # Capture hot comments
            comments = scraper.capture_hot_comments(args.keyword, args.time_range)

            if not comments:
                log_progress("No comments were captured.", level="WARNING")
                return

            # Save results to JSON
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(comments, f, ensure_ascii=False, indent=2)

            log_progress(f"Captured {len(comments)} comments. Results saved to {args.output}")

            # Print summary of captured comments
            print("\n===== CAPTURED COMMENTS SUMMARY =====")
            for i, comment in enumerate(comments, 1):
                print(f"\n--- Comment {i} ---")
                print(f"Platform: {comment['platform']}")
                print(f"Video: '{comment['video_title']}' by {comment['video_author']}")
                print(f"Comment by: {comment['comment_author']}")
                print(f"Content: {comment['comment_content']}")
                print(f"Likes: {comment['like_count']}")
                print(f"Screenshot: {comment['screenshot_path']}")
                if "note" in comment:
                    print(f"Note: {comment['note']}")

            # Generate a simple markdown report
            report_path = os.path.join(output_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# Comment-Vision-Claw Report\n\n")
                f.write(f"**Search Keyword:** {args.keyword}\n")
                f.write(f"**Platform:** {args.platform}\n")
                f.write(f"**Time Range:** {args.time_range}\n")
                f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                for i, comment in enumerate(comments, 1):
                    f.write(f"## Comment {i}\n\n")
                    f.write(f"**[捕获成功]：** {comment['platform']} - {comment['video_title']}\n\n")
                    f.write(f"**[神评截图]：** {comment['screenshot_path']} (显示点赞 {comment['like_count']})\n\n")
                    f.write(f"**[评论内容]：** {comment['comment_content']}\n\n")
                    f.write(f"**[评论作者]：** {comment['comment_author']}\n\n")
                    f.write(f"**[视频作者]：** {comment['video_author']}\n\n")
                    f.write(f"**[视频链接]：** {comment['video_url']}\n\n")
                    if "note" in comment:
                        f.write(f"**[备注]：** {comment['note']}\n\n")
                    f.write("---\n\n")

            log_progress(f"Generated report: {report_path}")

    except Exception as e:
        log_progress(f"Error: {str(e)}", level="ERROR")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    # Run the main function
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        log_progress(f"Unexpected error: {str(e)}", level="ERROR")
        import traceback

        traceback.print_exc()
        sys.exit(1)
