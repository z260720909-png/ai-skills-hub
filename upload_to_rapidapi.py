#!/usr/bin/env python3
"""
RapidAPI CI/CD 上传脚本
使用 OpenAPI Provisioning API 自动上传/更新 API 到 RapidAPI

参考: https://docs.rapidapi.com/v2.0/docs/automating-api-provisioning
"""

import os
import sys
import json
import requests

# ─── 配置 ───────────────────────────────────────────────
RAPIDAPI_KEY = os.getenv("RAPIDAPI_PROVIDER_KEY", "")
PROVISIONING_HOST = "openapi-provisioning.p.rapidapi.com"
PROVISIONING_URL = f"https://{PROVISIONING_HOST}/v1/apis"

OWNER_ID = os.getenv("RAPIDAPI_OWNER_ID", "")

# 4个API产品定义
APIS = {
    "football": {
        "name": "Football Match Analyzer",
        "category": "Sports",
        "description": "AI-powered football match analysis API. Fixtures, standings, H2H, score predictions, odds, statistics for 20+ leagues worldwide.",
        "long_description": """## Football Match Analyzer API

Comprehensive football/soccer data and analysis API covering 20+ major leagues worldwide.

### Features
- **Fixtures**: Query upcoming and past matches by league, date, or team
- **Standings**: Full league table with points, goals, form
- **Head-to-Head (H2H)**: Historical matchup comparison between two teams
- **Score Predictions**: AI-powered match outcome predictions
- **Odds**: Real-time betting odds (1X2, Over/Under, Asian Handicap)
- **Statistics**: Detailed match stats (possession, shots, corners, etc.)
- **Today's Summary**: Quick overview of all today's matches

### Supported Leagues
Premier League, La Liga, Serie A, Bundesliga, Ligue 1, Champions League, Europa League, and 15+ more.

### Data Source
Powered by API-Football v3 with real-time data updates.
""",
        "openapi_file": "rapidapi_specs/football_openapi.json",
    },
    "ecommerce": {
        "name": "Multi-Platform E-Commerce",
        "category": "E-Commerce",
        "description": "Unified API for 13 e-commerce platforms. Product management, orders, SEO, content generation across Gumroad, Shopify, Etsy, Amazon, and more.",
        "long_description": """## Multi-Platform E-Commerce API

Manage products, orders, and content across 13 e-commerce platforms from a single API.

### International Platforms (API Integration)
- **Gumroad**: Products, sales, messages, offers, SEO, revenue
- **Shopify**: Products, orders, inventory
- **Etsy**: Products, orders, analytics
- **Amazon**: Products, orders, listing content
- **Lazada**: Products, orders, listing content
- **Temu**: Products, orders, listing content
- **AliExpress**: Products, orders, listing content

### Chinese Platforms (AI Content Generation)
- Taobao, JD, Pinduoduo, Douyin, Xiaohongshu, Xianyu

### Key Features
- **Product Catalog**: Centralized product management across platforms
- **One-Click Sync**: Publish to multiple platforms simultaneously
- **AI Content Engine**: Platform-specific listing content generation
- **Dynamic Pricing**: Cross-platform price comparison and suggestions
- **Revenue Dashboard**: Unified view of sales across all platforms
""",
        "openapi_file": "rapidapi_specs/ecommerce_openapi.json",
    },
    "video": {
        "name": "Video Storyboard",
        "category": "Media",
        "description": "Extract scenes, key frames, and transcribe audio from videos. Supports YouTube, Bilibili, TikTok, and local files. Export to FCPXML.",
        "long_description": """## Video Storyboard API

Automatically deconstruct videos into structured storyboards with scene detection, key frame extraction, and speech-to-text.

### Features
- **Scene Detection**: AI-powered scene boundary detection with configurable threshold
- **Key Frame Extraction**: Three modes - scene-based, uniform interval, smart hybrid
- **Speech Recognition**: Whisper-powered transcription with timeline alignment
- **Video Info**: Duration, resolution, frame rate, orientation detection
- **FCPXML Export**: Import directly into Final Cut Pro

### Supported Sources
- Local video files (MP4, AVI, MOV, MKV, etc.)
- YouTube, Bilibili, TikTok, Douyin, Vimeo, Dailymotion, Twitch

### Use Cases
- Video editing pre-production
- Content analysis and tagging
- Automated video summarization
- Social media content repurposing
""",
        "openapi_file": "rapidapi_specs/video_openapi.json",
    },
    "social": {
        "name": "Social Media Content AI",
        "category": "Social",
        "description": "AI-powered social media content toolkit. Anti-AI rewriting, platform formatting, competitor analysis, banned words checker, and content calendar for 8 platforms.",
        "long_description": """## Social Media Content AI API

All-in-one social media content creation and optimization toolkit for 8 major platforms.

### Supported Platforms
Xiaohongshu (小红书), Douyin (抖音), WeChat Official Account (微信公众号), Weibo (微博), Bilibili (B站), Toutiao (头条), Zhihu (知乎), Kuaishou (快手)

### Features
- **Anti-AI Rewriting**: Transform AI-generated text to natural, human-sounding content with 3 intensity levels. Preserves technical terms.
- **Platform Formatting**: Auto-adapt content to each platform's character limits, hashtag style, emoji density, and tone
- **Image Prompt Generation**: Create platform-specific image descriptions for AI image generators
- **Comment Reply**: Auto-generate engaging replies to comments and DMs
- **Content Scoring**: Rate your content against platform best practices
- **Content Calendar**: Generate a 7-30 day posting schedule optimized for peak engagement times
- **Competitor Analysis**: Structured framework for analyzing competitor content strategies
- **Banned Words Checker**: Industry-specific prohibited terms checker (6 industries, 3 platform categories)
- **Trending Search**: Find trending topics and hashtags

### Industries Covered
Beauty & Skincare, Home & Building Materials, Food & Health, Medical & Healthcare, Finance, Education
""",
        "openapi_file": "rapidapi_specs/social_openapi.json",
    },
}


