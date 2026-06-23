#!/usr/bin/env python3
"""
生成国际热点新闻 HTML 页面 → docs/index.html
GitHub Pages 托管目录

页面结构：
  🔥 热度榜（TOP 20 卡片视图）
  🌏 按区域查看（10大区域分栏）
  🏷️ 按领域查看（10个领域分栏）
  📊 覆盖统计
"""
import io, os, sys, re, time, json
# Avoid 'html' module shadowing — rename it
import html as _html

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

REGION_FLAGS = {
    "中东与北非": "🕌", "拉美与加勒比": "🌎", "中亚与高加索": "🏔️",
    "东亚与太平洋": "🌏", "撒哈拉以南非洲": "🌍", "东欧": "🏰",
    "西欧与南欧": "🇪🇺", "南亚与东南亚": "🌴", "北美": "🇺🇸",
    "西欧": "🇪🇺", "东亚": "🌏", "南亚": "🌴", "拉美": "🌎",
}

TEN_DOMAINS = ["地缘", "军武", "经贸", "科创", "生态", "外交", "民生", "社运", "治安", "人文"]
NINE_REGIONS = ["中东与北非", "拉美与加勒比", "中亚与高加索", "东亚与太平洋",
                "撒哈拉以南非洲", "东欧", "西欧与南欧", "南亚与东南亚", "北美"]

DOMAIN_EMOJI = {"地缘": "🗺️", "军武": "⚔️", "经贸": "💰", "科创": "🔬", "生态": "🌿",
                "外交": "🤝", "民生": "🏥", "社运": "✊", "治安": "🛡️", "人文": "🎭"}


def generate(news_list: list, all_news: list = None, session_label: str = "auto") -> str:
    """生成完整 HTML 页面，包含热度榜 + 区域视图 + 领域视图 + 统计"""
    all_news = all_news or news_list
    today = time.strftime("%Y年%m月%d日", time.localtime())
    label_map = {"morning": "🌅 晨间速递", "noon": "🌤️ 午间速递", "evening": "🌙 晚间速递"}
    session_name = label_map.get(session_label, "📡 国际新闻速递")

    # === 统计 ===
    region_count = {}
    domain_count = {}
    for n in news_list[:20]:
        for r in n.get("regions", []):
            region_count[r] = region_count.get(r, 0) + 1
        for d in n.get("domains", []):
            domain_count[d] = domain_count.get(d, 0) + 1

    scores = [n.get("hotness_score", 0) for n in news_list[:20] if n.get("hotness_score", 0) > 0]
    avg_s = sum(scores) / len(scores) if scores else 0

    # === HELPERS ===
    def news_card(n, i):
        s = n.get("hotness_score", 0)
        # 优先用翻译后的中文标题，其次是 summary_cn，再往后用原始 title
        t = _html.escape(
            n.get("title_cn", "") or
            n.get("summary_cn", "") or
            n.get("title", "") or ""
        )
        # 概要：优先 description_cn > summary > description
        d = _html.escape(
            (n.get("description_cn", "") or
             n.get("summary", "") or
             n.get("description", "") or "")[:200]
        )
        link = n.get("url", "")
        source = _html.escape((n.get("source_name", "") or "")[:20])
        regions = n.get("regions", []) or []
        flag = REGION_FLAGS.get(regions[0], "📰") if regions else "📰"
        region = regions[0] if regions else ""
        heat = "🔥" if s >= 70 else ("🔶" if s >= 55 else "📌")
        return f'''
        <a href="{link}" class="card" target="_blank" rel="noopener">
          <div class="card-top">
            <span class="num">{i}</span>
            <span class="score">{heat} {s:.0f}分</span>
            <span class="badge region">{flag} {region}</span>
            <span class="badge source">{source}</span>
          </div>
          <p class="title">{t}</p>
          {f'<p class="desc">{d}</p>' if d else ''}
          <span class="arrow">→</span>
        </a>'''

    # === TOP 20 卡片 ===
    top_cards = "\n".join(news_card(n, i) for i, n in enumerate(news_list[:20], 1))

    # === 按区域分栏 ===
    region_sections = ""
    for reg in NINE_REGIONS:
        reg_news = [n for n in news_list[:20] if reg in (n.get("regions", []) or [])]
        if not reg_news:
            continue
        flag = REGION_FLAGS.get(reg, "🌍")
        cards = "\n".join(news_card(n, news_list[:20].index(n) + 1) for n in reg_news)
        region_sections += f'''
        <div class="section">
          <h2 class="section-title">{flag} {reg} ({len(reg_news)}条)</h2>
          <div class="card-grid">{cards}</div>
        </div>'''

    # === 按领域分栏 ===
    domain_sections = ""
    for dom in TEN_DOMAINS:
        dom_news = [n for n in news_list[:20] if dom in (n.get("domains", []) or [])]
        if not dom_news:
            continue
        de = DOMAIN_EMOJI.get(dom, "📌")
        cards = "\n".join(news_card(n, news_list[:20].index(n) + 1) for n in dom_news)
        domain_sections += f'''
        <div class="section">
          <h2 class="section-title">{de} {dom} ({len(dom_news)}条)</h2>
          <div class="card-grid">{cards}</div>
        </div>'''

    # === 覆盖统计 ===
    stat_rows = ""
    for reg in NINE_REGIONS:
        cnt = region_count.get(reg, 0)
        bar = "█" * cnt
        stat_rows += f"<tr><td class='stat-label'>{REGION_FLAGS.get(reg,'🌍')} {reg}</td><td class='stat-bar'>{bar}</td><td class='stat-num'>{cnt}条</td></tr>"

    # === FULL HTML ===
    html = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>🌍 国际热点新闻速递</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#0d1117;color:#c9d1d9;padding:12px;min-height:100vh;-webkit-text-size-adjust:none}}
