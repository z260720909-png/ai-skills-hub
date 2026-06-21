#!/usr/bin/env python3
"""
自媒体运营引擎 - AI Skills Hub 适配版
从全网自媒体自动运营技能 v2.0 适配而来
覆盖: 小红书/抖音/微信公众号/微博/B站/头条/知乎/快手
核心能力: 去AI味内容创作/配图生成/竞品分析/评论回复/平台适配/内容日历/行业违禁词
"""

import json
import re
import random
from datetime import datetime, timedelta

import requests

# ============================================================
# 平台配置
# ============================================================
PLATFORMS = {
    "xiaohongshu": {
        "name": "小红书",
        "max_title": 20,
        "max_content": 1000,
        "hashtag_style": "#标签",
        "emoji_density": "high",
        "paragraph_style": "short",
        "content_types": ["图文笔记", "视频笔记"],
        "tone": "生活化/种草/闺蜜聊天",
        "image_ratio": "3:4",
        "image_count": "6-9张",
        "posting_peak": ["12:00", "18:00", "21:00"],
    },
    "douyin": {
        "name": "抖音",
        "max_title": 55,
        "max_content": 300,
        "hashtag_style": "#标签",
        "emoji_density": "medium",
        "paragraph_style": "script",
        "content_types": ["短视频", "图文"],
        "tone": "节奏快/反转/情绪价值",
        "image_ratio": "9:16",
        "image_count": "封面1张",
        "posting_peak": ["12:00", "18:00", "21:00"],
    },
    "wechat": {
        "name": "微信公众号",
        "max_title": 64,
        "max_content": 20000,
        "hashtag_style": "#标签#",
        "emoji_density": "low",
        "paragraph_style": "long",
        "content_types": ["图文消息", "视频消息"],
        "tone": "深度/专业/有观点",
        "image_ratio": "16:9",
        "image_count": "3-5张",
        "posting_peak": ["08:00", "12:00", "20:00"],
    },
    "weibo": {
        "name": "微博",
        "max_title": 0,
        "max_content": 2000,
        "hashtag_style": "#话题#",
        "emoji_density": "medium",
        "paragraph_style": "short",
        "content_types": ["图文微博", "视频微博", "头条文章"],
        "tone": "观点鲜明/互动性强",
        "image_ratio": "1:1 or 16:9",
        "image_count": "1-9张",
        "posting_peak": ["08:00", "12:00", "18:00", "22:00"],
    },
    "bilibili": {
        "name": "B站",
        "max_title": 80,
        "max_content": 250,
        "hashtag_style": "空格分隔",
        "emoji_density": "medium",
        "paragraph_style": "description",
        "content_types": ["视频", "专栏", "动态"],
        "tone": "二次元/干货/弹幕友好",
        "image_ratio": "16:9",
        "image_count": "封面1张",
        "posting_peak": ["12:00", "18:00", "22:00"],
    },
    "toutiao": {
        "name": "头条",
        "max_title": 30,
        "max_content": 50000,
        "hashtag_style": "#标签",
        "emoji_density": "low",
        "paragraph_style": "long",
        "content_types": ["图文", "视频", "微头条"],
        "tone": "信息量/时效性/接地气",
        "image_ratio": "16:9",
        "image_count": "3-6张",
        "posting_peak": ["07:00", "12:00", "18:00", "21:00"],
    },
    "zhihu": {
        "name": "知乎",
        "max_title": 0,
        "max_content": 50000,
        "hashtag_style": "话题链接",
        "emoji_density": "low",
        "paragraph_style": "long",
        "content_types": ["回答", "文章", "想法"],
        "tone": "专业/理性/数据支撑",
        "image_ratio": "16:9",
        "image_count": "3-5张",
        "posting_peak": ["08:00", "12:00", "21:00"],
    },
    "kuaishou": {
        "name": "快手",
        "max_title": 30,
        "max_content": 300,
        "hashtag_style": "#标签",
        "emoji_density": "medium",
        "paragraph_style": "short",
        "content_types": ["短视频", "图文"],
        "tone": "接地气/老铁/真实",
        "image_ratio": "9:16",
        "image_count": "封面1张",
        "posting_peak": ["12:00", "19:00", "21:00"],
    },
}

# ============================================================
# 去AI味引擎
# ============================================================

# 过渡词黑名单 - 这些词让文章看起来像AI写的
TRANSITION_WORDS = [
    "首先", "其次", "再次", "最后", "总之", "综上所述",
    "值得注意的是", "需要指出的是", "不可否认", "毋庸置疑",
    "显而易见", "众所周知", "事实上", "实际上", "本质上",
    "从某种意义上说", "在一定程度上", "换句话说", "换言之",
    "与此同时", "不仅如此", "更重要的是", "更具体地说",
    "一方面", "另一方面", "总的来说", "总体而言",
    "基于以上分析", "通过以上讨论", "由此可见",
    "在这个背景下", "在这一背景下", "随着...的发展",
    "在当今社会", "在现代社会", "在当代社会",
]

