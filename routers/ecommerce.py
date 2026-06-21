#!/usr/bin/env python3
"""
全平台电商 FastAPI Router
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from core.ecommerce_engine import (
    catalog_list, catalog_add, catalog_get, catalog_update, catalog_remove,
    get_adapter, get_platforms_info,
    generate_multiplatform_content, smart_pricing,
    cross_platform_analyze, unified_orders, batch_sync, keyword_analysis,
)

router = APIRouter()


# ─── Pydantic Models ────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    price: Optional[float] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    variants: Optional[List[Dict[str, Any]]] = None

class ProductUpdate(BaseModel):
    updates: Dict[str, Any]

class PlatformProductCreate(BaseModel):
    platform: str
    product_data: Dict[str, Any]

class PlatformProductUpdate(BaseModel):
    platform: str
    updates: Dict[str, Any]

class MultiContentRequest(BaseModel):
    product_info: Dict[str, Any]
    platforms: List[str]

class SyncRequest(BaseModel):
    product_info: Dict[str, Any]
    target_platforms: List[str]

class MessageReply(BaseModel):
    message: str


# ─── 产品目录 ──────────────────────────────────────────

@router.get("/catalog", summary="产品目录列表")
async def list_catalog():
    """获取集中式产品目录中所有产品"""
    return catalog_list()


@router.post("/catalog", summary="添加产品到目录")
async def add_catalog_product(product: ProductCreate):
    """添加新产品到集中式产品目录"""
    pid = catalog_add(product.model_dump())
    return {"catalog_id": pid, "message": "产品已添加到目录"}


@router.get("/catalog/{product_id}", summary="产品详情")
async def get_catalog_product(product_id: str):
    """获取目录中指定产品的详细信息"""
    result = catalog_get(product_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"产品 {product_id} 不存在")
    return result


@router.put("/catalog/{product_id}", summary="更新产品")
async def update_catalog_product(product_id: str, product: ProductUpdate):
    """更新目录中指定产品的信息"""
    return catalog_update(product_id, product.updates)


@router.delete("/catalog/{product_id}", summary="删除产品")
async def remove_catalog_product(product_id: str):
    """从目录中移除指定产品"""
    return catalog_remove(product_id)


# ─── 平台产品操作 ──────────────────────────────────────

@router.get("/products", summary="平台产品列表")
async def list_platform_products(
    platform: str = Query(..., description="平台名: gumroad/shopify/etsy/amazon/lazada/temu/aliexpress"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """从指定平台获取产品列表。需要平台API凭证。"""
    adapter = get_adapter(platform)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")
    result = adapter.list_products(page=page, per_page=limit)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return {"platform": platform, "products": result, "page": page}


@router.get("/products/{product_id}", summary="平台产品详情")
async def get_platform_product(
    product_id: str,
    platform: str = Query(..., description="平台名"),
):
    """获取指定平台上某个产品的详细信息"""
    adapter = get_adapter(platform)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")
    result = adapter.get_product(product_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.post("/products", summary="创建平台产品")
async def create_platform_product(req: PlatformProductCreate):
    """在指定平台上创建新产品。需要平台API凭证。"""
    adapter = get_adapter(req.platform)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {req.platform}")
    result = adapter.create_product(req.product_data)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.put("/products/{product_id}", summary="更新平台产品")
async def update_platform_product(product_id: str, req: PlatformProductUpdate):
    """更新指定平台上的产品信息"""
    adapter = get_adapter(req.platform)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {req.platform}")
    result = adapter.update_product(product_id, req.updates)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.delete("/products/{product_id}", summary="删除平台产品")
async def delete_platform_product(
    product_id: str,
    platform: str = Query(..., description="平台名"),
):
    """从指定平台删除产品"""
    adapter = get_adapter(platform)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {platform}")
    result = adapter.delete_product(product_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


# ─── 订单和销售 ─────────────────────────────────────────

@router.get("/orders", summary="统一订单视图")
async def list_orders(
    platform: Optional[str] = Query(None, description="按平台过滤"),
    limit: int = Query(20, ge=1, le=100),
):
    """跨平台统一查看订单"""
    return unified_orders(limit=limit)


@router.get("/sales", summary="Gumroad销售数据")
async def get_gumroad_sales(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
):
    """获取Gumroad销售数据报告"""
    adapter = get_adapter("gumroad")
    if not adapter:
        raise HTTPException(status_code=400, detail="Gumroad未配置")
    result = adapter.sales(days=days)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/messages", summary="Gumroad消息列表")
async def get_gumroad_messages():
    """获取Gumroad客户消息列表"""
    adapter = get_adapter("gumroad")
    if not adapter:
        raise HTTPException(status_code=400, detail="Gumroad未配置")
    result = adapter.messages()
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.post("/messages/{message_id}/reply", summary="回复Gumroad消息")
async def reply_gumroad_message(message_id: str, req: MessageReply):
    """回复Gumroad客户消息"""
    adapter = get_adapter("gumroad")
    if not adapter:
        raise HTTPException(status_code=400, detail="Gumroad未配置")
    result = adapter.reply_message(message_id, req.message)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


# ─── 跨平台操作 ─────────────────────────────────────────

@router.post("/multi-content", summary="多平台内容生成")
async def generate_multi_content(req: MultiContentRequest):
    """为多个平台同时生成平台专属的产品listing内容"""
    result = generate_multiplatform_content(req.product_info, req.platforms)
    return result


@router.post("/sync", summary="一键同步全平台")
async def sync_to_platforms(req: SyncRequest):
    """将产品同步发布到多个平台，自动适配各平台格式"""
    result = batch_sync(req.product_info, req.target_platforms)
    return result


@router.get("/analyze", summary="跨平台数据分析")
async def analyze_cross_platform():
    """跨平台数据分析，汇总各平台表现"""
    return cross_platform_analyze()


@router.get("/keywords", summary="关键词热度分析")
async def analyze_keywords(
    keyword_type: str = Query("trending", description="分析类型: trending/seasonal/competitive"),
):
    """分析关键词热度和趋势，用于SEO优化"""
    return keyword_analysis(keyword_type)


@router.get("/platforms", summary="查看支持平台")
async def list_platforms():
    """获取所有支持的电商平台及其配置状态"""
    return get_platforms_info()
