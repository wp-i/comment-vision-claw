"""
PDF Report generator for Comment-Vision-Claw.
Compact layout with embedded screenshots and per-comment analysis.
"""

import os
import json
import asyncio
import base64
from datetime import datetime
from pathlib import Path

from engine.utils import log_progress
from engine.comment_analyzer import analyze_comment
from engine.config import MEDIACRAWLER_PATH


def image_to_base64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except:
        return ""


def load_mediapcrawler_data():
    """Load videos and comments data from MediaCrawler."""
    media_path = Path(MEDIACRAWLER_PATH) / "data" / "douyin" / "json"

    videos = []
    comments = []

    # Find latest files
    video_files = list(media_path.glob("search_contents_*.json"))
    comment_files = list(media_path.glob("search_comments_*.json"))

    if video_files:
        latest_video_file = max(video_files, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest_video_file, "r", encoding="utf-8") as f:
                videos = json.load(f)
        except:
            pass

    if comment_files:
        latest_comment_file = max(comment_files, key=lambda p: p.stat().st_mtime)
        try:
            with open(latest_comment_file, "r", encoding="utf-8") as f:
                comments = json.load(f)
        except:
            pass

    return videos, comments


def generate_data_summary_section(videos: list, comments: list) -> str:
    """Generate HTML for data summary section with top comments (deduplicated)."""

    # Deduplicate comments by content
    seen_contents = set()
    unique_comments = []
    for c in comments:
        content = c.get("content", "")
        if content and content not in seen_contents:
            seen_contents.add(content)
            unique_comments.append(c)

    # Top 10 comments by like count (deduplicated)
    comments_by_likes = sorted(unique_comments, key=lambda x: x.get("like_count", 0), reverse=True)[:10]
    like_rows = ""
    for i, c in enumerate(comments_by_likes, 1):
        likes = c.get("like_count", 0)
        content = c.get("content", "")[:50]
        author = c.get("nickname", "未知")
        like_rows += f"""
        <tr>
            <td style="padding:6px 8px;border-bottom:1px solid #f0f0f0;text-align:center;color:#999">{i}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #f0f0f0">{content}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #f0f0f0;text-align:center;color:#666">{author}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #f0f0f0;text-align:center;font-weight:bold;color:#fe2c55">{likes:,}</td>
        </tr>"""

    # Top 10 comments by reply count (deduplicated)
    comments_by_replies = sorted(
        unique_comments, key=lambda x: int(x.get("sub_comment_count", "0") or 0), reverse=True
    )[:10]
    reply_rows = ""
    for i, c in enumerate(comments_by_replies, 1):
        replies = int(c.get("sub_comment_count", "0") or 0)
        content = c.get("content", "")[:50]
        author = c.get("nickname", "未知")
        reply_rows += f"""
        <tr>
            <td style="padding:6px 8px;border-bottom:1px solid #f0f0f0;text-align:center;color:#999">{i}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #f0f0f0">{content}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #f0f0f0;text-align:center;color:#666">{author}</td>
            <td style="padding:6px 8px;border-bottom:1px solid #f0f0f0;text-align:center;font-weight:bold;color:#1890ff">{replies:,}</td>
        </tr>"""

    return f"""
    <!-- Data Summary -->
    <div style="margin-bottom:25px;page-break-inside:avoid">
        <div style="font-size:11px;color:#999;text-align:center;margin-bottom:15px">
            共抓取 {len(videos)} 个视频 | {len(unique_comments)} 条评论（去重后）
        </div>
        
        <!-- Top Comments by Likes -->
        <div style="margin-bottom:20px">
            <div style="font-size:13px;font-weight:bold;color:#333;margin-bottom:10px;padding-left:5px;border-left:3px solid #fe2c55">评论点赞数 Top 10</div>
            <table style="width:100%;border-collapse:collapse;font-size:11px">
                <thead>
                    <tr style="background:#fafafa">
                        <th style="padding:8px;text-align:center;width:30px">#</th>
                        <th style="padding:8px;text-align:left">评论内容</th>
                        <th style="padding:8px;text-align:center;width:70px">作者</th>
                        <th style="padding:8px;text-align:center;width:60px">点赞</th>
                    </tr>
                </thead>
                <tbody>{like_rows}</tbody>
            </table>
        </div>
        
        <!-- Top Comments by Replies -->
        <div style="margin-bottom:20px">
            <div style="font-size:13px;font-weight:bold;color:#333;margin-bottom:10px;padding-left:5px;border-left:3px solid #1890ff">评论回复数 Top 10</div>
            <table style="width:100%;border-collapse:collapse;font-size:11px">
                <thead>
                    <tr style="background:#fafafa">
                        <th style="padding:8px;text-align:center;width:30px">#</th>
                        <th style="padding:8px;text-align:left">评论内容</th>
                        <th style="padding:8px;text-align:center;width:70px">作者</th>
                        <th style="padding:8px;text-align:center;width:60px">回复</th>
                    </tr>
                </thead>
                <tbody>{reply_rows}</tbody>
            </table>
        </div>
    </div>
    
    <div style="text-align:center;margin:25px 0;color:#ccc;font-size:11px">─── 热评详情 ───</div>
    """