# 口语化替换词
COLLOQUIAL_MAP = {
    "获取": "拿到/搞到/弄到",
    "进行": "搞/做/来",
    "实施": "搞/做/干",
    "利用": "用/拿/靠",
    "通过": "靠/拿/用",
    "实现": "做到/搞定/弄成",
    "提供": "给/带来/送上",
    "确保": "保证/包准/稳住",
    "涉及": "牵扯/碰到/关联",
    "具备": "有/带着/含着",
    "呈现": "展现/露出/给人感觉",
    "探讨": "聊/说/扯扯",
    "阐述": "说/讲/聊聊",
    "分析": "拆/看/盘一盘",
    "探讨": "聊聊/说说/唠唠",
    "具备": "有/带着",
    "显著": "明显/大/猛",
    "极为": "特别/超/巨",
    "相当": "挺/蛮/超",
    "诸多": "好多/一堆/各种",
    "鉴于": "看在/考虑到/既然",
    "旨在": "想/就是为了/奔着",
    "予以": "给/上",
    "契合": "合/对味/搭",
}

# 专业术语保护 - 这些词汇不会被口语化替换
TECHNICAL_TERMS_PATTERNS = [
    # 技术参数：DN20, 1.6MPa, 2200W, 3200rpm
    r'\b[A-Z]{1,4}\d+\.?\d*[A-Z]*\b',
    # 百分比浓度：5%, 2.5%
    r'\d+\.?\d*%',
    # 医学/化学名词：烟酰胺、玻尿酸、III型胶原蛋白
    r'[ⅢII型]+胶原蛋白',
    r'烟酰胺|玻尿酸|水杨酸|神经酰胺|视黄醇|果酸|传明酸|虾青素',
    r'[A-Z]{2,}\s?\d+\.?\d*%?',  # 如PE、LPR、ISO等
    # 金融术语
    r'年化收益率|LPR|PE倍数|ROE|EPS|GDP|CPI|PPI',
    # 行业标准
    r'ISO\s?\d+|3C认证|FDA|CE认证|GB\s?\d+',
    # 规格：5ml, 30g, 200ml
    r'\d+\.?\d*(?:ml|g|kg|L|mm|cm|m|W|V|A|Ω|Pa|MPa|rpm|dB|Hz)',
    # 材料/型号
    r'[A-Z]{2,}[-–]?\d*',  # 如PPR、ABS、PVC
    r'304|316|316L',  # 不锈钢型号
]


def is_technical_term(text, start, end):
    """检查文本中指定位置是否属于专业术语"""
    for pattern in TECHNICAL_TERMS_PATTERNS:
        for match in re.finditer(pattern, text):
            if match.start() <= start < match.end() or match.start() < end <= match.end():
                return True
    return False


# 行业违禁词库
INDUSTRY_BANNED_WORDS = {
    "美妆护肤": {
        "小红书": [
            "最", "第一", "100%纯天然", "药妆", "速效", "特效", "全效",
            "绝对", "永久", "根除", "无效退款", "立竿见影", "零添加",
            "全网最低", "史上最强", "王牌", "冠军", "顶级", "极品",
            "医疗级别", "处方级", "祛斑", "换肤", "去疤",
        ],
        "抖音": [
            "最", "第一", "纯天然", "药妆", "特效", "全效", "绝对",
            "永久", "根除", "无效退款", "零添加", "全网最低",
            "医疗美容", "处方级", "三天见效",
        ],
        "通用": [
            "纯天然", "无添加", "0添加", "零添加", "药妆", "医学护肤",
            "处方级", "医疗级", "3天见效", "7天美白", "去疤", "祛斑",
        ],
    },
    "建材家居": {
        "小红书": [
            "抗菌率99%", "饮用级安全", "100%进口原料", "零甲醛",
            "E0级", "食品级", "医疗级", "绝对环保", "永久防水",
            "永不褪色", "防火等级A1", "零VOC", "无辐射",
        ],
        "抖音": [
            "抗菌率99%", "饮用级", "100%进口", "零甲醛", "E0级",
            "食品级", "医疗级", "绝对环保", "永久防水",
        ],
        "通用": [
            "抗菌率99%", "饮用级安全", "100%进口原料", "零甲醛",
            "E0级板材", "食品级涂料", "医疗级管材", "无辐射",
            "永不变形", "永久防水", "零VOC",
        ],
    },
    "食品保健": {
        "通用": [
            "治疗", "治愈", "药效", "处方", "包治", "根除",
            "降血糖", "降血压", "抗癌", "防癌", "减肥药",
            "壮阳", "提高免疫力", "0卡0糖0脂(除非有检测报告)",
            "天然", "纯天然", "绿色食品(除非有认证)", "有机(除非有认证)",
        ],
    },
    "医疗健康": {
        "通用": [
            "包治", "根治", "治愈率", "有效率", "无毒副作用",
            "最新技术", "最先进", "国家级", "世界级",
            "名医", "专家推荐(非正规)", "患者感谢信",
            "用药指导", "处方建议",
        ],
    },
    "金融理财": {
        "通用": [
            "保本保息", "零风险", "稳赚不赔", "100%收益",
            "内部消息", " guaranteed ", "年化XX%(具体承诺)",
            "翻倍", "暴涨", "必涨", "抄底",
            "内部渠道", "VIP专享",
        ],
    },
    "教育培训": {
        "通用": [
            "包过", "保过", "必过", "100%通过率",
            "原命题组", "内部题库", "押题", "密卷",
            "快速拿证", "免考", "代考", "挂靠",
            "月薪XX(具体承诺)", "就业保障(无合同)",
        ],
    },
}

