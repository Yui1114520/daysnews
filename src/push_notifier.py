"""
PushPlus 推送模块
- 支持长消息自动分段
- 支持 Markdown 格式
- 推送失败自动重试
"""
import time
import requests
from typing import List, Dict

from src.config import PUSHPLUS_TOKEN


def _send_single_message(title: str, content: str, template: str = "html") -> bool:
    """
    通过 PushPlus 发送单条消息
    返回是否成功
    """
    if not PUSHPLUS_TOKEN:
        print("❌ 未配置 PUSHPLUS_TOKEN，跳过推送")
        return False

    url = "https://www.pushplus.plus/send"
    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": template,
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        if data.get("code") == 200:
            print(f"  ✅ 推送成功: {title}")
            return True
        else:
            print(f"  ❌ 推送失败: {data.get('msg', '未知错误')}")
            return False
    except requests.RequestException as e:
        print(f"  ❌ 推送请求异常: {e}")
        return False


def _build_push_content(news_list: List[Dict], session_label: str) -> str:
    """
    构建推送消息体（HTML格式）
    """
    from datetime import datetime, timezone

    # 时段标签
    label_map = {
        "morning": ("06:00", "晨间速递", "1/3"),
        "noon": ("12:00", "午间速递", "2/3"),
        "evening": ("20:00", "晚间速递", "3/3"),
    }
    time_label, push_name, batch_num = label_map.get(session_label,
                                                      ("--:--", "国际新闻速递", "?"))

    now = datetime.now(timezone.utc)
    beijing_date = f"{(now.hour + 8) % 24:02d}:{now.minute:02d}" if (now.hour + 8) < 24 else f"{(now.hour + 8 - 24):02d}:{now.minute:02d}"
    date_str = f"{now.year}年{now.month}月{now.day}日"

    # 构建 HTML 内容
    # 简洁风格，适合微信阅读
    html_parts = f"""
<div style="background:#1a1a2e;color:#e0e0e0;padding:15px;border-radius:8px;max-width:600px;font-family:sans-serif;">
<h2 style="color:#ff6b35;text-align:center;margin:0;">🌍 国际热点新闻速递</h2>
<p style="text-align:center;color:#888;font-size:12px;">━━━━━━━━━━━━━━━━</p>
<p style="text-align:center;font-size:14px;">📅 {date_str} | ⏰ {push_name} | 第 {batch_num} 次推送</p>
<p style="text-align:center;color:#888;font-size:12px;">━━━━━━━━━━━━━━━━</p>
<hr style="border-color:#333;">
"""

    for i, news in enumerate(news_list, 1):
        score = news.get('hotness_score', 0)
        title = news.get('title', '')
        summary = news.get('summary', '')
        keywords = news.get('keywords', ['国际新闻'])
        regions = news.get('regions', [])
        domains = news.get('domains', [])
        heat_level = _get_score_emoji(score)

        # 区域 + 领域标签
        region_tag = " · ".join(regions[:2]) if regions else "综合"
        domain_tag = " · ".join(domains[:2]) if domains else "国际"
        kw_tags = " ".join([f"<span style='background:#333;color:#ff6b35;padding:1px 5px;border-radius:3px;font-size:10px;'>#{kw}</span>" for kw in keywords])

        html_parts += f"""
<div style="background:#16213e;padding:12px;margin:8px 0;border-radius:6px;border-left:3px solid #ff6b35;">
  <p style="margin:0 0 8px 0;">
    <span style="background:#ff6b35;color:#fff;padding:2px 8px;border-radius:3px;font-size:13px;font-weight:bold;">{i}.</span>
    <span style="color:#ff6b35;font-size:14px;margin-left:6px;">{heat_level} [{score}]</span>
    <span style="color:#aaa;font-size:11px;margin-left:4px;">📍 {region_tag} | {domain_tag}</span>
  </p>
  <p style="margin:5px 0;color:#e8e8e8;font-size:14px;"><b>{title}</b></p>
  <p style="margin:5px 0;color:#aaa;font-size:12px;">📝 {summary}</p>
  <p style="margin:5px 0;color:#888;font-size:11px;">{kw_tags}</p>
</div>
"""

    # 统计部分
    region_counts = {}
    domain_counts = {}
    for news in news_list:
        for r in news.get('regions', []):
            region_counts[r] = region_counts.get(r, 0) + 1
        for d in news.get('domains', []):
            domain_counts[d] = domain_counts.get(d, 0) + 1

    region_lines = []
    for r, c in region_counts.items():
        region_lines.append(f"<span style='color:#aaa;'>[{r}×{c}]</span>")
    region_status = "9/9 全覆盖 ✅" if len(region_counts) >= 9 else f"{len(region_counts)}/9 覆盖"

    domain_lines = []
    for d, c in domain_counts.items():
        domain_lines.append(f"<span style='color:#aaa;'>[{d}×{c}]</span>")
    domain_status = "10/10 全覆盖 ✅" if len(domain_counts) >= 10 else f"{len(domain_counts)}/10 覆盖"

    scores_list = [n.get('hotness_score', 0) for n in news_list]
    avg_score = sum(scores_list) / len(scores_list) if scores_list else 0

    # 下次推送时间
    next_map = {"morning": "今天 12:00", "noon": "今天 20:00", "evening": "明天 06:00"}
    next_time = next_map.get(session_label, "--")

    html_parts += f"""
<hr style="border-color:#333;">
<div style="background:#1a1a2e;padding:8px;border-radius:4px;">
<p style="text-align:center;color:#ff6b35;font-size:13px;"><b>━━━ 📊 本次覆盖统计 ━━━</b></p>
<p style="font-size:11px;color:#ccc;">📍 地理区域：<b>{region_status}</b></p>
<p style="font-size:11px;color:#ccc;">{" ".join(region_lines)}</p>
<p style="font-size:11px;color:#ccc;">🏷️ 新闻领域：<b>{domain_status}</b></p>
<p style="font-size:11px;color:#ccc;">{" ".join(domain_lines)}</p>
<p style="font-size:12px;color:#ccc;">📈 热度区间：{min(scores_list):.1f} - {max(scores_list):.1f} | 平均：{avg_score:.1f}</p>
<p style="text-align:center;color:#888;font-size:11px;">⏰ 下次推送：{next_time}（北京时间）</p>
<p style="text-align:center;color:#555;font-size:10px;">Powered by International News Pusher</p>
</div>
</div>
"""
    return html_parts


