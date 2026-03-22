#!/usr/bin/env python
"""
Comment-Vision-Claw MCP Server

This module implements a Model Context Protocol (MCP) server that provides
tools for capturing and analyzing high-engagement comments from Douyin.

Usage:
    # As MCP server
    python server.py

    # As CLI tool
    python -m comment_vision_claw "关键词"
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv

load_dotenv()

# Check if running as MCP server
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: MCP not installed. Running in CLI mode only.")
    print("Install with: pip install mcp")


# Import local modules
from engine.config import (
    PLATFORM,
    MIN_LIKE_COUNT,
    MIN_REPLY_COUNT,
    MAX_VIDEOS,
    MAX_COMMENTS,
)
from engine.utils import log_progress, setup_directories
from engine.mediacrawler_scraper import (
    MediaCrawlerDouyinScraper,
    check_mediacrawler_installed,
)
from engine.pdf_report import generate_pdf_report
from engine.comment_analyzer import analyze_comment


# Create MCP server
if MCP_AVAILABLE:
    server = Server("comment-vision-claw")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools."""
        return [
            Tool(
                name="capture_hot_comments",
                description="抓取抖音热评：根据关键词搜索视频，捕获高点赞/高回复的评论",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词，如 'AI视频生成'、'情感内容'",
                        },
                        "time_range": {
                            "type": "string",
                            "enum": ["1day", "7days"],
                            "default": "1day",
                            "description": "时间范围",
                        },
                        "min_likes": {
                            "type": "integer",
                            "default": 5000,
                            "description": "最小点赞数阈值",
                        },
                        "min_replies": {
                            "type": "integer",
                            "default": 500,
                            "description": "最小回复数阈值",
                        },
                        "max_videos": {
                            "type": "integer",
                            "default": 100,
                            "description": "最大抓取视频数",
                        },
                    },
                    "required": ["keyword"],
                },
            ),
            Tool(
                name="generate_report",
                description="生成热评分析报告（PDF格式）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词（与抓取时一致）",
                        }
                    },
                    "required": ["keyword"],
                },
            ),
            Tool(
                name="analyze_single_comment",
                description="使用AI分析单条评论（需要配置OPENAI_API_KEY）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "comment_content": {
                            "type": "string",
                            "description": "评论内容",
                        },
                        "video_title": {"type": "string", "description": "视频标题"},
                        "like_count": {"type": "integer", "description": "点赞数"},
                        "reply_count": {"type": "integer", "description": "回复数"},
                    },
                    "required": ["comment_content"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        """Handle tool calls."""
        if name == "capture_hot_comments":
            return await handle_capture_hot_comments(arguments)
        elif name == "generate_report":
            return await handle_generate_report(arguments)
        elif name == "analyze_single_comment":
            return await handle_analyze_single_comment(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_capture_hot_comments(args: dict) -> List[TextContent]:
    """Handle hot comments capture."""
    keyword = args.get("keyword", "")
    time_range = args.get("time_range", "1day")
    min_likes = args.get("min_likes", 5000)
    min_replies = args.get("min_replies", 500)
    max_videos = args.get("max_videos", 100)

    # Check MediaCrawler installation
    if not check_mediacrawler_installed():
        return [
            TextContent(
                type="text",
                text="错误：MediaCrawler 未安装。\n请运行：git clone https://github.com/NanmiCoder/MediaCrawler.git D:\\MediaCrawler",
            )
        ]

    try:
        # Set environment variables for this run
        os.environ["MIN_LIKE_COUNT"] = str(min_likes)
        os.environ["MIN_REPLY_COUNT"] = str(min_replies)
        os.environ["MAX_VIDEOS"] = str(max_videos)

        scraper = MediaCrawlerDouyinScraper()
        comments = scraper.capture_hot_comments(keyword, time_range)

        if not comments:
            return [
                TextContent(
                    type="text",
                    text=f"未找到符合条件的热评（≥{min_likes}赞 或 ≥{min_replies}回复）",
                )
            ]

        # Save results
        output_path = "./data/results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)

        # Format response
        result_text = f"✅ 成功捕获 {len(comments)} 条热评\n\n"
        for i, c in enumerate(comments[:5], 1):
            result_text += f"{i}. {c['like_count']:,}赞 / {c['reply_count']}回复\n"
            result_text += f"   评论：{c['comment_content'][:50]}...\n"
            result_text += f"   博主：{c['video_author']}\n\n"

        if len(comments) > 5:
            result_text += f"... 还有 {len(comments) - 5} 条热评\n"

        result_text += f"\n数据已保存到：{output_path}"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        return [TextContent(type="text", text=f"抓取失败：{str(e)}")]


async def handle_generate_report(args: dict) -> List[TextContent]:
    """Handle report generation."""
    keyword = args.get("keyword", "")

    try:
        # Load existing results
        results_path = "./data/results.json"
        if not os.path.exists(results_path):
            return [
                TextContent(
                    type="text",
                    text="错误：未找到热评数据。请先运行 capture_hot_comments 抓取数据。",
                )
            ]

        with open(results_path, "r", encoding="utf-8") as f:
            comments = json.load(f)

        if not comments:
            return [TextContent(type="text", text="错误：热评数据为空。")]

        # Generate PDF report
        report_path = generate_pdf_report(
            comments=comments,
            keyword=keyword or "热评分析",
            platform="douyin",
            time_range="1day",
            output_dir="./data",
        )

        return [
            TextContent(
                type="text",
                text=f"✅ PDF报告已生成：{report_path}\n\n报告包含 {len(comments)} 条热评的分析，每条评论包含：\n- 视频信息和博主ID\n- 热评截图\n- 热门成因分析\n- 爆点分析\n- 复刻方向建议",
            )
        ]

    except Exception as e:
        return [TextContent(type="text", text=f"生成报告失败：{str(e)}")]


async def handle_analyze_single_comment(args: dict) -> List[TextContent]:
    """Handle single comment analysis."""
    comment_data = {
        "comment_content": args.get("comment_content", ""),
        "video_title": args.get("video_title", ""),
        "like_count": args.get("like_count", 0),
        "reply_count": args.get("reply_count", 0),
    }

    video_info = {"title": args.get("video_title", "")}

    try:
        analysis = analyze_comment(comment_data, video_info)

        result_text = "📊 评论分析结果\n\n"
        result_text += "【热门成因】\n"
        for r in analysis["reasons"]:
            result_text += f"  • {r}\n"

        result_text += "\n【爆点分析】\n"
        for v in analysis["viral_points"]:
            result_text += f"  • {v}\n"

        result_text += "\n【复刻方向】\n"
        for d in analysis["directions"]:
            result_text += f"  • {d}\n"

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        return [TextContent(type="text", text=f"分析失败：{str(e)}")]


# CLI interface
def cli_main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Comment-Vision-Claw: 抖音热评抓取与分析工具"
    )
    parser.add_argument("keyword", nargs="?", help="搜索关键词")
    parser.add_argument("--time-range", default="1day", choices=["1day", "7days"])
    parser.add_argument("--min-likes", type=int, default=5000)
    parser.add_argument("--min-replies", type=int, default=500)
    parser.add_argument("--max-videos", type=int, default=100)
    parser.add_argument("--server", action="store_true", help="启动MCP服务器模式")

    args = parser.parse_args()

    # Ensure directories exist
    setup_directories(["./data", "./data/screenshots"])

    if args.server:
        # Run as MCP server
        if not MCP_AVAILABLE:
            print("错误：MCP 未安装。请运行：pip install mcp")
            sys.exit(1)

        print("启动 Comment-Vision-Claw MCP 服务器...")
        asyncio.run(run_mcp_server())
    elif args.keyword:
        # Run as CLI
        run_cli(args)
    else:
        parser.print_help()


def run_cli(args):
    """Run in CLI mode."""
    print(f"\n{'=' * 50}")
    print(f"Comment-Vision-Claw")
    print(f"关键词：{args.keyword}")
    print(f"{'=' * 50}\n")

    # Step 1: Capture hot comments
    print("[1/2] 正在抓取热评...")

    os.environ["MIN_LIKE_COUNT"] = str(args.min_likes)
    os.environ["MIN_REPLY_COUNT"] = str(args.min_replies)
    os.environ["MAX_VIDEOS"] = str(args.max_videos)

    scraper = MediaCrawlerDouyinScraper()
    comments = scraper.capture_hot_comments(args.keyword, args.time_range)

    if not comments:
        print("未找到符合条件的热评。")
        return

    print(f"✅ 找到 {len(comments)} 条热评\n")

    # Save results
    with open("./data/results.json", "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)

    # Step 2: Generate report
    print("[2/2] 正在生成报告...")

    report_path = generate_pdf_report(
        comments=comments,
        keyword=args.keyword,
        platform="douyin",
        time_range=args.time_range,
        output_dir="./data",
    )

    print(f"\n{'=' * 50}")
    print(f"✅ 完成！")
    print(f"热评数量：{len(comments)}")
    print(f"报告位置：{report_path}")
    print(f"{'=' * 50}")


async def run_mcp_server():
    """Run MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    cli_main()
