#!/usr/bin/env python3
"""
全平台电商运营引擎 v3.1 - 适配 AI Skills Hub
支持国际平台：Gumroad, Shopify, Etsy, Amazon, Lazada, Temu, AliExpress(速卖通)
支持国内平台：淘宝, 京东, 拼多多, 抖音小店, 小红书, 闲鱼

从原始技能文件适配，移除 coze_workload_identity 依赖和 SKILL_ID 引用，
改用标准 requests 库和标准环境变量名。
"""

import os
import json
import re
import math
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import requests

CATALOG_DIR = os.environ.get("ECOMMERCE_CATALOG_DIR", "/tmp/ecommerce_catalog")

# ==================== 凭证管理 ====================

CREDENTIAL_MAP = {
    "gumroad": "GUMROAD_API_KEY",
    "shopify": "SHOPIFY_API_KEY",
    "etsy": "ETSY_API_KEY",
    "amazon": "AMAZON_API_KEY",
    "lazada": "LAZADA_API_KEY",
    "temu": "TEMU_API_KEY",
    "aliexpress": "ALIEXPRESS_API_KEY",
}

SHOP_NAME_ENV = "SHOPIFY_SHOP_NAME"
AMAZON_MARKETPLACE_ENV = "AMAZON_MARKETPLACE"
LAZADA_APP_KEY_ENV = "LAZADA_APP_KEY"
TEMU_APP_KEY_ENV = "TEMU_APP_KEY"
ALIEXPRESS_APP_KEY_ENV = "ALIEXPRESS_APP_KEY"


def get_credential(platform):
    """获取平台 API 凭证"""
    env_key = CREDENTIAL_MAP.get(platform)
    if not env_key:
        return None
    return os.getenv(env_key)


# ==================== 产品目录系统 ====================

def _ensure_catalog_dir():
    os.makedirs(CATALOG_DIR, exist_ok=True)


def catalog_path(product_id=None):
    _ensure_catalog_dir()
    if product_id:
        safe_id = re.sub(r'[^\w\-.]', '_', product_id)
        return os.path.join(CATALOG_DIR, f"{safe_id}.json")
    return os.path.join(CATALOG_DIR, "_index.json")


def catalog_list():
    """列出所有本地产品目录"""
    _ensure_catalog_dir()
    index_path = catalog_path()
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"products": [], "last_updated": None}


def catalog_save_index(index):
    index["last_updated"] = datetime.now().isoformat()
    path = catalog_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def catalog_add(product_info):
    """添加产品到目录"""
    index = catalog_list()
    pid = product_info.get("catalog_id") or f"prod_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    product_info["catalog_id"] = pid
    product_info.setdefault("platforms", {})
    product_info.setdefault("created_at", datetime.now().isoformat())
    product_info.setdefault("variants", [])

    # 保存产品详情
    detail_path = catalog_path(pid)
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(product_info, f, ensure_ascii=False, indent=2)

    # 更新索引
    existing = [p for p in index["products"] if p.get("catalog_id") != pid]
    existing.append({
        "catalog_id": pid,
        "name": product_info.get("name", ""),
        "type": product_info.get("type", ""),
        "price": product_info.get("price", 0),
        "platforms": list(product_info.get("platforms", {}).keys()),
        "created_at": product_info["created_at"],
    })
    index["products"] = existing
    catalog_save_index(index)
    return pid


