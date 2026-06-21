"""
Football Engine — 基于 API-Football v3
从 football-match-analyzer 技能适配而来，供 FastAPI router 调用。
支持: 赛程查询/积分榜/H2H/比分预测/半全场/大小球/赔率/统计/今日速览
"""

import os
import math
from datetime import datetime
from collections import Counter

import requests

# ─── 配置 ───────────────────────────────────────────────
BASE_URL = "https://v3.football.api-sports.com"
TIMEOUT = 30

# 联赛中文名映射
LEAGUE_NAMES = {
    39: "英超", 140: "西甲", 135: "意甲", 78: "德甲", 61: "法甲",
    2: "欧冠", 3: "欧联", 848: "欧协联", 40: "英冠", 141: "西乙",
    136: "意乙", 79: "德乙", 62: "法乙", 88: "葡超", 89: "荷甲",
    94: "中超", 98: "日职", 292: "韩职", 253: "美职",
    1: "世界杯", 4: "欧洲杯", 9: "美洲杯", 766: "亚洲杯",
    10: "友谊赛", 5: "欧国联", 6: "非洲杯",
}

# 中文联赛名→ID映射
LEAGUE_CN_TO_ID = {v: k for k, v in LEAGUE_NAMES.items()}
LEAGUE_CN_TO_ID.update({
    "英超联赛": 39, "西班牙甲级联赛": 140, "意大利甲级联赛": 135,
    "德国甲级联赛": 78, "法国甲级联赛": 61,
    "英格兰超级联赛": 39, "西班牙足球甲级联赛": 140,
    "意大利足球甲级联赛": 135, "德国足球甲级联赛": 78,
    "法国足球甲级联赛": 61,
    "欧冠杯": 2, "欧冠联赛": 2, "欧联杯": 3, "欧联联赛": 3,
})


def get_api_key():
    """从环境变量读取 API Key"""
    key = os.getenv("APIFOOTBALL_KEY")
    if not key:
        raise ValueError(
            "缺少 API-Football 凭证，请先配置 APIFOOTBALL_KEY 环境变量。\n"
            "获取方式: 访问 https://dashboard.api-football.com/register 注册免费账号，"
            "在 Dashboard 中复制 API Key"
        )
    return key


def api_request(endpoint, params=None):
    """发送 API 请求，带错误处理"""
    key = get_api_key()
    headers = {"x-apisports-key": key}
    url = f"{BASE_URL}/{endpoint}"

    try:
        resp = requests.get(url, headers=headers, params=params or {}, timeout=TIMEOUT)
        data = resp.json()

        # 检查 API 级错误
        errors = data.get("errors", {})
        if errors:
            err_msg = "; ".join(f"{k}: {v}" for k, v in errors.items()) if isinstance(errors, dict) else str(errors)
            return {"error": f"API错误: {err_msg}"}

        return data.get("response", [])

    except requests.exceptions.Timeout:
        return {"error": "API请求超时，请稍后重试"}
    except requests.exceptions.ConnectionError:
        return {"error": "网络连接失败，请检查网络"}
    except Exception as e:
        return {"error": f"请求异常: {str(e)}"}


# ─── 联赛查询 ─────────────────────────────────────────
def search_leagues(name=None, country=None, season=None):
    """搜索联赛"""
    params = {}
    if name:
        params["search"] = name
    if country:
        params["country"] = country
    if season:
        params["season"] = season

    result = api_request("leagues", params)
    if isinstance(result, dict) and "error" in result:
        return result

    leagues = []
    for lg in result[:20]:
        info = lg.get("league", {})
        leagues.append({
            "id": info.get("id"),
            "name": info.get("name"),
            "cn_name": LEAGUE_NAMES.get(info.get("id"), ""),
            "country": lg.get("country", {}).get("name", ""),
            "type": info.get("type", ""),
        })
    return leagues


# ─── 球队搜索 ─────────────────────────────────────────
def search_teams(name=None, league_id=None):
    """搜索球队"""
    params = {}
    if name:
        params["search"] = name
    if league_id:
        params["league"] = league_id
        params["season"] = datetime.now().year - (1 if datetime.now().month < 7 else 0)

    result = api_request("teams", params)
    if isinstance(result, dict) and "error" in result:
        return result

    teams = []
    for t in result[:20]:
        team = t.get("team", {})
        venue = t.get("venue", {})
        teams.append({
            "id": team.get("id"),
            "name": team.get("name"),
            "code": team.get("code"),
            "country": team.get("country"),
            "founded": team.get("founded"),
            "venue": venue.get("name", ""),
        })
    return teams


