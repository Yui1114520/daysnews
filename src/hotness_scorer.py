"""
国际新闻五维热度评分引擎

完整实现：
H_最终 = max(0, (0.35A + 0.25B + 0.20C + 0.15D + 0.05E) × K + 加分 - 扣分)

A: 全域传播体量  B: 用户互动深度  C: 国际权威背书
D: 跨国辐射广度  E: 时效衰减修正  K: 降噪修正系数
"""
import json
import re
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from src.config import (
    HOTNESS_HISTORY_FILE,
    HOTNESS_WEIGHTS,
    PROPAGATION_SUB_WEIGHTS,
    INTERACTION_SUB_WEIGHTS,
    AUTHORITY_SUB_WEIGHTS,
    RADIATION_SUB_WEIGHTS,
    DECAY_SUB_WEIGHTS,
    MEDIA_TIER_SCORE,
    GLOBAL_WIRE_AGENCIES,
    INTERNATIONAL_ORGS,
    BONUS_PENALTY_CAP,
    DEFAULT_K,
    HOTNESS_HISTORY_DAYS,
)


# ============================================================
# 历史对比池管理
# ============================================================

def load_hotness_history() -> List[Dict]:
    """加载近7天热度历史对比池"""
    if not HOTNESS_HISTORY_FILE.exists():
        return []
    try:
        with open(HOTNESS_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_hotness_history(history: List[Dict]) -> None:
    """保存热度历史（只保留7天）"""
    cutoff = datetime.now().timestamp() - HOTNESS_HISTORY_DAYS * 24 * 3600
    cleaned = [h for h in history if h.get('scored_at', 0) > cutoff]
    # 最多保留 2000 条
    cleaned = cleaned[-2000:]
    with open(HOTNESS_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)


def add_to_history(news_with_scores: List[Dict]) -> None:
    """将本次评分的新闻加入历史对比池"""
    history = load_hotness_history()
    now = datetime.now().timestamp()
    for news in news_with_scores:
        history.append({
            'title': news.get('title', ''),
            'raw_scores': news.get('_raw_indicators', {}),
            'final_score': news.get('hotness_score', 0),
            'scored_at': now,
        })
    save_hotness_history(history)


# ============================================================
# Min-Max 归一化
# ============================================================

def minmax_normalize(value: float, history_values: List[float]) -> float:
    """
    将单条指标归一化到 0-100 分
    X = (当前值 - 最小值) / (最大值 - 最小值) × 100
    """
    if not history_values:
        # 没有历史数据，用自身
        return 50.0  # 默认中等分

    min_val = min(history_values)
    max_val = max(history_values)

    if max_val == min_val:
        return 50.0  # 所有值都一样

    normalized = (value - min_val) / (max_val - min_val) * 100.0

    # 上限封顶100，下限兜底0
    return max(0.0, min(100.0, normalized))


# ============================================================
# A 子系统：全域传播体量（35%）
# ============================================================

def _calc_A_propagation(news: Dict, history: List[Dict]) -> float:
    """
    A = overseas_social(50%) + domestic_total(20%) + wire_agency(20%) + local_media(10%)
    """
    # ---- A1: 海外社交平台曝光 (50%) ----
    # 基于 NewsAPI 的 source 数量 和 来源多样性估算
    source_count = news.get('source_count', 1)
    source_diversity = news.get('source_diversity', 1)  # 不同源的种类数
    overseas_social_raw = source_count * 5 + source_diversity * 10

    # ---- A2: 国内全网总曝光 (20%) ----
    # 微博数据 / 百度指数
    weibo_reads = news.get('weibo_reads', 0)
    baidu_index = news.get('baidu_index', 0)
    domestic_total_raw = weibo_reads * 0.1 + baidu_index * 0.5

    # ---- A3: 国际通讯社转载量 (20%) ----
    wire_count = news.get('wire_agency_count', 0)
    wire_agency_raw = wire_count * 15

    # ---- A4: 各国本土媒体转载数 (10%) ----
    local_media_count = news.get('local_media_count', 0)
    local_media_raw = local_media_count * 8

    # 从历史池中提取各指标原始值用于归一化
    hist_overseas = [h.get('raw_scores', {}).get('a1_overseas_raw', 0) for h in history] or [overseas_social_raw]
    hist_domestic = [h.get('raw_scores', {}).get('a2_domestic_raw', 0) for h in history] or [domestic_total_raw]
    hist_wire = [h.get('raw_scores', {}).get('a3_wire_raw', 0) for h in history] or [wire_agency_raw]
    hist_local = [h.get('raw_scores', {}).get('a4_local_raw', 0) for h in history] or [local_media_raw]

    # 归一化各子指标
    a1 = minmax_normalize(overseas_social_raw, hist_overseas)
    a2 = minmax_normalize(domestic_total_raw, hist_domestic)
    a3 = minmax_normalize(wire_agency_raw, hist_wire)
    a4 = minmax_normalize(local_media_raw, hist_local)

    A = (
        a1 * PROPAGATION_SUB_WEIGHTS["overseas_social"] +
        a2 * PROPAGATION_SUB_WEIGHTS["domestic_total"] +
        a3 * PROPAGATION_SUB_WEIGHTS["wire_agency"] +
        a4 * PROPAGATION_SUB_WEIGHTS["local_media"]
    )

    # 存储原始值供历史对比
    news['_raw_indicators'] = news.get('_raw_indicators', {})
    news['_raw_indicators'].update({
        'a1_overseas_raw': overseas_social_raw,
        'a2_domestic_raw': domestic_total_raw,
        'a3_wire_raw': wire_agency_raw,
        'a4_local_raw': local_media_raw,
    })

    return A


# ============================================================
# B 子系统：用户互动深度（25%）
# ============================================================

def _calc_B_interaction(news: Dict, history: List[Dict]) -> float:
    """
    B = multilingual_comments(45%) + cross_platform_share(30%)
        + deep_analysis(15%) + search_index(10%)
    """
    # ---- B1: 多语种有效评论 (45%) ----
    comment_count = news.get('comment_count', 0)
    long_comment_ratio = news.get('long_comment_ratio', 0.1)  # 长评论占比
    multilingual_comments_raw = comment_count * (1 + long_comment_ratio * 2)

    # ---- B2: 跨平台转发分享 (30%) ----
    share_count = news.get('share_count', 0)
    retweet_count = news.get('retweet_count', 0)
    cross_platform_share_raw = share_count + retweet_count * 1.5

    # ---- B3: 全网解析二创内容 (15%) ----
    analysis_count = news.get('analysis_count', 0)
    deep_analysis_raw = analysis_count * 10

    # ---- B4: 各国搜索指数均值 (10%) ----
    search_index_raw = news.get('search_index', 0)

    hist_comments = [h.get('raw_scores', {}).get('b1_comments_raw', 0) for h in history] or [multilingual_comments_raw]
    hist_share = [h.get('raw_scores', {}).get('b2_share_raw', 0) for h in history] or [cross_platform_share_raw]
    hist_analysis = [h.get('raw_scores', {}).get('b3_analysis_raw', 0) for h in history] or [deep_analysis_raw]
    hist_search = [h.get('raw_scores', {}).get('b4_search_raw', 0) for h in history] or [search_index_raw]

    b1 = minmax_normalize(multilingual_comments_raw, hist_comments)
    b2 = minmax_normalize(cross_platform_share_raw, hist_share)
    b3 = minmax_normalize(deep_analysis_raw, hist_analysis)
    b4 = minmax_normalize(search_index_raw, hist_search)

    B = (
        b1 * INTERACTION_SUB_WEIGHTS["multilingual_comments"] +
        b2 * INTERACTION_SUB_WEIGHTS["cross_platform_share"] +
        b3 * INTERACTION_SUB_WEIGHTS["deep_analysis"] +
        b4 * INTERACTION_SUB_WEIGHTS["search_index"]
    )

    news['_raw_indicators'] = news.get('_raw_indicators', {})
    news['_raw_indicators'].update({
        'b1_comments_raw': multilingual_comments_raw,
        'b2_share_raw': cross_platform_share_raw,
        'b3_analysis_raw': deep_analysis_raw,
        'b4_search_raw': search_index_raw,
    })

    return B


# ============================================================
# C 子系统：国际权威背书强度（20%）
# ============================================================

def _calc_C_authority(news: Dict, history: List[Dict]) -> float:
    """
    C = media_tier(50%) + official_statement(30%) + intl_org(20%)
    """
    # ---- C1: 全球头部媒体版面层级 (50%) ----
    source_tiers = news.get('source_tiers', ['C'])
    tier_scores = [MEDIA_TIER_SCORE.get(t, 25) for t in source_tiers]
    media_tier_raw = max(tier_scores) * 0.7 + (sum(tier_scores) / len(tier_scores)) * 0.3

    # ---- C2: 主权国家政要表态数量 (30%) ----
    official_count = news.get('official_statement_count', 0)
    official_raw = official_count * 20

    # ---- C3: 国际组织发声/会议 (20%) ----
    intl_org_count = news.get('intl_org_count', 0)
    intl_org_raw = intl_org_count * 25

    hist_media = [h.get('raw_scores', {}).get('c1_media_raw', 0) for h in history] or [media_tier_raw]
    hist_official = [h.get('raw_scores', {}).get('c2_official_raw', 0) for h in history] or [official_raw]
    hist_intl = [h.get('raw_scores', {}).get('c3_intl_raw', 0) for h in history] or [intl_org_raw]

    c1 = minmax_normalize(media_tier_raw, hist_media)
    c2 = minmax_normalize(official_raw, hist_official)
    c3 = minmax_normalize(intl_org_raw, hist_intl)

    C = (
        c1 * AUTHORITY_SUB_WEIGHTS["media_tier"] +
        c2 * AUTHORITY_SUB_WEIGHTS["official_statement"] +
        c3 * AUTHORITY_SUB_WEIGHTS["intl_org"]
    )

    news['_raw_indicators'] = news.get('_raw_indicators', {})
    news['_raw_indicators'].update({
        'c1_media_raw': media_tier_raw,
        'c2_official_raw': official_raw,
        'c3_intl_raw': intl_org_raw,
    })

    return C


# ============================================================
# D 子系统：跨国辐射广度（15%）
# ============================================================

# 大洲映射
COUNTRY_CONTINENT_MAP = {
    # 简易版，通过区域推导大洲
    "中东与北非": "亚洲+非洲",
    "拉美与加勒比": "南美洲",
    "中亚与高加索": "亚洲",
    "东亚与太平洋": "亚洲+大洋洲",
    "撒哈拉以南非洲": "非洲",
    "东欧": "欧洲",
    "西欧南欧与北欧": "欧洲",
    "南亚与东南亚": "亚洲",
    "北美": "北美洲",
}


def _calc_D_radiation(news: Dict, history: List[Dict]) -> float:
    """
    D = country_count(40%) + continent_count(35%) + chain_effect(25%)
    """
    # ---- D1: 覆盖独立国家数量 (40%) ----
    country_count = news.get('country_count', 1)
    country_raw = country_count * 12

    # ---- D2: 跨大洲分布 (35%) ----
    regions = news.get('regions', [])
    continents = set()
    for r in regions:
        cont = COUNTRY_CONTINENT_MAP.get(r, "其他")
        for c in cont.split("+"):
            continents.add(c.strip())
    continent_count = len(continents)
    continent_raw = continent_count * 25

    # ---- D3: 跨境连锁影响 (25%) ----
    # 检测贸易/汇率/边境/外交连锁反应关键词
    text = f"{news.get('title', '')} {news.get('description', '')}".lower()
    chain_keywords = [
        "ripple effect", "spillover", "contagion", "domino",
        "cross-border", "border closure", "sanction", "embargo",
        "supply chain disruption", "currency volatility",
        "连锁", "波及", "溢出", "跨境", "蔓延"
    ]
    chain_hits = sum(1 for kw in chain_keywords if kw in text)
    chain_raw = chain_hits * 15

    hist_country = [h.get('raw_scores', {}).get('d1_country_raw', 0) for h in history] or [country_raw]
    hist_continent = [h.get('raw_scores', {}).get('d2_continent_raw', 0) for h in history] or [continent_raw]
    hist_chain = [h.get('raw_scores', {}).get('d3_chain_raw', 0) for h in history] or [chain_raw]

    d1 = minmax_normalize(country_raw, hist_country)
    d2 = minmax_normalize(continent_raw, hist_continent)
    d3 = minmax_normalize(chain_raw, hist_chain)

    D = (
        d1 * RADIATION_SUB_WEIGHTS["country_count"] +
        d2 * RADIATION_SUB_WEIGHTS["continent_count"] +
        d3 * RADIATION_SUB_WEIGHTS["chain_effect"]
    )

    news['_raw_indicators'] = news.get('_raw_indicators', {})
    news['_raw_indicators'].update({
        'd1_country_raw': country_raw,
        'd2_continent_raw': continent_raw,
        'd3_chain_raw': chain_raw,
        'continent_count': continent_count,
    })

    return D


# ============================================================
# E 子系统：时效衰减修正（5%）
# ============================================================

def _calc_E_decay(news: Dict, history: List[Dict]) -> float:
    """
    E = time_decay(60%) + breaking_bonus(40%)
    """
    published_str = news.get('published_at', '')
    try:
        if published_str:
            # 支持 ISO 格式和常见格式
            published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
        else:
            published_dt = datetime.now(timezone.utc)
    except (ValueError, TypeError):
        published_dt = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    age_hours = (now - published_dt).total_seconds() / 3600.0

    # ---- E1: 发布时长衰减 (60%) ----
    # 24小时内基本不衰减，之后线性衰减
    if age_hours <= 6:
        time_decay_raw = 100
    elif age_hours <= 24:
        time_decay_raw = 100 - (age_hours - 6) * 2.0  # 6-24h: 100→64
    elif age_hours <= 72:
        time_decay_raw = 64 - (age_hours - 24) * 0.8   # 24-72h: 64→26
    else:
        time_decay_raw = max(5, 26 - (age_hours - 72) * 0.2)

    # ---- E2: 突发事件加成 (40%) ----
    text = f"{news.get('title', '')} {news.get('description', '')}".lower()
    breaking_keywords = [
        "breaking", "urgent", "just in", "alert",
        "war", "explosion", "earthquake", "coup",
        "assassination", "resign", "emergency",
        "突发", "紧急", "爆炸", "地震", "政变", "暗杀",
        "辞职", "紧急状态", "宣战", "空袭"
    ]
    breaking_hits = sum(1 for kw in breaking_keywords if kw in text)
    breaking_bonus_raw = breaking_hits * 30

    hist_time = [h.get('raw_scores', {}).get('e1_time_raw', 0) for h in history] or [time_decay_raw]
    hist_break = [h.get('raw_scores', {}).get('e2_break_raw', 0) for h in history] or [breaking_bonus_raw]

    e1 = minmax_normalize(time_decay_raw, hist_time)
    e2 = minmax_normalize(breaking_bonus_raw, hist_break)

    E = (
        e1 * DECAY_SUB_WEIGHTS["time_decay"] +
        e2 * DECAY_SUB_WEIGHTS["breaking_bonus"]
    )

    news['_raw_indicators'] = news.get('_raw_indicators', {})
    news['_raw_indicators'].update({
        'e1_time_raw': time_decay_raw,
        'e2_break_raw': breaking_bonus_raw,
        'age_hours': age_hours,
    })

    return E


# ============================================================
# K 降噪修正系数（0.3 ~ 1.0）
# ============================================================

def _calc_K_noise_reduction(news: Dict) -> float:
    """
    计算 K，综合考虑来源可信度、水军特征、辟谣情况等
    """
    k = DEFAULT_K  # 从默认值开始

    title = news.get('title', '')
    description = news.get('description', '')
    text = f"{title} {description}".lower()

    # 1. 来源权威度检测
    source_tiers = news.get('source_tiers', ['C'])
    tier_list = [MEDIA_TIER_SCORE.get(t, 25) for t in source_tiers]
    avg_tier = sum(tier_list) / len(tier_list) if tier_list else 25

    if avg_tier >= 90:
        k += 0.10  # 顶级源加分
    elif avg_tier >= 70:
        k += 0.05
    elif avg_tier <= 30:
        k -= 0.20  # 低质量源扣分

    # 2. 无海外媒体跟进 → K=0.6
    wire_count = news.get('wire_agency_count', 0)
    overseas_source = news.get('overseas_source_count', 0)
    if wire_count == 0 and overseas_source == 0:
        k = min(k, 0.65)  # 没有海外源跟进

    # 3. 仅国内自媒体炒作
    if news.get('is_domestic_only', False):
        k = min(k, 0.6)

    # 4. 娱乐化/花边检测
    entertainment_kw = [
        "celebrity", "gossip", "viral video", "tiktok trend",
        "scandal", "affair", "明星", "八卦", "绯闻", "网红"
    ]
    ent_hits = sum(1 for kw in entertainment_kw if kw in text)
    if ent_hits >= 2:
        k -= 0.20  # 娱乐化严重
    elif ent_hits >= 1:
        k -= 0.10

    # 5. 辟谣检测
    debunk_kw = ["fake news", "debunk", "false claim", "辟谣", "不实", "虚假"]
    if any(kw in text for kw in debunk_kw):
        k = 0.2  # 被辟谣，热度大幅作废

    # 6. 来源多样性：如果多个独立来源报道同一新闻
    unique_sources = news.get('unique_source_count', 1)
    if unique_sources >= 5:
        k += 0.08
    elif unique_sources >= 3:
        k += 0.04

    # 最终限制在 0.2 ~ 1.0 区间
    return max(0.2, min(1.0, k))


# ============================================================
# 浮动加减分（±10）
# ============================================================

def _calc_bonus_penalty(news: Dict) -> Tuple[float, float]:
    """
    计算加分项和扣分项，各自上限 10 分
    返回 (加分, 扣分)
    """
    title = news.get('title', '')
    description = news.get('description', '')
    text = f"{title} {description}".lower()

    bonus = 0.0
    penalty = 0.0

    # ========== 加分项 ==========

    # 1. 多国联合外交抗议/双边紧急会谈：+3~5
    protest_kw = ["joint protest", "diplomatic protest", "emergency talk",
                   "summon ambassador", "expel diplomat", "recall ambassador",
                   "联合抗议", "紧急会谈", "召回大使", "驱逐外交官"]
    if any(kw in text for kw in protest_kw):
        bonus += 4.0

    # 2. 联合国、安理会召开紧急会议：+4~6
    un_emergency_kw = ["security council emergency", "UN emergency session",
                       "general assembly emergency", "安理会紧急", "联大紧急"]
    if any(kw in text for kw in un_emergency_kw):
        bonus += 5.0

    # 3. 全球大宗商品/外汇/股市同步剧烈波动：+2~4
    market_kw = ["market turmoil", "stock plunge", "currency crash",
                 "oil price surge", "bond yield spike", "circuit breaker",
                 "股市暴跌", "熔断", "油价飙升", "汇率暴跌"]
    if any(kw in text for kw in market_kw):
        bonus += 3.0

    # 4. 多国爆发街头游行/边境军事调动：+2~3
    mass_kw = ["mass protest nationwide", "border mobilization", "military buildup",
               "nationwide strike", "martial law", "全国抗议", "军事集结", "戒严"]
    if any(kw in text for kw in mass_kw):
        bonus += 2.5

    # ========== 扣分项 ==========

    # 1. 仅单一小国地方民生，无任何跨境影响：-4
    regions = news.get('regions', [])
    country_count = news.get('country_count', 1)
    continent_count = news.get('_raw_indicators', {}).get('continent_count', 1)
    if country_count <= 1 and continent_count <= 1 and "跨区域" not in regions:
        penalty += 4.0

    # 2. 通篇娱乐化解读，无实质讨论：-3~6
    entertainment_kw = ["viral", "trending", "meme", "funny", "cute",
                        "celebrity", "网红", "搞笑"]
    ent_count = sum(1 for kw in entertainment_kw if kw in text)
    if ent_count >= 3:
        penalty += 5.0
    elif ent_count >= 1:
        penalty += 3.0

    # 3. 间隔3天以上无新增媒体跟进：-2
    age_hours = news.get('_raw_indicators', {}).get('age_hours', 0)
    follow_up = news.get('follow_up_count', 1)
    if age_hours > 72 and follow_up <= 0:
        penalty += 2.0

    # 限制在 0~10 范围内
    return min(bonus, BONUS_PENALTY_CAP), min(penalty, BONUS_PENALTY_CAP)


# ============================================================
# 主入口：计算单条新闻的最终热度分
# ============================================================

def calculate_hotness_scores(news_list: List[Dict]) -> List[Dict]:
    """
    对新闻列表逐一计算最终热度分

    输入每条新闻需包含：
    - title, description, url, published_at（必填）
    - source_count, source_diversity, source_tiers（来源相关）
    - weibo_reads, baidu_index, comment_count, share_count 等（平台数据，可选）
    - regions, country_count（区域和跨国相关）
    - wire_agency_count, local_media_count, overseas_source_count（传播相关）

    输出会添加：
    - hotness_score: 最终热度分 0-100
    - hotness_detail: 各维度得分明细
    """
    history = load_hotness_history()

    for news in news_list:
        # 初始化 raw_indicators
        news['_raw_indicators'] = {}

        # 计算五大维度
        A = _calc_A_propagation(news, history)
        B = _calc_B_interaction(news, history)
        C = _calc_C_authority(news, history)
        D = _calc_D_radiation(news, history)
        E = _calc_E_decay(news, history)

        # 基础热度 H = 0.35A + 0.25B + 0.20C + 0.15D + 0.05E
        H = (
            HOTNESS_WEIGHTS["A_propagation"] * A +
            HOTNESS_WEIGHTS["B_interaction"] * B +
            HOTNESS_WEIGHTS["C_authority"] * C +
            HOTNESS_WEIGHTS["D_radiation"] * D +
            HOTNESS_WEIGHTS["E_decay"] * E
        )

        # 降噪修正 K
        K = _calc_K_noise_reduction(news)

        # 修正后基础热度
        H_corrected = H * K

        # 浮动加减分
        bonus, penalty = _calc_bonus_penalty(news)

        # 最终热度分
        H_final = max(0.0, H_corrected + bonus - penalty)

        # 四舍五入到1位小数
        news['hotness_score'] = round(H_final, 1)
        news['hotness_detail'] = {
            'A_propagation': round(A, 1),
            'B_interaction': round(B, 1),
            'C_authority': round(C, 1),
            'D_radiation': round(D, 1),
            'E_decay': round(E, 1),
            'base_H': round(H, 1),
            'K_factor': round(K, 2),
            'H_corrected': round(H_corrected, 1),
            'bonus': round(bonus, 1),
            'penalty': round(penalty, 1),
        }
        # 清理临时数据
        del news['_raw_indicators']

    # 将本次数据加入历史池
    add_to_history(news_list)

    return news_list


def get_heat_level(score: float) -> str:
    """
    热度分级
    0-30: 低热度  30-60: 中等热度
    60-80: 高热度  80-100: 顶级全球热点
    """
    if score >= 80:
        return "🔴 顶级全球热点"
    elif score >= 60:
        return "🟠 高热度"
    elif score >= 30:
        return "🟡 中等热度"
    else:
        return "🟢 低热度"