def generate_openapi_specs(base_url: str):
    """从FastAPI应用生成OpenAPI规范文件"""
    try:
        from main import app
        openapi = app.openapi()

        # 为每个模块生成单独的OpenAPI spec
        for api_key, api_config in APIS.items():
            spec = {
                "openapi": openapi["openapi"],
                "info": {
                    "title": api_config["name"] + " API",
                    "description": api_config["description"],
                    "version": "1.0.0",
                },
                "servers": [{"url": base_url, "description": "Production"}],
                "paths": {},
                "components": openapi.get("components", {}),
            }

            # 筛选对应前缀的路径
            prefix = f"/{api_key.replace('social', 'social')}"
            if api_key == "social":
                prefix = "/social"
            elif api_key == "football":
                prefix = "/football"
            elif api_key == "ecommerce":
                prefix = "/ecommerce"
            elif api_key == "video":
                prefix = "/video"

            for path, methods in openapi.get("paths", {}).items():
                if path.startswith(prefix) or path in ["/", "/health"]:
                    spec["paths"][path] = methods

            # 添加RapidAPI扩展
            spec["x-rapidapi-info"] = {
                "name": api_config["name"],
                "category": api_config["category"],
                "description": api_config["description"],
            }

            # 保存
            output_path = os.path.join(
                os.path.dirname(__file__), api_config["openapi_file"]
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(spec, f, ensure_ascii=False, indent=2)
            print(f"✅ Generated: {output_path}")

    except Exception as e:
        print(f"❌ 生成OpenAPI规范失败: {e}")
        print("请先启动FastAPI服务后再运行: python upload_to_rapidapi.py --generate-specs http://localhost:8000")


def create_api(api_key: str):
    """创建API到RapidAPI"""
    if not RAPIDAPI_KEY or not OWNER_ID:
        print("❌ 缺少 RAPIDAPI_PROVIDER_KEY 或 RAPIDAPI_OWNER_ID 环境变量")
        return None

    config = APIS.get(api_key)
    if not config:
        print(f"❌ 未知API: {api_key}")
        return None

    openapi_path = os.path.join(os.path.dirname(__file__), config["openapi_file"])
    if not os.path.exists(openapi_path):
        print(f"❌ OpenAPI文件不存在: {openapi_path}")
        print(f"   请先运行: python upload_to_rapidapi.py --generate-specs <base_url>")
        return None

    with open(openapi_path, "r", encoding="utf-8") as f:
        openapi_content = f.read()

    url = f"{PROVISIONING_URL}/rapidapi-file"
    headers = {
        "x-rapidapi-host": PROVISIONING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }

    files = {
        "file": (f"{api_key}_openapi.json", openapi_content, "application/json"),
    }
    data = {
        "ownerId": OWNER_ID,
    }

    print(f"📤 上传 {config['name']} 到 RapidAPI...")
    try:
        resp = requests.post(url, headers=headers, data=data, files=files, timeout=60)
        if resp.status_code in (200, 201):
            result = resp.json()
            print(f"✅ {config['name']} 创建成功! API ID: {result.get('id', 'N/A')}")
            return result
        else:
            print(f"❌ 创建失败 [{resp.status_code}]: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


def update_api(api_key: str, api_id: str, version_id: str = None):
    """更新已有API"""
    if not RAPIDAPI_KEY:
        print("❌ 缺少 RAPIDAPI_PROVIDER_KEY")
        return None

    config = APIS.get(api_key)
    openapi_path = os.path.join(os.path.dirname(__file__), config["openapi_file"])

    with open(openapi_path, "r", encoding="utf-8") as f:
        openapi_content = f.read()

    url = f"{PROVISIONING_URL}/rapidapi-file/{api_id}"
    if version_id:
        url += f"/versions/{version_id}"

    headers = {
        "x-rapidapi-host": PROVISIONING_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }

    files = {
        "file": (f"{api_key}_openapi.json", openapi_content, "application/json"),
    }

    print(f"📤 更新 {config['name']} (API ID: {api_id})...")
    try:
        resp = requests.put(url, headers=headers, files=files, timeout=60)
        if resp.status_code == 200:
            print(f"✅ 更新成功!")
            return resp.json()
        else:
            print(f"❌ 更新失败 [{resp.status_code}]: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RapidAPI CI/CD 上传工具")
    parser.add_argument(
        "--generate-specs",
        metavar="BASE_URL",
        help="从FastAPI生成OpenAPI规范 (需提供base URL)",
    )
    parser.add_argument(
        "--create",
        choices=list(APIS.keys()),
        help="创建指定API到RapidAPI",
    )
    parser.add_argument(
        "--create-all",
        action="store_true",
        help="创建所有API到RapidAPI",
    )
    parser.add_argument(
        "--update",
        nargs=2,
        metavar=("API_KEY", "API_ID"),
        help="更新已有API",
    )

    args = parser.parse_args()

    if args.generate_specs:
        generate_openapi_specs(args.generate_specs)

    elif args.create:
        create_api(args.create)

    elif args.create_all:
        for key in APIS:
            create_api(key)

    elif args.update:
        update_api(args.update[0], args.update[1])

    else:
        parser.print_help()
