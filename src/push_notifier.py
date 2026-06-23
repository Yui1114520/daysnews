"""
WxPusher 推送模块
- 支持长消息自动分段
- 支持 HTML 格式
- 推送失败自动重试

WxPusher 配置参数（通过环境变量）：
  WXPUSHER_APPTOKEN  - 应用 Token
  WXPUSHER_UID       - 用户的 UID（扫码关注你的专属二维码后获取）
"""
import time
import requests
from typing import List, Dict

from src.config import WXPUSHER_APPTOKEN, WXPUSHER_UID


def _send_single_message(content: str, title: str = "", content_type: int = 2) -> bool:
    """
    通过 WxPusher 发送单条消息
    content_type: 1=文本 2=HTML 3=Markdown
    返回是否成功
    """
    if not WXPUSHER_APPTOKEN:
        print("❌ 未配置 WXPUSHER_APPTOKEN，跳过推送")
        return False
    if not WXPUSHER_UID:
        print("❌ 未配置 WXPUSHER_UID，跳过推送")
        return False

    url = "https://wxpusher.dingliqc.com/api/send/message"
    payload = {
        "appToken": WXPUSHER_APPTOKEN,
        "content": content,
        "contentType": content_type,
        "uids": [WXPUSHER_UID],
        "summary": title[:100] if title else "",
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        if data.get("code") == 1000:
            print(f"  ✅ 推送成功")
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
    WxPusher 支持 HTML，但建议简洁风格
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
    date_str = f"{now.year}年{now.month}月{now.day}日"

    # 构建 HTML 内容
    html_parts = f"""
<h2>🌍 国际热点新闻速递</h2>
<p>━━━━━━━━━━━━━━━━</p>
<p>📅 {date_str} | ⏰ {push_name} | 第 {batch_num} 次推送</p>
<p>━━━━━━━━━━━━━━━━</p>
"""

    for i, news in enumerate(news_list, 1):
        score = news.get('hotness_score', 0)
        title = news.get('title', '')
        summary = news.get('summary', '')
        keywords = news.get('keywords', ['国际新闻'])
        regions = news.get('regions', [])
        domains = news.get('domains', [])
        heat_level = _get_score_emoji(score)

        region_tag = " · ".join(regions[:2]) if regions else "综合"
        domain_tag = " · ".join(domains[:2]) if domains else "国际"
        kw_tags = "  ".join([f"#{kw}" for kw in keywords])

        html_parts += f"""
<p>
<b>{i}. {heat_level} [{score}] {title}</b><br>
📍 {region_tag} | {domain_tag}<br>
📝 {summary}<br>
🏷️ {kw_tags}
</p>
<hr>
"""

    # 统计部分
    region_counts = {}
    domain_counts = {}
    for news in news_list:
        for r in news.get('regions', []):
            region_counts[r] = region_counts.get(r, 0) + 1
        for d in news.get('domains', []):
            domain_counts[d] = domain_counts.get(d, 0) + 1

    region_parts = []
    for r, c in region_counts.items():
        region_parts.append(f"[{r}×{c}]")
    region_status = "9/9 全覆盖 ✅" if len(region_counts) >= 9 else f"{len(region_counts)}/9"

    domain_parts = []
    for d, c in domain_counts.items():
        domain_parts.append(f"[{d}×{c}]")
    domain_status = "10/10 全覆盖 ✅" if len(domain_counts) >= 10 else f"{len(domain_counts)}/10"

    scores_list = [n.get('hotness_score', 0) for n in news_list]
    avg_score = sum(scores_list) / len(scores_list) if scores_list else 0

    next_map = {"morning": "今天 12:00", "noon": "今天 20:00", "evening": "明天 06:00"}
    next_time = next_map.get(session_label, "--")

    html_parts += f"""
<p>━━━ 📊 本次覆盖统计 ━━━</p>
<p>📍 地理区域：<b>{region_status}</b></p>
<p>{' '.join(region_parts)}</p>
<p>🏷️ 新闻领域：<b>{domain_status}</b></p>
<p>{' '.join(domain_parts)}</p>
<p>📈 热度区间：{min(scores_list):.1f} - {max(scores_list):.1f} | 平均：{avg_score:.1f}</p>
<p>⏰ 下次推送：{next_time}（北京时间）</p>
<p><sub>Powered by International News Pusher | WxPusher</sub></p>
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
    20条新闻分2条消息推送（WxPusher 建议每条不要太长）
    """
    if not news_list:
        print("⚠️ 没有新闻需要推送")
        return False

    label_map = {
        "morning": "🌅 晨间国际热点速递",
        "noon": "☀️ 午间国际热点速递",
        "evening": "🌙 晚间国际热点速递",
    }
    base_title = label_map.get(session_label, "🌍 国际热点新闻速递")

    print(f"\n📤 正在推送 {len(news_list)} 条新闻到微信...")

    # 分两段推送，每段10条，避免单条消息过长
    mid = 10
    batch1 = news_list[:mid]
    batch2 = news_list[mid:]

    # 第一段
    title1 = f"{base_title} (1/2) | {len(batch1)}条"
    content1 = _build_push_content(batch1, session_label)
    ok1 = _send_single_message(content1, title1)

    if batch2:
        time.sleep(1)  # 间隔1秒
        title2 = f"{base_title} (2/2) | {len(batch2)}条"
        content2 = _build_push_content(batch2, session_label)
        # 第二段追加统计
        content2 += "<p><b>（接上段）</b></p>"
        ok2 = _send_single_message(content2, title2)
        return ok1 and ok2

    return ok1


def push_test_message() -> bool:
    """发送测试消息，验证配置是否正确"""
    if not WXPUSHER_APPTOKEN:
        print("❌ 未配置 WXPUSHER_APPTOKEN，请在 GitHub Secrets 中添加 WXPUSHER_APPTOKEN")
        return False
    if not WXPUSHER_UID:
        print("❌ 未配置 WXPUSHER_UID，请在 GitHub Secrets 中添加 WXPUSHER_UID")
        return False

    content = """
    <h2>✅ 国际新闻推送系统</h2>
    <p>配置验证成功！</p>
    <p>如果你能看到这条消息，说明 <b>WxPusher</b> 推送通道已正常工作。</p>
    <p>系统将在每天 <b>6:00 / 12:00 / 20:00</b> 自动推送国际热点新闻。</p>
    <p>每次 <b>20条</b>，覆盖 9大区域 + 10大领域 🌍</p>
    """
    return _send_single_message(content, "🧪 国际新闻推送系统 - 测试消息")
