"""
微信测试号推送模块
- 通过微信公众平台测试号发送模板消息
- 完全免费，不需要任何第三方服务
- 消息直接从微信公众号推送到你的微信
"""
import json
import time
import requests
from typing import List, Dict
from datetime import datetime, timezone

from src.config import WECHAT_APPID, WECHAT_APPSECRET, WECHAT_OPENID

# 缓存 access_token
_access_token_cache = {"token": "", "expires_at": 0}


def _get_access_token() -> str:
    """获取微信 access_token（自动缓存，有效期约2小时）"""
    now = time.time()
    if _access_token_cache["token"] and _access_token_cache["expires_at"] > now + 60:
        return _access_token_cache["token"]

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": WECHAT_APPID,
        "secret": WECHAT_APPSECRET,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if "access_token" in data:
            _access_token_cache["token"] = data["access_token"]
            _access_token_cache["expires_at"] = now + data.get("expires_in", 7200)
            print(f"  ✅ 获取微信 access_token 成功")
            return _access_token_cache["token"]
        else:
            print(f"  ❌ 获取 access_token 失败: {data}")
            return ""
    except Exception as e:
        print(f"  ❌ 请求 access_token 异常: {e}")
        return ""


def _send_template_message(news_list: List[Dict], session_label: str, part: int) -> bool:
    """
    通过微信模板消息发送新闻摘要
    由于模板消息限制，每条发送1条新闻（共20条=20次API调用）
    """
    token = _get_access_token()
    if not token:
        return False

    if not WECHAT_OPENID:
        print("❌ 未配置 WECHAT_OPENID")
        return False

    label_map = {
        "morning": ("晨间速递", "1/3"),
        "noon": ("午间速递", "2/3"),
        "evening": ("晚间速递", "3/3"),
    }
    push_name, batch_num = label_map.get(session_label, ("国际新闻速递", "?"))

    now = datetime.now(timezone.utc)
    beijing_now = now.replace(tzinfo=timezone.utc)
    date_str = f"{now.year}年{now.month}月{now.day}日"

    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"

    success_count = 0
    fail_count = 0

    for i, news in enumerate(news_list):
        score = news.get("hotness_score", 0)
        title = news.get("title", "")[:50]
        summary = news.get("summary", "")[:100]
        keywords = news.get("keywords", [])[:3]
        regions = news.get("regions", [])
        domains = news.get("domains", [])

        region_tag = "·".join(regions[:2]) if regions else "综合"
        domain_tag = "·".join(domains[:2]) if domains else "国际"

        payload = {
            "touser": WECHAT_OPENID,
            "template_id": "news_push_template_001",
            "data": {
                "first": {
                    "value": f"{push_name} | 第{batch_num}次 | 第{i+1}/{len(news_list)}条",
                    "color": "#1a1a2e"
                },
                "keyword1": {
                    "value": f"[{score}] {title}",
                    "color": "#ff6b35"
                },
                "keyword2": {
                    "value": summary,
                    "color": "#333333"
                },
                "keyword3": {
                    "value": f"📍{region_tag} | 🏷️{domain_tag}",
                    "color": "#888888"
                },
                "remark": {
                    "value": f"🏷️ {' '.join(['#'+k for k in keywords])}\n📅 {date_str}",
                    "color": "#666666"
                }
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("errcode") == 0:
                success_count += 1
            else:
                fail_count += 1
                if fail_count <= 2:
                    print(f"  ⚠ 第{i+1}条发送失败: {data.get('errmsg', '')}")
        except Exception as e:
            fail_count += 1
            if fail_count <= 2:
                print(f"  ⚠ 第{i+1}条请求异常: {e}")

        # 控制频率（微信限制），每条间隔0.1秒
        if i < len(news_list) - 1:
            time.sleep(0.1)

    print(f"  📊 微信模板消息: 成功 {success_count}/{len(news_list)}, 失败 {fail_count}")
    return success_count > 0


def push_news(news_list: List[Dict], session_label: str = "noon") -> bool:
    """推送新闻到微信"""
    if not news_list:
        print("⚠️ 没有新闻需要推送")
        return False

    if not WECHAT_APPID or not WECHAT_APPSECRET:
        print("❌ 未配置微信测试号信息")
        return False
    if not WECHAT_OPENID:
        print("❌ 未配置 WECHAT_OPENID，请用微信扫码关注测试号后获取")
        return False

    print(f"\n📤 正在通过微信测试号推送 {len(news_list)} 条新闻...")

    ok = _send_template_message(news_list, session_label, 1)

    if ok:
        print(f"  ✅ 微信推送完成！请在微信中查看「测试号」消息")
    return ok


def push_test_message() -> bool:
    """发送测试消息"""
    if not WECHAT_APPID or not WECHAT_APPSECRET:
        print("❌ 未配置微信测试号")
        return False
    if not WECHAT_OPENID:
        print("❌ 未配置 WECHAT_OPENID")
        return False

    token = _get_access_token()
    if not token:
        return False

    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": WECHAT_OPENID,
        "template_id": "news_push_template_001",
        "data": {
            "first": {"value": "🧪 测试消息", "color": "#1a1a2e"},
            "keyword1": {"value": "国际新闻推送系统配置成功！", "color": "#ff6b35"},
            "keyword2": {"value": "如果你能看到这条消息，说明微信测试号推送通道已正常工作。系统将在每天 6:00 / 12:00 / 20:00 自动推送国际热点新闻。每次 20 条，覆盖 9 大区域 + 10 大领域。", "color": "#333333"},
            "keyword3": {"value": "🌍 覆盖全球 | 📊 五维热度评分", "color": "#888888"},
            "remark": {"value": "⏰ 每天三次自动推送\nPowered by International News Pusher", "color": "#666666"},
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        print(f"  微信返回: {data}")
        if data.get("errcode") == 0:
            print("✅ 测试消息发送成功！请在微信中查看")
            return True
        else:
            print(f"❌ 测试消息发送失败: {data.get('errmsg', '')}")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False
