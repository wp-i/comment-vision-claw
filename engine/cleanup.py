"""
统一清理模块 - 管理启动时的数据清理（保留登录状态）
"""

import os
from pathlib import Path


def clear_app_data():
    """清理应用数据（保留 MediaCrawler 登录信息）"""
    project_dir = Path(__file__).parent.parent

    # 清除锁文件
    lock_file = project_dir / "data" / "capture.lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
        except Exception:
            pass

    # 清除上次结果
    for name in ("results.json", "capture_state.json", "stop_crawler.signal",
                 "screenshot_input.json", "screenshot_output.json"):
        f = project_dir / "data" / name
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass

    # 清除截图
    screenshots_dir = project_dir / "data" / "screenshots"
    if screenshots_dir.exists():
        for f in screenshots_dir.glob("*.png"):
            try:
                f.unlink()
            except Exception:
                pass

    # 清除 MediaCrawler 抓取数据（JSON/图片/视频），但不清除 browser_data（登录状态）
    try:
        from engine.config import MEDIACRAWLER_PATH
        mc_data_base = Path(MEDIACRAWLER_PATH) / "data" / "douyin"
        if mc_data_base.exists():
            for pattern in ["json/*.json", "picture/*.jpg", "video/*.mp4"]:
                for f in mc_data_base.glob(pattern):
                    try:
                        f.unlink()
                    except Exception:
                        pass
    except Exception:
        pass