# 口语化插入语
FILLER_PHRASES = [
    "说真的，", "老实讲，", "不瞒你说，", "讲真，",
    "怎么说呢，", "你想想，", "说白了，", "就这样，",
    "关键是，", "我跟你讲，", "别不信，", "真的，",
    "我跟你说，", "你品，", "你细品，", "信我，",
    "说句大实话，", "有一说一，", "咱就是说，",
]

# 个人细节模板
PERSONAL_DETAILS = [
    "我自己踩过这个坑，",
    "上次我朋友也遇到了，",
    "我用了三个月才搞明白，",
    "一开始我也不信，后来发现，",
    "我自己试了不下十次，",
    "之前我也被坑过，",
    "我踩坑踩了半年，",
    "我身边好几个朋友都这样，",
    "我研究了很久才发现，",
    "说起来我之前也纠结过，",
]


# ============================================================
# 核心功能函数
# ============================================================

def anti_ai_rewrite(text, level="medium", platform="general"):
    """
    去AI味改写引擎
    level: light(轻度) / medium(中度) / heavy(重度)
    platform: 针对平台风格调整
    """
    result = text

    # Step 1: 删除过渡词
    for word in TRANSITION_WORDS:
        pattern = re.compile(re.escape(word) + r'[，,]?\s*')
        result = pattern.sub('', result)

    # Step 2: 替换书面词为口语（跳过专业术语）
    for formal, colloquial in COLLOQUIAL_MAP.items():
        pattern = re.compile(re.escape(formal))
        for match in pattern.finditer(result):
            if is_technical_term(result, match.start(), match.end()):
                continue
            options = colloquial.split('/')
            chosen = random.choice(options)
            result = result[:match.start()] + chosen + result[match.end():]
            break  # 一次只替换一个，避免位置偏移

    # Step 3: 句长剧烈波动 - 打破均匀句长
    sentences = re.split(r'([。！？；])', result)
    processed = []
    i = 0
    while i < len(sentences):
        sentence = sentences[i]
        if i + 1 < len(sentences) and sentences[i + 1] in '。！？；':
            sentence += sentences[i + 1]
            i += 2
        else:
            i += 1

        if not sentence.strip():
            continue

        # 中度以上：长句拆短
        if level in ("medium", "heavy") and len(sentence) > 40:
            parts = sentence.split('，')
            if len(parts) > 2:
                split_point = random.randint(1, len(parts) - 1)
                first = '，'.join(parts[:split_point])
                rest = '，'.join(parts[split_point:])
                if not first.endswith(('。', '！', '？', '；')):
                    first += random.choice(['。', '！', '…'])
                processed.append(first)
                processed.append(rest)
                continue

        processed.append(sentence)

    result = ''.join(processed)

    # Step 4: 注入口语化插入语 (medium+)
    if level in ("medium", "heavy"):
        sentences = re.split(r'([。！？])', result)
        inject_positions = []
        for idx, s in enumerate(sentences):
            if len(s) > 15 and random.random() < 0.2:
                inject_positions.append(idx)

        for pos in reversed(inject_positions):
            filler = random.choice(FILLER_PHRASES)
            sentences[pos] = filler + sentences[pos]

        result = ''.join(sentences)

    # Step 5: 注入个人细节 (heavy)
    if level == "heavy":
        sentences = re.split(r'([。！？])', result)
        detail_positions = []
        for idx, s in enumerate(sentences):
            if len(s) > 20 and random.random() < 0.15:
                detail_positions.append(idx)

        for pos in reversed(detail_positions):
            detail = random.choice(PERSONAL_DETAILS)
            sentences[pos] = detail + sentences[pos]

        result = ''.join(sentences)

    # Step 6: 标点符号情感化
    if level in ("medium", "heavy"):
        result = re.sub(
            r'。(?=\s*[A-Z\u4e00-\u9fff])',
            lambda m: random.choice(['。', '！', '…']),
            result,
        )

    # Step 7: 平台风格微调
    if platform == "xiaohongshu":
        emoji_pool = ["✨", "🔥", "💯", "💕", "🌟", "💪", "👀", "🎯", "📌", "💡"]
        sentences = re.split(r'([。！？])', result)
        for idx in range(len(sentences)):
            if len(sentences[idx]) > 10 and random.random() < 0.3:
                sentences[idx] += random.choice(emoji_pool)
        result = ''.join(sentences)
    elif platform in ("kuaishou", "douyin"):
        result = result.replace("你们", "老铁们")
        result = result.replace("大家", "家人们")
        result = result.replace("朋友", "兄弟")

    # Step 8: 清理多余空格和重复标点
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'([。！？]){3,}', lambda m: m.group(1) * 2, result)
    result = re.sub(r'…{3,}', '…', result)

    return result.strip()


# ============================================================
# 平台格式适配
# ============================================================