# ─── 赛程查询 ─────────────────────────────────────────
def get_fixtures(league_id=None, date=None, team_id=None, season=None,
                 fixture_id=None, live="no", next_n=0):
    """查询赛程/赛果"""
    params = {"timezone": "Asia/Shanghai"}
    if fixture_id:
        params["id"] = fixture_id
    if league_id:
        params["league"] = league_id
    if date:
        params["date"] = date
    if team_id:
        params["team"] = team_id
    if season:
        params["season"] = season
    if live == "yes":
        params["live"] = "all"
    if next_n > 0:
        params["next"] = next_n

    result = api_request("fixtures", params)
    if isinstance(result, dict) and "error" in result:
        return result

    fixtures = []
    for fx in result[:30]:
        league = fx.get("league", {})
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        score = fx.get("score", {})
        fixture_info = fx.get("fixture", {})

        fixtures.append({
            "fixture_id": fixture_info.get("id"),
            "date": fixture_info.get("date", ""),
            "status": fixture_info.get("status", {}).get("short", ""),
            "league_id": league.get("id"),
            "league_name": league.get("name", ""),
            "league_cn": LEAGUE_NAMES.get(league.get("id"), ""),
            "home_team": teams.get("home", {}).get("name", ""),
            "home_id": teams.get("home", {}).get("id"),
            "away_team": teams.get("away", {}).get("name", ""),
            "away_id": teams.get("away", {}).get("id"),
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "ht_score": score.get("halftime", {}),
            "ft_score": score.get("fulltime", {}),
        })
    return fixtures


# ─── 积分榜 ─────────────────────────────────────────
def get_standings(league_id, season=None):
    """查询积分榜"""
    if not season:
        season = datetime.now().year - (1 if datetime.now().month < 7 else 0)
    params = {"league": league_id, "season": season}

    result = api_request("standings", params)
    if isinstance(result, dict) and "error" in result:
        return result

    standings = []
    for group in result:
        league_data = group.get("league", {})
        for entry in league_data.get("standings", []):
            if isinstance(entry, list):
                for e in entry:
                    standings.append(_parse_standing(e))
            else:
                standings.append(_parse_standing(entry))
    return standings


def _parse_standing(e):
    """解析单条积分榜记录"""
    team = e.get("team", {})
    all_stats = e.get("all", {})
    home_stats = e.get("home", {})
    away_stats = e.get("away", {})
    return {
        "rank": e.get("rank"),
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "points": e.get("points"),
        "played": all_stats.get("played"),
        "won": all_stats.get("win"),
        "draw": all_stats.get("draw"),
        "lost": all_stats.get("lose"),
        "goals_for": all_stats.get("goals", {}).get("for"),
        "goals_against": all_stats.get("goals", {}).get("against"),
        "goal_diff": e.get("goalDiff"),
        "form": all_stats.get("form", ""),
        "home_w": home_stats.get("win", 0) if isinstance(home_stats, dict) else 0,
        "home_d": home_stats.get("draw", 0) if isinstance(home_stats, dict) else 0,
        "home_l": home_stats.get("lose", 0) if isinstance(home_stats, dict) else 0,
        "away_w": away_stats.get("win", 0) if isinstance(away_stats, dict) else 0,
        "away_d": away_stats.get("draw", 0) if isinstance(away_stats, dict) else 0,
        "away_l": away_stats.get("lose", 0) if isinstance(away_stats, dict) else 0,
    }


