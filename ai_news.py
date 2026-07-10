#!/usr/bin/env python3
"""每日热点新闻聚合 - DuckDuckGo搜索 + 豆包格式化 + WxPusher推送"""
import os, json, time
from datetime import datetime
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor, as_completed

ARK_KEY = os.environ["ARK_API_KEY"]
EP = os.environ.get("ARK_ENDPOINT", "ep-m-20260703163123-ll2fh")
WX_TOKEN, WX_UID = os.environ["WXPUSHER_TOKEN"], os.environ["WXPUSHER_UID"]
ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
WX_URL = "https://wxpusher.zjiecode.com/api/send/message"

def doubao(prompt: str, max_tokens: int = 2000) -> str:
    req = Request(ARK_URL, data=json.dumps({
        "model": EP, "temperature": 0.7, "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode(), headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ARK_KEY}"
    })
    return json.loads(urlopen(req, timeout=180).read())["choices"][0]["message"]["content"]

def wxpush(content: str) -> bool:
    resp = json.loads(urlopen(Request(WX_URL, data=json.dumps({
        "appToken": WX_TOKEN, "content": content,
        "contentType": 2, "uids": [WX_UID]
    }).encode(), headers={"Content-Type": "application/json"}), timeout=10).read())
    return resp['code'] == 1000

def search_news(query: str, max_results: int = 5) -> list[str]:
    """DuckDuckGo 新闻搜索"""
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().news(query, max_results=max_results, region='cn-zh'))
        if results:
            return [f"{r['title']} — {r['body'][:60]}" for r in results]
    except Exception as e:
        print(f"    DDG搜索失败: {e}，用豆包生成...")
    return []

TASKS = [
    ("🌍 国际热点", 10, "国际热点新闻", "今天全球最重要的国际热点新闻"),
    ("🇨🇳 国内热点", 10, "中国国内热点新闻", "今天中国最重要的国内热点新闻"),
    ("🏙️ 兰州本地", 10, "兰州新闻热点", "今天兰州市本地民生交通政策热点"),
    ("🤖 AI Agent", 5, "AI Agent 发展趋势", "今天AI Agent人工智能体领域重要动态"),
    ("⚽ 体育热点", 5, "体育新闻", "今天全球体育热点新闻足球篮球电竞"),
    ("🏠 兰州二手房", 3, "兰州二手房房价 城关区 七里河区 安宁区", "兰州各区二手房均价"),
]

CSS = """
body{margin:0;padding:0;font-size:14px;color:#e0e0e0;background:#0d1117}
h2{color:#ffd700;text-align:center;margin:12px 0 4px;font-size:17px}
.sub{color:#888;text-align:center;font-size:11px;margin:0 0 10px}
.sec{margin:0;padding:10px 14px;border-bottom:1px solid #21262d}
.st{font-size:14px;font-weight:bold;margin:0 0 6px;color:#ffd700;border-left:3px solid #ffd700;padding-left:8px}
.ft{text-align:center;color:#555;font-size:11px;padding:10px}
"""

def generate_section(title: str, count: int, query: str, desc: str) -> str:
    """搜索 + 格式化单个板块"""
    # 先搜索
    search_results = search_news(query, max_results=count)
    
    if search_results:
        prompt = f"""根据以下搜索结果，生成{count}条新闻汇总。每条格式：<b>【标题】</b> — 简述（20字内）<br/><br/>
搜索结果：
{chr(10).join(search_results[:count*2])}

要求：按重要性排序，直接输出HTML格式。"""
    else:
        prompt = f"""搜索{desc}，生成{count}条。每条格式：<b>【标题】</b> — 简述（20字内）<br/><br/>
按重要性排序。如果没有今天的，用最近一周的。直接输出。"""
    
    return doubao(prompt, max_tokens=1500)

if __name__ == "__main__":
    today = datetime.now().strftime("%Y年%m月%d日")
    print(f"🕗 生成 {today} 新闻...")

    # 并行搜索+格式化
    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(generate_section, t, c, q, d): t for t, c, q, d in TASKS}
        for f in as_completed(futures, timeout=400):
            section = futures[f]
            try:
                results[section] = f.result(timeout=200)
                print(f"  ✅ {section}")
            except Exception as e:
                print(f"  ❌ {section}: {e}，重试...")
                time.sleep(10)
                try:
                    t, c, q, d = [(title, count, query, desc) for title, count, query, desc in TASKS if title == section][0]
                    results[section] = generate_section(t, c, q, d)
                    print(f"  ✅ {section} (重试)")
                except Exception as e2:
                    results[section] = f"⚠️ 本板块暂时无法生成: {e2}"
                    print(f"  ❌ {section}: 重试也失败")

    # 拼2条消息
    html_head = f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>{CSS}</style></head><body><h2>📡 {today}</h2><div class=\"sub\">{today} · 6大板块新闻推送</div>"
    html_foot = "<div class=\"ft\">每晚 20:00 自动推送 · AI 聚合 · 仅供参考</div></body></html>"
    
    mid = len(TASKS) // 2
    html = html_head
    for i, (title, _, _, _) in enumerate(TASKS):
        section = f'<div class="sec"><div class="st">📌 {title}</div>{results.get(title, "")}</div>'
        html += section
        if i == mid - 1 or i == len(TASKS) - 1:
            html += html_foot
            ok = wxpush(html)
            print(f"  推送{'✅' if ok else '❌'} 第{i//mid + 1}组")
            html = html_head
    print("✅ 完成")
