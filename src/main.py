#!/usr/bin/env python3
"""
国际热点新闻微信推送系统 - 主入口
编排整个流程：抓取 → 分类 → 评分 → 去重 → 筛选 → 摘要 → 推送

用法：
  python -m src.main                     # 自动检测时段
  python -m src.main --session morning   # 晨间推送
  python -m src.main --session noon      # 午间推送
  python -m src.main --session evening   # 晚间推送
  python -m src.main --test              # 测试模式（发一条测试消息）
"""
import sys
import os
import argparse
from datetime import datetime, timezone

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import (
    WECHAT_APPID,
    WECHAT_APPSECRET,
    WECHAT_OPENID,
    NEWSAPI_KEY,
    PUSH_BATCH_SIZE,
    MIN_REGION_COVERAGE,
    MIN_DOMAIN_COVERAGE,
    PUSH_SCHEDULE,
)
from src.news_fetcher import fetch_all_news, get_session_label
from src.domain_classifier import classify_domains
from src.region_classifier import classify_regions, all_regions
from src.hotness_scorer import calculate_hotness_scores, get_heat_level
from src.deduplicator import deduplicate_news, mark_as_sent
from src.article_generator import generate_article_content
from src.push_notifier import push_news, push_test_message


def select_batch(candidates: list, batch_size: int = PUSH_BATCH_SIZE) -> list:
    """
    从候选新闻中精选出推送批次，满足:
    - 每个区域至少 1 条（9 区保底）
    - 每个领域至少 1 条（10 领域保底）
    - 按热度从高到低排序
    - 总共 batch_size 条
    """
    if not candidates:
        return candidates

    nine_regions = all_regions()
    ten_domains = [
        "地缘", "军武", "经贸", "科创", "生态",
        "外交", "民生", "社运", "治安", "人文"
    ]

    selected = []
    selected_urls = set()

    # 第一轮：保底 - 每个区域选热度最高的一条
    for region in nine_regions:
        region_news = [n for n in candidates
                       if region in n.get('regions', [])
                       and n.get('url', '') not in selected_urls]
        region_news.sort(key=lambda x: x.get('hotness_score', 0), reverse=True)
        if region_news:
            sel = region_news[0]
            selected.append(sel)
            selected_urls.add(sel.get('url', ''))

    # 第二轮：保底 - 每个领域选热度最高的一条（如果还没选到）
    for domain in ten_domains:
        domain_news = [n for n in candidates
                       if domain in n.get('domains', [])
                       and n.get('url', '') not in selected_urls]
        domain_news.sort(key=lambda x: x.get('hotness_score', 0), reverse=True)
        if domain_news:
            sel = domain_news[0]
            selected.append(sel)
            selected_urls.add(sel.get('url', ''))

    # 第三轮：按热度填充剩余名额
    remaining = [n for n in candidates if n.get('url', '') not in selected_urls]
    remaining.sort(key=lambda x: x.get('hotness_score', 0), reverse=True)

    slots_left = batch_size - len(selected)
    if slots_left > 0:
        selected.extend(remaining[:slots_left])

    # 最终按热度降序排列
    selected.sort(key=lambda x: x.get('hotness_score', 0), reverse=True)

    return selected[:batch_size]


