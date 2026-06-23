"""
10 大新闻领域自动分类器
基于标题和摘要中的关键词匹配，每条新闻可同时归属多个领域
"""
import re
from typing import List, Set

# 每个领域的核心关键词（英文 + 中文）
DOMAIN_KEYWORDS = {
    "地缘": [
        # 英文
        "geopolitic", "strategic rival", "sphere of influence", "great power",
        "indo-pacific", "indopacific", "south china sea", "taiwan strait",
        "buffer zone", "border dispute", "territorial", "sovereignty",
        "hegemon", "multipolar", "balancing", "containment",
        "arctic claim", "demilitarized zone", "dmz",
        "border clash", "border clash", "occupied territor", "annex",
        # 中文
        "地缘", "战略博弈", "势力范围", "印太", "南海", "台海",
        "领土争端", "主权纷争", "缓冲区", "多极化", "大国竞争"
    ],
    "军武": [
        # 英文
        "military", "war", "ceasefire", "troop", "missile", "nuclear weapon",
        "arms race", "defense budget", "drone strike", "air strike",
        "ballistic", "artillery", "tank", "fighter jet", "naval",
        "deployment", "mobilization", "conscription", "armored",
        "battlefield", "offensive", "counteroffensive", "casualt",
        "munition", "armament", "weapon", "guerrilla", "paramilitary",
        "hezbollah", "rocket", "clash", "militant", "militia",
        "rebels", "insurgent", "bombing", "shelling", "airstrike",
        # 中文
        "军事", "战争", "停火", "导弹", "核武器", "军备", "国防",
        "空袭", "坦克", "战机", "军舰", "征兵", "伤亡", "战场"
    ],
    "经贸": [
        # 英文
        "economy", "economic", "trade", "tariff", "inflation", "recession",
        "gdp", "currency", "exchange rate", "central bank", "interest rate",
        "fiscal", "debt", "bond", "stock market", "commodity price",
        "oil price", "gas price", "supply chain", "sanction", "embargo",
        "export", "import", "investment", "fdi", "trade agreement",
        "deficit", "surplus", "sovereign wealth", "bailout", "default",
        # 中文
        "经济", "贸易", "关税", "通胀", "衰退", "GDP", "央行",
        "利率", "债务", "股市", "油价", "供应链", "制裁", "出口"
    ],
    "科创": [
        # 英文
        "artificial intelligence", "AI ", "machine learning", "chatgpt",
        "semiconductor", "chip", "microchip", "5G", "6G", "telecom",
        "space launch", "satellite", "nasa", "spacex", "rocket",
        "electric vehicle", "battery", "quantum", "biotech", "genetic",
        "autonomous driving", "blockchain", "crypto", "cybersecurity",
        "tech export control", "chip ban", "technology transfer",
        # 中文
        "人工智能", "芯片", "半导体", "5G", "航天", "卫星", "火箭",
        "新能源", "电池", "量子", "生物技术", "自动驾驶", "区块链"
    ],
    "生态": [
        # 英文
        "climate change", "global warming", "carbon emission", "net zero",
        "paris agreement", "renewable energy", "solar power", "wind power",
        "deforestation", "biodiversity", "extreme weather", "wildfire",
        "flood", "drought", "hurricane", "typhoon", "earthquake",
        "sea level", "ice melt", "pollution", "environmental",
        "carbon tax", "fossil fuel", "green hydrogen",
        # 中文
        "气候", "碳排放", "碳中和", "可再生能源", "极端天气",
        "洪水", "干旱", "地震", "海啸", "台风", "污染", "环保"
    ],
    "外交": [
        # 英文
        "diploma", "summit", "bilateral", "multilateral", "treaty",
        "united nations", "UN resolution", "security council",
        "nato", "g20", "g7", "brics", "asean", "eu summit",
        "foreign minister", "state visit", "peace talk", "mediation",
        "sanction", "diplomatic relation", "ambassador", "embassy",
        "international court", "icc", "icj", "extradition",
        "foreign policy", "alliance", "partnership",
        # 中文
        "外交", "峰会", "双边", "多边", "联合国", "安理会", "北约",
        "G20", "金砖", "东盟", "外长", "访问", "斡旋", "制裁",
        "条约", "大使", "使馆", "国际法"
    ],
    "民生": [
        # 英文
        "pandemic", "outbreak", "epidemic", "covid", "disease",
        "food crisis", "famine", "malnutrition", "hunger",
        "refugee", "displaced", "humanitarian", "aid", "relief",
        "earthquake", "tsunami", "natural disaster",
        "public health", "vaccine", "healthcare",
        "water scarcity", "power outage", "blackout",
        # 中文
        "疫情", "疾病", "饥荒", "难民", "人道主义", "救援",
        "灾害", "地震", "疫苗", "公共卫生", "粮食"
    ],
    "社运": [
        # 英文
        "protest", "demonstration", "rally", "strike", "unrest",
        "migrant", "immigration", "asylum seeker", "border crisis",
        "racism", "racial", "discrimination", "apartheid",
        "religious conflict", "sectarian", "ethnic cleansing",
        "populis", "far-right", "far-left", "nationalism",
        "feminist", "lgbtq", "gender equality", "abortion",
        "civil rights", "human rights", "freedom of",
        # 中文
        "抗议", "示威", "罢工", "骚乱", "移民", "难民",
        "种族", "歧视", "宗教冲突", "民粹", "人权", "游行"
    ],
    "治安": [
        # 英文
        "terroris", "bombing", "suicide attack", "hostage",
        "drug cartel", "narcotic", "trafficking", "smuggling",
        "cyber attack", "hack", "ransomware", "data breach",
        "piracy", "hijack", "kidnap", "assassination",
        "interpol", "extradition", "organized crime", "mafia",
        "mass shooting", "gun violence", "gang",
        # 中文
        "恐怖", "爆炸", "贩毒", "网络攻击", "黑客", "海盗",
        "绑架", "暗杀", "国际刑警", "有组织犯罪", "枪击"
    ],
    "人文": [
        # 英文
        "olympic", "world cup", "fifa", "champions league",
        "cultural heritage", "unesco", "world heritage",
        "education exchange", "international student",
        "archaeolog", "discovery", "ancient",
        "tourism", "travel", "festival", "exhibition",
        "film festival", "cannes", "venice", "art fair",
        "literature", "nobel prize", "award",
        # 中文
        "奥运", "世界杯", "文化遗产", "考古", "发现",
        "旅游", "艺术", "电影", "音乐", "教育", "留学"
    ],
}


def classify_domains(title: str, description: str = "") -> List[str]:
    """
    对一条新闻进行10大领域分类
    返回：领域标签列表（可能为多个）
    """
    text = f"{title} {description}".lower()
    matched_domains: Set[str] = set()

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            # 使用单词边界匹配（英文）或直接子串匹配（中文）
            if len(kw) <= 3:
                # 短关键词用词边界
                pattern = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            else:
                # 长关键词用子串匹配
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
            if pattern.search(text):
                matched_domains.add(domain)
                break  # 匹配到一个关键词即可

    # 如果没有任何匹配，给定默认分类
    if not matched_domains:
        # 尝试推断
        if any(w in text for w in ["war", "conflict", "attack", "军队"]):
            matched_domains.add("军武")
        elif any(w in text for w in ["trade", "economy", "market", "经济"]):
            matched_domains.add("经贸")
        elif any(w in text for w in ["summit", "meeting", "talk", "峰会"]):
            matched_domains.add("外交")
        else:
            matched_domains.add("外交")  # 默认归入外交

    return sorted(matched_domains)


def get_primary_domain(title: str, description: str = "") -> str:
    """获取主领域（第一个匹���的）"""
    domains = classify_domains(title, description)
    return domains[0] if domains else "外交"
