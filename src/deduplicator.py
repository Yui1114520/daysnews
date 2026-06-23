"""
去重引擎
- 基于标题余弦相似度（英文）
- 基于URL精确匹配
- 维护已发送新闻列表
"""
import json
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Set
from collections import Counter
from pathlib import Path

from src.config import SENT_NEWS_FILE


def _tokenize(text: str) -> Counter:
    """将文本分词并返回词频 Counter"""
    text = text.lower()
    # 移除标点
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    words = text.split()
    # 去掉短词（<3个字符的通常无意义）
    words = [w for w in words if len(w) >= 3]
    return Counter(words)


def cosine_similarity_counter(c1: Counter, c2: Counter) -> float:
    """基于 Counter 计算余弦相似度"""
    if not c1 or not c2:
        return 0.0
    # 计算点积
    intersection = set(c1.keys()) & set(c2.keys())
    dot_product = sum(c1[word] * c2[word] for word in intersection)
    # 计算模长
    norm1 = sum(v ** 2 for v in c1.values()) ** 0.5
    norm2 = sum(v ** 2 for v in c2.values()) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def _url_hash(url: str) -> str:
    """生成 URL 的短哈希作为唯一标识"""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _title_slug(title: str) -> str:
    """生成标题的唯一标识（去空格、小写、去标点）"""
    return re.sub(r'[^a-z0-9]', '', title.lower())[:80]


def load_sent_news() -> List[Dict]:
    """加载已发送新闻列表"""
    if not SENT_NEWS_FILE.exists():
        return []
    try:
        with open(SENT_NEWS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_sent_news(news_list: List[Dict]) -> None:
    """保存已发送新闻列表（只保留最近2天的记录）"""
    cutoff = datetime.now().timestamp() - 2 * 24 * 3600
    # 清理旧记录
    cleaned = [n for n in news_list if n.get('sent_at', 0) > cutoff]
    # 只保留最近 1000 条，防止文件过大
    cleaned = cleaned[-1000:]
    with open(SENT_NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)


def mark_as_sent(news_items: List[Dict]) -> None:
    """将新闻标记为已发送"""
    existing = load_sent_news()
    now = datetime.now().timestamp()
    for item in news_items:
        item['sent_at'] = now
        existing.append({
            'url_hash': item.get('url_hash', _url_hash(item.get('url', ''))),
            'title_slug': item.get('title_slug', _title_slug(item.get('title', ''))),
            'title': item.get('title', ''),
            'sent_at': now,
        })
    save_sent_news(existing)


def deduplicate_news(
    candidates: List[Dict],
    similarity_threshold: float = 0.82,
) -> List[Dict]:
    """
    对候选新闻去重：
    1. 与已发送历史比对（仅最近24小时内的记录参与相似度比对）
    2. 候选列表内部去重（按标题相似度 + URL）
    返回：去重后的新闻列表
    """
    sent = load_sent_news()
    now_ts = datetime.now().timestamp()
    recent_cutoff = now_ts - 24 * 3600  # 仅最近24小时参与相似度比对

    # 已发送的 URL hash 集合（全部历史）
    sent_url_hashes: Set[str] = {n.get('url_hash', '') for n in sent}
    # 已发送的 title slug 集合（全部历史，精确匹配）
    sent_title_slugs: Set[str] = {n.get('title_slug', '') for n in sent}
    # 仅最近24小时的标题 token（用于相似度比对）
    recent_title_tokens = [
        _tokenize(n.get('title', ''))
        for n in sent
        if n.get('sent_at', 0) > recent_cutoff
    ]
    print(f"  [去重] 历史记录 {len(sent)} 条，其中最近24小时内 {len(recent_title_tokens)} 条参与相似度比对")

    result: List[Dict] = []
    seen_url_hashes: Set[str] = set()
    seen_title_tokens: List[Counter] = []

    for news in candidates:
        url = news.get('url', '')
        title = news.get('title', '')

        url_h = _url_hash(url)
        title_s = _title_slug(title)

        # 1. URL 精确去重
        if url_h in sent_url_hashes or url_h in seen_url_hashes:
            continue

        # 2. 标题 slug 去重
        if title_s in sent_title_slugs:
            continue

        # 3. 标题相似度去重（仅与最近24小时的历史记录比对）
        title_tokens = _tokenize(title)
        # 与已发送历史（最近24h）比较
        dup = False
        for hist_tokens in recent_title_tokens:
            if cosine_similarity_counter(title_tokens, hist_tokens) >= similarity_threshold:
                dup = True
                break
        if dup:
            continue

        # 与本次已选中的比较
        for seen_tokens in seen_title_tokens:
            if cosine_similarity_counter(title_tokens, seen_tokens) >= similarity_threshold:
                dup = True
                break
        if dup:
            continue

        # 通过所有去重检查
        news['url_hash'] = url_h
        news['title_slug'] = title_s
        result.append(news)
        seen_url_hashes.add(url_h)
        seen_title_tokens.append(title_tokens)

    return result
