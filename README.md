# AI Skills Hub API

四合一智能技能API，部署到Render并上架RapidAPI。

## 模块

| 模块 | 前缀 | 能力 |
|------|------|------|
| ⚽ 足球分析 | `/football` | 赛程/积分榜/H2H/比分预测/赔率/统计 |
| 🛒 全平台电商 | `/ecommerce` | 7大国际平台+6大国内平台 |
| 🎬 视频分镜 | `/video` | 场景检测/关键帧/语音识别/FCPXML |
| 📱 自媒体运营 | `/social` | 去AI味/平台适配/竞品分析/违禁词 |

## 本地运行

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## 环境变量

| 变量名 | 用途 | 必填 |
|--------|------|------|
| APIFOOTBALL_KEY | API-Football v3密钥 | 足球模块 |
| GUMROAD_API_KEY | Gumroad API Token | 电商Gumroad |
| SHOPIFY_API_KEY | Shopify Access Token | 电商Shopify |
| SHOPIFY_SHOP_NAME | Shopify店铺域名 | 电商Shopify |

## 部署到Render

1. 推送到GitHub
2. 在Render创建Web Service，连接仓库
3. 设置环境变量
4. 自动部署

## 上架RapidAPI

```bash
# 生成OpenAPI规范
python generate_specs.py

# 上传到RapidAPI（需设置RAPIDAPI_PROVIDER_KEY和RAPIDAPI_OWNER_ID）
python upload_to_rapidapi.py --create-all
```
