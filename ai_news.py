#!/usr/bin/env python3
"""每日6大板块新闻 - NewsAPI搜索 + DeepSeek格式化 + WxPusher推送"""
import os, json, time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

DS_KEY = os.environ["DEEPSEEK_API_KEY"]
WX_TOKEN, WX_UID = os.environ["WXPUSHER_TOKEN"], os.environ["WXPUSHER_UID"]
NEWS_KEY = os.environ["NEWSAPI_KEY"]
DS_URL = "https://api.deepseek.com/v1/chat/completions"
WX_URL = "https://wxpusher.zjiecode.com/api/send/message"

def ds(prompt: str, max_tokens: int = 1500) -> str:
    data = json.dumps({
        "model": "deepseek-chat", "temperature": 0.7, "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = Request(DS_URL, data=data, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {DS_KEY}"
    })
    return json.loads(urlopen(req, timeout=60).read())["choices"][0]["message"]["content"]

def wxpush(content: str) -> bool:
    resp = json.loads(urlopen(Request(WX_URL, data=json.dumps({
        "appToken": WX_TOKEN, "content": content,
        "contentType": 2, "uids": [WX_UID]
    }).encode(), headers={"Content-Type": "application/json"}), timeout=10).read())
    return resp.get("code") == 1000

def fetch_news(endpoint: str, params: dict) -> list:
    qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    url = f"https://newsapi.org/v2/{endpoint}?{qs}&apiKey={NEWS_KEY}"
    try:
        resp = json.loads(urlopen(Request(url, headers={
            "User-Agent": "AI-News-Bot/1.0"
        }), timeout=15).read())
        return resp.get("articles", [])[:15] if resp["status"] == "ok" else []
    except Exception as e:
        print(f"    NewsAPI({e})")
        return []

SECTIONS = [
    # NewsAPI 实时板块
    ("🌍 国际热点", 10, "news", {
        "ep": "everything",
        "p": {"q": "world OR global OR international", "language": "en", "pageSize": "15", "sortBy": "publishedAt"},
        "d": "过去24小时全球最重要的国际新闻"
    }),
    ("⚽ 体育热点", 5, "news", {
        "ep": "everything",
        "p": {"q": "sports OR football OR basketball OR tennis OR F1", "pageSize": "15", "sortBy": "publishedAt"},
        "d": "全球体育热点（足球篮球网球F1电竞等）"
    }),
    ("🤖 AI Agent", 5, "news", {
        "ep": "everything",
        "p": {"q": '"AI agent" OR "LLM" OR "大模型" OR ChatGPT OR Claude', "pageSize": "15", "sortBy": "publishedAt"},
        "d": "AI Agent/大模型领域近期重要动态"
    }),
    # DeepSeek 知识库板块
    ("🇨🇳 国内热点", 10, "ds", {
        "p": f"请根据你的知识，列出近期中国10条最重要的国内热点新闻（今天是{datetime.now().strftime('%Y-%m-%d')}）。每条：<b>【标题】</b> — 简述（20字内）<br/><br/>直接输出。"
    }),
    ("🏙️ 兰州本地", 10, "ds", {
        "p": f"请列出近期兰州市10条本地民生、交通、政策、城建、天气热点。每条：<b>【标题】</b> — 简述（20字内）<br/><br/>兰州市位于甘肃省，是省会城市。今天日期：{datetime.now().strftime('%Y-%m-%d')}。"
    }),
    ("🏠 兰州二手房", 1, "ds", {
        "p": f"根据你的知识，汇总兰州二手房行情（今天{datetime.now().strftime('%Y-%m-%d')}）：<br/><b>城关区</b>：参考均价约X元/㎡<br/><b>七里河区</b>：参考均价约X元/㎡<br/><b>安宁区</b>：参考均价约X元/㎡<br/>注明：AI知识库参考价。"
    }),
]

CSS = ("body{margin:0;padding:0;font-size:14px;color:#e0e0e0;background:#0d1117}"
       "h2{color:#ffd700;text-align:center;margin:12px 0 4px;font-size:17px}"
       ".sub{color:#888;text-align:center;font-size:11px;margin:0 0 10px}"
       ".sec{margin:0;padding:10px 14px;border-bottom:1px solid #21262d}"
       ".st{font-size:14px;font-weight:bold;margin:0 0 6px;color:#ffd700;"
       "border-left:3px solid #ffd700;padding-left:8px}"
       ".ft{text-align:center;color:#555;font-size:10px;padding:10px}")

def gen_news(title: str, count: int, cfg: dict) -> tuple:
    articles = fetch_news(cfg["ep"], cfg["p"])
    if not articles:
        return title, "<span style='color:#888'>暂无实时数据</span>"
    src = "\n".join(f"{i+1}. {(a.get('title')or'')[:100]}" for i,a in enumerate(articles[:count]))
    prompt = f"精选{cfg['d']}，生成{count}条。\n格式：<b>【标题】</b> — 简述\n\n源：\n{src}\n\n只输出最重要的{count}条。"
    return title, ds(prompt, max_tokens=1200)

def gen_ds(title: str, count: int, cfg: dict) -> tuple:
    return title, ds(cfg["p"], max_tokens=1200)

if __name__ == "__main__":
    today = datetime.now().strftime("%Y年%m月%d日")
    print(f"🕗 {today} 新闻...")

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {}
        for title, count, src, cfg in SECTIONS:
            fn = gen_news if src == "news" else gen_ds
            futures[pool.submit(fn, title, count, cfg)] = title
        for f in as_completed(futures, timeout=300):
            t, html = f.result(timeout=180)
            results[t] = html
            print(f"  ✅ {t}")

    head = (f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>{CSS}</style>"
            f"</head><body><h2>📡 {today}</h2>"
            f"<div class=\"sub\">{today} · 6大板块新闻推送</div>")
    foot = "<div class=\"ft\">每晚 20:00 自动推送 · NewsAPI+DeepSeek</div></body></html>"

    mid = len(SECTIONS) // 2
    html = head
    for i, (title, _, _, _) in enumerate(SECTIONS):
        html += f'<div class="sec"><div class="st">📌 {title}</div>{results.get(title, "")}</div>'
        if i == mid - 1 or i == len(SECTIONS) - 1:
            html += foot
            ok = wxpush(html)
            print(f"  {'✅' if ok else '❌'} 第{i//mid+1}组")
            html = head
    print("✅ 完成")