def platform_format(content, title, platform, content_type="post"):
    """
    将内容适配到特定平台格式
    返回格式化后的完整内容
    """
    config = PLATFORMS.get(platform)
    if not config:
        return {"error": f"不支持的平台: {platform}", "supported": list(PLATFORMS.keys())}

    result = {
        "platform": config["name"],
        "platform_key": platform,
        "title": title,
        "content": content,
        "formatted": "",
        "image_suggestions": [],
        "hashtag_suggestions": [],
        "posting_time_suggestion": "",
        "notes": [],
    }

    # 标题处理
    if config["max_title"] > 0 and len(title) > config["max_title"]:
        result["title"] = title[: config["max_title"] - 3] + "..."
        result["notes"].append(f"标题已截断至{config['max_title']}字")

    # 正文处理
    if len(content) > config["max_content"]:
        result["notes"].append(f"正文超长({len(content)}>{config['max_content']})，建议精简")

    # 按平台生成格式
    if platform == "xiaohongshu":
        result["formatted"] = _format_xiaohongshu(title, content)
    elif platform == "douyin":
        result["formatted"] = _format_douyin(title, content)
    elif platform == "wechat":
        result["formatted"] = _format_wechat(title, content)
    elif platform == "weibo":
        result["formatted"] = _format_weibo(content)
    elif platform == "bilibili":
        result["formatted"] = _format_bilibili(title, content)
    elif platform == "toutiao":
        result["formatted"] = _format_toutiao(title, content)
    elif platform == "zhihu":
        result["formatted"] = _format_zhihu(content)
    elif platform == "kuaishou":
        result["formatted"] = _format_kuaishou(title, content)

    # 发布时间建议
    result["posting_time_suggestion"] = random.choice(config["posting_peak"])

    # 图片建议
    result["image_suggestions"] = _generate_image_specs(platform, content)

    return result


def _format_xiaohongshu(title, content):
    """小红书格式"""
    title_emojis = ["✨", "🔥", "💡", "🌟", "📌"]
    formatted_title = f"{random.choice(title_emojis)} {title} {random.choice(title_emojis)}"

    paragraphs = content.split('\n')
    short_paras = []
    for p in paragraphs:
        if len(p) > 60:
            sentences = re.split(r'[。！？]', p)
            chunk = []
            for s in sentences:
                chunk.append(s)
                if len(''.join(chunk)) > 40:
                    short_paras.append(''.join(chunk))
                    chunk = []
            if chunk:
                short_paras.append(''.join(chunk))
        else:
            short_paras.append(p)

    formatted_content = '\n\n'.join(short_paras)
    formatted_content += "\n\n———\n"

    return f"{formatted_title}\n\n{formatted_content}"


def _format_douyin(title, content):
    """抖音格式 - 视频脚本"""
    lines = [
        f"📌 视频标题：{title}",
        f"\n🎬 视频脚本：",
        f"",
    ]
    paragraphs = content.split('\n')
    for i, p in enumerate(paragraphs):
        if p.strip():
            lines.append(f"【画面{i+1}】{p.strip()}")
            lines.append(f"【旁白】{p.strip()}")
            lines.append("")
    return '\n'.join(lines)


def _format_wechat(title, content):
    """微信公众号格式"""
    paragraphs = content.split('\n')
    formatted = []
    for p in paragraphs:
        p = p.strip()
        if p:
            formatted.append(p)
            formatted.append("")
    return f"{title}\n\n{''.join(formatted)}"


def _format_weibo(content):
    """微博格式"""
    if len(content) > 2000:
        content = content[:1997] + "..."
    return content


def _format_bilibili(title, content):
    """B站格式"""
    desc = content[:250] if len(content) > 250 else content
    return f"{title}\n\n📝 简介：{desc}"


def _format_toutiao(title, content):
    """头条格式"""
    return f"{title}\n\n{content}"


def _format_zhihu(content):
    """知乎格式"""
    return content


def _format_kuaishou(title, content):
    """快手格式"""
    desc = content[:300] if len(content) > 300 else content
    return f"📌 {title}\n\n{desc}"


def _generate_image_specs(platform, content):
    """根据平台和内容生成配图规格建议"""
    specs = []

    if platform == "xiaohongshu":
        for i in range(random.randint(6, 9)):
            specs.append({
                "order": i + 1,
                "ratio": "3:4",
                "style": "清新/ins风",
                "content_hint": _extract_image_hint(content, i),
            })
    elif platform in ("douyin", "kuaishou"):
        specs.append({
            "order": 1,
            "ratio": "9:16",
            "style": "封面吸睛/大字报",
            "content_hint": title_hint_from_content(content),
        })
    elif platform in ("wechat", "toutiao", "zhihu"):
        for i in range(random.randint(3, 5)):
            specs.append({
                "order": i + 1,
                "ratio": "16:9",
                "style": "信息图/配图",
                "content_hint": _extract_image_hint(content, i),
            })
    elif platform == "weibo":
        for i in range(random.randint(1, 9)):
            specs.append({
                "order": i + 1,
                "ratio": "1:1",
                "style": "话题配图",
                "content_hint": _extract_image_hint(content, i),
            })
    elif platform == "bilibili":
        specs.append({
            "order": 1,
            "ratio": "16:9",
            "style": "封面/缩略图",
            "content_hint": title_hint_from_content(content),
        })

    return specs


def _extract_image_hint(content, index):
    """从内容中提取图片描述提示"""
    sentences = re.split(r'[。！？\n]', content)
    valid = [s.strip() for s in sentences if len(s.strip()) > 5]
    if valid:
        idx = min(index, len(valid) - 1)
        return valid[idx][:30]
    return "配图"


def title_hint_from_content(content):
    """从内容提取封面提示"""
    first_sentence = re.split(r'[。！？\n]', content)[0]
    return first_sentence[:20] if first_sentence else "封面"


