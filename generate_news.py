#!/usr/bin/env python3
"""
Generate a beautiful mobile-friendly HTML news landing page.
Called by GitHub Actions after news is fetched — outputs news.html
which gets committed to the repo and served via raw.githubusercontent.com
"""
import io, os, sys, re, html, time, json

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news.html")

REGION_FLAGS = {
    "北美": "🇺🇸", "西欧": "🇪🇺", "东亚": "🌏", "南亚": "🌴",
    "东欧": "🏰", "中东与北非": "🕌", "拉美": "🌎",
    "撒哈拉以南非洲": "🌍", "西欧与南欧": "🇪🇺",
    "东亚与太平洋": "🌏", "南亚与东南亚": "🌴",
    "拉美与加勒比": "🌎", "中亚与高加索": "🏔️",
}


def generate(news_list: list, session_label: str = "auto") -> str:
    """Build a beautiful mobile-optimized HTML page from news items.
    Each item dict: title, url, hotness_score, summary, regions, domains, source_name
    """
    today = time.strftime("%Y年%m月%d日 %H:%M", time.localtime())
    label_map = {"morning": "晨间速递", "noon": "午间速递", "evening": "晚间速递"}
    session_name = label_map.get(session_label, "国际新闻速递")

    cards = ""
    for i, n in enumerate(news_list[:20], 1):
        s = n.get("hotness_score", 0)
        t = html.escape(n.get("summary_cn", "") or n.get("title", "") or "")
        desc = html.escape((n.get("description", "") or "")[:120])
        link = n.get("url", "")
        source = html.escape((n.get("source_name", "") or "")[:20])
        regions = n.get("regions", []) or []
        flag = REGION_FLAGS.get(regions[0], "📰") if regions else "📰"
        region = regions[0] if regions else ""
        heat = "🔥" if s >= 70 else ("🔶" if s >= 55 else "📌")

        cards += f'''
      <a href="{link}" class="card" target="_blank">
        <div class="card-top">
          <span class="num">{i}</span>
          <span class="score">{heat} {s:.0f}</span>
          <span class="badge region">{flag} {region}</span>
          <span class="badge source">{source}</span>
        </div>
        <p class="title">{t}</p>
        {f'<p class="desc">{desc}</p>' if desc else ''}
        <div class="arrow">→</div>
      </a>'''

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>🌍 国际热点新闻速递</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#0d1117;color:#c9d1d9;padding:12px;min-height:100vh;-webkit-text-size-adjust:none}}
.container{{max-width:600px;margin:0 auto}}
.header{{text-align:center;padding:24px 0 20px;border-bottom:1px solid #21262d;margin-bottom:16px}}
.header h1{{font-size:24px;color:#ff6b35;margin-bottom:6px}}
.header .sub{{color:#8b949e;font-size:13px}}
.header .st{{display:flex;justify-content:center;gap:8px;margin-top:10px;flex-wrap:wrap}}
.header .st span{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:4px 10px;font-size:12px;color:#8b949e}}
.card{{display:block;background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;margin:8px 0;text-decoration:none;position:relative}}
.card:active{{background:#1c2230;border-color:#ff6b35}}
.card-top{{display:flex;align-items:center;gap:6px;margin-bottom:8px;flex-wrap:wrap}}
.num{{background:#ff6b35;color:#fff;border-radius:50%;min-width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold}}
.score{{color:#ff6b35;font-size:13px;font-weight:bold}}
.badge{{padding:2px 8px;border-radius:10px;font-size:11px}}
.badge.region{{background:rgba(255,107,53,.12);color:#ff8c42}}
.badge.source{{background:rgba(56,139,253,.12);color:#58a6ff}}
.title{{color:#e6edf3;font-size:15px;line-height:1.5;margin-bottom:6px;font-weight:500}}
.desc{{color:#8b949e;font-size:13px;line-height:1.5}}
.arrow{{position:absolute;right:12px;top:50%;transform:translateY(-50%);color:#ff6b35;font-size:18px}}
.footer{{text-align:center;color:#484f58;font-size:11px;padding:20px 0;border-top:1px solid #21262d;margin-top:16px}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>🌍 国际热点新闻速递</h1>
<p class="sub">{today} · {session_name}</p>
<div class="st"><span>📊 {len(news_list[:20])} 条</span><span>📡 多源聚合</span></div>
</div>
{cards}
<div class="footer"><p>👆 点击卡片跳转原文</p><p>International News Pusher</p></div>
</div>
</body>
</html>'''


def main():
    # Try to load news data from the working directory (passed by main.py)
    data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "_current_batch.json")
    news_list = []
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            news_list = json.load(f)
    else:
        print("No _current_batch.json found, generating sample HTML")

    html_content = generate(news_list or [], "auto")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"news.html written ({len(html_content)} bytes)")


if __name__ == "__main__":
    main()
