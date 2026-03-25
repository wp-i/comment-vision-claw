"""
Comment-Vision-Claw Web 界面 (Streamlit)

启动方式：
    streamlit run app.py
    或双击 start.bat
"""

import os
import json
import time
import threading
import streamlit as st
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from engine.config import min_like_count, min_reply_count, MEDIACRAWLER_PATH
from engine.utils import setup_directories

load_dotenv()

# 确保数据目录存在（每次加载时执行，无副作用）
setup_directories(["./data", "./data/screenshots"])


def update_status(status: str, is_error: bool = False):
    """将状态写入文件供前端轮询。"""
    state_file = "./data/capture_state.json"
    state = {
        "status": status,
        "is_error": is_error,
        "timestamp": datetime.now().isoformat(),
    }
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except Exception:
        pass


def read_status() -> dict:
    """从文件读取当前状态。"""
    state_file = "./data/capture_state.json"
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"status": "", "is_error": False}


# ──────────────────────────────────────────────
# 后台抓取任务（在独立线程中运行）
# ──────────────────────────────────────────────


def run_capture(keyword: str, time_range: str):
    """在后台线程中执行完整的抓取 → 截图 → 报告流程。"""
    try:
        from engine.mediacrawler_scraper import MediaCrawlerDouyinScraper, check_mediacrawler_installed

        update_status("正在启动抓取，请稍候...")

        if not check_mediacrawler_installed():
            update_status("错误: MediaCrawler 未安装，请先按文档安装", is_error=True)
            return

        scraper = MediaCrawlerDouyinScraper()
        update_status("正在抓取，浏览器将弹出（首次使用需扫码登录）...")

        with scraper:
            comments = scraper.capture_hot_comments(keyword, time_range)

        if not comments:
            update_status("未找到符合条件的热评（可尝试降低阈值）", is_error=True)
            return

        # 保存结果
        results_path = "./data/results.json"
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)

        # 生成 PDF 报告
        update_status("正在生成 PDF 报告...")
        try:
            from engine.pdf_report import generate_pdf_report

            generate_pdf_report(
                comments=comments,
                keyword=keyword,
                platform="douyin",
                time_range=time_range,
                output_dir="./data",
            )
        except Exception as e:
            print(f"PDF 生成失败: {e}")

        update_status("完成！")

    except Exception as e:
        update_status(f"抓取失败: {str(e)}", is_error=True)
        import traceback

        traceback.print_exc()


# ──────────────────────────────────────────────
# Streamlit 主界面
# ──────────────────────────────────────────────


def main():
    st.set_page_config(
        page_title="Comment Vision Claw",
        page_icon="🕷️",
        layout="centered",
    )

    st.title("🕷️ Comment Vision Claw")
    st.markdown("抖音热评抓取与分析工具")

    # ── 输入区 ──
    col1, col2 = st.columns([3, 1])
    with col1:
        keyword = st.text_input("输入关键词", placeholder="例如: 中医", key="keyword_input")
    with col2:
        time_range_label = st.selectbox("时间范围", ["近一个月", "近一周", "今日"], key="time_range_select")

    time_range_map = {"近一个月": "1month", "近一周": "7days", "今日": "1day"}
    time_range = time_range_map[time_range_label]

    start_button = st.button("开始抓取", type="primary", key="start_capture")

    # ── Session state 初始化 ──
    if "capture_running" not in st.session_state:
        st.session_state.capture_running = False
    if "capture_done" not in st.session_state:
        st.session_state.capture_done = False

    # ── 状态显示 ──
    state = read_status()
    if state.get("status"):
        if state.get("is_error"):
            st.error(state["status"])
        else:
            st.info(state["status"])

    # ── 启动抓取 ──
    if start_button and keyword:
        lock_file = "./data/capture.lock"
        if os.path.exists(lock_file):
            st.error("已有抓取任务正在进行中，请等待完成")
        elif st.session_state.capture_running:
            st.warning("抓取任务正在进行中，请稍候...")
        else:
            # 清理上次数据
            from engine.cleanup import clear_app_data

            clear_app_data()

            st.session_state.capture_running = True
            st.session_state.capture_done = False

            thread = threading.Thread(
                target=run_capture,
                args=(keyword, time_range),
                daemon=True,
            )
            thread.start()
            st.rerun()

    # ── 进度轮询（非阻塞：每次 rerun 检查一次状态）──
    if st.session_state.capture_running:
        state = read_status()
        current_status = state.get("status", "")

        if state.get("is_error"):
            st.session_state.capture_running = False
            st.error(current_status or "抓取失败")
        elif current_status == "完成！":
            st.session_state.capture_running = False
            st.session_state.capture_done = True
        else:
            # 显示进度并在 3 秒后自动刷新
            with st.spinner(current_status or "抓取中..."):
                time.sleep(3)
            st.rerun()

    # ── 结果展示 ──
    if st.session_state.capture_done:
        results_file = "./data/results.json"
        if os.path.exists(results_file):
            with open(results_file, "r", encoding="utf-8") as f:
                comments = json.load(f)

            st.success(f"✅ 抓取完成！共获取 {len(comments)} 条热评")

            st.subheader("热评列表")
            for i, comment in enumerate(comments[:10], 1):
                with st.expander(f"#{i} {comment.get('comment_content', '')[:50]}..."):
                    st.write(f"👍 点赞: {comment.get('like_count', 0):,}")
                    st.write(f"💬 回复: {comment.get('reply_count', 0)}")
                    st.write(f"📝 {comment.get('comment_content', '')}")
                    if comment.get("screenshot_path") and os.path.exists(comment["screenshot_path"]):
                        st.image(comment["screenshot_path"])

            # 查找最新 PDF 报告
            data_dir = Path("./data")
            pdf_files = sorted(data_dir.glob("report_*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
            if pdf_files:
                latest_pdf = pdf_files[0]
                with open(latest_pdf, "rb") as f:
                    st.download_button(
                        "📄 下载 PDF 报告",
                        f,
                        file_name=latest_pdf.name,
                        mime="application/pdf",
                    )


if __name__ == "__main__":
    main()