def run_push(session_label: str = None) -> bool:
    """
    执行一次完整的推送流程
    返回是否成功
    """
    if not session_label:
        session_label = get_session_label()

    schedule = PUSH_SCHEDULE.get(session_label)
    if not schedule:
        print(f"❌ 未知的推送时段: {session_label}")
        return False

    print(f"\n{'='*60}")
    print(f"🚀 国际新闻推送系统启动")
    print(f"⏰ 时段: {session_label} ({schedule['label']})")
    print(f"📦 目标: 每次 {PUSH_BATCH_SIZE} 条")
    print(f"{'='*60}\n")

    # ---- 检查配置 ----
    if not WECHAT_APPID:
        print("❌ 未配置 WECHAT_APPID，无法推送")
        print("   请在 GitHub Secrets 中配置 WECHAT_APPID")
        return False
    if not WECHAT_APPSECRET:
        print("❌ 未配置 WECHAT_APPSECRET，无法推送")
        print("   请在 GitHub Secrets 中配置 WECHAT_APPSECRET")
        return False
    if not WECHAT_OPENID:
        print("❌ 未配置 WECHAT_OPENID，无法推送")
        print("   请在 GitHub Secrets 中配置 WECHAT_OPENID")
        return False

    # ---- 1. 抓取新闻 ----
    print("\n📡 [1/6] 抓取新闻...")
    all_news = fetch_all_news(session_label)

    if not all_news:
        print("❌ 未获取到任何新闻，请检查 API Key 和网络连接")
        return False

    # ---- 2. 分类 ----
    print(f"\n🏷️ [2/6] 双维分类（10领域 + 9区域）...")
    for news in all_news:
        title = news.get('title', '')
        description = news.get('description', '')
        source_region = news.get('source_region', '')

        # 领域分类
        news['domains'] = classify_domains(title, description)

        # 区域分类
        if not news.get('regions'):
            news['regions'] = classify_regions(title, description, source_region)

    # 分类统计
    domain_dist = {}
    region_dist = {}
    for n in all_news:
        for d in n.get('domains', []):
            domain_dist[d] = domain_dist.get(d, 0) + 1
        for r in n.get('regions', []):
            region_dist[r] = region_dist.get(r, 0) + 1
    print(f"  领域分布: {domain_dist}")
    print(f"  区域分布: {region_dist}")

    # ---- 3. 评分 ----
    print(f"\n📊 [3/6] 五维热度评分...")
    all_news = calculate_hotness_scores(all_news)

    # 按热度降序
    all_news.sort(key=lambda x: x.get('hotness_score', 0), reverse=True)

    top_scores = [f"{n.get('hotness_score',0):.1f}" for n in all_news[:5]]
    print(f"  Top 5 热度: {top_scores}")

    # ---- 4. 去重 ----
    print(f"\n🔄 [4/6] 去重检查...")
    all_news = deduplicate_news(all_news)
    print(f"  去重后剩余 {len(all_news)} 条")

    # ---- 5. 筛选 ----
    print(f"\n✅ [5/6] 筛选 {PUSH_BATCH_SIZE} 条推送...")
    batch = select_batch(all_news, PUSH_BATCH_SIZE)

    # 检查覆盖情况
    region_coverage = set()
    domain_coverage = set()
    for n in batch:
        for r in n.get('regions', []):
            region_coverage.add(r)
        for d in n.get('domains', []):
            domain_coverage.add(d)
    print(f"  区域覆盖: {len(region_coverage)}/9 - {sorted(region_coverage)}")
    print(f"  领域覆盖: {len(domain_coverage)}/10 - {sorted(domain_coverage)}")

    # ---- 6. 生成摘要和推送 ----
    print(f"\n📝 [6/6] 生成摘要并推送...")
    for news in batch:
        generate_article_content(news)

    # ---- 6.5. 生成 GitHub Pages 页面 (docs/index.html) ----
    import json as _json
    _batch_path = os.path.join(os.path.dirname(__file__), "..", "data", "_current_batch.json")
    _all_path = os.path.join(os.path.dirname(__file__), "..", "data", "_all_news.json")
    try:
        # Translate titles for HTML display using the push_notifier helper
        from src.push_notifier import _quick_en2zh as _trans
        for _n in batch:
            _title = _n.get("title", "")
            _summary = _n.get("summary", "")
            if _summary:
                _n["summary_cn"] = _trans(_summary)
            elif _title:
                _n["summary_cn"] = _trans(_title)

        with open(_batch_path, "w", encoding="utf-8") as _f:
            _json.dump(batch, _f, ensure_ascii=False, default=str)
        with open(_all_path, "w", encoding="utf-8") as _f:
            _json.dump(all_news, _f, ensure_ascii=False, default=str)

        # Import generate_news module from src
        import src.generate_news as _gn
        _docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
        os.makedirs(_docs_dir, exist_ok=True)
        _gn.generate_and_save(batch, all_news, session_label, _docs_dir)
        print(f"  ✅ GitHub Pages 页面已生成: docs/index.html")
    except Exception as _e:
        import traceback as _tb
        print(f"  ⚠ HTML 生成失败（非致命）: {_e}")
        _tb.print_exc()

    # 显示推送预览
    for i, n in enumerate(batch[:5], 1):
        print(f"  {i}. [{n.get('hotness_score',0):.1f}] {n.get('title','')[:60]}...")
        print(f"     📍 {'·'.join(n.get('regions',[]))} | {'·'.join(n.get('domains',[]))}")
        print(f"     📝 {n.get('summary','')[:80]}...")
    if len(batch) > 5:
        print(f"  ... 还有 {len(batch)-5} 条")

    # 推送
    success = push_news(batch, session_label)

    if success:
        # 推送成功后标记
        mark_as_sent(batch)
        print(f"\n🎉 推送完成！{len(batch)} 条新闻已通过 PushPlus 送达微信")
    else:
        print(f"\n❌ 推送失败，请检查 PushPlus Token")

    return success


def main():
    parser = argparse.ArgumentParser(description='国际热点新闻微信推送系统')
    parser.add_argument('--session', '-s', choices=['morning', 'noon', 'evening'],
                        help='推送时段（不指定则自动检测）')
    parser.add_argument('--test', '-t', action='store_true',
                        help='发送测试消息到微信')
    parser.add_argument('--show-config', action='store_true',
                        help='显示当前配置状态')
    args = parser.parse_args()

    # 显示配置
    if args.show_config:
        print("📋 当前配置状态:")
        print(f"  PUSHPLUS_TOKEN: {'✅ 已配置' if PUSHPLUS_TOKEN else '❌ 未配置'}")
        print(f"  推送批次大小:       {PUSH_BATCH_SIZE} 条/次")
        print(f"  推送时段:           每天 6:00 / 12:00 / 20:00（北京时间）")
        return

    # 测试模式
    if args.test:
        print("🧪 测试模式：发送测试消息...")
        if push_test_message():
            print("✅ 测试消息发送成功！请在微信中查看。")
        else:
            print("❌ 测试消息发送失败。")
        return

    # 正常推送
    session_label = args.session
    if not session_label:
        session_label = get_session_label()
        print(f"🕐 自动检测时段: {session_label}")

    success = run_push(session_label)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
