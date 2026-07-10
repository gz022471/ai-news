#!/usr/bin/env python3
"""每日6大板块新闻 - NewsAPI实时搜索 + 豆包格式化 + WxPusher推送"""
import os, json, time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

ARK_KEY = os.environ["ARK_API_KEY"]
EP = os.environ.get("ARK_ENDPOINT", "ep-m-20260703163123-ll2fh")
WX_TOKEN, WX_UID = os.environ["WXPUSHER_TOKEN"], os.environ["WXPUSHER_UID"]
NEWS_KEY = os.environ["NEWSAPI_KEY"]
ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
WX_URL = "https://wxpusher.zjiecode.com/api/send/message"

def doubao(prompt: str, max_tokens: int = 2000) -> str:
    data = json.dumps({
        "model": EP, "temperature": 0.7, "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = Request(ARK_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ARK_KEY}"
    })
    return json.loads(urlopen(req, timeout=120).read())["choices"][0]["message"]["content"]

def wxpush(content: str) -> bool:
    resp = json.loads(urlopen(Request(WX_URL, data=json.dumps({
        "appToken": WX_TOKEN, "content": content,
        "contentType": 2, "uids": [WX_UID]
    }).encode(), headers={"Content-Type": "application/json"}), timeout=10).read())
    return resp.get("code") == 1000

def fetch_newsapi(endpoint: str, params: dict) -> list:
    """调用NewsAPI获取新闻"""
    qs = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
    url = f"https://newsapi.org/v2/{endpoint}?{qs}&apiKey={NEWS_KEY}"
    try:
        resp = json.loads(urlopen(Request(url, headers={
            "User-Agent": "AI-News-Bot/1.0"
        }), timeout=30).read())
        if resp["status"] == "ok":
            return resp.get("articles", [])[:20]
        else:
            print(f"    NewsAPI错误: {resp.get('message', 'unknown')}")
    except Exception as e:
        print(f"    NewsAPI失败: {e}")
    return []

def format_articles(articles: list, count: int, label: str) -> str:
    """将文章列表转为豆包可用的文本"""
    lines = []
    for i, a in enumerate(articles[:count]):
        title = a.get("title", "") or "无标题"
        desc = (a.get("description") or "")[:80]
        lines.append(f"{i+1}. {title} | {desc}")
    return "\n".join(lines)

# 6大板块定义
SECTIONS = [
    {
        "title": "🌍 国际热点", "count": 10,
        "endpoint": "everything",
        "params": {"q": "world OR global OR international", "language": "en", "pageSize": "20", "sortBy": "publishedAt"},
        "desc": "全球重大新闻"
    },
    {
        "title": "🇨🇳 国内热点", "count": 10,
        "endpoint": "everything",
        "params": {"q": "中国 OR 国内", "language": "zh", "pageSize": "20", "sortBy": "publishedAt"},
        "desc": "中国热点新闻"
    },
    {
        "title": "🏙️ 兰州本地", "count": 10,
        "endpoint": "everything",
        "params": {"q": "兰州市", "language": "zh", "pageSize": "20", "sortBy": "publishedAt"},
        "desc": "兰州市本地新闻"
    },
    {
        "title": "🤖 AI Agent", "count": 5,
        "endpoint": "everything",
        "params": {"q": "\"AI Agent\" OR \"智能体\" OR \"人工智能代理\"", "pageSize": "15", "sortBy": "publishedAt"},
        "desc": "AI Agent/智能体动态"
    },
    {
        "title": "⚽ 体育热点", "count": 5,
        "endpoint": "everything",
        "params": {"q": "sports OR football OR basketball OR 体育", "pageSize": "15", "sortBy": "publishedAt"},
        "desc": "全球体育热点"
    },
    {
        "title": "🏠 兰州二手房", "count": 1,
        "endpoint": "everything",
        "params": {"q": "兰州 房价 OR 二手房 OR 楼盘", "language": "zh", "pageSize": "10", "sortBy": "publishedAt"},
        "desc": "兰州各区二手房行情"
    },
]

CSS = ("body{margin:0;padding:0;font-size:14px;color:#e0e0e0;background:#0d1117}"
       "h2{color:#ffd700;text-align:center;margin:12px 0 4px;font-size:17px}"
       ".sub{color:#888;text-align:center;font-size:11px;margin:0 0 10px}"
       ".sec{margin:0;padding:10px 14px;border-bottom:1px solid #21262d}"
       ".st{font-size:14px;font-weight:bold;margin:0 0 6px;color:#ffd700;"
       "border-left:3px solid #ffd700;padding-left:8px}"
       ".ft{text-align:center;color:#555;font-size:10px;padding:10px}")

def generate_section(sec: dict) -> tuple:
    """获取新闻 + 豆包格式化"""
    articles = fetch_newsapi(sec["endpoint"], sec["params"])
    if not articles:
        return sec["title"], "<span style='color:#888'>暂无实时数据</span>"
    
    raw = format_articles(articles, sec["count"] * 2, sec["title"])
    prompt = f"""请根据以下新闻源，生成{sec['count']}条{sec['desc']}汇总。
每条格式：<b>【标题】</b> — 简述（20字内）<br/><br/>
新闻源：
{raw}

要求：精选最重要的{sec['count']}条，按重要性排序。直接输出HTML。"""
    
    try:
        result = doubao(prompt, max_tokens=1500)
        return sec["title"], result
    except Exception as e:
        return sec["title"], f"<span style='color:#f66'>⚠️ {e}</span>"

if __name__ == "__main__":
    today = datetime.now().strftime("%Y年%m月%d日")
    print(f"🕗 {today} 新闻...")

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(generate_section, s): s for s in SECTIONS}
        for f in as_completed(futures, timeout=400):
            title, html = f.result(timeout=200)
            results[title] = html
            print(f"  ✅ {title}")

    html_head = (f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>{CSS}</style>"
                 f"</head><body><h2>📡 {today}</h2>"
                 f"<div class=\"sub\">{today} · 6大板块新闻推送</div>")
    html_foot = "<div class=\"ft\">每晚 20:00 自动推送 · NewsAPI+豆包 · 仅供参考</div></body></html>"

    mid = len(SECTIONS) // 2
    html = html_head
    for i, sec in enumerate(SECTIONS):
        html += (f'<div class="sec"><div class="st">📌 {sec["title"]}</div>'
                 f'{results.get(sec["title"], "")}</div>')
        if i == mid - 1 or i == len(SECTIONS) - 1:
            html += html_foot
            ok = wxpush(html)
            print(f"  {'✅' if ok else '❌'} 第{i//mid+1}组")
            html = html_head
    print("✅ 完成")
