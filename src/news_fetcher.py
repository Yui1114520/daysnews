"""
多源新闻抓取模块
- NewsAPI 调用（10 大领域 × 多组关键词搜索）
- RSS 源并行聚合
- 国内平台数据补充
- 时间窗口过滤
- 多源去重合并
"""
import json
import hashlib
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote

import feedparser
import requests

from src.config import (
    NEWSAPI_KEY,
    DOMAIN_SEARCH_QUERIES,
    RSS_FEEDS,
    GLOBAL_WIRE_AGENCIES,
    INTERNATIONAL_ORGS,
    MEDIA_TIER_SCORE,
    PUSH_SCHEDULE,
)


# ============================================================
# 工具函数
# ============================================================

def _extract_countries(text: str, country_list: List[str]) -> int:
    """从文本中提取出现的国家数量"""
    text_lower = text.lower()
    count = 0
    for country in country_list:
        if country.lower() in text_lower:
            count += 1
    return count


def _extract_wire_agencies(text: str) -> int:
    """从文本中检测国际通讯社数量"""
    text_lower = text.lower()
    count = 0
    for agency in GLOBAL_WIRE_AGENCIES:
        if agency.lower() in text_lower:
            count += 1
    return count


def _extract_intl_orgs(text: str) -> int:
    """从文本中检测国际组织数量"""
    text_lower = text.lower()
    count = 0
    for org in INTERNATIONAL_ORGS:
        if org.lower() in text_lower:
            count += 1
    return count


def _get_source_tier(source_name: str, feed_tier: str = "C") -> str:
    """获取媒体的权威等级"""
    source_lower = source_name.lower()
    # S 级
    s_tier = ["reuters", "associated press", "afp", "bbc", "al jazeera",
              "bloomberg", "nyt", "new york times", "washington post", "ap news"]
    a_tier = ["cnn", "france 24", "dw", "nhk", "euronews", "financial times",
              "guardian", "economist", "scmp", "ndtv", "times of india"]
    b_tier = ["africanews", "mercopress", "moscow times", "arab news",
              "straits times", "jakarta post", "nikkei"]

    for s in s_tier:
        if s in source_lower:
            return "S"
    for a in a_tier:
        if a in source_lower:
            return "A"
    for b in b_tier:
        if b in source_lower:
            return "B"
    return feed_tier if feed_tier in ["S", "A", "B"] else "C"


