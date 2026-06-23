"""
配置模块 - 管理所有 API Key 和系统参数
敏感信息通过环境变量（GitHub Secrets）读取，本地开发可用 .env 文件
"""
import os
import json
from pathlib import Path

# ============================================================
# 项目路径
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SENT_NEWS_FILE = DATA_DIR / "sent_news.json"
HOTNESS_HISTORY_FILE = DATA_DIR / "hotness_history.json"

# 确保 data 目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# API Keys（从环境变量读取，GitHub Actions 中配置为 Secrets）
# ============================================================
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
# 微信测试号
WECHAT_APPID = os.environ.get("WECHAT_APPID", "")
WECHAT_APPSECRET = os.environ.get("WECHAT_APPSECRET", "")
WECHAT_OPENID = os.environ.get("WECHAT_OPENID", "")

# ============================================================
# 新闻源配置
# ============================================================

# ---- NewsAPI 搜索关键词（按10大领域分组）----
DOMAIN_SEARCH_QUERIES = {
    "地缘": [
        "geopolitics", "strategic rivalry", "Indo-Pacific", "NATO expansion",
        "South China Sea", "Taiwan Strait", "great power competition",
        "sphere of influence", "Arctic sovereignty", "buffer zone"
    ],
    "军武": [
        "military conflict", "ceasefire", "arms race", "nuclear weapons",
        "missile test", "defense budget", "troop deployment", "military exercise",
        "drone strike", "ballistic missile", "military base"
    ],
    "经贸": [
        "global economy", "inflation rate", "central bank interest",
        "oil price", "supply chain crisis", "trade war", "tariff",
        "sovereign debt", "currency crisis", "commodity price",
        "free trade agreement", "economic sanctions impact"
    ],
    "科创": [
        "artificial intelligence regulation", "semiconductor chip", "5G network",
        "space launch", "electric vehicle battery", "quantum computing",
        "biotechnology breakthrough", "tech export control"
    ],
    "生态": [
        "climate change", "carbon emission", "renewable energy",
        "extreme weather", "wildfire", "flood disaster", "drought",
        "Paris Agreement", "carbon neutrality", "deforestation"
    ],
    "外交": [
        "United Nations resolution", "G20 summit", "BRICS", "EU foreign policy",
        "diplomatic sanctions", "peace talks", "international mediation",
        "state visit", "bilateral summit", "multilateral agreement"
    ],
    "民生": [
        "pandemic outbreak", "food crisis", "refugee crisis",
        "earthquake disaster", "humanitarian aid", "famine",
        "infectious disease", "public health emergency"
    ],
    "社运": [
        "mass protest", "civil unrest", "labor strike", "migration crisis",
        "religious conflict", "ethnic tension", "populist movement",
        "gender equality movement", "indigenous rights"
    ],
    "治安": [
        "terrorist attack", "drug trafficking", "cyber attack",
        "human trafficking", "piracy", "organized crime",
        "INTERPOL operation", "counter-terrorism"
    ],
    "人文": [
        "Olympic Games", "World Cup", "cultural heritage UNESCO",
        "international education", "cross-cultural exchange",
        "tourism recovery", "archaeological discovery"
    ],
}

# ---- RSS 源列表（国际 + 国内）----
RSS_FEEDS = [
    # ---- 全球顶级通讯社 ----
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "region": "西欧", "tier": "S"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "region": "中东与北非", "tier": "S"},
    {"url": "http://feeds.reuters.com/reuters/worldnews", "region": "西欧", "tier": "S"},
    # ---- 区域主要媒体 ----
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "region": "北美", "tier": "S"},
    {"url": "https://feeds.washingtonpost.com/rss/world", "region": "北美", "tier": "A"},
    {"url": "https://www.france24.com/en/rss", "region": "西欧", "tier": "A"},
    {"url": "https://www.dw.com/en/rss/rss-en-news", "region": "西欧", "tier": "A"},
    {"url": "https://www3.nhk.or.jp/nhkworld/en/news/rss.xml", "region": "东亚", "tier": "A"},
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "region": "南亚", "tier": "B"},
    {"url": "https://www.africanews.com/feed/rss", "region": "撒哈拉以南非洲", "tier": "B"},
    {"url": "https://en.mercopress.com/rss", "region": "拉美", "tier": "B"},
    {"url": "https://www.euronews.com/rss", "region": "西欧", "tier": "A"},
    {"url": "https://www.themoscowtimes.com/rss/news", "region": "东欧", "tier": "B"},
    {"url": "https://www.arabnews.com/rss/top.xml", "region": "中东与北非", "tier": "B"},
    {"url": "https://www.scmp.com/rss/91/feed", "region": "东亚", "tier": "A"},
    # ---- 国内中文源（补充国内视角热度）----
    {"url": "https://feedx.net/rss/weibo-hot-search.xml", "region": "东亚", "tier": "C"},
    {"url": "https://feedx.net/rss/zhihu-hot.xml", "region": "东亚", "tier": "C"},
]