# ============================================================
# 配图文案生成
# ============================================================

def generate_image_prompt(topic, platform="general", style="modern", count=1):
    """
    为内容生成配图文案（给image_generate用的prompt）
    """
    style_map = {
        "xiaohongshu": "ins风格,明亮柔和色调,精致生活感,白底或浅色背景",
        "douyin": "视觉冲击力强,高对比度,潮流感,动态构图",
        "wechat": "商务质感,简洁大气,专业配色,留白充足",
        "weibo": "话题感,信息图风格,数据可视化,时事感",
        "bilibili": "二次元元素,ACG风格,弹幕友好,趣味性",
        "toutiao": "新闻感,纪实风格,高信息密度,标题党视觉",
        "zhihu": "学术质感,数据图表,逻辑清晰,理性配色",
        "kuaishou": "接地气,烟火气,真实生活场景,亲切感",
    }

    platform_style = style_map.get(platform, "现代简约风格")

    prompts = []
    for i in range(count):
        prompt = (
            f"【{PLATFORMS.get(platform, {}).get('name', '自媒体')}】"
            f"{platform_style}, "
            f"主题: {topic}, "
            f"风格: {style}, "
        )

        if platform == "xiaohongshu":
            prompt += "竖版3:4构图,文字清晰可读,标题用双引号包裹"
        elif platform in ("douyin", "kuaishou"):
            prompt += "竖版9:16构图,大字标题吸睛,视觉冲击力"
        elif platform in ("wechat", "toutiao"):
            prompt += "横版16:9构图,图文排版专业"
        elif platform == "weibo":
            prompt += "正方形1:1构图,话题标签清晰"
        elif platform == "bilibili":
            prompt += "横版16:9构图,封面标题醒目"
        elif platform == "zhihu":
            prompt += "横版16:9构图,数据可视化风格"
        else:
            prompt += "构图美观,配色和谐"

        prompts.append(prompt)

    return prompts


# ============================================================
# 评论/私信自动回复
# ============================================================

REPLY_TEMPLATES = {
    "xiaohongshu": {
        "positive": [
            "谢谢宝子的认可！💕 继续分享更多好物~",
            "被你夸到啦！✨ 会持续更新的哦~",
            "宝子眼光真好！👍 这个真的超推荐~",
            "姐妹太会说了！🥰 有问题随时问我~",
        ],
        "question": [
            "好问题！我来详细说说~ ",
            "宝子问得好！👇 看这里~ ",
            "很多姐妹都问了这个问题！统一回复下~ ",
        ],
        "negative": [
            "感谢反馈！每个人的体验确实不同~",
            "理解你的感受~这款可能不太适合所有人",
            "抱歉让你失望了😣 我后续会更仔细测评的~",
        ],
        "dm": [
            "哈喽！很高兴认识你~ 有什么想聊的呀？😊",
            "收到你的消息啦！让我看看怎么帮到你~",
            "谢谢关注！有什么问题尽管问我~ 💕",
        ],
    },
    "douyin": {
        "positive": [
            "感谢支持！🔥 下期更精彩~",
            "老铁给力！👍 点关注不迷路~",
            "被你暖到了！❤️ 继续冲~",
        ],
        "question": [
            "好问题！下期专门讲这个~",
            "这个很多人问！我整理一下发出来~",
            "问得好！评论区置顶有答案~",
        ],
        "negative": [
            "每个人感受不同，我尊重~",
            "理解！后续内容会优化的~",
            "虚心接受！会改进的💪",
        ],
        "dm": [
            "收到！有什么想聊的直接说~",
            "嘿！感谢私信~ 看到了哈！",
            "在呢在呢！有啥事说~",
        ],
    },
    "wechat": {
        "positive": [
            "感谢阅读和支持！会持续输出有价值的内容~",
            "很高兴内容对您有帮助！欢迎持续关注~",
        ],
        "question": [
            "感谢提问！这个问题很关键，我后续会专门撰文分析~",
            "好问题！我会在后续文章中详细解答~",
        ],
        "negative": [
            "感谢您的反馈，不同观点很有价值~",
            "理解您的看法，我会持续改进内容质量~",
        ],
        "dm": [
            "感谢来信！我会尽快回复~",
            "收到您的消息，稍后详细回复~",
        ],
    },
    "weibo": {
        "positive": [
            "谢谢！转评赞走一波~ 🔥",
            "认可就扩散！让更多人看到~",
        ],
        "question": [
            "评论区回答了，看看~",
            "这个值得展开，下条微博聊~",
        ],
        "negative": [
            "求同存异~",
            "各有各的看法，理解~",
        ],
        "dm": [
            "私信收到！稍后回复~",
            "看到了！有什么需要帮忙的？",
        ],
    },
    "bilibili": {
        "positive": [
            "感谢三连！下期更精彩~ ✨",
            "弹幕大军收容感谢！持续更新中~",
        ],
        "question": [
            "好问题！置顶评论有补充~",
            "这个展开讲太长了，下期安排~",
        ],
        "negative": [
            "虚心接受建议！会改进的~",
            "每个人的喜好不同，理解~",
        ],
        "dm": [
            "感谢私信！会看的~",
            "收到！有什么想聊的~",
        ],
    },
    "default": {
        "positive": ["感谢支持！❤️", "谢谢认可！会继续努力的~"],
        "question": ["好问题！我来解答~", "这个很关键，后续详细说~"],
        "negative": ["感谢反馈！会改进的~", "理解你的感受~"],
        "dm": ["收到！稍后回复~", "感谢关注！有什么问题尽管问~"],
    },
}