.container{{max-width:700px;margin:0 auto}}

/* Header */
.header{{text-align:center;padding:30px 0 20px;border-bottom:1px solid #21262d;margin-bottom:20px}}
.header h1{{font-size:26px;color:#ff6b35;margin-bottom:6px}}
.header .sub{{color:#8b949e;font-size:13px}}
.header .st{{display:flex;justify-content:center;gap:8px;margin-top:10px;flex-wrap:wrap}}
.header .st span{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:4px 10px;font-size:12px;color:#8b949e}}

/* Section titles */
.section-title{{font-size:18px;color:#ff6b35;margin:28px 0 12px;padding-bottom:8px;border-bottom:2px solid rgba(255,107,53,0.2)}}

/* Cards */
.card-grid{{display:flex;flex-direction:column;gap:8px}}
.card{{display:block;background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;text-decoration:none;position:relative}}
.card:active{{background:#1c2230;border-color:#ff6b35}}
.card-top{{display:flex;align-items:center;gap:6px;margin-bottom:8px;flex-wrap:wrap}}
.num{{background:#ff6b35;color:#fff;border-radius:50%;min-width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold}}
.score{{color:#ff6b35;font-size:13px;font-weight:bold}}
.badge{{padding:2px 8px;border-radius:10px;font-size:11px}}
.badge.region{{background:rgba(255,107,53,.12);color:#ff8c42}}
.badge.source{{background:rgba(56,139,253,.12);color:#58a6ff}}
.title{{color:#e6edf3;font-size:15px;line-height:1.5;margin-bottom:4px;font-weight:500}}
.desc{{color:#8b949e;font-size:13px;line-height:1.5}}
.arrow{{position:absolute;right:12px;top:50%;transform:translateY(-50%);color:#ff6b35;font-size:18px}}

/* Stats table */
.stat-table{{width:100%;border-collapse:collapse;margin:8px 0}}
.stat-table td{{padding:6px 8px;border-bottom:1px solid #21262d;font-size:13px}}
.stat-label{{color:#c9d1d9;white-space:nowrap}}
.stat-bar{{color:#ff6b35;font-family:monospace;letter-spacing:2px}}
.stat-num{{color:#8b949e;text-align:right}}

/* Nav */
.nav{{display:flex;justify-content:center;gap:8px;margin:16px 0;flex-wrap:wrap}}
.nav a{{display:inline-block;padding:6px 14px;background:#161b22;border:1px solid #30363d;border-radius:8px;color:#c9d1d9;text-decoration:none;font-size:13px}}
.nav a:active{{background:#1c2230;border-color:#ff6b35;color:#ff6b35}}

/* Footer */
.footer{{text-align:center;color:#484f58;font-size:11px;padding:24px 0;border-top:1px solid #21262d;margin-top:24px}}
.footer p{{margin:2px 0}}
</style>
</head>
<body>
<div class="container">

<div class="header">
<h1>🌍 国际时政日报</h1>
<p class="sub">{today} · {session_name}</p>
<div class="st">
  <span>📊 {len(news_list[:20])} 条精选</span>
  <span>🌐 {len(region_count)}/{len(NINE_REGIONS)} 区域</span>
  <span>🏷️ {len(domain_count)}/{len(TEN_DOMAINS)} 领域</span>
  <span>🔥 均{avg_s:.0f}分</span>
</div>
</div>

<nav class="nav">
  <a href="#top">🔥 热度榜</a>
  <a href="#regions">🌏 按区域</a>
  <a href="#domains">🏷️ 按领域</a>
  <a href="#stats">📊 统计</a>
</nav>

<!-- 🔥 热度榜 -->
<h2 class="section-title" id="top">🔥 今日热度榜 TOP {len(news_list[:20])}</h2>
<div class="card-grid">
{top_cards}
</div>

<!-- 🌏 按区域 -->
<h2 class="section-title" id="regions">🌏 按区域查看</h2>
{region_sections}

<!-- 🏷️ 按领域 -->
<h2 class="section-title" id="domains">🏷️ 按领域查看</h2>
{domain_sections}

<!-- 📊 覆盖统计 -->
<h2 class="section-title" id="stats">📊 覆盖统计</h2>
<table class="stat-table">
{stat_rows}
</table>

<div class="footer">
  <p>👆 点击任意卡片跳转原文</p>
  <p>International News Pusher · GitHub Pages · 每日 6:00/12:00/20:00 自动更新</p>
</div>
</div>
</body>
</html>'''

    return html


def generate_and_save(news_list, all_news, session_label, output_dir):
    """Entry point called from main.py"""
    html_content = generate(news_list, all_news, session_label)
    output_path = os.path.join(output_dir, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path


def main():
    """从 data/_current_batch.json 读取新闻数据，生成 HTML"""
    data_file = os.path.join(PROJECT_ROOT, "data", "_current_batch.json")
    all_file = os.path.join(PROJECT_ROOT, "data", "_all_news.json")

    news_list = []
    all_news = []

    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            news_list = json.load(f)
    if os.path.exists(all_file):
        with open(all_file, "r", encoding="utf-8") as f:
            all_news = json.load(f)
    if not all_news:
        all_news = news_list

    if not news_list:
        print("No _current_batch.json found")
        sys.exit(1)

    os.makedirs(DOCS_DIR, exist_ok=True)

    # Determine session from hour
    h = time.localtime().tm_hour
    session = "morning" if 4 <= h < 10 else ("noon" if 10 <= h < 16 else "evening")

    html_content = generate(news_list, all_news, session)
    output_path = os.path.join(DOCS_DIR, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"docs/index.html written ({len(html_content)} bytes)")
    print(f"  {len(news_list[:20])} news items, {len(set(r for n in news_list[:20] for r in n.get('regions',[])))} regions, {len(set(d for n in news_list[:20] for d in n.get('domains',[])))} domains")


if __name__ == "__main__":
    main()