# ---- 媒体权威等级 ----
MEDIA_TIER_SCORE = {
    "S": 100,   # 全球顶级通讯社 / 国家级旗舰媒体
    "A": 75,    # 主流国际媒体
    "B": 50,    # 区域性主要媒体
    "C": 25,    # 自媒体 / 聚合平台
}

# ---- 国际通讯社列表 ----
GLOBAL_WIRE_AGENCIES = [
    "Reuters", "Associated Press", "AP", "Agence France-Presse", "AFP",
    "Xinhua", "新华社", "Al Jazeera", "半岛", "BBC", "CNN",
    "Bloomberg", "Financial Times", "Deutsche Presse-Agentur", "DPA",
    "EFE", "ANSA", "TASS", "Kyodo News"
]

# ---- 国际组织关键词 ----
INTERNATIONAL_ORGS = [
    "United Nations", "UN", "NATO", "European Union", "EU",
    "IMF", "World Bank", "WHO", "WTO", "G20", "G7",
    "BRICS", "ASEAN", "African Union", "OPEC", "IAEA",
    "UNESCO", "UNICEF", "Red Cross", "ICRC"
]

# ============================================================
# 9 大地理区域 → 国家映射
# ============================================================
REGION_COUNTRIES = {
    "中东与北非": [
        "Iran", "Saudi Arabia", "Israel", "UAE", "United Arab Emirates", "Qatar",
        "Egypt", "Turkey", "Iraq", "Syria", "Jordan", "Lebanon", "Yemen",
        "Oman", "Bahrain", "Kuwait", "Morocco", "Algeria", "Tunisia",
        "Libya", "Sudan", "Palestine", "Gaza", "West Bank", "Afghanistan",
        "巴基斯坦", "伊朗", "沙特", "以色列", "阿联酋", "卡塔尔", "埃及", "土耳其",
        "伊拉克", "叙利亚", "约旦", "黎巴嫩", "也门", "阿曼", "巴林", "科威特",
        "摩洛哥", "阿尔及利亚", "突尼斯", "利比亚", "苏丹", "巴勒斯坦", "阿富汗"
    ],
    "拉美与加勒比": [
        "Brazil", "Mexico", "Argentina", "Colombia", "Chile", "Peru",
        "Venezuela", "Cuba", "Ecuador", "Bolivia", "Paraguay", "Uruguay",
        "Guyana", "Suriname", "Nicaragua", "Honduras", "Guatemala",
        "El Salvador", "Costa Rica", "Panama", "Jamaica", "Haiti",
        "Dominican Republic", "Trinidad", "Belize", "Barbados",
        "巴西", "墨西哥", "阿根廷", "哥伦比亚", "智利", "秘鲁",
        "委内瑞拉", "古巴", "厄瓜多尔", "玻利维亚", "巴拉圭", "乌拉圭",
        "圭亚那", "苏里南", "尼加拉瓜", "洪都拉斯", "危地马拉",
        "萨尔瓦多", "哥斯达黎加", "巴拿马", "牙买加", "海地",
        "多米尼加", "特立尼达", "伯利兹", "巴巴多斯"
    ],
    "中亚与高加索": [
        "Kazakhstan", "Uzbekistan", "Turkmenistan", "Kyrgyzstan", "Tajikistan",
        "Georgia", "Armenia", "Azerbaijan", "Mongolia",
        "哈萨克斯坦", "乌兹别克斯坦", "土库曼斯坦", "吉尔吉斯斯坦", "塔吉克斯坦",
        "格鲁吉亚", "亚美尼亚", "阿塞拜疆", "蒙古"
    ],
    "东亚与太平洋": [
        "China", "Japan", "South Korea", "North Korea", "Australia",
        "New Zealand", "Taiwan", "Fiji", "Papua New Guinea",
        "Solomon Islands", "Vanuatu", "Samoa", "Tonga",
        "中国", "日本", "韩国", "朝鲜", "澳大利亚", "新西兰", "台湾",
        "斐济", "巴布亚新几内亚", "所罗门群岛"
    ],
    "撒哈拉以南非洲": [
        "South Africa", "Nigeria", "Kenya", "Ethiopia", "DRC", "Congo",
        "Ghana", "Tanzania", "Uganda", "Rwanda", "Senegal", "Mali",
        "Burkina Faso", "Niger", "Chad", "Somalia", "Zimbabwe", "Zambia",
        "Mozambique", "Angola", "Cameroon", "Ivory Coast", "Botswana",
        "Namibia", "Mauritius", "Sierra Leone", "Liberia",
        "南非", "尼日利亚", "肯尼亚", "埃塞俄比亚", "刚果", "加纳",
        "坦桑尼亚", "乌干达", "卢旺达", "塞内加尔", "马里",
        "布基纳法索", "尼日尔", "乍得", "索马里", "津巴布韦", "赞比亚"
    ],
    "东欧": [
        "Ukraine", "Poland", "Romania", "Bulgaria", "Czech Republic",
        "Slovakia", "Hungary", "Moldova", "Belarus", "Serbia",
        "Croatia", "Slovenia", "Bosnia", "Montenegro", "North Macedonia",
        "Albania", "Kosovo", "Lithuania", "Latvia", "Estonia",
        "乌克兰", "波兰", "罗马尼亚", "保加利亚", "捷克", "斯洛伐克",
        "匈牙利", "摩尔多瓦", "白俄罗斯", "塞尔维亚", "克罗地亚",
        "立陶宛", "拉脱维亚", "爱沙尼亚"
    ],
    "西欧南欧与北欧": [
        "UK", "United Kingdom", "France", "Germany", "Italy", "Spain",
        "Netherlands", "Belgium", "Switzerland", "Austria", "Sweden",
        "Norway", "Denmark", "Finland", "Ireland", "Portugal", "Greece",
        "Iceland", "Luxembourg", "Malta", "Cyprus", "Vatican",
        "英国", "法国", "德国", "意大利", "西班牙", "荷兰", "比利时",
        "瑞士", "奥地利", "瑞典", "挪威", "丹麦", "芬兰", "爱尔兰",
        "葡萄牙", "希腊", "冰岛", "卢森堡"
    ],
    "南亚与东南亚": [
        "India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Bhutan",
        "Maldives", "Indonesia", "Vietnam", "Thailand", "Philippines",
        "Malaysia", "Singapore", "Myanmar", "Cambodia", "Laos",
        "Brunei", "East Timor",
        "印度", "巴基斯坦", "孟加拉", "斯里兰卡", "尼泊尔", "不丹",
        "马尔代夫", "印度尼西亚", "越南", "泰国", "菲律宾",
        "马来西亚", "新加坡", "缅甸", "柬埔寨", "老挝"
    ],
    "北美": [
        "United States", "US", "USA", "Canada", "Greenland",
        "美国", "加拿大", "格陵兰"
    ],
}