def analyze_comment_sentiment(comment):
    """简单情感分析"""
    positive_keywords = [
        "好", "赞", "棒", "牛", "厉害", "喜欢", "爱了", "绝了",
        "优秀", "干货", "收藏", "实用", "不错", "支持", "感谢",
        "学到了", "受用", "心动", "种草", "美", "帅", "酷",
        "哈哈", "笑死", "爱", "❤️", "👍", "🔥", "✨", "💕",
    ]
    negative_keywords = [
        "差", "烂", "假", "骗", "坑", "垃圾", "浪费", "无聊",
        "没用", "不靠谱", "踩雷", "差评", "无语", "失望",
        "太假", "广告", "水军", "不推荐", "别买", "恶心",
    ]
    question_keywords = [
        "？", "?", "怎么", "如何", "为什么", "请问", "吗",
        "哪", "什么", "多少", "多久", "哪里", "能不能",
    ]

    score = {"positive": 0, "negative": 0, "question": 0}

    for kw in positive_keywords:
        if kw in comment:
            score["positive"] += 1

    for kw in negative_keywords:
        if kw in comment:
            score["negative"] += 1

    for kw in question_keywords:
        if kw in comment:
            score["question"] += 1

    if score["question"] >= 1:
        return "question"
    if score["positive"] > score["negative"]:
        return "positive"
    if score["negative"] > score["positive"]:
        return "negative"
    return "neutral"


def generate_reply(comment, context="", platform="general", tone="auto"):
    """
    生成评论/私信回复
    comment: 原始评论内容
    context: 帖子上下文（可选）
    platform: 平台
    tone: auto(自动判断) / friendly / professional / humorous
    """
    sentiment = analyze_comment_sentiment(comment)

    # 选择回复类型
    if context and len(context) > 10:
        reply_type = "dm"
    else:
        reply_type = sentiment if sentiment != "neutral" else "positive"

    # 获取平台模板
    templates = REPLY_TEMPLATES.get(platform, REPLY_TEMPLATES["default"])

    # 选择回复
    type_key = reply_type if reply_type in templates else "positive"
    replies = templates.get(type_key, templates["positive"])

    selected_reply = random.choice(replies)

    # 根据语气调整
    if tone == "professional" and platform in ("wechat", "zhihu", "toutiao"):
        selected_reply = re.sub(r'[^\w\s，。！？、；：""''（）—…\u4e00-\u9fff]', '', selected_reply)
    elif tone == "humorous":
        humorous_addons = [
            "😂", "笑不活了", "绝绝子", "懂的自然懂~",
            "哈哈哈", "绷不住了",
        ]
        selected_reply += f" {random.choice(humorous_addons)}"

    return {
        "original_comment": comment,
        "sentiment": sentiment,
        "reply_type": reply_type,
        "suggested_reply": selected_reply,
        "platform": PLATFORMS.get(platform, {}).get("name", platform),
        "confidence": 0.8 if sentiment != "neutral" else 0.5,
    }


def batch_generate_replies(comments, platform="general", tone="auto"):
    """批量生成回复"""
    results = []
    for comment in comments:
        if isinstance(comment, dict):
            text = comment.get("text", comment.get("content", ""))
            ctx = comment.get("context", "")
        else:
            text = str(comment)
            ctx = ""
        results.append(generate_reply(text, ctx, platform, tone))
    return results


# ============================================================
# 内容质量评分
# ============================================================

def content_score(text, platform="general"):
    """
    评估内容质量 + AI检测风险
    返回: 质量分(0-100) + AI风险分(0-100, 越高越像AI)
    """
    char_count = len(text)
    sentence_count = len(re.split(r'[。！？\n]', text))
    valid_sentences = [s.strip() for s in re.split(r'[。！？\n]', text) if s.strip()]
    avg_sentence_len = char_count / max(sentence_count, 1)

    quality = {
        "length_score": min(char_count / 200, 1.0) * 25,
        "variety_score": 0,
        "engagement_score": 0,
        "originality_score": 0,
    }

    # 句长多样性
    if len(valid_sentences) > 2:
        lengths = [len(s) for s in valid_sentences]
        length_std = (sum((l - avg_sentence_len) ** 2 for l in lengths) / len(lengths)) ** 0.5
        quality["variety_score"] = min(length_std / 15, 1.0) * 25
    else:
        quality["variety_score"] = 10

    # 互动性
    engagement_markers = 0
    engagement_markers += len(re.findall(r'[？?]', text))
    engagement_markers += len(re.findall(r'[🔥💡✨💕👍❤️🌟💯🎯📌💪👀]', text))
    engagement_markers += len(re.findall(r'(你|大家|姐妹|兄弟|老铁|宝子|朋友)', text))
    quality["engagement_score"] = min(engagement_markers / 3, 1.0) * 25

    # 原创性
    transition_count = sum(1 for w in TRANSITION_WORDS if w in text)
    formality_count = sum(1 for f in COLLOQUIAL_MAP.keys() if f in text)
    originality_penalty = (transition_count * 3 + formality_count * 2)
    quality["originality_score"] = max(0, 25 - originality_penalty)

    total_quality = sum(quality.values())

    # AI检测风险评分
    ai_risk = 0
    ai_risk += min(transition_count * 8, 30)
    if len(valid_sentences) > 3:
        lengths = [len(s) for s in valid_sentences]
        length_std = (sum((l - avg_sentence_len) ** 2 for l in lengths) / len(lengths)) ** 0.5
        if length_std < 5:
            ai_risk += 25
        elif length_std < 10:
            ai_risk += 15
    ai_risk += min(formality_count * 5, 25)
    colloquial_markers = len(re.findall(r'(嘛|呗|哈|嗯|吧|呢|呀|啦|哦|噢)', text))
    if colloquial_markers == 0:
        ai_risk += 20
    elif colloquial_markers < 2:
        ai_risk += 10

    ai_risk = min(ai_risk, 100)

    return {
        "quality_score": round(total_quality, 1),
        "quality_breakdown": {k: round(v, 1) for k, v in quality.items()},
        "ai_risk_score": round(ai_risk, 1),
        "ai_risk_level": "低" if ai_risk < 30 else "中" if ai_risk < 60 else "高",
        "suggestions": _generate_suggestions(quality, ai_risk, transition_count, formality_count),
        "char_count": char_count,
        "sentence_count": sentence_count,
        "avg_sentence_len": round(avg_sentence_len, 1),
    }


