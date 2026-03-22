"""
Comment analysis module.

Supports two modes:
1. AI-based analysis (when OPENAI_API_KEY is set)
2. Keyword-based analysis (fallback)
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

# AI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def analyze_with_ai(comment: dict, video_info: dict) -> dict:
    """
    Analyze comment using AI (OpenAI-compatible API).

    Args:
        comment: Comment data
        video_info: Video information

    Returns:
        Analysis dict with reasons, viral_points, directions
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

        prompt = f"""你是一个专业的短视频评论分析师。请分析以下抖音热评，给出精准、可操作的分析。

【背景信息】
- 博主：{video_info.get("author", "未知")}
- 视频主题：{video_info.get("title", "未知")[:80]}

【热评数据】
- 评论内容：{comment.get("comment_content", "")}
- 点赞数：{comment.get("like_count", 0)}
- 回复数：{comment.get("reply_count", 0)}

【分析要求】
请从以下三个维度分析，每个维度给出具体、有针对性的分析（不要泛泛而谈）：

1. 热门成因（reasons）：这条评论为什么能获得高赞？
   - 分析评论与视频的关联性
   - 分析评论的情绪触发点
   - 分析评论的表达技巧

2. 爆点分析（viral_points）：这条评论的传播关键是什么？
   - 是否引发共鸣或争议
   - 是否适合截图传播
   - 是否引发二次讨论

3. 复刻方向（directions）：如何复制这种成功？
   - 针对同类型视频的创作建议
   - 评论引导策略
   - 内容优化方向

【返回格式】
直接返回JSON，不要其他内容：
{{"reasons": ["原因1", "原因2"], "viral_points": ["爆点1"], "directions": ["方向1", "方向2"]}}"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )

        result_text = response.choices[0].message.content

        # Parse JSON from response
        # Try to find JSON in the response
        import re

        json_match = re.search(r"\{[^}]+\}", result_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "reasons": result.get("reasons", [])[:3],
                "viral_points": result.get("viral_points", [])[:2],
                "directions": result.get("directions", [])[:3],
            }

    except Exception as e:
        print(f"AI analysis failed: {e}")

    # Fallback to keyword analysis
    return analyze_with_keywords(comment)


def analyze_with_keywords(comment: dict) -> dict:
    """
    Analyze comment using improved keyword matching.

    Args:
        comment: Comment data

    Returns:
        Analysis dict
    """
    content = comment.get("comment_content", "")
    likes = comment.get("like_count", 0)
    replies = comment.get("reply_count", 0)

    # Hotness reasons - more specific
    reasons = []

    # Length-based
    if len(content) <= 10:
        reasons.append("极简金句：10字以内，易于记忆和传播")
    elif len(content) <= 25:
        reasons.append("短小精悍：一句话直击要害")

    # Content-based (more specific patterns)
    humor_patterns = {
        "谐音梗": ["谐音", "音译", "同音"],
        "反转幽默": ["但是", "结果", "没想到", "然而"],
        "自嘲": ["我就是", "说的就是我", "中枪"],
        "夸张": ["笑死", "笑不活", "绷不住", "破防"],
        "玩梗": ["梗", "典", "绝了", "yyds", "神"],
    }

    for pattern_name, keywords in humor_patterns.items():
        if any(k in content for k in keywords):
            reasons.append(f"{pattern_name}：制造意外笑点")
            break

    resonance_patterns = {
        "强烈认同": ["一样", "同款", "我也是", "真实", "确实是"],
        "回忆杀": ["以前", "小时候", "记得", "当年"],
        "吐槽共鸣": ["烦", "讨厌", "无语", "服了"],
        "情绪宣泄": ["啊啊啊", "救命", "绝了", "离谱"],
    }

    for pattern_name, keywords in resonance_patterns.items():
        if any(k in content for k in keywords):
            reasons.append(f"情绪共振：触发{pattern_name}心理")
            break

    # Engagement-based
    if likes > 20000:
        reasons.append("马太效应：高赞引发从众点赞")
    elif likes > 10000:
        reasons.append("破圈传播：突破圈层获得广泛关注")

    if replies > 500:
        reasons.append("互动引爆：高回复带动二次讨论")

    if not reasons:
        reasons.append("精准定位：击中目标受众内心")

    # Viral points
    viral_points = []

    if len(content) < 30:
        viral_points.append("短平快：适合截图二次传播")

    if any(e in content for e in ["[", "【", "表情"]):
        viral_points.append("表情加持：图文结合增强表现力")

    if replies > likes * 0.1:  # 回复率高
        viral_points.append("话题性强：激发用户讨论欲望")

    if any(k in content for k in ["?", "？", "怎么", "为什么", "谁"]):
        viral_points.append("设问引发：问题句式引导用户参与")

    if not viral_points:
        viral_points.append("自然发酵：优质内容自带传播力")

    # Replication directions
    directions = []

    # Topic-based directions
    topic_mapping = {
        "游戏": [
            "游戏解说类：结合热门游戏梗和玩家痛点",
            "游戏攻略类：实用技巧+幽默解说",
        ],
        "王者": ["王者荣耀类：英雄台词梗、皮肤梗"],
        "LOL": ["LOL类：职业赛事梗、英雄梗"],
        "吃鸡": ["FPS类：操作翻车、神仙操作"],
        "AI": ["AI科普类：新技术解读+应用场景"],
        "绘画": ["创意绘画类：过程展示+成品反差"],
        "恋爱": ["情感共鸣类：恋爱日常、分手感悟"],
        "分手": ["情感故事类：真实经历引发共鸣"],
        "工作": ["职场吐槽类：打工人日常、老板语录"],
        "上班": ["打工人系列：通勤、加班、摸鱼"],
        "老板": ["职场关系类：向上管理、同事相处"],
        "美食": ["美食探店类：真实评价+避坑指南"],
        "减肥": ["身材管理类：减肥心得、健身日常"],
        "猫": ["萌宠类：猫咪日常、养宠心得"],
        "狗": ["宠物互动类：狗狗搞笑瞬间"],
    }

    for topic, dirs in topic_mapping.items():
        if topic in content:
            directions.extend(dirs[:2])
            break

    if len(content) < 20:
        directions.append("短评制造：设计槽点引导神评")
        directions.append("争议话题：抛出观点引发站队讨论")

    if not directions:
        directions.append("情绪价值：提供快乐/共鸣/认同")
        directions.append("互动设计：设置问题引导评论")

    return {
        "reasons": reasons[:3],
        "viral_points": viral_points[:2],
        "directions": directions[:3],
    }


def analyze_comment(comment: dict, video_info: dict = None) -> dict:
    """
    Main analysis function. Uses AI if API key is set, otherwise keywords.

    Args:
        comment: Comment data
        video_info: Video information (optional)

    Returns:
        Analysis dict
    """
    if OPENAI_API_KEY:
        return analyze_with_ai(comment, video_info or {})
    else:
        return analyze_with_keywords(comment)