# 国家 → 区域反向映射
COUNTRY_TO_REGION = {}
for region, countries in REGION_COUNTRIES.items():
    for country in countries:
        COUNTRY_TO_REGION[country.lower()] = region

# ============================================================
# 推送时间窗口配置（北京时间）
# ============================================================
# 北京时间与UTC换算: UTC = 北京时间 - 8
PUSH_SCHEDULE = {
    "morning": {   # 北京时间 06:00 → UTC 22:00 (前日)
        "window_hours": 10,
        "label": "晨间速递",
    },
    "noon": {      # 北京时间 12:00 → UTC 04:00
        "window_hours": 6,
        "label": "午间速递",
    },
    "evening": {   # 北京时间 20:00 → UTC 12:00
        "window_hours": 8,
        "label": "晚间速递",
    },
}

# ============================================================
# 热度公式权重参数
# ============================================================
HOTNESS_WEIGHTS = {
    "A_propagation": 0.35,    # 全域传播体量
    "B_interaction": 0.25,    # 用户互动深度
    "C_authority": 0.20,      # 国际权威背书
    "D_radiation": 0.15,      # 跨国辐射广度
    "E_decay": 0.05,          # 时效衰减修正
}

# A 子系统权重
PROPAGATION_SUB_WEIGHTS = {
    "overseas_social": 0.50,  # 海外社交平台曝光
    "domestic_total": 0.20,   # 国内全网总曝光
    "wire_agency": 0.20,      # 国际通讯社转载量
    "local_media": 0.10,      # 各国本土媒体转载数
}

# B 子系统权重
INTERACTION_SUB_WEIGHTS = {
    "multilingual_comments": 0.45,  # 多语种有效评论
    "cross_platform_share": 0.30,   # 跨平台转发分享
    "deep_analysis": 0.15,          # 全网解析二创内容
    "search_index": 0.10,           # 各国搜索指数均值
}

# C 子系统权重
AUTHORITY_SUB_WEIGHTS = {
    "media_tier": 0.50,       # 全球头部媒体版面层级
    "official_statement": 0.30,  # 主权国家政要表态
    "intl_org": 0.20,         # 国际组织发声/会议
}

# D 子系统权重
RADIATION_SUB_WEIGHTS = {
    "country_count": 0.40,    # 覆盖独立国家数量
    "continent_count": 0.35,  # 跨大洲分布
    "chain_effect": 0.25,     # 跨境连锁影响
}

# E 子系统权重
DECAY_SUB_WEIGHTS = {
    "time_decay": 0.60,       # 发布时长衰减
    "breaking_bonus": 0.40,   # 突发事件加成
}

# 浮动加减分上限
BONUS_PENALTY_CAP = 10.0

# 降噪系数 K 默认值
DEFAULT_K = 0.85

# 热度历史保留天数
HOTNESS_HISTORY_DAYS = 7

# ============================================================
# 推送配置
# ============================================================
PUSH_BATCH_SIZE = 20  # 每次推送 20 条
MIN_REGION_COVERAGE = 1   # 每个区域至少 1 条
MIN_DOMAIN_COVERAGE = 1   # 每个领域至少 1 条