def catalog_get(product_id):
    """获取产品详情"""
    path = catalog_path(product_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def catalog_update(product_id, updates):
    """更新产品信息"""
    product = catalog_get(product_id)
    if not product:
        return {"error": f"产品 {product_id} 不在目录中"}
    product.update(updates)
    product["updated_at"] = datetime.now().isoformat()
    path = catalog_path(product_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(product, f, ensure_ascii=False, indent=2)
    # 同步索引
    index = catalog_list()
    for p in index["products"]:
        if p["catalog_id"] == product_id:
            p["name"] = product.get("name", p["name"])
            p["platforms"] = list(product.get("platforms", {}).keys())
            break
    catalog_save_index(index)
    return product


def catalog_update_platform_status(product_id, platform, status_info):
    """更新产品在某平台的状态"""
    product = catalog_get(product_id)
    if not product:
        return {"error": f"产品 {product_id} 不在目录中"}
    product.setdefault("platforms", {})
    product["platforms"][platform] = {
        **status_info,
        "updated_at": datetime.now().isoformat(),
    }
    return catalog_update(product_id, product)


def catalog_remove(product_id):
    """从目录移除产品"""
    index = catalog_list()
    index["products"] = [p for p in index["products"] if p["catalog_id"] != product_id]
    catalog_save_index(index)
    path = catalog_path(product_id)
    if os.path.exists(path):
        os.remove(path)
    return {"status": "removed", "catalog_id": product_id}


# ==================== 平台配置 ====================

PLATFORM_CONFIG = {
    "gumroad": {
        "name": "Gumroad",
        "region": "international",
        "base_url": "https://api.gumroad.com/v2",
        "auth_type": "bearer",
        "price_unit": "cents",
        "supports_tags": True,
        "tag_format": "array",
        "max_tags": 15,
        "title_max": 80,
        "desc_format": "html",
        "category": "digital_products",
        "file_upload_via_api": False,
        "commission_rate": 0.10,
        "currency": "USD",
    },
    "shopify": {
        "name": "Shopify",
        "region": "international",
        "base_url": "https://{shop}.myshopify.com/admin/api/2024-01",
        "auth_type": "x-shopify-access-token",
        "price_unit": "cents",
        "supports_tags": True,
        "tag_format": "comma",
        "max_tags": 20,
        "title_max": 255,
        "desc_format": "html",
        "category": "ecommerce",
        "file_upload_via_api": True,
        "commission_rate": 0.0,
        "monthly_fee": 39,
        "currency": "USD",
    },
    "etsy": {
        "name": "Etsy",
        "region": "international",
        "base_url": "https://openapi.etsy.com/v3",
        "auth_type": "bearer",
        "price_unit": "dollars",
        "supports_tags": True,
        "tag_format": "array",
        "max_tags": 13,
        "title_max": 140,
        "desc_format": "plain",
        "category": "marketplace",
        "file_upload_via_api": True,
        "commission_rate": 0.065,
        "listing_fee": 0.20,
        "currency": "USD",
    },
    "amazon": {
        "name": "Amazon",
        "region": "international",
        "base_url": "https://sellingpartnerapi-na.amazon.com",
        "auth_type": "bearer",
        "price_unit": "dollars",
        "supports_tags": True,
        "tag_format": "comma",
        "max_tags": 20,
        "title_max": 200,
        "desc_format": "html",
        "category": "marketplace",
        "file_upload_via_api": True,
        "commission_rate": 0.15,
        "referral_fee_range": "6%-45%（按品类）",
        "currency": "USD",
        "marketplaces": {
            "US": "ATVPDKIKX0DER",
            "UK": "A1F83G8C2ARO7P",
            "DE": "A1PA6795UKMFR9",
            "JP": "A1VC38T7YXB528",
            "CA": "A2EUQ1WTGCTBG2",
            "AU": "A39IBJ37TRP1C6",
        },
    },
    "lazada": {
        "name": "Lazada",
        "region": "southeast_asia",
        "base_url": "https://api.lazada.com.my/rest",
        "auth_type": "app_sign",
        "price_unit": "dollars",
        "supports_tags": True,
        "tag_format": "comma",
        "max_tags": 20,
        "title_max": 255,
        "desc_format": "html",
        "category": "marketplace",
        "file_upload_via_api": True,
        "commission_rate": 0.04,
        "commission_range": "1%-5%（按品类）",
        "currency": "USD",
        "regions": {
            "TH": "https://api.lazada.co.th/rest",
            "VN": "https://api.lazada.vn/rest",
            "PH": "https://api.lazada.com.ph/rest",
            "MY": "https://api.lazada.com.my/rest",
            "SG": "https://api.lazada.sg/rest",
            "ID": "https://api.lazada.co.id/rest",
        },
    },
    "temu": {
        "name": "Temu",
        "region": "international",
        "base_url": "https://openapi-b-global.temu.com/openapi/router",
        "auth_type": "app_sign",
        "price_unit": "dollars",
        "supports_tags": True,
        "tag_format": "comma",
        "max_tags": 20,
        "title_max": 128,
        "desc_format": "html",
        "category": "marketplace",
        "file_upload_via_api": True,
        "commission_rate": 0.0,
        "commission_range": "0%（卖家自主定价，无平台佣金）",
        "currency": "USD",
        "regions": {
            "US": "https://openapi-b-global.temu.com/openapi/router",
            "EU": "https://openapi-b-eu.temu.com/openapi/router",
            "UK": "https://openapi-b-global.temu.com/openapi/router",
            "AU": "https://openapi-b-global.temu.com/openapi/router",
        },
    },
    "aliexpress": {
        "name": "AliExpress(速卖通)",
        "region": "international",
        "base_url": "https://api.taobao.com/router/rest",
        "auth_type": "app_sign",
        "price_unit": "dollars",
        "supports_tags": True,
        "tag_format": "comma",
        "max_tags": 20,
        "title_max": 218,
        "desc_format": "html",
        "category": "marketplace",
        "file_upload_via_api": True,
        "commission_rate": 0.05,
        "commission_range": "5%-8%（按品类）",
        "currency": "USD",
        "regions": {
            "US": "https://api.taobao.com/router/rest",
            "EU": "https://de-api.aliexpress.com/router/rest",
            "RU": "https://ru-api.aliexpress.com/router/rest",
        },
    },
}

CHINESE_PLATFORMS = {
    "taobao": {
        "name": "淘宝/天猫",
        "title_max": 60,
        "main_images": 5,
        "content_style": "seo_title",
        "commission_rate": 0.006,
        "currency": "CNY",
        "keywords_position": "title",
        "tips": "标题必须包含核心搜索词，前30字最重要；主图第1张决定点击率；详情页前3屏决定转化率",
        "listing_fields": ["标题(60字)", "主图(5张)", "价格", "库存", "类目属性", "详情页", "SKU"],
        "price_tier": "mid",
        "hot_categories": ["数码配件", "家居好物", "穿搭时尚", "美食零食", "美妆护肤"],
    },
    "jd": {
        "name": "京东",
        "title_max": 45,
        "main_images": 8,
        "content_style": "spec_param",
        "commission_rate": 0.006,
        "currency": "CNY",
        "keywords_position": "title+属性",
        "tips": "京东用户看重品质和正品保障；标题简洁+规格参数完善；详情页突出品牌背书和质量证明",
        "listing_fields": ["标题(45字)", "主图(8张)", "价格", "规格参数", "商品详情", "售后说明"],
        "price_tier": "premium",
        "hot_categories": ["3C数码", "家用电器", "品质生鲜", "办公文具", "母婴用品"],
    },
    "pinduoduo": {
        "name": "拼多多",
        "title_max": 30,
        "main_images": 10,
        "content_style": "concise_price",
        "commission_rate": 0.006,
        "currency": "CNY",
        "keywords_position": "title",
        "tips": "价格是第一竞争力；标题精简突出性价比；主图突出价格和数量优势；团购描述引导拼单",
        "listing_fields": ["标题(30字)", "主图(10张)", "拼团价", "单独价", "库存", "商品描述"],
        "price_tier": "budget",
        "hot_categories": ["日用杂货", "食品饮料", "服装鞋帽", "家居装饰", "农副产品"],
    },
    "douyin": {
        "name": "抖音小店",
        "title_max": 30,
        "main_images": 5,
        "content_style": "video_script",
        "commission_rate": 0.01,
        "currency": "CNY",
        "keywords_position": "标题+话题",
        "tips": "短视频是核心引流方式；标题口语化+话题标签；商品描述配合视频节奏；直播话术准备",
        "listing_fields": ["标题(30字)", "主图(5张)", "价格", "短视频脚本", "话题标签", "商品描述"],
        "price_tier": "impulse",
        "hot_categories": ["美妆个护", "食品饮料", "服饰箱包", "家居好物", "数码3C"],
    },
    "xiaohongshu": {
        "name": "小红书",
        "title_max": 20,
        "main_images": 9,
        "content_style": "note_style",
        "commission_rate": 0.0,
        "currency": "CNY",
        "keywords_position": "标题+正文+标签",
        "tips": "笔记体内容，口语化+真实体验感；封面图决定点击率；前3行决定阅读完成率；标签5-10个",
        "listing_fields": ["标题(20字)", "封面图", "正文(笔记体)", "标签(5-10个)", "图片(9张)", "关联商品"],
        "price_tier": "aesthetic",
        "hot_categories": ["美妆护肤", "穿搭时尚", "美食探店", "家居好物", "旅行攻略"],
    },
    "xianyu": {
        "name": "闲鱼",
        "title_max": 30,
        "main_images": 9,
        "content_style": "casual",
        "commission_rate": 0.0,
        "currency": "CNY",
        "keywords_position": "标题+描述",
        "tips": "文案要像个人卖家，不要太商业；标题加[全新]/[正品]等标签；描述突出转手原因和成色",
        "listing_fields": ["标题(30字)", "图片(9张)", "价格", "描述(口语化)", "分类", "发货方式"],
        "price_tier": "secondhand",
        "hot_categories": ["数码产品", "二手书籍", "服饰鞋包", "兴趣爱好", "家居闲置"],
    },
}


# ==================== API 平台适配器 ====================

class PlatformAdapter(ABC):
    def __init__(self, platform):
        self.platform = platform
        self.config = PLATFORM_CONFIG[platform]
        self.token = get_credential(platform)

    def _check_credential(self):
        if not self.token:
            return {
                "error": f"{self.config['name']} 凭证未配置",
                "solution": f"请先配置 {self.config['name']} 的 API Token。"
            }
        return None

    @abstractmethod
    def list_products(self, **kwargs):
        pass

    @abstractmethod
    def get_product(self, product_id):
        pass

    @abstractmethod
    def create_product(self, **kwargs):
        pass

    @abstractmethod
    def update_product(self, product_id, **kwargs):
        pass

    @abstractmethod
    def delete_product(self, product_id):
        pass


class GumroadAdapter(PlatformAdapter):
    def __init__(self):
        super().__init__("gumroad")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def _api(self, method, path, **kwargs):
        url = f"{self.config['base_url']}{path}"
        resp = getattr(requests, method)(url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code >= 400:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            raise Exception(f"HTTP {resp.status_code} [{path}]: {err}")
        data = resp.json()
        if not data.get("success"):
            raise Exception(f"API错误 [{path}]: {json.dumps(data, ensure_ascii=False)}")
        return data

    def _format(self, p):
        tags = p.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        return {
            "id": p.get("id"), "name": p.get("name"),
            "price": p.get("price"), "formatted_price": p.get("formatted_price", ""),
            "short_url": p.get("short_url"), "published": p.get("published", False),
            "sales_count": p.get("sales_count", 0), "views_count": p.get("views_count", 0),
            "description": (p.get("description", "") or "")[:200], "tags": tags,
        }

    def list_products(self, page=1, per_page=10, **kwargs):
        data = self._api("get", "/products", params={"page": page, "per_page": per_page})
        return [self._format(p) for p in data.get("products", [])]

    def get_product(self, product_id):
        data = self._api("get", f"/products/{product_id}")
        p = data.get("product", {})
        tags = p.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        views = max(p.get("views_count", 0), 1)
        return {
            "id": p.get("id"), "name": p.get("name"),
            "price": p.get("price"), "formatted_price": p.get("formatted_price", ""),
            "short_url": p.get("short_url"), "published": p.get("published", False),
            "description": p.get("description", ""), "tags": tags,
            "sales_count": p.get("sales_count", 0), "views_count": p.get("views_count", 0),
            "conversion_rate": f"{p.get('sales_count', 0) / views * 100:.2f}%",
            "covers": [{"url": c.get("url")} for c in p.get("covers", [])],
            "custom_receipt": p.get("custom_receipt", ""),
            "category": p.get("category", ""),
        }

    def create_product(self, name, price, description="", tags=None, **kwargs):
        body = {
            "name": name, "price": price, "description": description,
            "custom_receipt": kwargs.get("custom_receipt", f"Thank you for purchasing {name}!"),
            "category": kwargs.get("category", "other"),
        }
        if tags and isinstance(tags, list):
            for i, tag in enumerate(tags):
                body[f"tags[{i}]"] = tag
        data = self._api("post", "/products", data=body)
        product = data.get("product", {})
        return {
            "id": product.get("id"), "name": product.get("name"),
            "short_url": product.get("short_url"),
            "edit_url": f"https://app.gumroad.com/products/{product.get('id')}/edit",
            "message": "产品已创建！请在网页端上传产品文件"
        }

    def update_product(self, product_id, name=None, price=None, description=None,
                       tags=None, published=None, **kwargs):
        body = {}
        if name is not None: body["name"] = name
        if price is not None: body["price"] = price
        if description is not None: body["description"] = description
        if published is not None: body["published"] = published
        if kwargs.get("custom_receipt"): body["custom_receipt"] = kwargs["custom_receipt"]
        if tags is not None and isinstance(tags, list):
            for i, tag in enumerate(tags):
                body[f"tags[{i}]"] = tag
        data = self._api("put", f"/products/{product_id}", data=body)
        p = data.get("product", {})
        return {"id": p.get("id"), "name": p.get("name"), "tags": p.get("tags", []),
                "published": p.get("published"), "message": "更新成功"}

    def delete_product(self, product_id):
        self._api("delete", f"/products/{product_id}")
        return {"status": "deleted", "product_id": product_id}

    def list_messages(self, page=1, per_page=20):
        data = self._api("get", "/messages", params={"page": page, "per_page": per_page})
        return [{"id": m.get("id"), "sender": m.get("sender_name"),
                 "content": m.get("message", ""), "replied": m.get("is_replied", False)}
                for m in data.get("messages", [])]

    def reply_message(self, message_id, content):
        self._api("post", f"/messages/{message_id}/reply", data={"message": content})
        return {"status": "sent", "message_id": message_id}

    def list_sales(self, page=1, per_page=50, **kwargs):
        data = self._api("get", "/sales", params={"page": page, "per_page": per_page})
        return [{"id": s.get("id"), "product": s.get("product_name"),
                 "price": s.get("price"), "refunded": s.get("refunded", False),
                 "email": s.get("email", ""), "created_at": s.get("created_at")}
                for s in data.get("sales", [])]

    def list_offers(self, product_id):
        data = self._api("get", f"/products/{product_id}/offer_codes")
        return data.get("offer_codes", [])

    def seo_audit(self, product_id):
        p = self.get_product(product_id)
        issues, suggestions = [], []
        score = 100
        name = p.get("name", "")
        desc = p.get("description", "")
        tags = p.get("tags", [])
        clean_desc = re.sub(r'<[^>]+>', '', desc)

        if len(name) < 20: issues.append(f"标题过短({len(name)}字符)"); score -= 15
        if len(name) > 80: issues.append(f"标题过长({len(name)}字符)"); score -= 5
        device_kw = ["iphone", "android", "ipad", "phone", "tablet", "desktop"]
        if not any(kw in name.lower() for kw in device_kw): suggestions.append("标题缺少设备关键词"); score -= 10
        spec_kw = ["4k", "8k", "hd", "uhd", "retina", "lossless"]
        if not any(kw in name.lower() for kw in spec_kw): suggestions.append("标题缺少规格关键词"); score -= 10
        if len(clean_desc) < 100: issues.append(f"描述过短(约{len(clean_desc)}字符)"); score -= 15
        if not tags: issues.append("未设置标签"); score -= 20
        elif len(tags) < 5: issues.append(f"标签仅{len(tags)}个"); score -= 10
        if not p.get("covers"): issues.append("未设置封面图"); score -= 15

        return {
            "product_name": p["name"], "product_id": product_id,
            "seo_score": max(0, score),
            "grade": "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D",
            "issues": issues, "suggestions": suggestions,
        }

    def revenue_report(self, days=30):
        """生成收入报告"""
        sales = self.list_sales(per_page=100)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [s for s in sales if s.get("created_at", "") >= cutoff and not s.get("refunded")]

        total_revenue = sum(s.get("price", 0) for s in recent) / 100
        total_sales = len(recent)
        gumroad_fee = total_revenue * self.config["commission_rate"]
        net_revenue = total_revenue - gumroad_fee

        # 按产品分组
        by_product = {}
        for s in recent:
            pname = s.get("product", "Unknown")
            if pname not in by_product:
                by_product[pname] = {"count": 0, "revenue": 0}
            by_product[pname]["count"] += 1
            by_product[pname]["revenue"] += s.get("price", 0) / 100

        # 按日分组（最近7天趋势）
        daily = {}
        for s in recent:
            day = s.get("created_at", "")[:10]
            daily[day] = daily.get(day, 0) + s.get("price", 0) / 100

        return {
            "period": f"最近{days}天",
            "total_sales": total_sales,
            "gross_revenue": round(total_revenue, 2),
            "gumroad_fee": round(gumroad_fee, 2),
            "net_revenue": round(net_revenue, 2),
            "avg_order_value": round(total_revenue / max(total_sales, 1), 2),
            "by_product": by_product,
            "daily_trend": dict(sorted(daily.items())[-7:]),
            "currency": "USD",
        }

    def batch_update_tags(self, product_ids, tags):
        """批量更新标签"""
        results = []
        for pid in product_ids:
            try:
                r = self.update_product(pid, tags=tags)
                results.append({"product_id": pid, "status": "success", "tags": r.get("tags", [])})
            except Exception as e:
                results.append({"product_id": pid, "status": "error", "error": str(e)})
        return results


class ShopifyAdapter(PlatformAdapter):
    def __init__(self):
        super().__init__("shopify")
        self.shop_name = os.getenv(SHOP_NAME_ENV, "")

    def _headers(self):
        return {"X-Shopify-Access-Token": self.token, "Content-Type": "application/json"}

    def _base_url(self):
        if not self.shop_name:
            raise ValueError("Shopify 店铺名未配置")
        return f"https://{self.shop_name}.myshopify.com/admin/api/2024-01"

    def _api(self, method, path, **kwargs):
        url = f"{self._base_url()}{path}"
        resp = getattr(requests, method)(url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise Exception(f"Shopify API [{resp.status_code}]: {resp.text[:500]}")
        return resp.json()

    def list_products(self, limit=10, **kwargs):
        data = self._api("get", "/products.json", params={"limit": limit})
        return [{
            "id": p.get("id"), "name": p.get("title"),
            "price": p.get("variants", [{}])[0].get("price", "0"),
            "published": p.get("status") == "active",
            "tags": p.get("tags", "").split(", ") if p.get("tags") else [],
            "handle": p.get("handle"),
        } for p in data.get("products", [])]

    def get_product(self, product_id):
        data = self._api("get", f"/products/{product_id}.json")
        p = data.get("product", {})
        return {
            "id": p.get("id"), "name": p.get("title"),
            "price": p.get("variants", [{}])[0].get("price", "0"),
            "published": p.get("status") == "active",
            "tags": p.get("tags", "").split(", ") if p.get("tags") else [],
            "description": p.get("body_html", ""),
            "handle": p.get("handle"),
            "images": [{"url": img.get("src")} for img in p.get("images", [])],
        }

    def create_product(self, name, price, description="", tags=None, **kwargs):
        product_data = {
            "product": {
                "title": name,
                "body_html": description,
                "variants": [{"price": str(price / 100) if self.config["price_unit"] == "cents" else str(price)}],
                "status": "draft",
            }
        }
        if tags:
            product_data["product"]["tags"] = tags if isinstance(tags, str) else ", ".join(tags)
        data = self._api("post", "/products.json", json=product_data)
        p = data.get("product", {})
        return {"id": p.get("id"), "name": p.get("title"), "handle": p.get("handle"), "message": "Shopify 产品已创建"}

    def update_product(self, product_id, name=None, price=None, description=None, tags=None, **kwargs):
        product_data = {"product": {}}
        if name is not None: product_data["product"]["title"] = name
        if description is not None: product_data["product"]["body_html"] = description
        if tags is not None:
            product_data["product"]["tags"] = tags if isinstance(tags, str) else ", ".join(tags)
        data = self._api("put", f"/products/{product_id}.json", json=product_data)
        p = data.get("product", {})
        return {"id": p.get("id"), "name": p.get("title"), "message": "Shopify 产品已更新"}

    def delete_product(self, product_id):
        self._api("delete", f"/products/{product_id}.json")
        return {"status": "deleted", "product_id": product_id}

    def list_orders(self, limit=10, status="any"):
        data = self._api("get", "/orders.json", params={"limit": limit, "status": status})
        orders = data.get("orders", [])
        return [{
            "id": o.get("id"), "order_number": o.get("order_number"),
            "total_price": o.get("total_price"), "currency": o.get("currency"),
            "financial_status": o.get("financial_status"),
            "created_at": o.get("created_at"),
            "items": [{"name": li.get("title"), "qty": li.get("quantity")} for li in o.get("line_items", [])],
        } for o in orders]


class EtsyAdapter(PlatformAdapter):
    def __init__(self):
        super().__init__("etsy")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "x-api-key": self.token,
            "Content-Type": "application/json"
        }

    def _api(self, method, path, **kwargs):
        url = f"{self.config['base_url']}{path}"
        resp = getattr(requests, method)(url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise Exception(f"Etsy API [{resp.status_code}]: {resp.text[:500]}")
        return resp.json()

    def list_products(self, limit=10, **kwargs):
        data = self._api("get", "/application/shops/me/listings", params={"limit": limit})
        return [{
            "id": l.get("listing_id"), "name": l.get("title"),
            "price": l.get("price", {}).get("amount", "0"),
            "published": l.get("state") == "active", "tags": l.get("tags", []),
        } for l in data.get("results", [])]

    def get_product(self, product_id):
        data = self._api("get", f"/application/listings/{product_id}")
        l = data.get("results", [{}])[0] if isinstance(data.get("results"), list) else data
        return {
            "id": l.get("listing_id"), "name": l.get("title"),
            "price": l.get("price", {}).get("amount", "0"),
            "published": l.get("state") == "active",
            "tags": l.get("tags", []), "description": l.get("description", ""),
        }

    def create_product(self, name, price, description="", tags=None, **kwargs):
        listing_data = {
            "quantity": kwargs.get("quantity", 1),
            "title": name[:140],
            "description": description,
            "price": str(price),
            "who_made": "i_did", "when_made": "made_to_order",
        }
        if tags and isinstance(tags, list):
            listing_data["tags"] = tags[:13]
        data = self._api("post", "/application/shops/me/listings", json=listing_data)
        return {"id": data.get("listing_id"), "name": name, "message": "Etsy 产品已创建"}

    def update_product(self, product_id, name=None, price=None, description=None, tags=None, **kwargs):
        listing_data = {}
        if name is not None: listing_data["title"] = name[:140]
        if description is not None: listing_data["description"] = description
        if price is not None: listing_data["price"] = str(price)
        if tags is not None: listing_data["tags"] = tags[:13] if isinstance(tags, list) else tags
        self._api("put", f"/application/listings/{product_id}", json=listing_data)
        return {"id": product_id, "name": name, "message": "Etsy 产品已更新"}

    def delete_product(self, product_id):
        self._api("delete", f"/application/listings/{product_id}")
        return {"status": "deleted", "product_id": product_id}


class AmazonAdapter(PlatformAdapter):
    """Amazon Selling Partner API (SP-API) 适配器

    Amazon SP-API 认证较复杂（OAuth + AWS Signature V4），本适配器采用简化模式：
    - 用户需在外部完成 OAuth 授权，获取 Access Token
    - 通过 AMAZON_API_KEY 环境变量传入 Access Token
    - 通过 AMAZON_MARKETPLACE 环境变量传入 Marketplace ID（默认US）
    - 如需完整 AWS Signature V4 签名，建议使用 amazon-sp-api Python SDK
    """

    def __init__(self):
        super().__init__("amazon")
        self.marketplace_id = os.getenv(AMAZON_MARKETPLACE_ENV, "ATVPDKIKX0DER")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "x-amz-access-token": self.token,
        }

    def _api(self, method, path, **kwargs):
        url = f"{self.config['base_url']}{path}"
        resp = getattr(requests, method)(url, headers=self._headers(), timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise Exception(f"Amazon SP-API [{resp.status_code}]: {resp.text[:500]}")
        data = resp.json()
        if "errors" in data:
            errs = data["errors"]
            raise Exception(f"Amazon API错误: {errs[0].get('message', str(errs))}")
        return data

    def list_products(self, marketplace_ids=None, **kwargs):
        """列出产品（通过 ListCatalogItems 或 GetListingsItem）"""
        mids = marketplace_ids or [self.marketplace_id]
        data = self._api("get", "/listings/2021-08-01/items",
                         params={"marketplaceIds": ",".join(mids)})
        items = data.get("items", [])
        return [{
            "id": i.get("sku"), "name": i.get("title", i.get("sku")),
            "price": i.get("price", {}),
            "published": i.get("status") == "BUYABLE",
            "marketplace": mids[0],
        } for i in items]

    def get_product(self, product_id):
        """获取产品详情"""
        mids = [self.marketplace_id]
        data = self._api("get", f"/listings/2021-08-01/items/{product_id}",
                         params={"marketplaceIds": ",".join(mids)})
        item = data.get("item", data)
        summaries = item.get("summaries", [{}])
        summary = summaries[0] if summaries else {}
        return {
            "id": product_id, "name": summary.get("itemName", product_id),
            "price": summary.get("price", {}),
            "published": item.get("status") == "BUYABLE",
            "marketplace": self.marketplace_id,
            "asin": summary.get("asin", ""),
            "category": summary.get("category", ""),
        }

    def create_product(self, name=None, price=None, description="", tags=None, **kwargs):
        """创建产品 Listing"""
        sku = kwargs.get("sku", f"SKU-{datetime.now().strftime('%Y%m%d%H%M')}")
        listing_data = {
            "sku": sku,
            "productType": kwargs.get("product_type", "PRODUCT"),
            "requirements": "LISTING_OFFER_ONLY",
            "attributes": {
                "item_name": [{"value": name, "language_tag": "en_US"}],
                "item_type": [{"value": kwargs.get("item_type", "wall_art")}],
            },
        }
        if price:
            listing_data["attributes"]["list_price"] = [{
                "value": str(price), "currency": "USD"
            }]
        if description:
            listing_data["attributes"]["product_description"] = [{
                "value": description, "language_tag": "en_US"
            }]
        if tags:
            listing_data["attributes"]["generic_keywords"] = [{
                "value": ", ".join(tags) if isinstance(tags, list) else tags,
                "language_tag": "en_US"
            }]

        body = {"issueLocale": "en_US", "listings": [listing_data]}
        data = self._api("put", f"/listings/2021-08-01/items/{sku}",
                         params={"marketplaceIds": self.marketplace_id}, json=body)
        return {
            "sku": sku, "name": name, "marketplace": self.marketplace_id,
            "message": "Amazon Listing 已创建", "response": data,
        }

    def update_product(self, product_id, name=None, price=None, description=None, tags=None, **kwargs):
        """更新产品（使用 put 完整覆盖模式）"""
        listing_data = {
            "sku": product_id,
            "productType": kwargs.get("product_type", "PRODUCT"),
            "requirements": "LISTING_OFFER_ONLY",
            "attributes": {},
        }
        if name is not None:
            listing_data["attributes"]["item_name"] = [{"value": name, "language_tag": "en_US"}]
        if price is not None:
            listing_data["attributes"]["list_price"] = [{"value": str(price), "currency": "USD"}]
        if description is not None:
            listing_data["attributes"]["product_description"] = [{"value": description, "language_tag": "en_US"}]
        if tags is not None:
            listing_data["attributes"]["generic_keywords"] = [{
                "value": ", ".join(tags) if isinstance(tags, list) else tags, "language_tag": "en_US"
            }]

        body = {"issueLocale": "en_US", "listings": [listing_data]}
        data = self._api("put", f"/listings/2021-08-01/items/{product_id}",
                         params={"marketplaceIds": self.marketplace_id}, json=body)
        return {"sku": product_id, "message": "Amazon 产品已更新", "response": data}

    def delete_product(self, product_id):
        """删除产品"""
        data = self._api("delete", f"/listings/2021-08-01/items/{product_id}",
                         params={"marketplaceIds": self.marketplace_id})
        return {"status": "deleted", "sku": product_id, "response": data}

    def list_orders(self, created_after=None, limit=10):
        """查询订单"""
        from datetime import timezone
        if not created_after:
            created_after = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        data = self._api("get", "/orders/v0/orders",
                         params={"MarketplaceIds": self.marketplace_id,
                                 "CreatedAfter": created_after, "MaxResultsPerPage": limit})
        orders = data.get("Orders", [])
        return [{
            "id": o.get("AmazonOrderId"),
            "status": o.get("OrderStatus"),
            "total": o.get("OrderTotal", {}),
            "items_count": o.get("NumberOfItemsShipped", 0) + o.get("NumberOfItemsUnshipped", 0),
            "created_at": o.get("PurchaseDate"),
        } for o in orders]

    def generate_amazon_listing_content(self, product_info):
        """生成 Amazon 专属 Listing 内容"""
        name = product_info.get("name", "")
        features = product_info.get("features", [])
        keywords = product_info.get("keywords", [])

        result = {
            "platform": "amazon",
            "platform_name": "Amazon",
        }

        brand = product_info.get("brand", "")
        title_parts = [brand, name] if brand else [name]
        if keywords:
            title_parts.extend(keywords[:3])
        if features:
            title_parts.append(features[0] if isinstance(features[0], str) else str(features[0]))
        result["title"] = " ".join(title_parts)[:200]

        bullet_templates = [
            "💎 【品质/规格】{feature} — 强调产品核心品质和技术规格",
            "🎨 【内容/风格】{feature} — 描述内容丰富度和风格多样性",
            "📱 【兼容/适用】{feature} — 明确适用设备和场景",
            "⚡ 【便捷/体验】{feature} — 突出使用便捷性和用户体验",
            "🛡️ 【保障/服务】{feature} — 说明售后保障和客户服务",
        ]
        result["bullet_points"] = []
        for i, tpl in enumerate(bullet_templates):
            feat = features[i] if i < len(features) else "详见产品描述"
            result["bullet_points"].append(tpl.format(feature=feat))

        result["description_template"] = (
            f"<h2>{name}</h2>"
            "<p>Discover our premium collection...</p>"
            "<h3>Why Choose Us?</h3>"
            "<ul><li>Feature 1</li><li>Feature 2</li></ul>"
        )

        backend_kw = keywords[:10] if keywords else []
        result["backend_keywords"] = ", ".join(backend_kw)[:250]
        result["backend_keywords_note"] = "后台关键词不会显示在页面上，但影响搜索排名。≤250字节，用空格或逗号分隔"

        result["product_type_suggestions"] = {
            "壁纸/数字下载": "DIGITAL_ELECTRONIC_SOFTWARE",
            "设计素材": "DOWNLOADABLE_SOFTWARE",
            "实体商品": "PRODUCT",
        }

        return result


class LazadaAdapter(PlatformAdapter):
    """Lazada Open Platform API 适配器

    Lazada API 使用 App Key + App Secret 签名认证：
    - LAZADA_API_KEY: App Secret（用于签名）
    - LAZADA_APP_KEY: App Key
    - 签名方式：HMAC-SHA256
    """

    def __init__(self):
        super().__init__("lazada")
        self.app_key = os.getenv(LAZADA_APP_KEY_ENV, "")

    def _get_base_url(self, region=None):
        if region and region in self.config["regions"]:
            return self.config["regions"][region]
        return self.config["base_url"]

    def _sign(self, params, app_secret):
        """Lazada API 签名：按参数名排序拼接后 HMAC-SHA256"""
        import hashlib as _hashlib
        import hmac as _hmac

        sorted_params = sorted(params.items())
        concat = "".join(f"{k}{v}" for k, v in sorted_params)
        signature = _hmac.new(
            app_secret.encode("utf-8"),
            concat.encode("utf-8"),
            _hashlib.sha256
        ).hexdigest()
        return signature.upper()

    def _api(self, method, action, params=None, region=None, **kwargs):
        if not self.app_key:
            raise ValueError("Lazada App Key 未配置")

        base_url = self._get_base_url(region)
        timestamp = str(int(datetime.now().timestamp() * 1000))

        api_params = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "sign_method": "sha256",
            "action": action,
        }
        if params:
            api_params.update(params)

        api_params["sign"] = self._sign(api_params, self.token)

        url = f"{base_url}/{action}"
        if method == "get":
            resp = requests.get(url, params=api_params, timeout=30, **kwargs)
        else:
            resp = requests.post(url, data=api_params, timeout=30, **kwargs)

        if resp.status_code >= 400:
            raise Exception(f"Lazada API [{resp.status_code}]: {resp.text[:500]}")

        data = resp.json()
        if data.get("code") != "0":
            raise Exception(f"Lazada API错误: {data.get('message', str(data))}")
        return data

    def list_products(self, limit=10, offset=0, **kwargs):
        data = self._api("get", "GetProducts", params={
            "limit": str(limit), "offset": str(offset), "filter": "all"
        })
        products = data.get("data", {}).get("products", [])
        return [{
            "id": p.get("item_id"), "name": p.get("attributes", {}).get("name", ""),
            "price": p.get("skus", [{}])[0].get("price", {}).get("special_price", "0") if p.get("skus") else "0",
            "published": p.get("status") == "Active",
            "sku": p.get("skus", [{}])[0].get("SellerSku", "") if p.get("skus") else "",
        } for p in products]

    def get_product(self, product_id):
        data = self._api("get", "GetProductItem", params={"product_id": str(product_id)})
        item = data.get("data", {})
        return {
            "id": item.get("item_id"), "name": item.get("attributes", {}).get("name", ""),
            "price": item.get("skus", [{}])[0].get("price", {}).get("special_price", "0") if item.get("skus") else "0",
            "published": item.get("status") == "Active",
        }

    def create_product(self, name, price, description="", tags=None, **kwargs):
        result = {
            "platform": "lazada",
            "action": "create_product",
            "payload": {
                "Request": {
                    "Product": {
                        "PrimaryCategory": kwargs.get("category_id", ""),
                        "SPUId": kwargs.get("spu_id", ""),
                        "Attributes": {
                            "name": name,
                            "description": description,
                            "brand": kwargs.get("brand", "No Brand"),
                            "short_description": kwargs.get("short_description", name),
                        },
                        "Skus": {
                            "Sku": [{
                                "SellerSku": kwargs.get("sku", f"SKU-{datetime.now().strftime('%Y%m%d%H%M')}"),
                                "price": str(price),
                                "quantity": str(kwargs.get("quantity", 100)),
                            }]
                        }
                    }
                }
            },
            "message": "Lazada 产品创建数据已生成，需通过 API 提交或 Seller Center 手动创建",
        }
        if tags and isinstance(tags, list):
            result["payload"]["Request"]["Product"]["Attributes"]["keywords"] = ", ".join(tags)
        return result

    def update_product(self, product_id, name=None, price=None, description=None, tags=None, **kwargs):
        attrs = {}
        if name is not None: attrs["name"] = name
        if description is not None: attrs["description"] = description
        if tags is not None: attrs["keywords"] = ", ".join(tags) if isinstance(tags, list) else tags

        result = {
            "platform": "lazada",
            "action": "update_product",
            "product_id": product_id,
            "attributes": attrs,
            "message": "Lazada 产品更新数据已生成",
        }
        if price is not None:
            result["sku_update"] = {"price": str(price)}
        return result

    def delete_product(self, product_id):
        data = self._api("post", "RemoveProduct", params={"product_id": str(product_id)})
        return {"status": "deleted", "product_id": product_id, "response": data}

    def list_orders(self, created_after=None, limit=10, status=None):
        params = {"limit": str(limit), "offset": "0"}
        if created_after:
            params["create_after"] = created_after
        if status:
            params["status"] = status
        data = self._api("get", "GetOrders", params=params)
        orders = data.get("data", {}).get("orders", [])
        return [{
            "id": o.get("order_id"),
            "status": o.get("statuses", []),
            "price": o.get("price", ""),
            "created_at": o.get("created_at"),
        } for o in orders]

    def generate_lazada_listing_content(self, product_info):
        """生成 Lazada 专属 Listing 内容"""
        name = product_info.get("name", "")
        features = product_info.get("features", [])
        keywords = product_info.get("keywords", [])

        result = {
            "platform": "lazada",
            "platform_name": "Lazada",
        }

        title_parts = [name]
        if keywords:
            title_parts = keywords[:3] + title_parts
        result["title"] = " ".join(title_parts)[:255]

        result["description_template"] = (
            f"<h2>{name}</h2>"
            "<p>🔥 Special Offer! Limited Time!</p>"
            "<h3>Product Features:</h3>"
            "<ul>" + "".join(f"<li>{f}</li>" for f in features[:5]) + "</ul>"
            "<p>✅ Fast Delivery ✅ Quality Guarantee ✅ Easy Return</p>"
        )

        result["search_keywords"] = keywords[:20] if keywords else []
        result["brand_suggestion"] = product_info.get("brand", "No Brand")

        result["tips"] = [
            "Lazada 买家对价格敏感，促销标记（🔥/Special Offer）显著提升CTR",
            "主图必须白底，尺寸800×800以上",
            "描述用HTML格式，带促销标签",
            "东南亚6国市场各有定价策略，越南/菲律宾价格敏感度更高",
            "利用 Lazada Flash Sale 和 Voucher 功能提升销量",
        ]

        result["regional_pricing"] = {
            "TH": {"currency": "THB", "multiplier": 35, "tips": "泰国是Lazada最大市场，竞争激烈"},
            "VN": {"currency": "VND", "multiplier": 25000, "tips": "越南价格敏感，走量为主"},
            "PH": {"currency": "PHP", "multiplier": 56, "tips": "菲律宾偏好美式消费，品质+价格平衡"},
            "MY": {"currency": "MYR", "multiplier": 4.7, "tips": "马来西亚消费力较强，可适当溢价"},
            "SG": {"currency": "SGD", "multiplier": 1.35, "tips": "新加坡消费力最高，品质优先"},
            "ID": {"currency": "IDR", "multiplier": 16000, "tips": "印尼市场最大，价格战激烈"},
        }

        return result


class TemuAdapter(PlatformAdapter):
    """Temu Partner Platform API 适配器

    Temu 使用 app_key + access_token + HMAC-SHA256 签名认证：
    - TEMU_API_KEY: App Secret（用于签名）
    - TEMU_APP_KEY: App Key
    - API入口: https://openapi-b-global.temu.com/openapi/router
    """

    def __init__(self):
        super().__init__("temu")
        self.app_key = os.getenv(TEMU_APP_KEY_ENV, "")

    def _get_base_url(self, region=None):
        if region and region in self.config["regions"]:
            return self.config["regions"][region]
        return self.config["base_url"]

    def _sign(self, params, app_secret):
        """Temu API 签名：按参数名排序拼接后 HMAC-SHA256"""
        import hashlib as _hashlib
        import hmac as _hmac

        sorted_params = sorted(params.items())
        concat = "".join(f"{k}{v}" for k, v in sorted_params)
        signature = _hmac.new(
            app_secret.encode("utf-8"),
            concat.encode("utf-8"),
            _hashlib.sha256
        ).hexdigest()
        return signature.upper()

    def _api(self, method, api_type, params=None, region=None, **kwargs):
        if not self.app_key:
            raise ValueError("Temu App Key 未配置")
        if not self.token:
            raise ValueError("Temu Access Token 未配置")

        base_url = self._get_base_url(region)
        timestamp = str(int(datetime.now().timestamp()))

        api_params = {
            "app_key": self.app_key,
            "access_token": self.token,
            "timestamp": timestamp,
            "type": api_type,
            "data_type": "JSON",
        }
        if params:
            api_params.update(params)

        api_params["sign"] = self._sign(api_params, self.token)

        url = base_url
        if method == "get":
            resp = requests.get(url, params=api_params, timeout=30, **kwargs)
        else:
            resp = requests.post(url, json=api_params, timeout=30, **kwargs)

        if resp.status_code >= 400:
            raise Exception(f"Temu API [{resp.status_code}]: {resp.text[:500]}")

        data = resp.json()
        if not data.get("success", False):
            err_msg = data.get("errorMsg", data.get("error_msg", str(data)))
            raise Exception(f"Temu API错误: {err_msg}")
        return data

    def list_products(self, limit=10, page=1, **kwargs):
        data = self._api("post", "bg.goods.list.get", params={
            "page": str(page), "page_size": str(limit),
        })
        result = data.get("result", {})
        products = result.get("goods_list", [])
        return [{
            "id": p.get("goods_id"), "name": p.get("goods_name", ""),
            "price": p.get("sku_price", "0"),
            "published": p.get("status") == 1,
            "sku_count": p.get("sku_count", 0),
            "category_id": p.get("cat_id", ""),
        } for p in products]

    def get_product(self, product_id):
        data = self._api("post", "bg.goods.detail.get", params={
            "goods_id": str(product_id),
        })
        result = data.get("result", {})
        goods = result.get("goods", result)
        return {
            "id": goods.get("goods_id"), "name": goods.get("goods_name", ""),
            "price": goods.get("sku_price", "0"),
            "published": goods.get("status") == 1,
            "category_id": goods.get("cat_id", ""),
            "description": goods.get("goods_desc", ""),
            "skus": goods.get("sku_list", []),
        }

    def create_product(self, name, price, description="", tags=None, **kwargs):
        result = {
            "platform": "temu",
            "action": "create_product",
            "api_type": "bg.goods.add",
            "payload": {
                "goods_name": name[:128],
                "goods_desc": description,
                "cat_id": kwargs.get("category_id", ""),
                "goods_attribute_list": [],
                "sku_list": [{
                    "sku_price": str(price),
                    "sku_stock": str(kwargs.get("quantity", 100)),
                    "barcode": kwargs.get("barcode", ""),
                }],
            },
            "message": "Temu 产品创建数据已生成。建议通过 Seller Center 或完整 API 提交",
        }
        if tags and isinstance(tags, list):
            result["payload"]["search_keywords"] = ", ".join(tags)
        return result

    def update_product(self, product_id, name=None, price=None, description=None, tags=None, **kwargs):
        payload = {"goods_id": str(product_id)}
        if name is not None: payload["goods_name"] = name[:128]
        if description is not None: payload["goods_desc"] = description
        if tags is not None: payload["search_keywords"] = ", ".join(tags) if isinstance(tags, list) else tags
        if price is not None:
            payload["sku_update_list"] = [{"sku_price": str(price)}]

        return {
            "platform": "temu",
            "action": "update_product",
            "api_type": "bg.goods.update",
            "product_id": product_id,
            "payload": payload,
            "message": "Temu 产品更新数据已生成",
        }

    def delete_product(self, product_id):
        data = self._api("post", "bg.goods.off", params={"goods_id": str(product_id)})
        return {"status": "delisted", "product_id": product_id, "response": data}

    def list_orders(self, created_after=None, limit=10, **kwargs):
        params = {"page": "1", "page_size": str(limit)}
        if created_after:
            params["start_time"] = created_after
        data = self._api("post", "bg.order.list.get", params=params)
        orders = data.get("result", {}).get("order_list", [])
        return [{
            "id": o.get("order_sn"),
            "status": o.get("order_status", ""),
            "price": o.get("order_amount", ""),
            "currency": "USD",
            "items_count": o.get("item_count", 0),
            "created_at": o.get("create_time", ""),
        } for o in orders]

    def generate_temu_listing_content(self, product_info):
        """生成 Temu 专属 Listing 内容"""
        name = product_info.get("name", "")
        features = product_info.get("features", [])
        keywords = product_info.get("keywords", [])

        result = {
            "platform": "temu",
            "platform_name": "Temu",
        }

        title_parts = [name]
        if keywords:
            title_parts = [keywords[0]] + title_parts
        if features:
            title_parts.append(features[0] if isinstance(features[0], str) else str(features[0]))
        result["title"] = " ".join(title_parts)[:128]

        result["description_template"] = (
            f"<p><strong>{name}</strong></p>"
            "<ul>" + "".join(f"<li>{f}</li>" for f in features[:5]) + "</ul>"
            "<p>✅ Instant Download ✅ High Quality ✅ Multiple Formats</p>"
        )

        result["search_keywords"] = keywords[:20] if keywords else []

        result["tips"] = [
            "Temu 平台自动翻译标题和描述，只需提交英文版本",
            "主图必须白底800×800以上，不能有水印和文字",
            "Temu 卖家无佣金，但定价需符合平台'极致性价比'调性",
            "SKU至少2个变体（不同规格/数量），提高客单价",
            "利用 Temu 的满减和推荐奖励机制提升销量",
            "发货时效要求严格（48小时内），注意库存管理",
        ]

        result["regional_pricing"] = {
            "US": {"currency": "USD", "multiplier": 1.0, "tips": "美国是主战场，走量为主"},
            "EU": {"currency": "EUR", "multiplier": 0.92, "tips": "欧洲多国，注意VAT和合规"},
            "UK": {"currency": "GBP", "multiplier": 0.79, "tips": "英国脱欧后独立清关，注意物流"},
            "AU": {"currency": "AUD", "multiplier": 1.55, "tips": "澳洲市场小但消费力强"},
        }

        return result


class AliexpressAdapter(PlatformAdapter):
    """AliExpress(速卖通) Open Platform API 适配器

    速卖通使用淘宝开放平台(TOP) API 体系：
    - ALIEXPRESS_API_KEY: App Secret（用于签名）
    - ALIEXPRESS_APP_KEY: App Key
    - 签名方式：HMAC-MD5 或 MD5
    """

    def __init__(self):
        super().__init__("aliexpress")
        self.app_key = os.getenv(ALIEXPRESS_APP_KEY_ENV, "")

    def _get_base_url(self, region=None):
        if region and region in self.config["regions"]:
            return self.config["regions"][region]
        return self.config["base_url"]

    def _sign(self, params, app_secret):
        """速卖通 TOP 签名：HMAC-MD5"""
        import hashlib as _hashlib
        import hmac as _hmac

        sorted_params = sorted(params.items())
        concat = "".join(f"{k}{v}" for k, v in sorted_params)
        signature = _hmac.new(
            app_secret.encode("utf-8"),
            concat.encode("utf-8"),
            _hashlib.md5
        ).hexdigest()
        return signature.upper()

    def _api(self, method, api_method, params=None, region=None, **kwargs):
        if not self.app_key:
            raise ValueError("AliExpress App Key 未配置")
        if not self.token:
            raise ValueError("AliExpress Session Token 未配置")

        base_url = self._get_base_url(region)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        api_params = {
            "method": api_method,
            "app_key": self.app_key,
            "session": self.token,
            "timestamp": timestamp,
            "format": "json",
            "v": "2.0",
            "sign_method": "hmac",
        }
        if params:
            api_params.update(params)

        api_params["sign"] = self._sign(api_params, self.token)

        url = base_url
        if method == "get":
            resp = requests.get(url, params=api_params, timeout=30, **kwargs)
        else:
            resp = requests.post(url, data=api_params, timeout=30, **kwargs)

        if resp.status_code >= 400:
            raise Exception(f"AliExpress API [{resp.status_code}]: {resp.text[:500]}")

        data = resp.json()
        if "error_response" in data:
            err = data["error_response"]
            raise Exception(f"AliExpress API错误: code={err.get('code')}, msg={err.get('sub_msg', err.get('msg', ''))}")
        return data

    def list_products(self, limit=10, page=1, **kwargs):
        data = self._api("post", "aliexpress.solution.product.list.get", params={
            "page_no": str(page), "page_size": str(limit),
        })
        resp_key = "aliexpress_solution_product_list_get_response"
        result = data.get(resp_key, {}).get("result", {})
        products = result.get("product_list", [])
        return [{
            "id": p.get("product_id"), "name": p.get("subject", ""),
            "price": p.get("price", {}).get("min_price", "0") if isinstance(p.get("price"), dict) else p.get("price", "0"),
            "published": p.get("product_status_type") == "onSelling",
            "sku_count": len(p.get("sku_list", [])),
        } for p in products]

    def get_product(self, product_id):
        data = self._api("post", "aliexpress.solution.product.info.get", params={
            "product_id": str(product_id),
        })
        resp_key = "aliexpress_solution_product_info_get_response"
        result = data.get(resp_key, {}).get("result", {})
        product = result.get("product", result)
        return {
            "id": product.get("product_id"), "name": product.get("subject", ""),
            "price": product.get("price", {}),
            "published": product.get("product_status_type") == "onSelling",
            "description": product.get("description", ""),
            "category_id": product.get("category_id", ""),
        }

    def create_product(self, name, price, description="", tags=None, **kwargs):
        result = {
            "platform": "aliexpress",
            "action": "create_product",
            "api_method": "aliexpress.solution.product.post",
            "payload": {
                "subject": name[:218],
                "description": description,
                "category_id": kwargs.get("category_id", ""),
                "attribute_list": [],
                "sku_info_list": [{
                    "price": str(price),
                    "inventory": str(kwargs.get("quantity", 100)),
                    "sku_code": kwargs.get("sku_code", f"SKU-{datetime.now().strftime('%Y%m%d%H%M')}"),
                }],
            },
            "message": "AliExpress 产品创建数据已生成。需通过完整 API 提交或 Seller Center 上架",
        }
        if tags and isinstance(tags, list):
            result["payload"]["keywords"] = tags
        return result

    def update_product(self, product_id, name=None, price=None, description=None, tags=None, **kwargs):
        payload = {"product_id": str(product_id)}
        if name is not None: payload["subject"] = name[:218]
        if description is not None: payload["description"] = description
        if tags is not None: payload["keywords"] = tags if isinstance(tags, list) else tags.split(",")
        if price is not None:
            payload["sku_update"] = {"price": str(price)}

        return {
            "platform": "aliexpress",
            "action": "update_product",
            "api_method": "aliexpress.solution.product.edit",
            "product_id": product_id,
            "payload": payload,
            "message": "AliExpress 产品更新数据已生成",
        }

    def delete_product(self, product_id):
        data = self._api("post", "aliexpress.solution.product.offline", params={
            "product_id": str(product_id),
        })
        return {"status": "delisted", "product_id": product_id, "response": data}

    def list_orders(self, created_after=None, limit=10, **kwargs):
        params = {"page_no": "1", "page_size": str(limit)}
        if created_after:
            params["create_date_start"] = created_after
        data = self._api("post", "aliexpress.solution.order.list.get", params=params)
        resp_key = "aliexpress_solution_order_list_get_response"
        result = data.get(resp_key, {}).get("result", {})
        orders = result.get("order_list", [])
        return [{
            "id": o.get("order_id"),
            "status": o.get("order_status", ""),
            "amount": o.get("order_amount", {}).get("amount", "0") if isinstance(o.get("order_amount"), dict) else o.get("order_amount", "0"),
            "currency": o.get("order_amount", {}).get("currency_code", "USD") if isinstance(o.get("order_amount"), dict) else "USD",
            "items_count": o.get("product_count", 0),
            "created_at": o.get("gmt_create", ""),
        } for o in orders]

    def generate_aliexpress_listing_content(self, product_info):
        """生成 AliExpress 专属 Listing 内容"""
        name = product_info.get("name", "")
        features = product_info.get("features", [])
        keywords = product_info.get("keywords", [])

        result = {
            "platform": "aliexpress",
            "platform_name": "AliExpress(速卖通)",
        }

        title_parts = []
        if keywords:
            title_parts.extend(keywords[:5])
        title_parts.append(name)
        if features:
            title_parts.extend([f for f in features[:3] if isinstance(f, str)])
        result["title"] = " ".join(title_parts)[:218]

        result["description_template"] = (
            f"<h2>{name}</h2>"
            "<p>🌍 Worldwide Shipping | 📦 Fast Delivery | ✅ Quality Guarantee</p>"
            "<h3>Product Features:</h3>"
            "<ul>" + "".join(f"<li>{f}</li>" for f in features[:5]) + "</ul>"
            "<h3>Specifications:</h3>"
            "<p>Format: Digital Download | Resolution: High Quality | Instant Access</p>"
            "<h3>Why Choose Us:</h3>"
            "<p>✅ Professional Quality ✅ Instant Download ✅ 24/7 Support ✅ Money Back Guarantee</p>"
        )

        result["search_keywords"] = keywords[:20] if keywords else []

        result["tips"] = [
            "速卖通标题SEO权重最高，关键词越密集越好（218字符上限）",
            "主图800×800以上，白底最佳，可加促销标签",
            "描述支持HTML，利用<h2>/<ul>等标签提升可读性",
            "设置多SKU（不同数量/规格）提高客单价",
            "利用 AliExpress Plus（7日达）和 Free Shipping 标签提升转化率",
            "200+国家市场，注意合规和物流时效",
            "客服响应时效要求高（24小时内回复），准备多语言模板",
        ]

        result["regional_pricing"] = {
            "US": {"currency": "USD", "multiplier": 1.0, "tips": "美国是最大市场，竞争激烈"},
            "EU": {"currency": "EUR", "multiplier": 0.92, "tips": "欧洲注意VAT，德国/法国/西班牙是重点"},
            "RU": {"currency": "RUB", "multiplier": 92, "tips": "俄罗斯是速卖通最大市场之一，价格敏感"},
            "BR": {"currency": "BRL", "multiplier": 5.0, "tips": "巴西增长快，但物流慢，注意清关"},
            "SA": {"currency": "SAR", "multiplier": 3.75, "tips": "中东消费力强，利润空间大"},
        }

        return result


# ==================== 智能内容引擎 ====================

def generate_smart_content(platform, product_info):
    """为国内平台生成智能适配内容"""
    config = CHINESE_PLATFORMS.get(platform)
    if not config:
        return {"error": f"不支持的国内平台: {platform}", "supported": list(CHINESE_PLATFORMS.keys())}

    name = product_info.get("name", "")
    product_type = product_info.get("type", "")
    features = product_info.get("features", [])
    price = product_info.get("price", "")
    keywords = product_info.get("keywords", [])
    style = config["content_style"]
    title_max = config["title_max"]

    result = {
        "platform": platform,
        "platform_name": config["name"],
        "content_style": style,
        "tips": config["tips"],
        "currency": config["currency"],
    }

    if style == "seo_title":
        core_kw = keywords[0] if keywords else product_type
        sub_kw = " ".join(keywords[1:3]) if len(keywords) > 1 else ""
        result["title"] = f"{core_kw}{name} {sub_kw} 高清无损 适用多设备"[:title_max]
        result["description_structure"] = [
            "【产品亮点】核心卖点3条（规格+数量+品质）",
            "【适用场景】使用场景描述（锁屏/聊天背景/社交头像）",
            "【规格详情】分辨率、格式、数量、设备兼容性",
            "【售后保障】退款政策、更新说明",
        ]
        result["main_image_suggestions"] = [
            "图1：最吸引眼球的壁纸+大字标题（决定点击率）",
            "图2：壁纸风格拼图（展示多样性）",
            "图3：手机实拍效果图（真实感）",
            "图4：对比图（4K vs 普通）",
            "图5：数量展示（100+张缩略图）",
        ]

    elif style == "spec_param":
        result["title"] = f"{name} {product_type} {' '.join(features[:2])} 通用"[:title_max]
        result["description_structure"] = [
            "【品牌信息】品质承诺、正品保障",
            "【规格参数】分辨率、格式、兼容设备详细列表",
            "【产品特色】技术亮点（4K/8K/无损等）",
            "【使用说明】安装步骤、兼容性说明",
            "【售后政策】7天无理由、技术支持",
        ]
        result["spec_params"] = {
            "分辨率": product_info.get("resolution", "4K (3840×2160)"),
            "格式": product_info.get("format", "PNG/JPG"),
            "数量": product_info.get("count", ""),
            "兼容": "iPhone/Android/iPad/桌面",
        }

    elif style == "concise_price":
        count = product_info.get("count", "XX")
        result["title"] = f"{name} {count}张 秒发"[:title_max]
        result["description_structure"] = [
            "数量优势：XX张壁纸只要X元",
            "品质保证：4K高清原图",
            "自动发货：拍下即送",
        ]
        result["pricing_strategy"] = "最低价SKU引流+套餐组合提利润"

    elif style == "video_script":
        result["title"] = f"壁纸太绝了！{name} #壁纸推荐"[:title_max]
        result["description_structure"] = [
            "商品描述：配合视频节奏，突出视觉冲击",
            "话题标签：3-5个热门话题",
        ]
        result["video_script"] = {
            "0-3秒": {"画面": "壁纸快速切换+动感BGM", "文案": "家人们看这个壁纸！"},
            "3-8秒": {"画面": "展示不同风格壁纸", "文案": f"{'/'.join(features[:3])}全都有"},
            "8-12秒": {"画面": "手指点击购物车", "文案": "点击下方链接"},
            "12-15秒": {"画面": "数量+价格展示", "文案": f"{product_info.get('count', '100')}+张只要X元"},
        }
        result["live_script"] = {
            "开场": "家人们！今天给大家分享一组绝美壁纸",
            "展示": "边滑壁纸边讲解风格",
            "卖点": "4K超清、一键设置、XX种风格",
            "促单": "现在下单立减/限时优惠",
        }
        result["hashtag_suggestions"] = ["#壁纸推荐", "#手机壁纸", "#4K壁纸", "#桌面美化", "#高清壁纸"]

    elif style == "note_style":
        result["title"] = f"壁纸控必入！{name}太绝了"[:title_max]
        result["description_structure"] = [
            "口语化开头（姐妹们/家人们+情绪词）",
            "产品体验描述（用了感觉/对比之前）",
            "细节展示（数量/风格/清晰度）",
            "购买引导（自然植入，不强推）",
        ]
        result["note_template"] = {
            "opening": "姐妹们！终于找到满意的壁纸了😭",
            "body": [
                f"📱 一共{product_info.get('count', 'XX')}张4K超清壁纸",
                f"🎨 {'/'.join(features[:3])}全都有",
                "💡 一键设置超级方便",
            ],
            "tags": ["壁纸推荐", "手机壁纸", "4K壁纸", "壁纸分享", "高清壁纸"],
            "cover_style": "最美单张壁纸+手写体标题",
        }

    elif style == "casual":
        result["title"] = f"[全新] {name} {product_type} 秒发"[:title_max]
        result["description_structure"] = [
            "转手原因（个人整理/朋友推荐/自己用的）",
            "产品描述（品质+数量+格式）",
            "成色说明（全新/高清/无损）",
            "交易说明（秒发/不议价）",
        ]
        result["desc_template"] = (
            f"闲置转让~\n{name}壁纸合集，{features[0] if features else '品质超好'}\n"
            "买来自己用的，整理了一份合集分享给大家\n"
            "高清原图，不是那种压缩过的模糊图！\n需要直接拍，秒发~"
        )

    return result


def generate_multiplatform_content(product_info, platforms=None):
    """一次生成多平台适配内容"""
    if platforms is None:
        platforms = list(CHINESE_PLATFORMS.keys())
    results = {}
    for p in platforms:
        if p in CHINESE_PLATFORMS:
            results[p] = generate_smart_content(p, product_info)
    return results


# ==================== 动态定价引擎 ====================

USD_CNY_RATE = 7.2

PRICE_TIERS = {
    "gumroad": {"multiplier": 1.0, "currency": "USD", "min": 0.99, "sweet_spot": (2.99, 9.99)},
    "shopify": {"multiplier": 1.0, "currency": "USD", "min": 0.99, "sweet_spot": (4.99, 19.99)},
    "etsy": {"multiplier": 1.15, "currency": "USD", "min": 1.99, "sweet_spot": (3.99, 14.99)},
    "taobao": {"multiplier": 0.35, "currency": "CNY", "min": 1.0, "sweet_spot": (5.0, 30.0)},
    "jd": {"multiplier": 0.45, "currency": "CNY", "min": 5.0, "sweet_spot": (10.0, 50.0)},
    "pinduoduo": {"multiplier": 0.20, "currency": "CNY", "min": 0.5, "sweet_spot": (1.0, 10.0)},
    "douyin": {"multiplier": 0.30, "currency": "CNY", "min": 1.0, "sweet_spot": (5.0, 20.0)},
    "xiaohongshu": {"multiplier": 0.40, "currency": "CNY", "min": 3.0, "sweet_spot": (9.9, 39.9)},
    "xianyu": {"multiplier": 0.25, "currency": "CNY", "min": 1.0, "sweet_spot": (3.0, 15.0)},
    "amazon": {"multiplier": 1.10, "currency": "USD", "min": 0.99, "sweet_spot": (9.99, 29.99)},
    "lazada": {"multiplier": 0.80, "currency": "USD", "min": 0.50, "sweet_spot": (2.99, 12.99)},
    "temu": {"multiplier": 0.70, "currency": "USD", "min": 0.50, "sweet_spot": (1.99, 9.99)},
    "aliexpress": {"multiplier": 0.90, "currency": "USD", "min": 0.99, "sweet_spot": (3.99, 15.99)},
}


def smart_pricing(product_info, platforms=None):
    """动态定价引擎：基于产品信息和平台特性给出定价建议"""
    base_usd = float(product_info.get("price", 0))
    if base_usd <= 0:
        return {"error": "请提供基础价格（USD）"}

    all_platforms = platforms or list(PRICE_TIERS.keys())
    results = {}

    for p in all_platforms:
        tier = PRICE_TIERS.get(p)
        if not tier:
            continue

        if tier["currency"] == "USD":
            suggested = round(base_usd * tier["multiplier"], 2)
        else:
            suggested = round(base_usd * USD_CNY_RATE * tier["multiplier"], 1)

        suggested = max(suggested, tier["min"])

        sweet_low, sweet_high = tier["sweet_spot"]
        in_sweet = sweet_low <= suggested <= sweet_high

        if p in PLATFORM_CONFIG:
            commission_rate = PLATFORM_CONFIG[p].get("commission_rate", 0)
        elif p in CHINESE_PLATFORMS:
            commission_rate = CHINESE_PLATFORMS[p].get("commission_rate", 0)
        else:
            commission_rate = 0

        commission = round(suggested * commission_rate, 2)
        net = round(suggested - commission, 2)

        if tier["currency"] == "USD":
            display_price = f"${math.floor(suggested) + 0.99}"
        else:
            int_part = math.floor(suggested)
            if suggested - int_part < 0.5:
                display_price = f"¥{int_part}.9"
            else:
                display_price = f"¥{int_part + 1}.0"

        results[p] = {
            "suggested_price": suggested,
            "display_price": display_price,
            "currency": tier["currency"],
            "in_sweet_spot": in_sweet,
            "sweet_spot": tier["sweet_spot"],
            "commission_rate": f"{commission_rate * 100:.1f}%",
            "commission": commission,
            "net_revenue": net,
            "pricing_tip": _get_pricing_tip(p, suggested, tier),
        }

    return results


def _get_pricing_tip(platform, price, tier):
    """平台专属定价建议"""
    tips = {
        "gumroad": "数字产品$2.99起测转化率，$5以下冲动购买概率高",
        "shopify": "独立站定价更自由，可做阶梯定价（基础/进阶/豪华）",
        "etsy": "Etsy买家偏品质，可溢价15%定价；数字产品免运费是优势",
        "amazon": "Amazon推荐价$9.99-$29.99，注意Referral Fee 6%-45%按品类；Bullet Points比价格更重要",
        "lazada": "Lazada东南亚市场，$2.99-$12.99走量；Flash Sale期间可降价30%冲排名",
        "temu": "Temu极致性价比调性，$1.99-$9.99走量；无平台佣金但价格要低；多SKU变体提高客单价",
        "aliexpress": "速卖通全球市场，$3.99-$15.99为主；关键词密集标题提升曝光；Free Shipping标签是转化利器",
        "taobao": "壁纸类1-10元走量，9.9元是心理锚点；可做多SKU梯度定价",
        "jd": "京东用户品质付费意愿强，可适当定高，突出品质保障",
        "pinduoduo": "拼多多价格战激烈，1元引流+套餐提客单价",
        "douyin": "抖音是冲动消费场景，5-20元转化率最高",
        "xiaohongshu": "小红书用户愿为颜值付费，9.9-39.9元是舒适区间",
        "xianyu": "闲鱼定价低于新品3-5折，强调性价比",
    }
    return tips.get(platform, "根据市场情况调整")


# ==================== 跨平台分析引擎 ====================

def cross_platform_analyze(product_id=None):
    """跨平台数据分析：从已连接平台拉取数据做对比"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "platforms": {},
        "comparison": {},
    }

    # Gumroad 数据
    if get_credential("gumroad"):
        try:
            adapter = GumroadAdapter()
            products = adapter.list_products(per_page=50)
            total_sales = sum(p.get("sales_count", 0) for p in products)
            total_views = sum(p.get("views_count", 0) for p in products)
            results["platforms"]["gumroad"] = {
                "product_count": len(products),
                "total_sales": total_sales,
                "total_views": total_views,
                "avg_conversion": f"{total_sales / max(total_views, 1) * 100:.2f}%",
                "published": sum(1 for p in products if p.get("published")),
                "unpublished": sum(1 for p in products if not p.get("published")),
            }
            try:
                results["platforms"]["gumroad"]["revenue"] = adapter.revenue_report(days=30)
            except Exception:
                pass
        except Exception as e:
            results["platforms"]["gumroad"] = {"error": str(e)}

    # Shopify 数据
    if get_credential("shopify"):
        try:
            adapter = ShopifyAdapter()
            products = adapter.list_products(limit=50)
            results["platforms"]["shopify"] = {
                "product_count": len(products),
                "published": sum(1 for p in products if p.get("published")),
                "unpublished": sum(1 for p in products if not p.get("published")),
            }
        except Exception as e:
            results["platforms"]["shopify"] = {"error": str(e)}

    # Etsy 数据
    if get_credential("etsy"):
        try:
            adapter = EtsyAdapter()
            products = adapter.list_products(limit=50)
            results["platforms"]["etsy"] = {
                "product_count": len(products),
                "published": sum(1 for p in products if p.get("published")),
            }
        except Exception as e:
            results["platforms"]["etsy"] = {"error": str(e)}

    # 跨平台对比
    connected = [p for p in results["platforms"] if "error" not in results["platforms"][p]]
    if len(connected) >= 2:
        results["comparison"]["connected_platforms"] = connected
        results["comparison"]["total_products"] = sum(
            results["platforms"][p].get("product_count", 0) for p in connected
        )
        results["comparison"]["total_sales"] = sum(
            results["platforms"][p].get("total_sales", 0) for p in connected
        )

    return results


# ==================== 订单统一视图 ====================

def unified_orders(limit=20):
    """从所有已连接平台拉取订单，统一视图"""
    orders = []

    # Gumroad
    if get_credential("gumroad"):
        try:
            adapter = GumroadAdapter()
            sales = adapter.list_sales(per_page=limit)
            for s in sales:
                orders.append({
                    "platform": "Gumroad",
                    "order_id": s.get("id"),
                    "product": s.get("product"),
                    "amount": s.get("price", 0) / 100,
                    "currency": "USD",
                    "refunded": s.get("refunded", False),
                    "customer_email": s.get("email", ""),
                    "created_at": s.get("created_at"),
                })
        except Exception:
            pass

    # Shopify
    if get_credential("shopify"):
        try:
            adapter = ShopifyAdapter()
            shopify_orders = adapter.list_orders(limit=limit)
            for o in shopify_orders:
                orders.append({
                    "platform": "Shopify",
                    "order_id": o.get("id"),
                    "order_number": o.get("order_number"),
                    "product": ", ".join(i["name"] for i in o.get("items", [])),
                    "amount": float(o.get("total_price", 0)),
                    "currency": o.get("currency", "USD"),
                    "financial_status": o.get("financial_status"),
                    "created_at": o.get("created_at"),
                })
        except Exception:
            pass

    # 按时间排序
    orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return orders[:limit]


# ==================== 批量同步引擎 ====================

def batch_sync(product_info, platforms, catalog_id=None):
    """一键同步产品到多个平台

    Args:
        product_info: 产品基础信息
        platforms: 目标平台列表
        catalog_id: 可选，已有目录产品ID
    """
    results = {}
    errors = {}

    if catalog_id:
        existing = catalog_get(catalog_id)
        if existing:
            product_info = {**existing, **product_info}
        else:
            catalog_id = None

    if not catalog_id:
        catalog_id = catalog_add(product_info)

    # 国际平台：API上架
    for p in platforms:
        if p in PLATFORM_CONFIG:
            adapter = get_adapter(p)
            if not adapter:
                errors[p] = "适配器不可用"
                continue
            cred_check = adapter._check_credential()
            if cred_check:
                errors[p] = cred_check["error"]
                continue
            try:
                name = product_info.get("name", "")
                price = product_info.get("price", 0)
                desc = product_info.get("description", "")
                tags = product_info.get("tags", product_info.get("keywords", []))

                result = adapter.create_product(name=name, price=price, description=desc, tags=tags)
                results[p] = result
                catalog_update_platform_status(catalog_id, p, {
                    "status": "created",
                    "platform_id": result.get("id"),
                    "url": result.get("short_url", result.get("handle", "")),
                })
            except Exception as e:
                errors[p] = str(e)

    # 国内平台：生成内容
    chinese_targets = [p for p in platforms if p in CHINESE_PLATFORMS]
    if chinese_targets:
        content = generate_multiplatform_content(product_info, chinese_targets)
        for p, c in content.items():
            results[p] = c
            catalog_update_platform_status(catalog_id, p, {
                "status": "content_generated",
                "content_style": c.get("content_style"),
            })

    # 定价建议
    pricing = smart_pricing(product_info, platforms)

    return {
        "catalog_id": catalog_id,
        "sync_results": results,
        "errors": errors,
        "pricing_suggestions": pricing,
        "summary": f"已同步到 {len(results)} 个平台，{len(errors)} 个平台出错",
    }


# ==================== 关键词热度分析 ====================

def keyword_analysis(product_type, keywords=None):
    """生成关键词分析报告"""
    default_keywords = {
        "壁纸": ["4K壁纸", "手机壁纸", "桌面壁纸", "高清壁纸", "壁纸合集", "动态壁纸", "锁屏壁纸", "风景壁纸", "动漫壁纸"],
        "数字产品": ["数字下载", "Digital Download", "Instant Download", "Printable", "Template"],
        "设计素材": ["Design Asset", "UI Kit", "Icon Pack", "Illustration", "Vector"],
    }

    base_keywords = default_keywords.get(product_type, [product_type])
    if keywords:
        base_keywords = keywords + base_keywords

    return {
        "product_type": product_type,
        "keywords_to_research": base_keywords,
        "research_instructions": {
            "淘宝": f"搜索 {' '.join(base_keywords[:5])}，查看销量TOP10的标题和关键词组合",
            "京东": f"搜索 {' '.join(base_keywords[:3])}，分析商品标题中的参数词和品牌词",
            "拼多多": f"搜索 {' '.join(base_keywords[:3])}，统计低价商品的标题关键词频率",
            "小红书": f"搜索 {' '.join(base_keywords[:5])}，提取笔记标题中的情绪词和标签",
            "Gumroad": f"搜索 {product_type} on Gumroad，分析TOP产品的tag和description关键词",
            "Etsy": f"搜索 {product_type} digital，分析listing标题的SEO关键词布局",
            "Amazon": f"搜索 {product_type} on Amazon，分析Best Seller的标题+Bullet Points+Backend Keywords",
            "Lazada": f"搜索 {product_type} on Lazada，分析东南亚市场的标题关键词和促销标签",
            "Temu": f"搜索 {product_type} on Temu，分析极致性价比产品的标题和主图策略",
            "AliExpress": f"搜索 {product_type} on AliExpress，分析Best Seller的SEO关键词布局和Free Shipping标签",
        },
        "output_format": {
            "keyword": "关键词",
            "platform": "平台",
            "search_volume": "搜索量（高/中/低）",
            "competition": "竞争度（高/中/低）",
            "opportunity_score": "机会分（1-10）",
        },
    }


# ==================== 平台工厂 ====================

def get_adapter(platform):
    """获取平台适配器实例"""
    adapters = {
        "gumroad": GumroadAdapter,
        "shopify": ShopifyAdapter,
        "etsy": EtsyAdapter,
        "amazon": AmazonAdapter,
        "lazada": LazadaAdapter,
        "temu": TemuAdapter,
        "aliexpress": AliexpressAdapter,
    }
    adapter_class = adapters.get(platform)
    if not adapter_class:
        return None
    return adapter_class()


def get_platforms_info():
    """获取所有支持平台的信息"""
    international = []
    for k, v in PLATFORM_CONFIG.items():
        cred = bool(get_credential(k))
        international.append({
            "id": k,
            "name": v["name"],
            "commission_rate": v.get("commission_rate", 0),
            "credential_configured": cred,
        })

    chinese = []
    for k, v in CHINESE_PLATFORMS.items():
        chinese.append({
            "id": k,
            "name": v["name"],
            "title_max": v["title_max"],
            "content_style": v["content_style"],
            "price_tier": v["price_tier"],
        })

    return {
        "international": international,
        "chinese": chinese,
    }