def _parse_published_date(entry) -> Optional[datetime]:
    """解析 RSS 条目或 API 结果中的发布日期"""
    for attr in ['published_parsed', 'updated_parsed']:
        if hasattr(entry, attr):
            val = getattr(entry, attr)
            if val:
                try:
                    return datetime(*val[:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    pass

    for attr in ['published', 'updated', 'pubDate']:
        if hasattr(entry, attr):
            val = getattr(entry, attr)
            if val:
                try:
                    # 尝试解析常见格式
                    for fmt in [
                        '%a, %d %b %Y %H:%M:%S %z',
                        '%a, %d %b %Y %H:%M:%S %Z',
                        '%Y-%m-%dT%H:%M:%SZ',
                        '%Y-%m-%dT%H:%M:%S%z',
                        '%Y-%m-%d %H:%M:%S',
                    ]:
                        try:
                            return datetime.strptime(val, fmt).replace(tzinfo=timezone.utc) if 'z' not in fmt.lower() else datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
                        except ValueError:
                            continue
                except Exception:
                    pass

    return datetime.now(timezone.utc)


def _get_time_window(session_label: str) -> Tuple[datetime, datetime]:
    """
    获取本次推送的时间窗口
    session_label: "morning" | "noon" | "evening"
    返回: (start_dt, end_dt) UTC时间
    """
    now = datetime.now(timezone.utc)
    schedule = PUSH_SCHEDULE.get(session_label, PUSH_SCHEDULE["noon"])
    window_hours = schedule["window_hours"]
    start_dt = now - timedelta(hours=window_hours)

    # 如果是早上6点推送，窗口往前推
    if session_label == "morning":
        # 前日20:00到现在
        start_dt = now.replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(hours=16)
        end_dt = now.replace(hour=22, minute=0, second=0, microsecond=0)
        if end_dt > now:
            end_dt = now
    else:
        end_dt = now

    return start_dt, end_dt


# ============================================================
# NewsAPI 抓取
# ============================================================

def _fetch_newsapi_for_query(query: str, max_results: int = 5) -> List[Dict]:
    """通过 NewsAPI 搜索单个关键词，返回新闻列表"""
    if not NEWSAPI_KEY:
        return []

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": max_results,
            "apiKey": NEWSAPI_KEY,
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "ok":
            return []

        articles = []
        for art in data.get("articles", []):
            title = art.get("title", "").strip()
            description = art.get("description", "") or ""
            url = art.get("url", "")

            if not title or not url or "[Removed]" in title:
                continue

            source_name = art.get("source", {}).get("name", "")
            published_str = art.get("publishedAt", "")

            text = f"{title} {description}"
            articles.append({
                "title": title,
                "description": description[:300],
                "url": url,
                "source_name": source_name,
                "source_tiers": [_get_source_tier(source_name)],
                "published_at": published_str,
                "source_count": 1,
                "source_diversity": 1,
                "wire_agency_count": _extract_wire_agencies(text),
                "intl_org_count": _extract_intl_orgs(text),
                "overseas_source_count": 1 if source_name else 0,
                "weibo_reads": 0,
                "baidu_index": 0,
                "comment_count": 0,
                "share_count": 0,
                "retweet_count": 0,
                "long_comment_ratio": 0.1,
                "analysis_count": 0,
                "search_index": 0,
                "country_count": 0,
                "regions": [],
                "domains": [],
                "local_media_count": 0,
                "unique_source_count": 1,
                "follow_up_count": 0,
                "is_domestic_only": False,
            })

        return articles

    except Exception as e:
        print(f"  ⚠ NewsAPI 搜索 '{query}' 失败: {e}")
        return []


def fetch_from_newsapi(session_label: str) -> List[Dict]:
    """
    通过 NewsAPI 批量搜索所有领域关键词
    每天免费100次请求，限定80次用于搜索，剩余20次备用
    """
    print("📡 正在从 NewsAPI 抓取新闻...")

    all_articles = []
    seen_urls = set()

    # 每个领域取1-2组最有代表性的关键词
    max_queries = 75  # 留一些余量
    query_count = 0

    for domain, queries in DOMAIN_SEARCH_QUERIES.items():
        if query_count >= max_queries:
            break
        # 每个领域取前2个关键词
        for query in queries[:2]:
            if query_count >= max_queries:
                break
            articles = _fetch_newsapi_for_query(query, max_results=3)
            for art in articles:
                url_hash = art['url']
                if url_hash not in seen_urls:
                    art['domains'] = [domain]
                    all_articles.append(art)
                    seen_urls.add(url_hash)
            query_count += 1

    print(f"  ✅ NewsAPI 获取 {len(all_articles)} 条去重新闻")
    return all_articles


# ============================================================
# RSS 源抓取
# ============================================================

def _fetch_single_rss(feed_info: Dict) -> List[Dict]:
    """抓取单个 RSS 源"""
    url = feed_info['url']
    region = feed_info.get('region', '')
    tier = feed_info.get('tier', 'C')

    try:
        feed = feedparser.parse(url)
        articles = []

        for entry in feed.entries[:10]:  # 每个源最多取10条
            title = entry.get('title', '').strip()
            description = entry.get('summary', '') or entry.get('description', '') or ''

            # 清理 HTML 标签
            description = re.sub(r'<[^>]+>', '', description)[:300]

            link = entry.get('link', '')
            if not title or not link:
                continue

            pub_dt = _parse_published_date(entry)
            source_name = feed_info.get('url', '')

            text = f"{title} {description}"
            articles.append({
                "title": title,
                "description": description[:300],
                "url": link,
                "source_name": feed.get('feed', {}).get('title', source_name),
                "source_tiers": [tier],
                "published_at": pub_dt.isoformat() if pub_dt else '',
                "source_region": region,
                "source_count": 1,
                "source_diversity": 1,
                "wire_agency_count": _extract_wire_agencies(text),
                "intl_org_count": _extract_intl_orgs(text),
                "overseas_source_count": 1 if region else 0,
                "weibo_reads": 0,
                "baidu_index": 0,
                "comment_count": 0,
                "share_count": 0,
                "retweet_count": 0,
                "long_comment_ratio": 0.1,
                "analysis_count": 0,
                "search_index": 0,
                "country_count": 0,
                "regions": [region] if region else [],
                "domains": [],
                "local_media_count": 0,
                "unique_source_count": 1,
                "follow_up_count": 0,
                "is_domestic_only": False,
            })

        return articles

    except Exception as e:
        print(f"  ⚠ RSS 抓取失败 {url[:50]}...: {e}")
        return []


def fetch_from_rss(session_label: str) -> List[Dict]:
    """并行抓取所有 RSS 源"""
    print(f"📡 正在从 {len(RSS_FEEDS)} 个 RSS 源抓取...")

    all_articles = []
    seen_urls = set()

    # 使用线程池并行抓取（最多10线程）
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_single_rss, feed): feed for feed in RSS_FEEDS}
        for future in as_completed(futures):
            try:
                articles = future.result()
                for art in articles:
                    url = art['url']
                    if url not in seen_urls:
                        all_articles.append(art)
                        seen_urls.add(url)
            except Exception as e:
                print(f"  ⚠ RSS 抓取线程异常: {e}")

    print(f"  ✅ RSS 获取 {len(all_articles)} 条去重新闻")
    return all_articles


# ============================================================
# 国内平台数据补充（模拟/估算）
# ============================================================

