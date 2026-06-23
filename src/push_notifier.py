"""
微信测试号推送模块 v5
- 20条新闻 → 1条模板消息（带 url 参数，整条消息可点击）
- 点消息 → 打开浏览器 → 精美的 HTML 过渡页
- HTML 页面上每条标题都是可点击链接，直达原文
"""
import json, time, re, requests
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from src.config import WECHAT_APPID, WECHAT_APPSECRET, WECHAT_OPENID

_access_token_cache = {"token": "", "expires_at": 0}

HTML_URL = "https://raw.githubusercontent.com/Yui1114520/daysnews/main/news.html"

REGION_FLAG = {
    "中东与北非": "🕌", "拉美与加勒比": "🌎", "中亚与高加索": "🏔️",
    "东亚与太平洋": "🌏", "撒哈拉以南非洲": "🌍", "东欧": "🏰",
    "西欧与南欧": "🇪🇺", "南亚与东南亚": "🌴", "北美": "🇺🇸",
    "西欧": "🇪🇺", "东亚": "🌏", "南亚": "🌴", "拉美": "🌎",
}

_EN_ZH = {
    "war": "战争", "killed": "死亡", "attack": "袭击", "strike": "打击",
    "death": "死亡", "dead": "死亡", "wounded": "受伤", "injured": "受伤",
    "ceasefire": "停火", "missile": "导弹", "drone": "无人机", "nuclear": "核",
    "troops": "部队", "military": "军事", "border": "边境", "crisis": "危机",
    "president": "总统", "minister": "部长", "election": "选举", "vote": "投票",
    "summit": "峰会", "meeting": "会议", "talks": "会谈", "agreement": "协议",
    "sanctions": "制裁", "trade": "贸易", "tariff": "关税", "economy": "经济",
    "market": "市场", "inflation": "通胀", "rate": "利率", "price": "价格",
    "protest": "抗议", "flood": "洪水", "earthquake": "地震", "fire": "火灾",
    "storm": "风暴", "climate": "气候", "carbon": "碳", "energy": "能源",
    "refugee": "难民", "migrant": "移民", "humanitarian": "人道主义",
    "court": "法院", "rights": "权利", "law": "法律", "ban": "禁止",
    "launch": "发射", "satellite": "卫星", "rocket": "火箭", "space": "太空",
    "virus": "病毒", "vaccine": "疫苗", "health": "健康", "hospital": "医院",
    "police": "警察", "arrest": "逮捕", "sentence": "判决",
    "Russia": "俄罗斯", "Ukraine": "乌克兰", "US": "美国", "China": "中国",
    "Israel": "以色列", "Iran": "伊朗", "India": "印度", "France": "法国",
    "Germany": "德国", "UK": "英国", "Japan": "日本", "Brazil": "巴西",
    "Korea": "韩国", "North Korea": "朝鲜", "Africa": "非洲", "Europe": "欧洲",
    "Asia": "亚洲", "America": "美国", "Middle East": "中东",
    "says": "表示", "urges": "敦促", "warns": "警告",
    "reports": "报道", "announces": "宣布",
    "oil": "石油", "gas": "天然气", "gold": "黄金", "stock": "股市",
    "NATO": "北约", "EU": "欧盟", "UN": "联合国",
    "security": "安全", "defense": "国防", "foreign": "外交",
    "breaking": "突发", "update": "更新", "live": "直播",
}


def _quick_en2zh(text: str) -> str:
    if not text or not any(c.isascii() and c.isalpha() for c in text):
        return text
    result = text
    for en, zh in sorted(_EN_ZH.items(), key=lambda x: -len(x[0])):
        if en in result:
            result = result.replace(en, zh)
    result = re.sub(r"\s+", " ", result).strip()
    return result[:120]


def _get_access_token() -> str:
    now = time.time()
    if _access_token_cache["token"] and _access_token_cache["expires_at"] > now + 60:
        return _access_token_cache["token"]
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": WECHAT_APPID, "secret": WECHAT_APPSECRET}
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if "access_token" in data:
            _access_token_cache["token"] = data["access_token"]
            _access_token_cache["expires_at"] = now + data.get("expires_in", 7200)
            print("  OK access_token")
            return _access_token_cache["token"]
    except Exception as e:
        print(f"  FAIL access_token: {e}")
    return ""


def _build_k1_k2(news_list: List[Dict]) -> str:
    """紧凑列表：序号.🔥标题"""
    lines = []
    for i, n in enumerate(news_list, 1):
        s = n.get("hotness_score", 0)
        flag = REGION_FLAG.get((n.get("regions") or ["?"])[0], "📰")
        t = n.get("summary_cn", "")[:45]
        heat = "🔥" if s >= 70 else ("🔶" if s >= 55 else "📌")
        lines.append(f"{i:2d}.{heat}{flag}{t}")
    result = "\n".join(lines)
    return result[:797] + "..." if len(result) > 800 else result