def _generate_suggestions(quality, ai_risk, transition_count, formality_count):
    """生成改进建议"""
    suggestions = []

    if ai_risk > 60:
        suggestions.append("⚠️ AI味较重，建议使用 anti_ai_rewrite 进行去AI味改写")
    elif ai_risk > 30:
        suggestions.append("💡 AI味中等，可适当调整口语化表达")

    if transition_count > 3:
        suggestions.append(f"🗑 发现{transition_count}个过渡词，建议删除（首先/其次/总之等）")

    if formality_count > 5:
        suggestions.append(f"📝 发现{formality_count}个书面词汇，建议替换为口语化表达")

    if quality["variety_score"] < 15:
        suggestions.append("📏 句长过于均匀，建议混合长短句，打破节奏规律")

    if quality["engagement_score"] < 10:
        suggestions.append("💬 互动性不足，建议加入提问、emoji或口语化称呼")

    if not suggestions:
        suggestions.append("✅ 内容质量良好，AI味较低")

    return suggestions


# ============================================================
# 内容日历规划
# ============================================================

def content_calendar(niche, days=7, platforms=None):
    """
    生成内容日历
    niche: 领域/赛道
    days: 规划天数
    platforms: 目标平台列表
    """
    if platforms is None:
        platforms = ["xiaohongshu", "douyin", "wechat"]

    content_types = {
        "xiaohongshu": ["干货合集", "好物推荐", "对比测评", "教程攻略", "生活vlog", "穿搭/场景展示"],
        "douyin": ["干货口播", "反转剧情", "沉浸体验", "科普解说", "挑战/互动", "热点点评"],
        "wechat": ["深度长文", "行业分析", "案例拆解", "观点评论", "方法论总结", "资源合集"],
        "weibo": ["热点观点", "互动话题", "资讯速递", "金句文案", "投票互动", "抽奖转发"],
        "bilibili": ["教程干货", "评测对比", "趣味实验", "知识科普", "Vlog", "二创"],
        "toutiao": ["深度解读", "热点追踪", "数据报告", "行业洞察", "人物故事", "实用指南"],
        "zhihu": ["专业回答", "经验分享", "数据分析", "方法论", "行业解读", "辟谣科普"],
        "kuaishou": ["生活分享", "实用技巧", "搞笑段子", "接地气教程", "真实体验", "老铁互动"],
    }

    calendar = []
    start_date = datetime.now()

    for day in range(days):
        date = start_date + timedelta(days=day)
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()]

        daily_plan = {
            "date": date.strftime("%Y-%m-%d"),
            "weekday": weekday,
            "tasks": [],
        }

        for platform in platforms:
            config = PLATFORMS.get(platform)
            if not config:
                continue

            types = content_types.get(platform, content_types["xiaohongshu"])
            selected_type = types[day % len(types)]
            posting_time = config["posting_peak"][day % len(config["posting_peak"])]

            daily_plan["tasks"].append({
                "platform": config["name"],
                "platform_key": platform,
                "content_type": selected_type,
                "topic_hint": f"{niche}相关{selected_type}",
                "posting_time": posting_time,
                "needs_image": platform in ("xiaohongshu", "weibo"),
                "needs_video": platform in ("douyin", "kuaishou", "bilibili"),
            })

        calendar.append(daily_plan)

    return {
        "niche": niche,
        "days": days,
        "platforms": [PLATFORMS.get(p, {}).get("name", p) for p in platforms],
        "calendar": calendar,
    }


# ============================================================
# 竞品分析框架
# ============================================================

