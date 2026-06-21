#!/usr/bin/env python3
"""
AI Skills Hub API — 四合一智能技能API
覆盖: 足球分析 / 全平台电商 / 视频分镜 / 自媒体运营
"""

import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 添加core目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from routers import football, ecommerce, video, social_media

app = FastAPI(
    title="AI Skills Hub API",
    description="""
# 🚀 AI Skills Hub — 四合一智能API

| 模块 | 端点前缀 | 能力 |
|------|----------|------|
| ⚽ 足球分析 | `/football` | 赛程/积分榜/H2H/比分预测/赔率/统计 |
| 🛒 全平台电商 | `/ecommerce` | Gumroad/Shopify/Etsy/Amazon等7大国际平台+6大国内平台 |
| 🎬 视频分镜 | `/video` | 场景检测/关键帧/语音识别/FCPXML导出 |
| 📱 自媒体运营 | `/social` | 去AI味/平台适配/竞品分析/违禁词/内容日历 |

认证方式: 所有请求需在Header中携带 `X-RapidAPI-Key`
    """,
    version="1.0.0",
    contact={
        "name": "AI Skills Hub Support",
        "email": "support@aiskillshub.dev",
    },
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(football.router, prefix="/football", tags=["⚽ Football Analysis"])
app.include_router(ecommerce.router, prefix="/ecommerce", tags=["🛒 E-Commerce"])
app.include_router(video.router, prefix="/video", tags=["🎬 Video Storyboard"])
app.include_router(social_media.router, prefix="/social", tags=["📱 Social Media"])


@app.get("/", summary="API概览")
async def root():
    return {
        "api": "AI Skills Hub",
        "version": "1.0.0",
        "modules": {
            "football": "/football",
            "ecommerce": "/ecommerce",
            "video": "/video",
            "social": "/social",
        },
        "docs": "/docs",
    }


@app.get("/health", summary="健康检查")
async def health():
    return {"status": "ok"}