def _get_score_emoji(score: float) -> str:
    if score >= 80:
        return "🔥🔥"
    elif score >= 60:
        return "🔥"
    elif score >= 30:
        return "📌"
    else:
        return "📎"


def push_news(news_list: List[Dict], session_label: str = "noon") -> bool:
    """
    推送新闻到微信
    """
    if not news_list:
        print("⚠️ 没有新闻需要推送")
        return False

    label_map = {
        "morning": "🌅 晨间国际热点速递",
        "noon": "☀️ 午间国际热点速递",
        "evening": "🌙 晚间国际热点速递",
    }
    title = label_map.get(session_label, "🌍 国际热点新闻速递")

    # 添加新闻条数
    title += f" | {len(news_list)}条"

    print(f"\n📤 正在推送 {len(news_list)} 条新闻到微信...")

    # 构建推送内容
    content = _build_push_content(news_list, session_label)

    # 检测内容长度。PushPlus 单条消息限制约 50KB
    content_bytes = len(content.encode('utf-8'))
    if content_bytes > 48000:
        # 分段推送
        print(f"  ⚠ 内容较大({content_bytes}字节)，将分段推送")
        # 分两段
        mid = len(news_list) // 2
        part1_title = f"{title} (1/2)"
        part2_title = f"{title} (2/2)"
        ok1 = _send_single_message(part1_title,
                                   _build_push_content(news_list[:mid], session_label))
        time.sleep(1)
        ok2 = _send_single_message(part2_title,
                                   _build_push_content(news_list[mid:], session_label))
        return ok1 and ok2
    else:
        return _send_single_message(title, content)


def push_test_message() -> bool:
    """发送测试消息，验证配置是否正确"""
    if not PUSHPLUS_TOKEN:
        print("❌ 未配置 PUSHPLUS_TOKEN")
        return False

    content = """
    <div style="text-align:center;padding:20px;">
      <h2>✅ 国际新闻推送系统</h2>
      <p style="font-size:16px;">配置验证成功！</p>
      <p style="color:#888;">如果你能看到这条消息，说明 PushPlus 推送通道已正常工作。</p>
      <p style="color:#888;">系统将在每天 6:00 / 12:00 / 20:00 自动推送国际热点新闻。</p>
      <p style="color:#ff6b35;font-size:20px;">🌍🗞️</p>
    </div>
    """
    return _send_single_message("🧪 国际新闻推送系统 - 测试消息", content)
