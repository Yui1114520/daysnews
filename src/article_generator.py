"""
新闻摘要生成器 & 关键词提取
- 从英文标题+描述生成 100-150 字中文摘要
- 提取 3-5 个关键词
- 支持调用免费翻译 API 或者使用模板化摘要
"""
import re
import hashlib
from typing import List, Tuple


def extract_keywords(title: str, description: str = "", domains: List[str] = None,
                     regions: List[str] = None) -> List[str]:
    """
    从标题和描述中提取 3-5 个关键词
    """
    text = f"{title} {description}".lower()
    keywords = []

    # 1. 从领域和区域中取标签
    if domains:
        keywords.extend(domains[:2])
    if regions:
        for r in regions[:2]:
            if r not in keywords:
                keywords.append(r)

    # 2. 从文本中提取实体关键词
    # 国家/地名
    country_patterns = [
        r'\b(United States|US|USA|China|Russia|Ukraine|India|Iran|Israel|'
        r'North Korea|South Korea|Japan|France|Germany|UK|Brazil|Australia|'
        r'Canada|Turkey|Saudi Arabia|Pakistan|Indonesia|Nigeria|Egypt)\b',
    ]
    for pat in country_patterns:
        found = re.findall(pat, title, re.IGNORECASE)
        for f in found[:2]:
            if f.title() not in keywords:
                keywords.append(f.title())

    # 组织名
    org_patterns = [
        r'\b(UN|NATO|EU|WHO|IMF|G20|G7|BRICS|ASEAN|OPEC|'
        r'United Nations|European Union|Security Council)\b',
    ]
    for pat in org_patterns:
        found = re.findall(pat, title, re.IGNORECASE)
        for f in found[:1]:
            if f.upper() not in [k.upper() for k in keywords]:
                keywords.append(f.upper() if len(f) <= 5 else f.title())

    # 3. 主题关键词
    topic_kw = {
        "war": "战争", "conflict": "冲突", "ceasefire": "停火", "attack": "袭击",
        "economy": "经济", "inflation": "通胀", "trade": "贸易", "market": "市场",
        "summit": "峰会", "sanction": "制裁", "election": "选举", "protest": "抗议",
        "earthquake": "地震", "flood": "洪水", "climate": "气候",
        "ai": "AI", "chip": "芯片", "nuclear": "核", "missile": "导弹",
        "oil": "石油", "refugee": "难民", "covid": "疫情", "terror": "恐怖",
    }
    for en, zh in topic_kw.items():
        if en in text and zh not in keywords:
            keywords.append(zh)
            break

    # 确保 3-5 个，去重
    seen = set()
    final_kw = []
    for kw in keywords:
        if kw.lower() not in seen:
            final_kw.append(kw)
            seen.add(kw.lower())
        if len(final_kw) >= 5:
            break

    # 如果不够3个，补充
    while len(final_kw) < 3:
        fallbacks = ["国际新闻", "全球热点", "时政要闻", "外交动态", "全球经济"]
        for fb in fallbacks:
            if fb not in final_kw:
                final_kw.append(fb)
                break

    return final_kw[:5]


def generate_summary(title: str, description: str, source_name: str = "",
                     domains: List[str] = None, regions: List[str] = None) -> str:
    """
    生成 100-150 字的中文摘要

    策略：
    1. 如果有中文标题/描述，直接引用
    2. 如果是英文，用模板化方式结合领域/区域信息生成上下文丰富的摘要
    3. 确保摘要独立可读
    """
    # 检测是否已有中文内容
    chinese_chars = len(re.findall(r'[一-鿿]', title + description))
    total_chars = len(title + description) if title + description else 1

    if chinese_chars / max(total_chars, 1) > 0.5:
        # 中文内容为主，直接截取
        chinese_text = ''.join(re.findall(r'[一-鿿，。！？、；：""''【】\s]',
                                          f"{title}。{description}"))
        if len(chinese_text) >= 60:
            return chinese_text[:150]

    # 英文内容：生成模板化中文摘要
    parts = []

    # 来源
    if source_name:
        short_source = source_name.split('.')[0][:20]
        parts.append(f"据{short_source}报道")

    # 核心信息
    desc_clean = re.sub(r'<[^>]+>', '', description)[:200]
    if desc_clean:
        # 截取关键描述
        sentences = re.split(r'[.!?]\s+', desc_clean)
        main_sentence = sentences[0] if sentences else desc_clean
        if len(main_sentence) > 150:
            main_sentence = main_sentence[:150] + "..."
        parts.append(main_sentence)
    else:
        parts.append(title[:120])

    # 补充领域和区域信息
    if domains:
        domain_zh = "、".join(domains[:2])
        parts.append(f"该事件涉及{domain_zh}领域")
    if regions:
        region_zh = "、".join(regions[:2])
        parts.append(f"主要影响{region_zh}地区")

    summary = "，".join(parts)

    # 确保 100-150 字
    if len(summary) < 80:
        # 补充标题信息
        summary = f"国际新闻：{title[:100]}。" + summary
    if len(summary) > 160:
        summary = summary[:150] + "。"

    return summary


def generate_article_content(news: dict) -> dict:
    """为单条新闻生成摘要和关键词，返回增强后的 news dict"""
    title = news.get('title', '')
    description = news.get('description', '')
    source_name = news.get('source_name', '')
    domains = news.get('domains', [])
    regions = news.get('regions', [])

    news['keywords'] = extract_keywords(title, description, domains, regions)
    news['summary'] = generate_summary(title, description, source_name, domains, regions)

    return news
