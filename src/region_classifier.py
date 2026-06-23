"""
9 大地理区域自动分类器
基于新闻中出现国家名匹配对应区域
"""
from typing import List, Set
from src.config import REGION_COUNTRIES, COUNTRY_TO_REGION


def classify_regions(title: str, description: str = "", source_region: str = "") -> List[str]:
    """
    对一条新闻进行9大地理区域分类
    返回：区域标签列表（一条新闻可能涉及多个区域）
    """
    text = f"{title} {description}".lower()
    matched_regions: Set[str] = set()

    for country_lower, region in COUNTRY_TO_REGION.items():
        if country_lower in text:
            matched_regions.add(region)

    # 如果通过内容没找到，尝试使用来源的区域
    if not matched_regions and source_region:
        matched_regions.add(source_region)

    # 如果还是没找到，标记为"跨区域"
    if not matched_regions:
        matched_regions.add("跨区域综合")

    return sorted(matched_regions)


def get_primary_region(title: str, description: str = "", source_region: str = "") -> str:
    """获取最主要的区域"""
    regions = classify_regions(title, description, source_region)
    # 优先返回非"跨区域综合"的
    for r in regions:
        if r != "跨区域综合":
            return r
    return regions[0]


def get_region_for_country(country: str) -> str:
    """根据国家名查区域"""
    return COUNTRY_TO_REGION.get(country.lower(), "跨区域综合")


def all_regions() -> List[str]:
    """返回所有9大区域名称列表"""
    return list(REGION_COUNTRIES.keys())
