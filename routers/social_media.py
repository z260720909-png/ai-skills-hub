#!/usr/bin/env python3
"""
自媒体运营模块 FastAPI Router
暴露社交引擎核心能力的 HTTP 端点
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import List, Optional

from core.social_engine import (
    anti_ai_rewrite,
    platform_format,
    generate_image_prompt,
    generate_reply,
    batch_generate_replies,
    content_score,
    content_calendar,
    competitor_analysis_template,
    trending_search,
    get_banned_words,
    get_platforms_info,
)

router = APIRouter(tags=["Social Media"])


# ============================================================
# Pydantic 请求体模型
# ============================================================


class AntiAiRequest(BaseModel):
    text: str = Field(..., description="待改写的文本")
    level: str = Field(default="medium", description="改写强度: light / medium / heavy")
    platform: str = Field(default="general", description="目标平台: xiaohongshu/douyin/wechat/weibo/bilibili/toutiao/zhihu/kuaishou")


class FormatRequest(BaseModel):
    content: str = Field(..., description="正文内容")
    title: str = Field(..., description="标题")
    platform: str = Field(..., description="目标平台: xiaohongshu/douyin/wechat/weibo/bilibili/toutiao/zhihu/kuaishou")


class ImagePromptRequest(BaseModel):
    topic: str = Field(..., description="配图主题")
    platform: str = Field(default="general", description="目标平台")
    style: str = Field(default="modern", description="视觉风格")
    count: int = Field(default=1, ge=1, le=10, description="生成prompt数量")


class ReplyRequest(BaseModel):
    comment: str = Field(..., description="评论内容")
    platform: str = Field(default="general", description="目标平台")
    tone: str = Field(default="auto", description="回复语气: auto/friendly/professional/humorous")


class BatchReplyRequest(BaseModel):
    comments: List[str] = Field(..., description="评论列表")
    platform: str = Field(default="general", description="目标平台")
    tone: str = Field(default="auto", description="回复语气: auto/friendly/professional/humorous")


class ScoreRequest(BaseModel):
    text: str = Field(..., description="待评分文本")
    platform: str = Field(default="general", description="目标平台")


# ============================================================
# POST 端点
# ============================================================


@router.post("/anti-ai", summary="去AI味改写")
def anti_ai_endpoint(req: AntiAiRequest):
    """对文本进行去AI味改写，降低AIGC检测风险"""
    rewritten = anti_ai_rewrite(req.text, level=req.level, platform=req.platform)
    return {
        "original_length": len(req.text),
        "rewritten": rewritten,
        "rewritten_length": len(rewritten),
        "level": req.level,
        "platform": req.platform,
    }


@router.post("/format", summary="平台格式适配")
def format_endpoint(req: FormatRequest):
    """将内容适配到指定平台格式，返回排版建议和配图规格"""
    return platform_format(req.content, req.title, req.platform)


@router.post("/image-prompt", summary="配图文案生成")
def image_prompt_endpoint(req: ImagePromptRequest):
    """为内容生成配图prompt，可直接用于图片生成工具"""
    prompts = generate_image_prompt(req.topic, req.platform, req.style, req.count)
    return {
        "topic": req.topic,
        "platform": req.platform,
        "prompts": prompts,
    }


@router.post("/reply", summary="评论回复")
def reply_endpoint(req: ReplyRequest):
    """根据评论内容和情感自动生成回复"""
    return generate_reply(req.comment, context="", platform=req.platform, tone=req.tone)


@router.post("/batch-reply", summary="批量回复")
def batch_reply_endpoint(req: BatchReplyRequest):
    """批量生成评论回复"""
    return batch_generate_replies(req.comments, req.platform, req.tone)


@router.post("/score", summary="内容评分")
def score_endpoint(req: ScoreRequest):
    """评估内容质量分和AI检测风险分"""
    return content_score(req.text, req.platform)


# ============================================================
# GET 端点
# ============================================================


@router.get("/calendar", summary="内容日历")
def calendar_endpoint(
    niche: str = Query(..., description="领域/赛道"),
    days: int = Query(default=7, ge=1, le=30, description="规划天数"),
    platforms: str = Query(default="xiaohongshu,douyin,wechat", description="目标平台，逗号分隔"),
):
    """生成内容发布日历规划"""
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]
    return content_calendar(niche, days, platform_list)


@router.get("/competitor", summary="竞品分析")
def competitor_endpoint(
    niche: str = Query(..., description="领域/赛道"),
    platform: str = Query(default="general", description="目标平台"),
):
    """生成竞品分析框架，包含搜索关键词和分析维度"""
    return competitor_analysis_template(niche, platform)


@router.get("/trending", summary="热点搜索")
def trending_endpoint(
    topic: str = Query(default="", description="搜索关键词"),
    platform: str = Query(default="general", description="目标平台"),
):
    """获取各平台热点/热搜数据"""
    return trending_search(topic, platform)


@router.get("/banned-words", summary="违禁词查询")
def banned_words_endpoint(
    industry: str = Query(..., description="行业名称，如: 美妆护肤/建材家居/食品保健/医疗健康/金融理财/教育培训"),
    platform: Optional[str] = Query(default=None, description="可选，指定平台过滤"),
):
    """查询行业违禁词库"""
    return get_banned_words(industry, platform)


@router.get("/platforms", summary="查看支持平台")
def platforms_endpoint():
    """返回所有支持的平台及其配置信息"""
    return get_platforms_info()