# ─── H2H 历史交锋 ─────────────────────────────────────────
def get_h2h(team1_id, team2_id, last_n=15):
    """查询历史交锋"""
    params = {"h2h": f"{team1_id}-{team2_id}", "last": last_n}
    result = api_request("fixtures/headtohead", params)
    if isinstance(result, dict) and "error" in result:
        return result

    h2h_data = []
    team1_wins = 0
    team2_wins = 0
    draws = 0
    team1_goals = 0
    team2_goals = 0
    half_time_results = Counter()

    for fx in result:
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        score = fx.get("score", {})
        fixture_info = fx.get("fixture", {})

        home_name = teams.get("home", {}).get("name", "")
        away_name = teams.get("away", {}).get("name", "")
        home_goals = goals.get("home") or 0
        away_goals = goals.get("away") or 0
        ht = score.get("halftime", {})

        is_team1_home = teams.get("home", {}).get("id") == team1_id
        if home_goals > away_goals:
            if is_team1_home:
                team1_wins += 1
            else:
                team2_wins += 1
        elif home_goals < away_goals:
            if is_team1_home:
                team2_wins += 1
            else:
                team1_wins += 1
        else:
            draws += 1

        team1_goals += home_goals if is_team1_home else away_goals
        team2_goals += away_goals if is_team1_home else home_goals

        ht_home = ht.get("home") or 0
        ht_away = ht.get("away") or 0
        ft_home = home_goals
        ft_away = away_goals
        ht_label = f"半场{ht_home}-{ht_away}"
        ft_label = f"全场{ft_home}-{ft_away}"
        half_time_results[f"{ht_label}/{ft_label}"] += 1

        h2h_data.append({
            "date": fixture_info.get("date", "")[:10],
            "home": home_name,
            "away": away_name,
            "score": f"{home_goals}-{away_goals}",
            "ht_score": f"{ht_home}-{ht_away}" if ht_home is not None else "",
        })

    return {
        "total": len(result),
        "team1_wins": team1_wins,
        "team2_wins": team2_wins,
        "draws": draws,
        "team1_avg_goals": round(team1_goals / max(len(result), 1), 2),
        "team2_avg_goals": round(team2_goals / max(len(result), 1), 2),
        "half_time_distribution": dict(half_time_results.most_common(5)),
        "matches": h2h_data,
    }


# ─── API 预测 ─────────────────────────────────────────
def get_prediction(fixture_id):
    """获取 API 预测"""
    params = {"fixture": fixture_id}
    result = api_request("predictions", params)
    if isinstance(result, dict) and "error" in result:
        return result
    if not result:
        return {"error": "无预测数据"}

    pred = result[0]
    comparison = pred.get("comparison", {})

    return {
        "winner": pred.get("predictions", {}).get("winner", {}),
        "win_or_draw": pred.get("predictions", {}).get("win_or_draw", False),
        "under_over": pred.get("predictions", {}).get("under_over"),
        "goals_home": pred.get("predictions", {}).get("goals", {}).get("home"),
        "goals_away": pred.get("predictions", {}).get("goals", {}).get("away"),
        "advice": pred.get("predictions", {}).get("advice", ""),
        "percent_home": comparison.get("forme", {}).get("home", ""),
        "percent_draw": comparison.get("forme", {}).get("draw", ""),
        "percent_away": comparison.get("forme", {}).get("away", ""),
        "comparison": {
            k: v for k, v in comparison.items()
            if k in ("forme", "att", "def", "poisson_distribution", "h2h", "goals", "total")
        },
    }


# ─── 赔率 ─────────────────────────────────────────
def get_odds(fixture_id=None, league_id=None, season=None, bet=1):
    """查询赔率 (bet=1: 1X2, bet=5: 大小球, bet=3: 亚洲让球)"""
    params = {}
    if fixture_id:
        params["fixture"] = fixture_id
    if league_id:
        params["league"] = league_id
    if season:
        params["season"] = season
    params["bet"] = bet

    result = api_request("odds", params)
    if isinstance(result, dict) and "error" in result:
        return result

    odds_list = []
    for o in result[:10]:
        bookmaker = o.get("bookmaker", {})
        bets = o.get("bets", [])
        odds_list.append({
            "bookmaker": bookmaker.get("name", ""),
            "bets": bets,
        })
    return odds_list


# ─── 比赛统计 ─────────────────────────────────────────
def get_statistics(fixture_id):
    """查询比赛统计"""
    params = {"fixture": fixture_id}
    result = api_request("fixtures/statistics", params)
    if isinstance(result, dict) and "error" in result:
        return result

    stats = {}
    for s in result:
        team = s.get("team", {})
        team_name = team.get("name", "")
        team_stats = {}
        for st in s.get("statistics", []):
            team_stats[st.get("type", "")] = st.get("value")
        stats[team_name] = team_stats
    return stats


