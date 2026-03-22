"""
Comment screenshot capture module.

Captures screenshots of comment sections for each video.
Uses page-extracted comment data for accurate matching.
"""

import asyncio
import os
import random
import re
from datetime import datetime

from playwright.async_api import async_playwright

from engine.config import SCREENSHOTS_DIR, MIN_LIKE_COUNT, CDP_URL
from engine.utils import log_progress, setup_directories

# Minimum thresholds (must match config)
MIN_REPLY_COUNT = 400


async def extract_comments_from_page(page) -> list:
    """
    Extract comment data from the current page.
    Returns a list of dicts with: element, content, likes, author, bbox
    """
    comments = []
    comment_items = await page.query_selector_all("div[data-e2e='comment-item']")

    for elem in comment_items:
        try:
            if not await elem.is_visible():
                continue

            bbox = await elem.bounding_box()
            if not bbox or bbox["height"] < 40:
                continue

            full_text = await elem.inner_text()

            # Extract like count (handle "万" format)
            likes = 0
            wan_matches = re.findall(r"(\d+\.?\d*)\s*万", full_text)
            if wan_matches:
                likes = int(float(wan_matches[0]) * 10000)
            else:
                numbers = re.findall(r"\b(\d{2,6})\b", full_text)
                for num_str in numbers:
                    num = int(num_str)
                    if num > likes and num < 1000000:
                        likes = num

            # Extract comment content (first line after author name)
            lines = full_text.strip().split("\n")
            content = ""
            for line in lines:
                line = line.strip()
                if len(line) > 5 and not line.isdigit() and "回复" not in line and "展开" not in line:
                    content = line
                    break

            # Extract author name (usually first line)
            author = lines[0].strip() if lines else ""

            comments.append(
                {
                    "element": elem,
                    "content": content,
                    "likes": likes,
                    "author": author,
                    "bbox": bbox,
                    "full_text": full_text[:100],
                }
            )
        except Exception:
            continue

    return comments


def match_comment(page_comments: list, target_content: str, target_likes: int, exclude_contents: set = None):
    """
    Match a target comment from page-extracted comments.
    Returns the matched comment dict or None.

    Args:
        page_comments: List of comments extracted from page
        target_content: Target comment content to match
        target_likes: Target like count
        exclude_contents: Set of content prefixes to exclude (already captured)
    """
    if not page_comments:
        return None

    if exclude_contents is None:
        exclude_contents = set()

    # Extract content prefix for matching
    content_prefix = target_content[:15] if len(target_content) > 15 else target_content

    # First try: exact content match (only if target meets criteria)
    if target_likes >= MIN_LIKE_COUNT:
        for comment in page_comments:
            if content_prefix and content_prefix in comment["content"]:
                # Check if this content is excluded
                if exclude_contents:
                    comment_prefix = comment["content"][:20] if comment["content"] else ""
                    if comment_prefix in exclude_contents:
                        continue
                print(f"[screenshot] Matched by content: '{comment['content'][:30]}...'")
                return comment

    # Second try: like count match with tolerance (only if meets criteria)
    tolerance = max(target_likes * 0.15, 500)
    best_match = None
    best_diff = float("inf")

    for comment in page_comments:
        # Check if this content is excluded
        if exclude_contents:
            comment_prefix = comment["content"][:20] if comment["content"] else ""
            if comment_prefix in exclude_contents:
                continue

        # Only match comments that meet our criteria
        if comment["likes"] < MIN_LIKE_COUNT:
            continue

        if comment["likes"] > 0:
            diff = abs(comment["likes"] - target_likes)
            if diff <= tolerance and diff < best_diff:
                best_diff = diff
                best_match = comment

    if best_match:
        print(f"[screenshot] Matched by likes: {best_match['likes']} (target: {target_likes}, diff: {best_diff})")
        return best_match

    return None


async def capture_single_comment(page, comment_data: dict, filepath: str) -> bool:
    """
    Capture screenshot of a single comment element.
    Returns True if successful.
    """
    try:
        elem = comment_data["element"]

        # Scroll into view
        await elem.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)

        # Get updated bbox
        bbox = await elem.bounding_box()
        if not bbox:
            return False

        # Calculate clip area with padding
        padding = 10
        clip_x = max(0, bbox["x"] - padding)
        clip_y = max(0, bbox["y"] - padding)
        clip_width = min(1280 - clip_x, bbox["width"] + 2 * padding)
        clip_height = min(900 - clip_y, bbox["height"] + 2 * padding)

        if clip_width > 0 and clip_height > 0 and clip_y + clip_height <= 900:
            await page.screenshot(
                path=filepath,
                clip={"x": clip_x, "y": clip_y, "width": clip_width, "height": clip_height},
            )
            return True

    except Exception as e:
        print(f"[screenshot] Capture failed: {str(e)[:30]}")

    return False


