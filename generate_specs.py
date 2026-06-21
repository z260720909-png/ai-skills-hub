#!/usr/bin/env python3
"""
RapidAPI 手动 OpenAPI 规范生成器
不需要启动FastAPI服务，直接从代码结构生成OpenAPI 3.0规范
"""

import json
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "rapidapi_specs")

BASE_URL = "https://ai-skills-hub.onrender.com"


def make_football_spec():
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Football Match Analyzer API",
            "description": "AI-powered football match analysis API. Fixtures, standings, H2H, score predictions, odds, statistics for 20+ leagues worldwide including Premier League, La Liga, Serie A, Bundesliga, and Champions League.",
            "version": "1.0.0",
            "contact": {"name": "AI Skills Hub Support", "email": "support@aiskillshub.dev"},
            "license": {"name": "MIT"},
        },
        "servers": [{"url": BASE_URL}],
        "paths": {
            "/football/fixtures": {
                "get": {
                    "summary": "Query Football Fixtures",
                    "description": "Search for upcoming and past football matches by league, date, team, or season. Supports live match queries.",
                    "operationId": "getFixtures",
                    "tags": ["Fixtures"],
                    "parameters": [
                        {"name": "league", "in": "query", "schema": {"type": "string"}, "description": "League name (e.g. '英超', 'Premier League') or ID"},
                        {"name": "date", "in": "query", "schema": {"type": "string", "format": "date"}, "description": "Match date (YYYY-MM-DD)"},
                        {"name": "team", "in": "query", "schema": {"type": "string"}, "description": "Team name or ID"},
                        {"name": "season", "in": "query", "schema": {"type": "string"}, "description": "Season year (e.g. 2024)"},
                        {"name": "live", "in": "query", "schema": {"type": "string", "enum": ["yes", "no"], "default": "no"}, "description": "Show live matches only"},
                        {"name": "next", "in": "query", "schema": {"type": "integer", "default": 0}, "description": "Number of upcoming matches to return"},
                    ],
                    "responses": {"200": {"description": "Fixture list", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/football/standings": {
                "get": {
                    "summary": "League Standings",
                    "description": "Get full league table with points, wins, draws, losses, goals for/against, and recent form.",
                    "operationId": "getStandings",
                    "tags": ["Standings"],
                    "parameters": [
                        {"name": "league", "in": "query", "required": True, "schema": {"type": "string"}, "description": "League name or ID (required)"},
                        {"name": "season", "in": "query", "schema": {"type": "string"}, "description": "Season year"},
                    ],
                    "responses": {"200": {"description": "League standings", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/football/teams": {
                "get": {
                    "summary": "Search Teams",
                    "description": "Search for football teams by name or filter by league.",
                    "operationId": "searchTeams",
                    "tags": ["Teams"],
                    "parameters": [
                        {"name": "name", "in": "query", "schema": {"type": "string"}, "description": "Team name to search"},
                        {"name": "league", "in": "query", "schema": {"type": "string"}, "description": "Filter by league"},
                    ],
                    "responses": {"200": {"description": "Team list", "content": {"application/json": {"schema": {"type": "array"}}}}},
                }
            },
            "/football/h2h": {
                "get": {
                    "summary": "Head-to-Head Comparison",
                    "description": "Compare two teams' historical head-to-head record including wins, draws, losses, and goals.",
                    "operationId": "getH2H",
                    "tags": ["H2H"],
                    "parameters": [
                        {"name": "team1", "in": "query", "required": True, "schema": {"type": "integer"}, "description": "Team 1 ID"},
                        {"name": "team2", "in": "query", "required": True, "schema": {"type": "integer"}, "description": "Team 2 ID"},
                    ],
                    "responses": {"200": {"description": "H2H comparison", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/football/prediction": {
                "get": {
                    "summary": "Match Score Prediction",
                    "description": "AI-powered match outcome prediction based on team form, H2H record, and statistical models.",
                    "operationId": "getPrediction",
                    "tags": ["Prediction"],
                    "parameters": [
                        {"name": "fixture_id", "in": "query", "required": True, "schema": {"type": "integer"}, "description": "Fixture ID (required)"},
                    ],
                    "responses": {"200": {"description": "Match prediction", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/football/analysis": {
                "get": {
                    "summary": "Full Match Analysis",
                    "description": "Comprehensive match analysis combining predictions, H2H, team form, and statistics into a unified report.",
                    "operationId": "getAnalysis",
                    "tags": ["Analysis"],
                    "parameters": [
                        {"name": "fixture_id", "in": "query", "required": True, "schema": {"type": "integer"}, "description": "Fixture ID (required)"},
                    ],
                    "responses": {"200": {"description": "Full analysis report", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/football/odds": {
                "get": {
                    "summary": "Betting Odds",
                    "description": "Real-time betting odds for matches. Supports 1X2, Over/Under, and Asian Handicap markets.",
                    "operationId": "getOdds",
                    "tags": ["Odds"],
                    "parameters": [
                        {"name": "fixture_id", "in": "query", "schema": {"type": "integer"}, "description": "Fixture ID"},
                        {"name": "league", "in": "query", "schema": {"type": "string"}, "description": "League name or ID"},
                        {"name": "season", "in": "query", "schema": {"type": "string"}, "description": "Season year"},
                        {"name": "bet_type", "in": "query", "schema": {"type": "integer", "enum": [1, 3, 5], "default": 1}, "description": "1=1X2, 3=Asian Handicap, 5=Over/Under"},
                    ],
                    "responses": {"200": {"description": "Odds data", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/football/statistics": {
                "get": {
                    "summary": "Match Statistics",
                    "description": "Detailed match statistics including possession, shots, corners, fouls, and more.",
                    "operationId": "getStatistics",
                    "tags": ["Statistics"],
                    "parameters": [
                        {"name": "fixture_id", "in": "query", "required": True, "schema": {"type": "integer"}, "description": "Fixture ID (required)"},
                    ],
                    "responses": {"200": {"description": "Match statistics", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/football/today": {
                "get": {
                    "summary": "Today's Matches Summary",
                    "description": "Quick overview of all today's football matches across major leagues.",
                    "operationId": "getTodaySummary",
                    "tags": ["Today"],
                    "parameters": [],
                    "responses": {"200": {"description": "Today's match summary", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
        },
    }


def make_social_spec():
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Social Media Content AI API",
            "description": "AI-powered social media content toolkit for 8 platforms. Anti-AI rewriting, platform formatting, competitor analysis, banned words checker, content calendar, and more.",
            "version": "1.0.0",
            "contact": {"name": "AI Skills Hub Support"},
        },
        "servers": [{"url": BASE_URL}],
        "paths": {
            "/social/anti-ai": {
                "post": {
                    "summary": "Anti-AI Content Rewriting",
                    "description": "Transform AI-generated text into natural, human-sounding content. 3 intensity levels (light/medium/heavy). Preserves technical terms like DN20, 1.6MPa, ISO certifications.",
                    "operationId": "antiAiRewrite",
                    "tags": ["Content Creation"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string", "description": "Text to rewrite"}, "level": {"type": "string", "enum": ["light", "medium", "heavy"], "default": "medium"}, "platform": {"type": "string", "default": "general"}}}}},
                    },
                    "responses": {"200": {"description": "Rewritten content", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/social/format": {
                "post": {
                    "summary": "Platform Format Adaptation",
                    "description": "Auto-adapt content to specific platform requirements: character limits, hashtag style, emoji density, paragraph style, and tone.",
                    "operationId": "platformFormat",
                    "tags": ["Content Creation"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["content", "title", "platform"], "properties": {"content": {"type": "string"}, "title": {"type": "string"}, "platform": {"type": "string", "enum": ["xiaohongshu", "douyin", "wechat", "weibo", "bilibili", "toutiao", "zhihu", "kuaishou"]}}}}},
                    },
                    "responses": {"200": {"description": "Formatted content", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/social/image-prompt": {
                "post": {
                    "summary": "Image Prompt Generation",
                    "description": "Generate platform-specific image description prompts for AI image generators, considering aspect ratio, style, and platform norms.",
                    "operationId": "imagePrompt",
                    "tags": ["Content Creation"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["topic"], "properties": {"topic": {"type": "string"}, "platform": {"type": "string", "default": "general"}, "style": {"type": "string", "default": "modern"}, "count": {"type": "integer", "default": 1}}}}},
                    },
                    "responses": {"200": {"description": "Image prompts", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/social/reply": {
                "post": {
                    "summary": "Comment/DM Reply Generator",
                    "description": "Auto-generate engaging, platform-appropriate replies to comments and direct messages.",
                    "operationId": "generateReply",
                    "tags": ["Engagement"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["comment"], "properties": {"comment": {"type": "string"}, "platform": {"type": "string", "default": "general"}, "tone": {"type": "string", "default": "auto"}}}}},
                    },
                    "responses": {"200": {"description": "Generated reply", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/social/score": {
                "post": {
                    "summary": "Content Quality Scoring",
                    "description": "Rate your content against platform best practices. Scores title, body, hashtags, emoji usage, and overall engagement potential.",
                    "operationId": "contentScore",
                    "tags": ["Analytics"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}, "platform": {"type": "string", "default": "general"}}}}},
                    },
                    "responses": {"200": {"description": "Content score", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/social/calendar": {
                "get": {
                    "summary": "Content Calendar Generator",
                    "description": "Generate a multi-day posting schedule optimized for platform peak engagement times.",
                    "operationId": "contentCalendar",
                    "tags": ["Planning"],
                    "parameters": [
                        {"name": "niche", "in": "query", "schema": {"type": "string", "default": "综合"}, "description": "Content niche/industry"},
                        {"name": "days", "in": "query", "schema": {"type": "integer", "default": 7}, "description": "Number of days (1-30)"},
                        {"name": "platforms", "in": "query", "schema": {"type": "string", "default": "xiaohongshu,douyin,wechat"}, "description": "Comma-separated platform list"},
                    ],
                    "responses": {"200": {"description": "Content calendar", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/social/competitor": {
                "get": {
                    "summary": "Competitor Analysis Framework",
                    "description": "Generate a structured competitor analysis framework for a specific niche and platform, including data fields to fill.",
                    "operationId": "competitorAnalysis",
                    "tags": ["Analytics"],
                    "parameters": [
                        {"name": "niche", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Niche/industry to analyze"},
                        {"name": "platform", "in": "query", "schema": {"type": "string", "default": "general"}, "description": "Platform context"},
                    ],
                    "responses": {"200": {"description": "Competitor analysis", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/social/banned-words": {
                "get": {
                    "summary": "Industry Banned Words Checker",
                    "description": "Check prohibited advertising terms for 6 industries (Beauty, Home & Building, Food & Health, Medical, Finance, Education) across platforms.",
                    "operationId": "bannedWords",
                    "tags": ["Compliance"],
                    "parameters": [
                        {"name": "industry", "in": "query", "required": True, "schema": {"type": "string", "enum": ["beauty", "home", "food", "medical", "finance", "education"]}, "description": "Industry category"},
                        {"name": "platform", "in": "query", "schema": {"type": "string", "default": "all"}, "description": "Platform filter (xiaohongshu/douyin/all)"},
                    ],
                    "responses": {"200": {"description": "Banned words list", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/social/trending": {
                "get": {
                    "summary": "Trending Topics Search",
                    "description": "Find trending topics and hashtags for content creation.",
                    "operationId": "trendingSearch",
                    "tags": ["Discovery"],
                    "parameters": [
                        {"name": "topic", "in": "query", "schema": {"type": "string"}, "description": "Topic keyword"},
                        {"name": "platform", "in": "query", "schema": {"type": "string", "default": "general"}, "description": "Platform context"},
                    ],
                    "responses": {"200": {"description": "Trending topics", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/social/platforms": {
                "get": {
                    "summary": "List Supported Platforms",
                    "description": "Get the list of all 8 supported social media platforms with their specs.",
                    "operationId": "listPlatforms",
                    "tags": ["Info"],
                    "parameters": [],
                    "responses": {"200": {"description": "Platform list", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
        },
    }


def make_ecommerce_spec():
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Multi-Platform E-Commerce API",
            "description": "Unified API for 13 e-commerce platforms. Product management, orders, SEO, content generation across Gumroad, Shopify, Etsy, Amazon, Lazada, Temu, AliExpress and Chinese platforms.",
            "version": "1.0.0",
            "contact": {"name": "AI Skills Hub Support"},
        },
        "servers": [{"url": BASE_URL}],
        "paths": {
            "/ecommerce/platforms": {
                "get": {
                    "summary": "List Supported Platforms",
                    "description": "Get all 13 supported e-commerce platforms with their configuration status.",
                    "operationId": "listPlatforms",
                    "tags": ["Platform Info"],
                    "parameters": [],
                    "responses": {"200": {"description": "Platform list", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/catalog": {
                "get": {
                    "summary": "List Product Catalog",
                    "description": "List all products in your centralized product catalog.",
                    "operationId": "listCatalog",
                    "tags": ["Product Catalog"],
                    "parameters": [],
                    "responses": {"200": {"description": "Product catalog", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/catalog": {
                "post": {
                    "summary": "Add Product to Catalog",
                    "description": "Add a new product to your centralized product catalog.",
                    "operationId": "addCatalogProduct",
                    "tags": ["Product Catalog"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "price": {"type": "number"}, "description": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}}}},
                    },
                    "responses": {"200": {"description": "Added product", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/products": {
                "get": {
                    "summary": "List Platform Products",
                    "description": "List products from a specific platform. Requires platform API credentials.",
                    "operationId": "listProducts",
                    "tags": ["Products"],
                    "parameters": [
                        {"name": "platform", "in": "query", "required": True, "schema": {"type": "string", "enum": ["gumroad", "shopify", "etsy", "amazon", "lazada", "temu", "aliexpress"]}, "description": "Platform name"},
                        {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}, "description": "Page number"},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}, "description": "Items per page"},
                    ],
                    "responses": {"200": {"description": "Product list", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/products": {
                "post": {
                    "summary": "Create Product on Platform",
                    "description": "Create a new product on a specific platform. Requires platform API credentials.",
                    "operationId": "createProduct",
                    "tags": ["Products"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["platform", "product_data"], "properties": {"platform": {"type": "string"}, "product_data": {"type": "object"}}}}},
                    },
                    "responses": {"200": {"description": "Created product", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/orders": {
                "get": {
                    "summary": "Unified Order View",
                    "description": "View orders across all connected platforms in a unified format.",
                    "operationId": "listOrders",
                    "tags": ["Orders"],
                    "parameters": [
                        {"name": "platform", "in": "query", "schema": {"type": "string"}, "description": "Filter by platform"},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}, "description": "Number of orders"},
                    ],
                    "responses": {"200": {"description": "Order list", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/sales": {
                "get": {
                    "summary": "Sales Report (Gumroad)",
                    "description": "Get Gumroad sales data for a specified period.",
                    "operationId": "getSales",
                    "tags": ["Sales"],
                    "parameters": [
                        {"name": "days", "in": "query", "schema": {"type": "integer", "default": 30}, "description": "Number of days to report"},
                    ],
                    "responses": {"200": {"description": "Sales data", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/multi-content": {
                "post": {
                    "summary": "Multi-Platform Content Generation",
                    "description": "Generate platform-specific product listing content for multiple platforms at once.",
                    "operationId": "multiContent",
                    "tags": ["Cross-Platform"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["product_info", "platforms"], "properties": {"product_info": {"type": "object"}, "platforms": {"type": "array", "items": {"type": "string"}}}}}},
                    },
                    "responses": {"200": {"description": "Generated content", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/sync": {
                "post": {
                    "summary": "Cross-Platform Sync",
                    "description": "Sync a product to multiple platforms simultaneously with platform-specific adaptations.",
                    "operationId": "syncProduct",
                    "tags": ["Cross-Platform"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "required": ["product_info", "target_platforms"], "properties": {"product_info": {"type": "object"}, "target_platforms": {"type": "array", "items": {"type": "string"}}}}}},
                    },
                    "responses": {"200": {"description": "Sync results", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/analyze": {
                "get": {
                    "summary": "Cross-Platform Analytics",
                    "description": "Analyze performance across all connected platforms.",
                    "operationId": "analyzePlatforms",
                    "tags": ["Analytics"],
                    "parameters": [],
                    "responses": {"200": {"description": "Analytics data", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/ecommerce/keywords": {
                "get": {
                    "summary": "Keyword Trend Analysis",
                    "description": "Analyze keyword trends and popularity for product SEO optimization.",
                    "operationId": "keywordAnalysis",
                    "tags": ["SEO"],
                    "parameters": [
                        {"name": "type", "in": "query", "schema": {"type": "string", "default": "trending"}, "description": "Analysis type"},
                    ],
                    "responses": {"200": {"description": "Keyword data", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
        },
    }


def make_video_spec():
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Video Storyboard API",
            "description": "Extract scenes, key frames, and transcribe audio from videos. Supports YouTube, Bilibili, TikTok, and local files. Export to FCPXML for Final Cut Pro.",
            "version": "1.0.0",
            "contact": {"name": "AI Skills Hub Support"},
        },
        "servers": [{"url": BASE_URL}],
        "paths": {
            "/video/analyze": {
                "post": {
                    "summary": "Analyze Video",
                    "description": "Full video analysis: scene detection, key frame extraction, and optional speech-to-text. Supports local files and online URLs (YouTube, Bilibili, TikTok, etc.).",
                    "operationId": "analyzeVideo",
                    "tags": ["Analysis"],
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object", "properties": {
                            "video_url": {"type": "string", "description": "Video URL (YouTube/Bilibili/TikTok/etc.)"},
                            "mode": {"type": "string", "enum": ["scene", "uniform", "smart"], "default": "scene", "description": "Extraction mode"},
                            "max_scenes": {"type": "integer", "default": 20, "description": "Max scenes for smart mode"},
                            "threshold": {"type": "number", "default": 0.3, "description": "Scene detection threshold (0-1)"},
                            "asr": {"type": "boolean", "default": False, "description": "Enable speech recognition"},
                            "whisper_model": {"type": "string", "enum": ["tiny", "base", "small", "medium", "large"], "default": "base"},
                            "whisper_lang": {"type": "string", "description": "Language code (zh/en, auto-detect if empty)"},
                            "export": {"type": "array", "items": {"type": "string", "enum": ["fcpxml"]}, "description": "Extra export formats"},
                        }}}},
                    },
                    "responses": {
                        "200": {"description": "Analysis results", "content": {"application/json": {"schema": {"type": "object"}}}},
                        "400": {"description": "Invalid video URL or file"},
                    },
                }
            },
            "/video/info": {
                "get": {
                    "summary": "Get Video Info",
                    "description": "Get video metadata (duration, resolution, frame rate, orientation) without full processing.",
                    "operationId": "getVideoInfo",
                    "tags": ["Info"],
                    "parameters": [
                        {"name": "video_url", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Video URL"},
                    ],
                    "responses": {"200": {"description": "Video info", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/video/supported-domains": {
                "get": {
                    "summary": "List Supported Video Domains",
                    "description": "Get the list of all supported online video platform domains.",
                    "operationId": "listDomains",
                    "tags": ["Info"],
                    "parameters": [],
                    "responses": {"200": {"description": "Domain list", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/video/health": {
                "get": {
                    "summary": "Check Service Health",
                    "description": "Check if ffmpeg and Whisper are available on the server.",
                    "operationId": "videoHealth",
                    "tags": ["Info"],
                    "parameters": [],
                    "responses": {"200": {"description": "Health status", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
        },
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    specs = {
        "football_openapi.json": make_football_spec(),
        "social_openapi.json": make_social_spec(),
        "ecommerce_openapi.json": make_ecommerce_spec(),
        "video_openapi.json": make_video_spec(),
    }

    for filename, spec in specs.items():
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        print(f"✅ {path} ({len(json.dumps(spec))} bytes)")

    print(f"\n📊 共生成 {len(specs)} 个OpenAPI规范文件")
    print("下一步:")
    print("1. 部署FastAPI到Render/Railway")
    print("2. 设置RAPIDAPI_PROVIDER_KEY和RAPIDAPI_OWNER_ID环境变量")
    print("3. 运行: python upload_to_rapidapi.py --create-all")


if __name__ == "__main__":
    main()