# ─── 球队近期战绩 ─────────────────────────────────────────
def get_team_form(team_id, last_n=5):
    """获取球队近期战绩"""
    params = {"team": team_id, "last": last_n, "timezone": "Asia/Shanghai"}
    result = api_request("fixtures", params)
    if isinstance(result, dict) and "error" in result:
        return result

    form = []
    goals_for = 0
    goals_against = 0
    results_str = ""

    for fx in result:
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        is_home = teams.get("home", {}).get("id") == team_id
        home_g = goals.get("home") or 0
        away_g = goals.get("away") or 0

        my_goals = home_g if is_home else away_g
        opp_goals = away_g if is_home else home_g
        goals_for += my_goals
        goals_against += opp_goals

        if my_goals > opp_goals:
            results_str += "W"
        elif my_goals < opp_goals:
            results_str += "L"
        else:
            results_str += "D"

        form.append({
            "opponent": teams.get("away" if is_home else "home", {}).get("name", ""),
            "home_away": "主" if is_home else "客",
            "score": f"{home_g}-{away_g}",
            "result": "W" if my_goals > opp_goals else ("L" if my_goals < opp_goals else "D"),
        })

    return {
        "form_str": results_str,
        "avg_goals_for": round(goals_for / max(len(result), 1), 2),
        "avg_goals_against": round(goals_against / max(len(result), 1), 2),
        "matches": form,
    }


# ─── 综合分析 ─────────────────────────────────────────
def full_analysis(fixture_id):
    """综合对阵分析：预测+H2H+近期战绩+赔率"""
    # 1. 获取比赛信息
    fixtures = get_fixtures(fixture_id=fixture_id)
    if isinstance(fixtures, dict) and "error" in fixtures:
        return fixtures
    if not fixtures:
        return {"error": f"未找到比赛 ID={fixture_id}"}

    fx = fixtures[0]
    home_id = fx["home_id"]
    away_id = fx["away_id"]
    home_name = fx["home_team"]
    away_name = fx["away_team"]
    league_cn = fx.get("league_cn") or fx.get("league_name", "")

    result = {
        "match": f"{home_name} vs {away_name}",
        "league": league_cn,
        "date": fx.get("date", "")[:16],
        "status": fx.get("status", ""),
    }

    # 2. API 预测
    pred = get_prediction(fixture_id)
    if not (isinstance(pred, dict) and "error" in pred):
        result["prediction"] = pred

    # 3. H2H
    h2h = get_h2h(home_id, away_id)
    if not (isinstance(h2h, dict) and "error" in h2h):
        result["h2h"] = h2h

    # 4. 主队近期
    home_form = get_team_form(home_id, 5)
    if not (isinstance(home_form, dict) and "error" in home_form):
        result["home_form"] = home_form

    # 5. 客队近期
    away_form = get_team_form(away_id, 5)
    if not (isinstance(away_form, dict) and "error" in away_form):
        result["away_form"] = away_form

    # 6. 半全场推算
    result["half_full_analysis"] = _calc_half_full(result)

    # 7. 大小球推算
    result["over_under_analysis"] = _calc_over_under(result)

    # 8. 赔率
    odds = get_odds(fixture_id=fixture_id, bet=1)
    if not (isinstance(odds, dict) and "error" in odds):
        result["odds_1x2"] = odds[:5] if isinstance(odds, list) else odds

    return result


def _calc_half_full(analysis):
    """基于 H2H 和近期战绩推算半全场概率"""
    half_full = Counter()

    h2h = analysis.get("h2h", {})
    for pattern, count in h2h.get("half_time_distribution", {}).items():
        half_full[pattern] += count * 2

    home_form = analysis.get("home_form", {})
    away_form = analysis.get("away_form", {})

    home_avg_gf = home_form.get("avg_goals_for", 1.2)
    home_avg_ga = home_form.get("avg_goals_against", 0.9)
    away_avg_gf = away_form.get("avg_goals_for", 1.1)
    away_avg_ga = away_form.get("avg_goals_against", 0.8)

    pred = analysis.get("prediction", {})
    pred_home_g = pred.get("goals_home")
    pred_away_g = pred.get("goals_away")

    if pred_home_g is not None and pred_away_g is not None:
        total_goals = float(pred_home_g) + float(pred_away_g)
        half_goals = round(total_goals * 0.42, 1)
        half_home = int(half_goals * float(pred_home_g) / max(total_goals, 0.1))
        half_away = int(half_goals) - half_home

        patterns = [
            (f"半场{half_home}-{half_away}/全场{int(float(pred_home_g))}-{int(float(pred_away_g))}", 5),
            (f"半场0-0/全场{int(float(pred_home_g))}-{int(float(pred_away_g))}", 3),
            (f"半场{half_home}-{half_away}/全场{int(float(pred_home_g))+1}-{int(float(pred_away_g))}", 2),
        ]
        for p, w in patterns:
            half_full[p] += w

    total_count = sum(half_full.values()) or 1
    ranked = []
    for pattern, count in half_full.most_common(5):
        ranked.append({
            "pattern": pattern,
            "probability": f"{count / total_count * 100:.1f}%",
        })
    return ranked