def push_news(news_list: List[Dict], session_label: str = "noon") -> bool:
    """推送 1 条可点击模板消息（url → HTML 过渡页 → 20条可点标题）"""
    if not news_list:
        print("WARN: empty news list")
        return False
    if not WECHAT_APPID or not WECHAT_APPSECRET or not WECHAT_OPENID:
        print("FAIL: no WeChat config")
        return False

    token = _get_access_token()
    if not token:
        return False

    label_map = {"morning": "☀️ 晨间速递", "noon": "🌤️ 午间速递", "evening": "🌙 晚间速递"}
    push_name = label_map.get(session_label, "📡 国际新闻速递")

    now_beijing = datetime.now(timezone.utc) + timedelta(hours=8)
    date_str = f"{now_beijing.year}年{now_beijing.month:02d}月{now_beijing.day:02d}日"
    h = now_beijing.hour
    next_push = "明天 06:00" if h >= 20 else ("今天 20:00" if h >= 12 else "今天 12:00")

    # Translate
    for n in news_list:
        title = n.get("title", "")
        summary = n.get("summary", "")
        if summary:
            n["summary_cn"] = _quick_en2zh(summary)
        elif title:
            n["summary_cn"] = _quick_en2zh(title)
        else:
            n["summary_cn"] = "(无摘要)"

    # Stats
    region_set, domain_set = set(), set()
    scores = [n.get("hotness_score", 0) for n in news_list if n.get("hotness_score", 0) > 0]
    for n in news_list:
        for r in n.get("regions", []): region_set.add(r)
        for d in n.get("domains", []): domain_set.add(d)

    avg_s = sum(scores) / len(scores) if scores else 0
    min_s = min(scores) if scores else 0
    max_s = max(scores) if scores else 0

    keyword1 = _build_k1_k2(news_list[:10])
    keyword2 = _build_k1_k2(news_list[10:20])
    keyword3 = f"🌐 区域{len(region_set)}/9 领域{len(domain_set)}/10 | 🔥{min_s:.0f}-{max_s:.0f} 均{avg_s:.0f}"
    first = f"{push_name} | 📅 {date_str} | 共{len(news_list)}条 | 👆点击查看详情"

    remark = f"🔗 点击本条消息，打开网页查看全部20条新闻\n每条标题可点击跳转原文\n⏰ 下次推送: {next_push}"

    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": WECHAT_OPENID,
        "template_id": "bxtS2g3YWB-RdZxmvZ2aHNYXKVkDGRArxxwTgA2uJjw",
        "url": HTML_URL,   # <-- 关键！整条消息可点，跳转到 HTML 页面
        "data": {
            "first":    {"value": first,    "color": "#ff6b35"},
            "keyword1": {"value": keyword1, "color": "#ff6b35"},
            "keyword2": {"value": keyword2, "color": "#333333"},
            "keyword3": {"value": keyword3, "color": "#888888"},
            "remark":   {"value": remark,   "color": "#666666"},
        }
    }

    print(f"\nPushing 1 template msg (url={HTML_URL[:40]}...)...")
    try:
        resp = requests.post(url, json=payload, timeout=20)
        data = resp.json()
        if data.get("errcode") == 0:
            print(f"  OK sent (msgid={data.get('msgid','?')})")
            return True
        else:
            print(f"  FAIL: {data.get('errmsg','')} (errcode={data.get('errcode')})")
            return False
    except Exception as e:
        print(f"  FAIL exception: {e}")
        return False


def push_test_message() -> bool:
    """发送测试消息"""
    if not WECHAT_APPID or not WECHAT_APPSECRET or not WECHAT_OPENID:
        print("FAIL: no WeChat config")
        return False
    token = _get_access_token()
    if not token:
        return False
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": WECHAT_OPENID,
        "template_id": "bxtS2g3YWB-RdZxmvZ2aHNYXKVkDGRArxxwTgA2uJjw",
        "url": HTML_URL,
        "data": {
            "first":    {"value": "🧪 国际新闻推送系统 - 测试", "color": "#ff6b35"},
            "keyword1": {"value": "✅ 推送通道配置成功！点击本条消息查看完整内容", "color": "#ff6b35"},
            "keyword2": {"value": "每天6:00/12:00/20:00 自动推送20条国际热点新闻\n覆盖9大区域+10大领域+五维热度评分", "color": "#333333"},
            "keyword3": {"value": "🌍 全球覆盖 | 📊 AI评分 | 📰 多源聚合", "color": "#888888"},
            "remark":   {"value": "👆 点击查看完整新闻列表\n⏰ 每天三档自动推送", "color": "#666666"},
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if data.get("errcode") == 0:
            print("TEST OK")
            return True
        else:
            print(f"TEST FAIL: {data.get('errmsg','')}")
            return False
    except Exception as e:
        print(f"TEST exception: {e}")
        return False
