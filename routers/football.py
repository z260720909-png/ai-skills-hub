"""
Football Router — FastAPI 路由
暴露足球分析模块的 REST API 端点，调用 core/football_engine 中的函数。
"""

from fastapi import APIRouter, Query

from core.football_engine import (
    search_leagues,
    search_teams,
    get_fixtures,
    get_standings,
    get_h2h,
    get_prediction,
    full_analysis,
    get_odds,
    get_statistics,
    today_summary,
    resolve_league_id,
)

router = APIRouter(tags=["足球分析"])


# ─── 赛程查询 ─────────────────────────────────────────
@router.get(
    "/fixtures",
    summary="查询赛程",
    description="查询足球赛程/赛果，支持按联赛、日期、球队、赛季等条件筛选",
)
async def fixtures(
    league: str | None = Query(None, description="联赛名或ID（如：英超、39）"),
    date: str | None = Query(None, description="日期，格式 YYYY-MM-DD"),
    team: str | None = Query(None, description="球队名或ID"),
    season: int | None = Query(None, description="赛季年份，如 2024"),
    live: str = Query("no", description="是否查询实时比赛：yes / no"),
    next: int = Query(0, description="查询某球队/联赛最近N场即将开赛的比赛"),
):
    league_id = resolve_league_id(league) if league else None

    team_id = None
    if team:
        try:
            team_id = int(team)
        except ValueError:
            teams_result = search_teams(name=team, league_id=league_id)
            if isinstance(teams_result, list) and teams_result:
                team_id = teams_result[0]["id"]
            else:
                return {"error": f"未找到球队: {team}"}

    return get_fixtures(
        league_id=league_id,
        date=date,
        team_id=team_id,
        season=season,
        live=live,
        next_n=next,
    )


# ─── 积分榜 ─────────────────────────────────────────
@router.get(
    "/standings",
    summary="积分榜",
    description="查询指定联赛的积分榜排名",
)
async def standings(
    league: str = Query(..., description="联赛名或ID（如：英超、39）"),
    season: int | None = Query(None, description="赛季年份，如 2024"),
):
    league_id = resolve_league_id(league)
    if league_id is None:
        return {"error": f"无法解析联赛: {league}"}
    return get_standings(league_id, season)


# ─── 球队搜索 ─────────────────────────────────────────
@router.get(
    "/teams",
    summary="球队搜索",
    description="按名称搜索球队，可限定联赛范围",
)
async def teams(
    name: str | None = Query(None, description="球队名称关键词"),
    league: str | None = Query(None, description="限定联赛名或ID"),
):
    league_id = resolve_league_id(league) if league else None
    return search_teams(name=name, league_id=league_id)


# ─── 联赛搜索 ─────────────────────────────────────────
@router.get(
    "/leagues",
    summary="联赛搜索",
    description="按名称搜索联赛信息",
)
async def leagues(
    name: str | None = Query(None, description="联赛名称关键词"),
):
    return search_leagues(name=name)


# ─── H2H 历史交锋 ─────────────────────────────────────────
@router.get(
    "/h2h",
    summary="历史交锋",
    description="查询两支球队的历史交锋记录与统计",
)
async def h2h(
    team1: int = Query(..., description="主队 ID"),
    team2: int = Query(..., description="客队 ID"),
):
    return get_h2h(team1, team2)


# ─── 比分预测 ─────────────────────────────────────────
@router.get(
    "/prediction",
    summary="比分预测",
    description="获取 API-Football 对指定比赛的预测数据",
)
async def prediction(
    fixture_id: int = Query(..., description="比赛 ID"),
):
    return get_prediction(fixture_id)


# ─── 综合分析 ─────────────────────────────────────────
@router.get(
    "/analysis",
    summary="综合分析",
    description="综合对阵分析：预测 + H2H + 近期战绩 + 半全场 + 大小球 + 赔率",
)
async def analysis(
    fixture_id: int = Query(..., description="比赛 ID"),
):
    return full_analysis(fixture_id)


# ─── 赔率查询 ─────────────────────────────────────────
@router.get(
    "/odds",
    summary="赔率查询",
    description="查询比赛赔率，支持 1X2 / 大小球 / 亚洲让球等盘口",
)
async def odds(
    fixture_id: int | None = Query(None, description="比赛 ID"),
    league: str | None = Query(None, description="联赛名或ID"),
    season: int | None = Query(None, description="赛季年份"),
    bet_type: int = Query(1, description="赔率类型：1=1X2, 5=大小球, 3=亚洲让球"),
):
    league_id = resolve_league_id(league) if league else None
    return get_odds(
        fixture_id=fixture_id,
        league_id=league_id,
        season=season,
        bet=bet_type,
    )


# ─── 比赛统计 ─────────────────────────────────────────
@router.get(
    "/statistics",
    summary="比赛统计",
    description="查询指定比赛的技术统计数据（控球率、射门等）",
)
async def statistics(
    fixture_id: int = Query(..., description="比赛 ID"),
):
    return get_statistics(fixture_id)


# ─── 今日赛事概览 ─────────────────────────────────────────
@router.get(
    "/today",
    summary="今日赛事概览",
    description="获取今日五大联赛 + 欧冠/欧联的赛程速览",
)
async def today():
    return today_summary()