def _calc_over_under(analysis):
    """推算大小球"""
    h2h = analysis.get("h2h", {})
    home_form = analysis.get("home_form", {})
    away_form = analysis.get("away_form", {})
    pred = analysis.get("prediction", {})

    h2h_avg = (h2h.get("team1_avg_goals", 1.2) + h2h.get("team2_avg_goals", 1.1))
    form_avg = (home_form.get("avg_goals_for", 1.2) + home_form.get("avg_goals_against", 0.9) +
                away_form.get("avg_goals_for", 1.1) + away_form.get("avg_goals_against", 0.8)) / 2

    pred_total = None
    if pred.get("goals_home") is not None and pred.get("goals_away") is not None:
        try:
            pred_total = float(pred["goals_home"]) + float(pred["goals_away"])
        except (ValueError, TypeError):
            pass

    weights_sum = 0
    goals_sum = 0
    if h2h.get("total", 0) > 0:
        goals_sum += h2h_avg
        weights_sum += 1
    goals_sum += form_avg
    weights_sum += 1
    if pred_total is not None:
        goals_sum += pred_total * 2
        weights_sum += 2

    expected_goals = round(goals_sum / max(weights_sum, 1), 2)

    over_prob = 1 - math.exp(-expected_goals) * (1 + expected_goals + expected_goals**2 / 2)
    over_prob = min(max(over_prob, 0.05), 0.95)

    return {
        "expected_total_goals": expected_goals,
        "over_2_5_prob": f"{over_prob * 100:.1f}%",
        "under_2_5_prob": f"{(1 - over_prob) * 100:.1f}%",
        "over_3_5_prob": f"{max(1 - math.exp(-expected_goals) * sum(expected_goals**i / math.factorial(i) for i in range(4)), 0.05) * 100:.1f}%",
        "suggestion": "大2.5" if over_prob > 0.5 else "小2.5",
        "pred_total_from_api": pred_total,
    }


# ─── 今日赛事速览 ─────────────────────────────────────────
def today_summary(league_ids=None):
    """今日赛事速览"""
    today = datetime.now().strftime("%Y-%m-%d")
    params = {"date": today, "timezone": "Asia/Shanghai"}

    if league_ids:
        target_leagues = league_ids
    else:
        target_leagues = [39, 140, 135, 78, 61, 2, 3]

    all_fixtures = []
    for lid in target_leagues:
        params_lg = {**params, "league": lid,
                     "season": datetime.now().year - (1 if datetime.now().month < 7 else 0)}
        fx = api_request("fixtures", params_lg)
        if isinstance(fx, list):
            all_fixtures.extend(fx)

    if isinstance(all_fixtures, dict) and "error" in all_fixtures:
        return all_fixtures

    summary = []
    for fx in all_fixtures:
        league = fx.get("league", {})
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        fixture_info = fx.get("fixture", {})
        score_data = fx.get("score", {})

        status = fixture_info.get("status", {}).get("short", "")
        home_g = goals.get("home")
        away_g = goals.get("away")

        item = {
            "fixture_id": fixture_info.get("id"),
            "league": LEAGUE_NAMES.get(league.get("id"), league.get("name", "")),
            "time": fixture_info.get("date", "")[11:16],
            "home": teams.get("home", {}).get("name", ""),
            "away": teams.get("away", {}).get("name", ""),
            "status": status,
        }
        if home_g is not None:
            item["score"] = f"{home_g}-{away_g}"
            ht = score_data.get("halftime", {})
            if ht.get("home") is not None:
                item["ht"] = f"{ht['home']}-{ht['away']}"
        summary.append(item)

    return summary


# ─── 解析联赛名 ─────────────────────────────────────────
def resolve_league_id(name):
    """将中文/英文名解析为联赛 ID"""
    if not name:
        return None
    name = name.strip()

    # 直接匹配中文映射
    if name in LEAGUE_CN_TO_ID:
        return LEAGUE_CN_TO_ID[name]

    # 模糊匹配
    for cn_name, lid in LEAGUE_CN_TO_ID.items():
        if name in cn_name or cn_name in name:
            return lid

    # 尝试数字
    try:
        return int(name)
    except ValueError:
        pass

    # 搜索 API
    leagues = search_leagues(name=name)
    if isinstance(leagues, list) and leagues:
        return leagues[0].get("id")
    return None
