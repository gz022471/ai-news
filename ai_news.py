#!/usr/bin/env python3
"""每日6大板块新闻 - NewsAPI实时 + 豆包知识库 + WxPusher推送"""
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
    return json.loads(urlopen(req, timeout=180).read())["choices"][0]["message"]["content"]

def wxpush(content: str) -> bool:
    resp = json.loads(urlopen(Request(WX_URL, data=json.dumps({
        "appToken": WX_TOKEN, "content": content,
        "contentType": 2, "uids": [WX_UID]
    }).encode(), headers={"Content-Type": "application/json"}), timeout=10).read())
    return resp.get("code") == 1000

def fetch_newsapi(endpoint: str, params: dict) -> list:
    qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    url = f"https://newsapi.org/v2/{endpoint}?{qs}&apiKey={NEWS_KEY}"
    try:
        resp = json.loads(urlopen(Request(url, headers={
            "User-Agent": "AI-News-Bot/1.0"
        }), timeout=30).read())
        if resp["status"] == "ok":
            return resp.get("articles", [])[:20]
        print(f"    NewsAPI({resp.get('message','?')})")
    except Exception as e:
        print(f"    NewsAPI({e})")
    return []

def format_articles(articles: list, count: int) -> str:
    lines = []
    for i, a in enumerate(articles[:count]):
        title = (a.get("title") or "无标题")[:100]
        lines.append(f"{i+1}. {title}")
    return "\n".join(lines)

# 板块定义: (标题, 数量, 来源, 提示词/参数)
SECTIONS = [
    # NewsAPI 板块
    ("🌍 国际热点", 10, "newsapi", {
        "endpoint": "everything",
        "params": {"q": "world OR global OR international", "language": "en", "pageSize": "20", "sortBy": "publishedAt"},
        "desc": "过去24小时全球最重要的国际大事"
    }),
    ("⚽ 体育热点", 5, "newsapi", {
        "endpoint": "everything",
        "params": {"q": "sports OR football OR basketball OR tennis OR F1", "pageSize": "15", "sortBy": "publishedAt"},
        "desc": "体育热点新闻（足球篮球网球F1电竞等）"
    }),
    ("🤖 AI Agent", 5, "newsapi", {
        "endpoint": "everything",
        "params": {"q": '"AI agent" OR "artificial intelligence" OR LLM OR chatbot', "pageSize": "15", "sortBy": "publishedAt"},
        "desc": "AI Agent/大模型/人工智能领域近期重要动态"
    }),
    # 豆包直接生成板块
    ("🇨🇳 国内热点", 10, "doubao", {
        "prompt": "请列出近期中国10条最重要的国内热点新闻。每条格式：<b>【标题】</b> — 简述（20字内）<br/><br/>如果不知道今天的，用最近一周的。直接输出。",
    }),
    ("🏙️ 兰州本地", 10, "doubao", {
        "prompt": "请列出近期兰州市10条本地民生、交通、政策、城建、天气方面的热点。每条：<b>【标题】</b> — 简述（20字内）<br/><br/>直接输出。",
    }),
    ("🏠 兰州二手房", 1, "doubao", {
        "prompt": "根据你的知识，汇总兰州三个区二手房行情：<br/><b>城关区</b>：参考均价约X元/㎡，热门板块：XX<br/><b>七里河区</b>：参考均价约X元/㎡，热门板块：XX<br/><b>安宁区</b>：参考均价约X元/㎡，热门板块：XX<br/>注明：数据为AI知识库参考。",
    }),
]

CSS = ("body{margin:0;padding:0;font-size:14px;color:#e0e0e0;background:#0d1117}"
       "h2{color:#ffd700;text-align:center;margin:12px 0 4px;font-size:17px}"
       ".sub{color:#888;text-align:center;font-size:11px;margin:0 0 10px}"
       ".sec{margin:0;padding:10px 14px;border-bottom:1px solid #21262d}"
       ".st{font-size:14px;font-weight:bold;margin:0 0 6px;color:#ffd700;"
       "border-left:3px solid #ffd700;padding-left:8px}"
       ".ft{text-align:center;color:#555;font-size:10px;padding:10px}")

def generate_newsapi(title: str, count: int, cfg: dict) -> tuple:
    articles = fetch_newsapi(cfg["endpoint"], cfg["params"])
    if not articles:
        return title, "<span style='color:#888'>暂无实时数据，稍后更新</span>"
    raw = format_articles(articles, count)
    prompt = f"""精选{cfg['desc']}，生成{count}条。
格式：<b>【标题】</b> — 简述<br/><br/>
新闻源：
{raw}
只输出最重要的{count}条，按重要性排序。直接输出HTML。"""
    return title, doubao(prompt, max_tokens=1000)

def generate_doubao(title: str, count: int, cfg: dict) -> tuple:
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"今天日期：{today}。\n{cfg['prompt']}"
    return title, doubao(prompt, max_tokens=1000)

if __name__ == "__main__":
    today = datetime.now().strftime("%Y年%m月%d日")
    print(f"🕗 {today} 新闻...")

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {}
        for title, count, src, cfg in SECTIONS:
            if src == "newsapi":
                futures[pool.submit(generate_newsapi, title, count, cfg)] = title
            else:
                futures[pool.submit(generate_doubao, title, count, cfg)] = title

        for f in as_completed(futures, timeout=500):
            t, html = f.result(timeout=300)
            results[t] = html
            print(f"  ✅ {t}")

    html_head = (f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>{CSS}</style>"
                 f"</head><body><h2>📡 {today}</h2>"
                 f"<div class=\"sub\">{today} · 6大板块新闻推送</div>")
    html_foot = "<div class=\"ft\">每晚 20:00 自动推送 · NewsAPI+豆包 · 仅供参考</div></body></html>"

    mid = len(SECTIONS) // 2
    html = html_head
    for i, (title, _, _, _) in enumerate(SECTIONS):
        html += f'<div class="sec"><div class="st">📌 {title}</div>{results.get(title, "")}</div>'
        if i == mid - 1 or i == len(SECTIONS) - 1:
            html += html_foot
            ok = wxpush(html)
            print(f"  {'✅' if ok else '❌'} 第{i//mid+1}组")
            html = html_head
    print("✅ 完成")