async def capture_comment_screenshots(hot_comments: list, max_screenshots: int = 5) -> list:
    """
    Capture screenshots of comment sections.

    Strategy:
    1. Open video page
    2. Scroll down to load comments
    3. Click "最热" to sort by likes
    4. Extract comment data from page
    5. Match target comment
    6. Screenshot matched comment

    Args:
        hot_comments: List with video_url, like_count, comment_content
        max_screenshots: Max screenshots

    Returns:
        Updated list with screenshot_path
    """
    setup_directories([SCREENSHOTS_DIR])

    comments_to_capture = hot_comments[:max_screenshots]
    total = len(comments_to_capture)

    if total == 0:
        return hot_comments

    print(f"\n[screenshot] starting {total} screenshots...")

    # Track actually captured comment content prefixes per video
    video_captured_contents = {}  # video_url -> set of content prefixes

    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()

            for i, comment in enumerate(comments_to_capture, 1):
                video_url = comment.get("video_url", "")
                like_count = comment.get("like_count", 0)
                comment_content = comment.get("comment_content", "")

                if not video_url:
                    continue

                print(f"[screenshot] ({i}/{total}) {like_count} likes")

                try:
                    page = await context.new_page()
                    await page.set_viewport_size({"width": 1280, "height": 900})

                    # Open video page
                    await page.goto(video_url, wait_until="domcontentloaded", timeout=25000)
                    await asyncio.sleep(3)

                    # Scroll down to load comments
                    for scroll in range(8):
                        await page.evaluate("window.scrollBy(0, 300)")
                        await asyncio.sleep(0.3)
                    await asyncio.sleep(2)

                    # Click "最热" button
                    hot_btn_clicked = False
                    for sel in ["span:text-is('最热')", "span:has-text('最热')", "div:text-is('最热')"]:
                        try:
                            btn = await page.query_selector(sel)
                            if btn and await btn.is_visible():
                                await btn.click()
                                hot_btn_clicked = True
                                print(f"[screenshot] Clicked '最热'")
                                break
                        except:
                            continue

                    # Wait for comments to reload
                    await asyncio.sleep(3)

                    # Scroll a bit more
                    await page.evaluate("window.scrollBy(0, 100)")
                    await asyncio.sleep(1)

                    # Generate filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"comment_{like_count}likes_{timestamp}_{i}.png"
                    filepath = os.path.join(SCREENSHOTS_DIR, filename)

                    # Extract comments from page
                    page_comments = await extract_comments_from_page(page)
                    print(f"[screenshot] Extracted {len(page_comments)} comments from page")

                    # Get exclude set for this video (actually captured content prefixes)
                    exclude_contents = video_captured_contents.get(video_url, set())

                    # Try to match target comment
                    matched = match_comment(page_comments, comment_content, like_count, exclude_contents)

                    captured_content_prefix = None
                    if matched:
                        success = await capture_single_comment(page, matched, filepath)
                        if success:
                            comment["screenshot_path"] = filepath
                            captured_content_prefix = matched["content"][:20] if matched["content"] else ""
                            print(f"[screenshot] ({i}/{total}) saved (matched)")
                        else:
                            print(f"[screenshot] Match found but capture failed")
                            matched = None

                    # Fallback: use top visible comment not already captured
                    # Only use comments that meet our criteria (high likes OR high replies)
                    if not matched and page_comments:
                        # Filter to only comments that meet our criteria
                        valid_comments = []
                        for pc in page_comments:
                            content_prefix = pc["content"][:20] if pc["content"] else ""
                            if content_prefix in exclude_contents:
                                continue
                            # Check if meets criteria (likes >= 5000 OR replies >= 400)
                            # Note: we don't have reply count from page, so only check likes
                            if pc["likes"] >= MIN_LIKE_COUNT:
                                valid_comments.append(pc)

                        # Sort by likes
                        valid_comments.sort(key=lambda x: x["likes"], reverse=True)

                        if valid_comments:
                            top_comment = valid_comments[0]
                            success = await capture_single_comment(page, top_comment, filepath)
                            if success:
                                comment["screenshot_path"] = filepath
                                captured_content_prefix = top_comment["content"][:20] if top_comment["content"] else ""
                                print(f"[screenshot] ({i}/{total}) saved (fallback: {top_comment['likes']} likes)")
                        else:
                            print(f"[screenshot] ({i}/{total}) SKIPPED - no valid comment found on page")

                    # Record captured content for this video
                    if captured_content_prefix:
                        if video_url not in video_captured_contents:
                            video_captured_contents[video_url] = set()
                        video_captured_contents[video_url].add(captured_content_prefix)

                    if not comment.get("screenshot_path"):
                        print(f"[screenshot] ({i}/{total}) SKIPPED - no matching comment found")

                    await page.close()
                    await asyncio.sleep(random.uniform(1, 2))

                except Exception as e:
                    print(f"[screenshot] ({i}/{total}) failed: {str(e)[:50]}")
                    continue

            print(f"[screenshot] done!\n")

    except Exception as e:
        print(f"[screenshot] connection failed: {str(e)}")

    return hot_comments

    print(f"\n[screenshot] starting {total} screenshots...")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()

            for i, comment in enumerate(comments_to_capture, 1):
                video_url = comment.get("video_url", "")
                like_count = comment.get("like_count", 0)
                comment_content = comment.get("comment_content", "")

                if not video_url:
                    continue

                print(f"[screenshot] ({i}/{total}) {like_count} likes")

                try:
                    page = await context.new_page()
                    await page.set_viewport_size({"width": 1280, "height": 900})

                    # Open video page
                    await page.goto(video_url, wait_until="domcontentloaded", timeout=25000)
                    await asyncio.sleep(3)

                    # Scroll down to load comments
                    for scroll in range(8):
                        await page.evaluate("window.scrollBy(0, 300)")
                        await asyncio.sleep(0.3)
                    await asyncio.sleep(2)

                    # Click "最热" button
                    hot_btn_clicked = False
                    for sel in ["span:text-is('最热')", "span:has-text('最热')", "div:text-is('最热')"]:
                        try:
                            btn = await page.query_selector(sel)
                            if btn and await btn.is_visible():
                                await btn.click()
                                hot_btn_clicked = True
                                print(f"[screenshot] Clicked '最热'")
                                break
                        except:
                            continue

                    # Wait for comments to reload
                    await asyncio.sleep(3)

                    # Scroll a bit more
                    await page.evaluate("window.scrollBy(0, 100)")
                    await asyncio.sleep(1)

                    # Generate filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"comment_{like_count}likes_{timestamp}_{i}.png"
                    filepath = os.path.join(SCREENSHOTS_DIR, filename)

                    # Extract comments from page
                    page_comments = await extract_comments_from_page(page)
                    print(f"[screenshot] Extracted {len(page_comments)} comments from page")

                    # Build exclude set for already captured comments from same video
                    exclude_contents = set()
                    for prev_comment in comments_to_capture[: i - 1]:
                        if prev_comment.get("video_url") == video_url and prev_comment.get("screenshot_path"):
                            prev_content = prev_comment.get("comment_content", "")
                            if prev_content:
                                exclude_contents.add(prev_content[:20])

                    # Try to match target comment
                    matched = match_comment(page_comments, comment_content, like_count, exclude_contents)

                    if matched:
                        success = await capture_single_comment(page, matched, filepath)
                        if success:
                            comment["screenshot_path"] = filepath
                            print(f"[screenshot] ({i}/{total}) saved (matched)")
                        else:
                            print(f"[screenshot] Match found but capture failed")
                            matched = None

                    # Fallback: use top visible comment
                    if not matched and page_comments:
                        # Sort by likes and use the highest
                        page_comments.sort(key=lambda x: x["likes"], reverse=True)

                        # Find a comment that hasn't been captured yet for this video
                        already_captured_contents = set()
                        for prev_comment in comments_to_capture[: i - 1]:
                            if prev_comment.get("video_url") == video_url and prev_comment.get("screenshot_path"):
                                # Get the content prefix of already captured comments
                                prev_content = prev_comment.get("comment_content", "")
                                if prev_content:
                                    already_captured_contents.add(prev_content[:20])

                        # Find first comment not already captured
                        top_comment = None
                        for pc in page_comments:
                            content_prefix = pc["content"][:20] if pc["content"] else ""
                            if content_prefix not in already_captured_contents:
                                top_comment = pc
                                break

                        # If all comments already captured, use the highest anyway
                        if not top_comment and page_comments:
                            top_comment = page_comments[0]

                        if top_comment:
                            success = await capture_single_comment(page, top_comment, filepath)
                            if success:
                                comment["screenshot_path"] = filepath
                                print(f"[screenshot] ({i}/{total}) saved (fallback: {top_comment['likes']} likes)")

                    # Last resort: area screenshot
                    if not comment.get("screenshot_path"):
                        await page.screenshot(path=filepath, clip={"x": 0, "y": 300, "width": 900, "height": 200})
                        comment["screenshot_path"] = filepath
                        print(f"[screenshot] ({i}/{total}) saved (area fallback)")

                    await page.close()
                    await asyncio.sleep(random.uniform(1, 2))

                except Exception as e:
                    print(f"[screenshot] ({i}/{total}) failed: {str(e)[:50]}")
                    continue

            print(f"[screenshot] done!\n")

    except Exception as e:
        print(f"[screenshot] connection failed: {str(e)}")

    return hot_comments


def capture_screenshots_sync(hot_comments: list, max_screenshots: int = 5) -> list:
    """Synchronous wrapper."""
    return asyncio.run(capture_comment_screenshots(hot_comments, max_screenshots))