def competitor_analysis_template(niche, platform="general"):
    """
    生成竞品分析框架（供agent搜索后填充）
    """
    template = {
        "niche": niche,
        "platform": PLATFORMS.get(platform, {}).get("name", platform),
        "analysis_dimensions": [
            {
                "dimension": "内容策略",
                "questions": [
                    f"在{niche}赛道，头部账号主要发什么类型的内容？",
                    "发文频率和时间段有什么规律？",
                    "标题和封面有什么共性特征？",
                ],
                "search_queries": [
                    f"{niche} 自媒体 头部账号",
                    f"{niche} 小红书 爆款笔记",
                    f"{niche} 抖音 热门视频",
                ],
            },
            {
                "dimension": "互动数据",
                "questions": [
                    "平均点赞/评论/转发比例是多少？",
                    "什么类型的内容互动率最高？",
                    "评论区用户主要在讨论什么？",
                ],
                "search_queries": [
                    f"{niche} 互动率 数据",
                    f"{niche} 爆款 数据分析",
                ],
            },
            {
                "dimension": "差异化机会",
                "questions": [
                    "竞品的内容有什么共性问题或空白？",
                    "用户在评论区抱怨什么？",
                    "哪些细分话题还没有被充分覆盖？",
                ],
                "search_queries": [
                    f"{niche} 痛点 用户需求",
                    f"{niche} 内容空白 蓝海",
                ],
            },
            {
                "dimension": "变现模式",
                "questions": [
                    "头部账号的主要变现方式是什么？",
                    "带货/广告/付费内容的比例如何？",
                    "有哪些创新的变现模式？",
                ],
                "search_queries": [
                    f"{niche} 自媒体 变现",
                    f"{niche} 带货 数据",
                ],
            },
        ],
        "competitor_tracking_fields": [
            "账号名称", "粉丝数", "平均互动率", "内容类型占比",
            "发文频率", "热门话题", "变现方式", "差异化标签",
        ],
    }

    return template


# ============================================================
# 热点搜索
# ============================================================

def trending_search(topic="", platform="general"):
    """
    热点搜索 - 使用公开API获取各平台热搜
    """
    results = {
        "platform": PLATFORMS.get(platform, {}).get("name", platform),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trending": [],
        "source": "",
    }

    # 微博热搜 (公开API)
    if platform in ("weibo", "general"):
        try:
            resp = requests.get(
                "https://weibo.com/ajax/side/hotSearch",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                realtime = data.get("data", {}).get("realtime", [])
                for item in realtime[:10]:
                    results["trending"].append({
                        "title": item.get("note", ""),
                        "rank": item.get("rank", 0),
                        "hot": item.get("num", 0),
                        "source": "weibo",
                    })
                results["source"] = "weibo_hot"
        except Exception:
            results["source"] = "weibo_unavailable"

    # 知乎热榜
    if platform in ("zhihu", "general") and not results["trending"]:
        try:
            resp = requests.get(
                "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total",
                params={"limit": 10},
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", [])[:10]:
                    target = item.get("target", {})
                    results["trending"].append({
                        "title": target.get("title", ""),
                        "hot": target.get("excerpt", "")[:50],
                        "source": "zhihu",
                    })
                results["source"] = "zhihu_hot"
        except Exception:
            if not results["source"]:
                results["source"] = "zhihu_unavailable"

    # 关键词搜索补充
    if topic:
        results["keyword"] = topic
        results["suggestion"] = f"建议搜索: {topic} 热点 趋势 最新"

    if not results["trending"]:
        results["suggestion"] = "热门API暂时不可用，建议搜索相关热点"

    return results


# ============================================================
# 违禁词查询
# ============================================================

def get_banned_words(industry, platform=None):
    """
    查询行业违禁词
    industry: 行业名称
    platform: 可选，指定平台
    """
    result = INDUSTRY_BANNED_WORDS.get(industry)
    if not result:
        # 模糊匹配
        matches = [k for k in INDUSTRY_BANNED_WORDS.keys() if industry in k or k in industry]
        if matches:
            result = INDUSTRY_BANNED_WORDS[matches[0]]
            industry = matches[0]
        else:
            return {
                "error": f"未找到行业: {industry}",
                "available_industries": list(INDUSTRY_BANNED_WORDS.keys()),
                "suggestion": f"建议搜索: {industry} 小红书/抖音 违禁词 限流词",
            }

    # 如果指定了平台，只返回该平台的违禁词
    if platform:
        platform_words = result.get(platform, result.get("通用", []))
        all_words = set(platform_words)
        return {
            "industry": industry,
            "platform": platform,
            "banned_words": sorted(list(all_words)),
            "total_count": len(all_words),
            "warning": "⚠️ 使用以上词汇可能导致内容被限流、下架或账号处罚",
        }

    # 汇总所有平台的违禁词
    all_words = set()
    for platform_words in result.values():
        all_words.update(platform_words)

    return {
        "industry": industry,
        "banned_words_by_platform": result,
        "all_banned_words": sorted(list(all_words)),
        "total_count": len(all_words),
        "warning": "⚠️ 使用以上词汇可能导致内容被限流、下架或账号处罚，发布前务必检查",
        "tip": "每个平台审核标准不同，建议发布前在对应平台搜索该词是否被限流",
    }


# ============================================================
# 平台信息
# ============================================================

def get_platforms_info():
    """返回支持的平台信息"""
    info = {}
    for key, config in PLATFORMS.items():
        info[key] = {
            "name": config["name"],
            "max_title": config["max_title"],
            "max_content": config["max_content"],
            "tone": config["tone"],
            "image_ratio": config["image_ratio"],
            "posting_peak": config["posting_peak"],
        }
    return info
