"""
去重引擎 v3 — 精确匹配优先，避免过度过滤
- 历史去重：URL 精确匹配 + 标题 slug 精确匹配（不做相似度）
- 批次内部去重：URL + slug + 相似度（避免同批次内重复）
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
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    words = text.split()
    words = [w for w in words if len(w) >= 3]
    return Counter(words)


def cosine_similarity_counter(c1: Counter, c2: Counter) -> float:
    """基于 Counter 计算余弦相似度"""
    if not c1 or not c2:
        return 0.0
    intersection = set(c1.keys()) & set(c2.keys())
    dot_product = sum(c1[word] * c2[word] for word in intersection)
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
    cleaned = [n for n in news_list if n.get('sent_at', 0) > cutoff]
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
    similarity_threshold: float = 0.90,
) -> List[Dict]:
    """
    去重策略 v3：
      - 历史：仅精确匹配（URL hash + title slug），不做相似度比对
      - 本次批次内部：精确匹配 + 高阈值相似度（≥0.90），防止同批次重复

    为什么历史不做相似度？
      RSS 源每次返回的热门新闻标题高度相似（同一事件持续报道），
      对 100+ 条历史记录做余弦相似度会误杀大量合法新闻。
      精确匹配已经足够防止"完全相同的文章"重复推送。
    """
    sent = load_sent_news()

    # ---- 历史精确匹配（全部历史，不限时间）----
    sent_url_hashes: Set[str] = {n.get('url_hash', '') for n in sent}
    sent_title_slugs: Set[str] = {n.get('title_slug', '') for n in sent}

    print(f"  [去重] 历史记录 {len(sent)} 条（精确匹配：{len(sent_url_hashes)} URLs, {len(sent_title_slugs)} slugs）")

    result: List[Dict] = []
    seen_url_hashes: Set[str] = set()
    seen_title_slugs: Set[str] = set()
    seen_title_tokens: List[Counter] = []

    filtered_by_url = 0
    filtered_by_slug = 0
    filtered_by_similar = 0

    for news in candidates:
        url = news.get('url', '')
        title = news.get('title', '')

        url_h = _url_hash(url)
        title_s = _title_slug(title)

        # 1. URL 精确去重（历史 + 本批）
        if url_h in sent_url_hashes or url_h in seen_url_hashes:
            filtered_by_url += 1
            continue

        # 2. 标题 slug 精确去重（历史 + 本批）
        if title_s in sent_title_slugs or title_s in seen_title_slugs:
            filtered_by_slug += 1
            continue

        # 3. 仅本批次内部的相似度去重（高阈值 0.90）
        title_tokens = _tokenize(title)
        dup = False
        for seen_tokens in seen_title_tokens:
            if cosine_similarity_counter(title_tokens, seen_tokens) >= similarity_threshold:
                dup = True
                break
        if dup:
            filtered_by_similar += 1
            continue

        # 通过所有检查
        news['url_hash'] = url_h
        news['title_slug'] = title_s
        result.append(news)
        seen_url_hashes.add(url_h)
        seen_title_slugs.add(title_s)
        seen_title_tokens.append(title_tokens)

    print(f"  [去重] 过滤: URL重复={filtered_by_url}, 标题重复={filtered_by_slug}, 相似={filtered_by_similar}")
    print(f"  [去重] 结果: {len(candidates)} → {len(result)} 条")
    return result