def generate_pdf_report(
    comments: list,
    keyword: str,
    platform: str = "douyin",
    time_range: str = "1day",
    output_dir: str = "./data",
) -> str:
    """Generate a PDF report with all hot comments and per-comment analysis."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(output_dir, f"report_{ts}.pdf")
    html_path = os.path.join(output_dir, f"_temp_{ts}.html")

    sorted_data = sorted(comments, key=lambda x: x.get("like_count", 0), reverse=True)

    # Load MediaCrawler data for summary
    all_videos, all_comments = load_mediapcrawler_data()

    # Generate data summary section
    data_summary = generate_data_summary_section(all_videos, all_comments)

    # Build cards with video info, screenshot, and per-comment analysis
    cards = ""
    for i, c in enumerate(sorted_data, 1):
        # Get video info for analysis
        video_info = {
            "author": c.get("video_author", ""),
            "title": c.get("video_title", ""),
        }

        # Analyze this specific comment
        analysis = analyze_comment(c, video_info)

        # Screenshot
        screenshot = ""
        sp = c.get("screenshot_path", "")
        if sp and os.path.exists(sp):
            screenshot = f'<img src="{image_to_base64(sp)}" style="width:100%;max-height:350px;object-fit:contain;border-radius:8px;margin:10px 0;box-shadow:0 2px 10px rgba(0,0,0,.15)">'
        else:
            screenshot = f'<div style="background:#f5f5f5;padding:40px;text-align:center;color:#999;border-radius:8px;margin:10px 0;border:1px dashed #ddd">暂无截图（需启动Chrome获取）</div>'

        # Build analysis bullets
        reasons_html = "".join(f"<li>{r}</li>" for r in analysis["reasons"])
        viral_html = "".join(f"<li>{v}</li>" for v in analysis["viral_points"])
        directions_html = "".join(f"<li>{d}</li>" for d in analysis["directions"])

        cards += f"""
        <div style="margin-bottom:30px;page-break-inside:avoid;border:1px solid #e8e8e8;border-radius:12px;overflow:hidden">
            <!-- Header -->
            <div style="background:linear-gradient(135deg,#fe2c55,#ff6f91);color:#fff;padding:15px 20px">
                <div style="display:flex;align-items:center;justify-content:space-between">
                    <div style="display:flex;align-items:center">
                        <div style="background:#fff;color:#fe2c55;width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;margin-right:12px">#{i}</div>
                        <div>
                            <div style="font-size:16px;font-weight:bold">{c.get("video_author", "未知")}</div>
                            <div style="font-size:11px;opacity:0.9">{c.get("like_count", 0):,}赞 | {c.get("reply_count", 0)}回复</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Video Info -->
            <div style="padding:12px 20px;background:#f8f9fa;border-bottom:1px solid #e8e8e8">
                <div style="font-size:12px;color:#666;margin-bottom:6px">📹 视频内容</div>
                <div style="font-size:13px;color:#333;line-height:1.5">{c.get("video_title", "未知")[:120]}</div>
                <a href="{c.get("video_url", "#")}" style="font-size:11px;color:#fe2c55;text-decoration:none">🔗 查看原视频</a>
            </div>
            
            <!-- Screenshot -->
            <div style="padding:15px 20px">
                {screenshot}
            </div>
            
            <!-- Analysis -->
            <div style="padding:0 20px 20px">
                <div style="background:#fff5f5;border-radius:8px;padding:15px;margin-bottom:12px">
                    <div style="font-size:14px;font-weight:bold;color:#fe2c55;margin-bottom:8px">🔥 热门成因</div>
                    <ul style="margin:0;padding-left:20px;font-size:12px;color:#666;line-height:1.8">{reasons_html}</ul>
                </div>
                
                <div style="background:#f0f7ff;border-radius:8px;padding:15px;margin-bottom:12px">
                    <div style="font-size:14px;font-weight:bold;color:#1890ff;margin-bottom:8px">💥 爆点分析</div>
                    <ul style="margin:0;padding-left:20px;font-size:12px;color:#666;line-height:1.8">{viral_html}</ul>
                </div>
                
                <div style="background:#f6ffed;border-radius:8px;padding:15px">
                    <div style="font-size:14px;font-weight:bold;color:#52c41a;margin-bottom:8px">🎯 复刻方向</div>
                    <ul style="margin:0;padding-left:20px;font-size:12px;color:#666;line-height:1.8">{directions_html}</ul>
                </div>
            </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
    @page {{ size: A4; margin: 1cm; }}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: "Microsoft YaHei",sans-serif; font-size:12px; color:#333; }}
    h1 {{ font-size:22px; color:#fe2c55; text-align:center; margin:20px 0 10px; }}
    .meta {{ text-align:center; color:#999; font-size:11px; margin-bottom:20px; }}
    .footer {{ text-align:center; color:#999; font-size:10px; margin-top:30px; padding-top:15px; border-top:1px solid #e8e8e8; }}
</style></head>
<body>
    <h1>抖音热评分析报告</h1>
    <div class="meta">关键词：{keyword} | 平台：{platform} | 共{len(comments)}条热评 | {datetime.now().strftime("%Y-%m-%d")}</div>
    
    {data_summary}
    
    {cards}
    
    <div class="footer">Comment-Vision-Claw 自动生成</div>
</body></html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    try:
        asyncio.run(_to_pdf(html_path, pdf_path))
        log_progress(f"Generated PDF: {pdf_path}")
        os.remove(html_path)
    except Exception as e:
        log_progress(f"PDF failed: {e}", level="ERROR")
        pdf_path = html_path

    return pdf_path


async def _to_pdf(html: str, pdf: str):
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file:///{os.path.abspath(html)}")
        await page.pdf(
            path=pdf,
            format="A4",
            margin={
                "top": "0.5cm",
                "right": "0.5cm",
                "bottom": "0.5cm",
                "left": "0.5cm",
            },
            print_background=True,
        )
        await browser.close()