def _enrich_with_domestic_data(articles: List[Dict]) -> List[Dict]:
    """
    补充国内平台热度数据（模拟/估算）
    实际部署时可接入微博公开API、百度新闻指数等
    """
    print("📊 正在补充国内平台热度数据...")

    for art in articles:
        title = art.get('title', '')
        description = art.get('description', '')

        # 估算搜索指数（基于标题长度和关键词密度）
        text_len = len(title) + len(description)
        keyword_count = len(re.findall(r'\b(war|conflict|economy|crisis|summit|disaster)\b',
                                        f"{title} {description}".lower()))
        art['search_index'] = max(1, int(text_len * 0.5 + keyword_count * 20))

        # 估算评论和分享（基于来源权威度 + 突发事件程度）
        tier_score = MEDIA_TIER_SCORE.get(art.get('source_tiers', ['C'])[0], 25)
        breaking_bonus = art.get('_raw_indicators', {}).get('e2_break_raw', 0)

        art['comment_count'] = int(tier_score * 3 + breaking_bonus * 5)
        art['share_count'] = int(tier_score * 2 + breaking_bonus * 3)
        art['retweet_count'] = int(tier_score * 1.5 + breaking_bonus * 2)
        art['analysis_count'] = max(0, int(tier_score * 0.5))

        # 估算微博阅读量
        art['weibo_reads'] = int(tier_score * 1000 + breaking_bonus * 2000)
        art['baidu_index'] = int(tier_score * 50 + breaking_bonus * 100)

    return articles


# ============================================================
# 时间窗口过滤
# ============================================================

def filter_by_time_window(
    articles: List[Dict],
    session_label: str,
) -> List[Dict]:
    """只保留时间窗口内的新闻"""
    start_dt, end_dt = _get_time_window(session_label)

    filtered = []
    for art in articles:
        pub_str = art.get('published_at', '')
        if not pub_str:
            # 没有发布时间的默认保留
            filtered.append(art)
            continue

        try:
            pub_dt = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
            if start_dt <= pub_dt <= end_dt:
                filtered.append(art)
        except (ValueError, TypeError):
            # 解析失败的默认保留
            filtered.append(art)

    print(f"⏰ 时间窗口过滤: {len(articles)} → {len(filtered)}")
    return filtered


# ============================================================
# 主抓取函数：整合所有来源
# ============================================================

def fetch_all_news(session_label: str = "noon") -> List[Dict]:
    """
    主抓取函数：整合 NewsAPI + RSS + 国内数据
    返回：统一的新闻列表
    """
    print(f"\n{'='*60}")
    print(f"🌍 开始抓取国际新闻 | 时段: {session_label}")
    print(f"{'='*60}")

    all_news: List[Dict] = []
    seen_urls: set = set()

    # 1. NewsAPI 抓取
    try:
        newsapi_articles = fetch_from_newsapi(session_label)
        for art in newsapi_articles:
            if art['url'] not in seen_urls:
                all_news.append(art)
                seen_urls.add(art['url'])
    except Exception as e:
        print(f"❌ NewsAPI 整体抓取失败: {e}")

    # 2. RSS 源抓取
    try:
        rss_articles = fetch_from_rss(session_label)
        for art in rss_articles:
            if art['url'] not in seen_urls:
                all_news.append(art)
                seen_urls.add(art['url'])
    except Exception as e:
        print(f"❌ RSS 整体抓取失败: {e}")

    # 3. 时间窗口过滤
    all_news = filter_by_time_window(all_news, session_label)

    # 4. 国内平台数据补充
    all_news = _enrich_with_domestic_data(all_news)

    # 5. 补充额外的元数据
    from src.config import REGION_COUNTRIES
    all_countries = [c for countries in REGION_COUNTRIES.values() for c in countries]

    for art in all_news:
        text = f"{art.get('title', '')} {art.get('description', '')}"
        # 统计涉及的国家数
        if art.get('country_count', 0) == 0:
            art['country_count'] = _extract_countries(text, all_countries)
        # 统计通讯社转载
        if art.get('wire_agency_count', 0) == 0:
            art['wire_agency_count'] = _extract_wire_agencies(text)
        # 统计国际组织
        if art.get('intl_org_count', 0) == 0:
            art['intl_org_count'] = _extract_intl_orgs(text)
        # 计算来源多样性
        art['source_diversity'] = max(1, art.get('source_count', 1))
        art['unique_source_count'] = max(1, art.get('source_count', 1))
        # 海外源数量
        art['overseas_source_count'] = max(0, art.get('overseas_source_count', 0))
        art['local_media_count'] = max(0, art.get('local_media_count', 0))

    # 6. 按发布时间降序排列
    all_news.sort(key=lambda x: x.get('published_at', ''), reverse=True)

    print(f"\n📊 总计获取 {len(all_news)} 条候选新闻")
    return all_news


# ============================================================
# 按时间窗口快速筛选（补充用）
# ============================================================

def get_session_label() -> str:
    """根据当前北京时间自动判断推送时段"""
    # 获取北京时间的小时
    utc_now = datetime.now(timezone.utc)
    beijing_hour = (utc_now.hour + 8) % 24

    if 4 <= beijing_hour < 10:
        return "morning"
    elif 10 <= beijing_hour < 16:
        return "noon"
    else:
        return "evening"
