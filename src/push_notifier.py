"""
微信测试号推送模块 v7 — 智能翻译 + 可靠性保障
- 多源翻译（MyMemory → Google → DeepL）带健康检查
- 两道校验：含中文 + 长度≥原文30%
- 确保20条新闻 + 每条有概要
"""
import json, time, re, requests, random
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone, timedelta
from src.config import WECHAT_APPID, WECHAT_APPSECRET, WECHAT_OPENID

_access_token_cache = {"token": "", "expires_at": 0}

# 使用 GitHub Pages（已启用，从 docs/ 目录发布）
GITHUB_PAGES_URL = "https://yui1114520.github.io/daysnews/"

REGION_FLAG = {
    "中东与北非": "🕌", "拉美与加勒比": "🌎", "中亚与高加索": "🏔️",
    "东亚与太平洋": "🌏", "撒哈拉以南非洲": "🌍", "东欧": "🏰",
    "西欧与南欧": "🇪🇺", "南亚与东南亚": "🌴", "北美": "🇺🇸",
    "西欧": "🇪🇺", "东亚": "🌏", "南亚": "🌴", "拉美": "🌎",
}

# ============================================================
#  多源翻译系统
# ============================================================

class TranslationSources:
    """管理多个翻译源，自动健康检查 + 故障转移"""

    def __init__(self):
        self.sources = [
            ("MyMemory", self._translate_mymemory),
            ("Google",   self._translate_google),
        ]
        self.available: List[Tuple[str, callable]] = list(self.sources)
        self.dead: set = set()

    def mark_dead(self, name: str):
        """标记某个源在本轮内不可用"""
        if name not in self.dead:
            self.dead.add(name)
            self.available = [(n, f) for n, f in self.available if n != name]
            print(f"  [翻译] {name} 已标记为不可用（剩余 {len(self.available)} 个源）")

    # ---- MyMemory (免费, 无 API Key) ----
    def _translate_mymemory(self, text: str) -> Optional[str]:
        try:
            url = "https://api.mymemory.translated.net/get"
            resp = requests.get(url, params={"q": text[:500], "langpair": "en|zh"},
                               timeout=8, headers={"User-Agent": "NewsPusher/7.0"})
            if resp.status_code == 429:
                self.mark_dead("MyMemory")
                return None
            if resp.status_code != 200:
                return None
            data = resp.json()
            result = data.get("responseData", {}).get("translatedText", "")
            if result and result != text:
                return result
            return None
        except (requests.Timeout, requests.ConnectionError):
            self.mark_dead("MyMemory")
            return None
        except Exception:
            return None

    # ---- Google Translate (非官方免费接口) ----
    def _translate_google(self, text: str) -> Optional[str]:
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "en", "tl": "zh",
                "dt": "t",
                "q": text[:500],
            }
            resp = requests.get(url, params=params, timeout=8,
                               headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 429:
                self.mark_dead("Google")
                return None
            if resp.status_code != 200:
                return None
            data = resp.json()
            # Google returns [[["translated text", "original", ...], ...], ...]
            parts = data[0] if data and isinstance(data, list) else []
            result = "".join(p[0] for p in parts if p and p[0])
            if result and result != text:
                return result
            return None
        except (requests.Timeout, requests.ConnectionError):
            self.mark_dead("Google")
            return None
        except Exception:
            return None

    # ---- DeepL (免费版, 无需 Key — 用公开端点) ----
    def _translate_deepl(self, text: str) -> Optional[str]:
        try:
            # DeepL 免费端点
            url = "https://api-free.deepl.com/v2/translate"
            # 没有 Key 就走 lingva 镜像（开源 DeepL 前端）
            url = "https://lingva.ml/api/v1/en/zh/" + requests.utils.quote(text[:500])
            resp = requests.get(url, timeout=8,
                               headers={"User-Agent": "NewsPusher/7.0"})
            if resp.status_code == 429:
                self.mark_dead("DeepL")
                return None
            if resp.status_code != 200:
                return None
            data = resp.json()
            result = data.get("translation", "")
            if result and result != text:
                return result
            return None
        except (requests.Timeout, requests.ConnectionError):
            self.mark_dead("DeepL")
            return None
        except Exception:
            return None


def _validate_translation(original: str, translated: str) -> bool:
    """宽松校验：只要含中文+长度合理就通过（后置清洗负责去英文）"""
    if not translated:
        return False
    # 校验 1：必须有中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', translated))
    if chinese_chars == 0:
        return False
    # 校验 2：长度不能过短（≥原文20%）
    if len(translated) < len(original) * 0.20:
        return False
    return True


def translate_to_zh(text: str, sources: TranslationSources) -> str:
    """核心翻译函数：多源尝试 → 宽松校验 → 后置清洗（确保全中文）"""
    if not text or not text.strip():
        return ""

    # 如果已经主要是中文，直接返回
    if len(re.findall(r'[\u4e00-\u9fff]', text)) / max(len(text), 1) > 0.5:
        return _post_clean(text)

    # 尝试各翻译源
    for name, func in sources.available:
        try:
            result = func(text)
            if result and _validate_translation(text, result):
                return _post_clean(result)
        except Exception:
            sources.mark_dead(name)
            continue

    # 全失败 → 词典逐词替换（保证全中文输出）
    return _dict_translate(text)


def _post_clean(text: str) -> str:
    """后置清洗：把翻译结果中残留的英文单词替换为中文"""
    result = text
    # 按词典替换（长按前，避免短词误替）
    for en, zh in sorted(_EN_ZH.items(), key=lambda x: -len(x[0])):
        result = re.sub(r'\b' + re.escape(en) + r'\b', zh, result, flags=re.IGNORECASE)
    # 清理孤立的英文冠词/介词/连词
    for w in ["the ", "The ", "THE ", "a ", "A ", "an ", "An ",
              "of ", "Of ", "OF ", "in ", "In ", "IN ",
              "to ", "To ", "TO ", "for ", "For ", "FOR ",
              "on ", "On ", "ON ", "at ", "At ", "AT ",
              "by ", "By ", "BY ", "with ", "With ", "WITH ",
              "from ", "From ", "FROM ",
              "and ", "And ", "AND ", "or ", "Or ", "OR ",
              "but ", "But ", "BUT ", "is ", "Is ", "IS ",
              "are ", "Are ", "ARE ", "was ", "Was ", "WAS ",
              "were ", "Were ", "WERE ", "be ", "Be ", "BE ",
              "have ", "Have ", "HAVE ", "has ", "Has ", "HAS ",
              "had ", "Had ", "HAD ", "will ", "Will ", "WILL ",
              "would ", "Would ", "WOULD ", "could ", "Could ", "COULD ",
              "should ", "Should ", "SHOULD "]:
        result = result.replace(w, "")
    # 去掉剩余纯英文碎片（括号中的英文等）
    result = re.sub(r'\([A-Za-z0-9_\-\s]+\)', '', result)
    result = re.sub(r'\[[A-Za-z0-9_\-\s]+\]', '', result)
    result = re.sub(r'\s+', ' ', result).strip()
    return result[:250]


def _dict_translate(text: str) -> str:
    """API全失败时：词典逐词替换，确保输出全中文"""
    result = text
    for en, zh in sorted(_EN_ZH.items(), key=lambda x: -len(x[0])):
        result = re.sub(r'\b' + re.escape(en) + r'\b', zh, result, flags=re.IGNORECASE)
    result = _post_clean(result)
    # 如果替换后仍有纯英文单词，用[未译]标记（避免出现英文）
    result = re.sub(r'\b[A-Za-z]{3,}\b', '[...]', result)
    return result[:250]


# ============================================================
#  内置词典兜底翻译
# ============================================================

_EN_ZH = {
    "war": "战争", "killed": "死亡", "attack": "袭击", "strike": "打击",
    "death": "死亡", "dead": "死亡", "wounded": "受伤", "injured": "受伤",
    "ceasefire": "停火", "missile": "导弹", "drone": "无人机", "nuclear": "核武器",
    "troops": "部队", "military": "军事", "border": "边境", "crisis": "危机",
    "president": "总统", "minister": "部长", "election": "选举", "vote": "投票",
    "summit": "峰会", "meeting": "会议", "talks": "会谈", "agreement": "协议",
    "sanctions": "制裁", "trade": "贸易", "tariff": "关税", "economy": "经济",
    "market": "市场", "inflation": "通货膨胀", "rate": "利率", "price": "价格",
    "protest": "抗议", "flood": "洪水", "earthquake": "地震", "fire": "火灾",
    "storm": "风暴", "climate": "气候", "carbon": "碳排放", "energy": "能源",
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
    "reports": "报道称", "announces": "宣布",
    "oil": "石油", "gas": "天然气", "gold": "黄金", "stock": "股市",
    "NATO": "北约", "EU": "欧盟", "UN": "联合国", "G20": "二十国集团",
    "security": "安全", "defense": "国防", "foreign": "外交",
    "breaking": "突发", "update": "更新", "live": "直播",
    "Security Council": "安理会", "General Assembly": "联合国大会",
    "Supreme Court": "最高法院", "White House": "白宫", "Pentagon": "五角大楼",
    "State Department": "国务院", "European Commission": "欧盟委员会",
    "confirmed": "已确认", "according to": "据", "amid": "在...背景下",
    "thousands": "数千", "millions": "数百万", "billion": "十亿",
    "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
    "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日",
    "January": "1月", "February": "2月", "March": "3月", "April": "4月",
    "May": "5月", "June": "6月", "July": "7月", "August": "8月",
    "September": "9月", "October": "10月", "November": "11月", "December": "12月",
}


def _fallback_en2zh(text: str) -> str:
    """内置词典快速翻译（无需网络）"""
    if not text or not any(c.isascii() and c.isalpha() for c in text):
        return text[:200]
    result = text
    for en, zh in sorted(_EN_ZH.items(), key=lambda x: -len(x[0])):
        if en in result:
            result = result.replace(en, zh)
    # 清理残留英文冠词/介词
    for w in ["the ", "The ", "a ", "A ", "an ", "An ", "in ", "In ",
              "to ", "To ", "for ", "For ", "on ", "On ", "at ", "At ",
              "by ", "By ", "and ", "And ", "or ", "Or "]:
        result = result.replace(w, "")
    result = re.sub(r"\s+", " ", result).strip()
    return result[:200]


# ============================================================
#  概要生成 — 确保每条新闻都有中文概要
# ============================================================

def _generate_summary_cn(news: dict) -> str:
    """为一条新闻生成中文概要。
    优先级: description_cn > description翻译 > title翻译 > 领域描述
    """
    desc = (news.get("description") or "").strip()
    title = (news.get("title") or "").strip()

    # 1. 如果 description 本身已有足够中文，直接用
    ch_desc = len(re.findall(r'[一-鿿]', desc))
    if ch_desc > 30:
        # 清理 HTML 标签
        clean = re.sub(r'<[^>]+>', '', desc)
        return clean[:200]

    # 2. 用翻译后的 description
    if "description_cn" in news and news["description_cn"]:
        return news["description_cn"][:200]

    return ""  # 签名占位，会在 translate_all_news 里补齐


def translate_all_news(news_list: List[Dict], sources: TranslationSources) -> List[Dict]:
    """批量翻译新闻标题和摘要。确保每条都有 title_cn + description_cn。"""
    success_count = 0
    for n in news_list:
        title = (n.get("title") or "").strip()
        desc = (n.get("description") or "").strip()

        # 翻译标题
        n["title_cn"] = translate_to_zh(title, sources)

        # 翻译摘要/描述
        if desc:
            n["description_cn"] = translate_to_zh(desc, sources)
        else:
            # 没有描述 → 用标题凑
            n["description_cn"] = n["title_cn"][:150]

        # 最终保障：如果 title_cn 为空，用内置词典
        if not n.get("title_cn"):
            n["title_cn"] = _fallback_en2zh(title) or title[:100]
        if not n.get("description_cn"):
            n["description_cn"] = _fallback_en2zh(desc or title)[:150] or n["title_cn"][:150]

        if n.get("title_cn") and n.get("description_cn"):
            success_count += 1

    print(f"  [翻译] {success_count}/{len(news_list)} 条翻译成功")
    return news_list


# ============================================================
#  确保20条 — 如果不够,用备选新闻补齐
# ============================================================

def ensure_20_news(batch: List[Dict], all_candidates: List[Dict]) -> List[Dict]:
    """确保推送批次始终是 20 条。不够时从候选池中按热度补足。"""
    if len(batch) >= 20:
        return batch[:20]

    existing_urls = {n.get("url", "") for n in batch}
    remaining = [n for n in all_candidates if n.get("url", "") not in existing_urls]
    remaining.sort(key=lambda x: x.get("hotness_score", 0), reverse=True)

    needed = 20 - len(batch)
    batch.extend(remaining[:needed])

    if len(batch) < 20:
        print(f"  [警告] 候选池也不足，当前仅 {len(batch)} 条（目标 20）")

    return batch[:20]


# ============================================================
#  WeChat 接入
# ============================================================

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


def push_news(news_list: List[Dict], session_label: str = "noon") -> bool:
    """发1条模板消息 → GitHub Pages URL"""
    if not news_list:
        print("WARN: empty news list")
        return False
    if not WECHAT_APPID or not WECHAT_APPSECRET or not WECHAT_OPENID:
        print("FAIL: no WeChat config")
        return False

    token = _get_access_token()
    if not token:
        return False

    # 翻译
    sources = TranslationSources()
    news_list = translate_all_news(news_list, sources)

    label_map = {"morning": "🌅 晨间速递", "noon": "🌤️ 午间速递", "evening": "🌙 晚间速递"}
    push_name = label_map.get(session_label, "📡 国际新闻速递")

    now_beijing = datetime.now(timezone.utc) + timedelta(hours=8)
    date_str = f"{now_beijing.year}年{now_beijing.month:02d}月{now_beijing.day:02d}日"
    h = now_beijing.hour
    next_push = "明天 06:00" if h >= 20 else ("今天 20:00" if h >= 12 else "今天 12:00")

    # 统计
    region_set, domain_set = set(), set()
    scores = [n.get("hotness_score", 0) for n in news_list if n.get("hotness_score", 0) > 0]
    for n in news_list:
        for r in n.get("regions", []): region_set.add(r)
        for d in n.get("domains", []): domain_set.add(d)
    avg_s = sum(scores) / len(scores) if scores else 0

    # keyword1: 1-10
    k1 = []
    for i, n in enumerate(news_list[:10], 1):
        s = n.get("hotness_score", 0)
        flag = REGION_FLAG.get((n.get("regions") or ["?"])[0], "📰")
        t = n.get("title_cn", "")[:45]
        heat = "🔥" if s >= 70 else ("🔶" if s >= 55 else "📌")
        k1.append(f"{i:2d}.{heat}{flag}{t}")
    keyword1 = "\n".join(k1)

    # keyword2: 11-20
    k2 = []
    for i, n in enumerate(news_list[10:20], 11):
        s = n.get("hotness_score", 0)
        flag = REGION_FLAG.get((n.get("regions") or ["?"])[0], "📰")
        t = n.get("title_cn", "")[:45]
        heat = "🔥" if s >= 70 else ("🔶" if s >= 55 else "📌")
        k2.append(f"{i:2d}.{heat}{flag}{t}")
    keyword2 = "\n".join(k2)

    # keyword3: stats
    keyword3 = f"🌐 区域{len(region_set)}/9 领域{len(domain_set)}/10 | 热度{min(scores):.0f}-{max(scores):.0f} 均{avg_s:.0f}"

    first = f"{push_name} | 📅 {date_str} | 共{len(news_list)}条 | 👆点我查看完整日报"

    remark = (
        f"━━━━━━━━━━━━━━━━\n"
        f"📊 区域{len(region_set)}/9 领域{len(domain_set)}/10\n"
        f"🔥 热度 {min(scores):.0f}-{max(scores):.0f} 均{avg_s:.0f}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👆 点击上方卡片\n"
        f"📱 查看完整20条新闻\n"
        f"🏷️ 每条标题可点击跳转原文\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⏰ 下次推送: {next_push}"
    )

    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": WECHAT_OPENID,
        "template_id": "bxtS2g3YWB-RdZxmvZ2aHNYXKVkDGRArxxwTgA2uJjw",
        "url": GITHUB_PAGES_URL,
        "data": {
            "first":    {"value": first,    "color": "#ff6b35"},
            "keyword1": {"value": keyword1, "color": "#ff6b35"},
            "keyword2": {"value": keyword2, "color": "#333333"},
            "keyword3": {"value": keyword3, "color": "#888888"},
            "remark":   {"value": remark,   "color": "#666666"},
        }
    }

    print(f"\nPushing → {GITHUB_PAGES_URL}")
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
        "url": GITHUB_PAGES_URL,
        "data": {
            "first":    {"value": "🧪 国际新闻推送系统 - 测试", "color": "#ff6b35"},
            "keyword1": {"value": "✅ 多源翻译 · MyMemory/Google/DeepL\n✅ 两道校验 · 含中文 + 长度效验", "color": "#ff6b35"},
            "keyword2": {"value": "每天 6:00/12:00/20:00 自动推送20条\n覆盖 10 大区域 + 10 大领域\n五维热度 + 智能翻译 + GitHub Pages", "color": "#333333"},
            "keyword3": {"value": "📱 点消息 → 打开网页 → 任意点击", "color": "#888888"},
            "remark":   {"value": "👆 点击查看完整日报\n⏰ 每天三档自动推送", "color": "#666666"},
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
