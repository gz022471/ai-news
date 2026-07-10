#!/usr/bin/env python3
"""每日6大板块新闻 - 豆包生成 + WxPusher推送"""
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
        "model": EP, "temperature": 0.5, "max_tokens": max_tokens,
        "messages": [{"role": "system",
            "content": f"你是新闻编辑。今天日期：{datetime.now().strftime('%Y-%m-%d')}。根据你的知识库整理近期热点，无法确认的标注「据公开报道」。直接输出HTML格式结果。"},
            {"role": "user", "content": prompt}]
    }).encode(), headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ARK_KEY}"
    })
    try:
        return json.loads(urlopen(req, timeout=120).read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"<span style='color:#ff6666'>⚠️ {e}</span>"

def wxpush(content: str) -> bool:
    resp = json.loads(urlopen(Request(WX_URL, data=json.dumps({
        "appToken": WX_TOKEN, "content": content,
        "contentType": 2, "uids": [WX_UID]
    }).encode(), headers={"Content-Type": "application/json"}), timeout=10).read())
    return resp['code'] == 1000

TASKS = [
    ("🌍 国际热点", "列出近期全球10条重要国际新闻。每条：<b>【标题】</b> — 15字简述<br/>按重要性排序。"),
    ("🇨🇳 国内热点", "列出近期中国10条重要国内新闻。每条：<b>【标题】</b> — 15字简述<br/>按热度排序。"),
    ("🏙️ 兰州本地", "列出近期兰州10条本地热点（民生/交通/政策/城建/天气）。每条：<b>【标题】</b> — 15字简述<br/>"),
    ("🤖 AI Agent", "列出近期AI Agent/智能体领域5条重要动态。每条：<b>【标题】</b> — 25字简述<br/>"),
    ("⚽ 体育热点", "列出近期5条体育热点（足球篮球电竞等）。每条：<b>【标题】</b> — 15字简述<br/>"),
    ("🏠 兰州二手房", "汇总兰州城关区/七里河区/安宁区二手房行情。<br/><b>城关区</b>：均价X元/㎡，热门：XX、XX<br/><b>七里河区</b>：均价X元/㎡，热门：XX、XX<br/><b>安宁区</b>：均价X元/㎡，热门：XX、XX<br/>注明数据来源。"),
]

CSS = "body{margin:0;padding:0;font-size:14px;color:#e0e0e0;background:#0d1117}" \
      "h2{color:#ffd700;text-align:center;margin:12px 0 4px;font-size:17px}" \
      ".sub{color:#888;text-align:center;font-size:11px;margin:0 0 10px}" \
      ".sec{margin:0;padding:10px 14px;border-bottom:1px solid #21262d}" \
      ".st{font-size:14px;font-weight:bold;margin:0 0 6px;color:#ffd700;" \
      "border-left:3px solid #ffd700;padding-left:8px}" \
      ".ft{text-align:center;color:#555;font-size:10px;padding:10px}"

HTML_HEAD = lambda d: f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>{CSS}</style></head><body><h2>📡 {d}</h2><div class=\"sub\">{d} · 6大板块新闻推送</div>"
HTML_FOOT = "<div class=\"ft\">每晚 20:00 自动推送 · AI生成 · 仅供参考</div></body></html>"

def generate(title: str, prompt: str) -> tuple:
    try:
        return title, doubao(prompt)
    except Exception as e:
        return title, f"<span style='color:#f66'>⚠️ 生成失败</span>"

if __name__ == "__main__":
    today = datetime.now().strftime("%Y年%m月%d日")
    print(f"🕗 {today} 新闻...")

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(generate, t, p): t for t, p in TASKS}
        for f in as_completed(futures, timeout=300):
            t, content = f.result(timeout=150)
            results[t] = content
            print(f"  ✅ {t}")

    mid = len(TASKS) // 2
    html = HTML_HEAD(today)
    for i, (title, _) in enumerate(TASKS):
        html += f'<div class="sec"><div class="st">📌 {title}</div>{results.get(title, "")}</div>'
        if i == mid - 1 or i == len(TASKS) - 1:
            html += HTML_FOOT
            ok = wxpush(html)
            print(f"  {'✅' if ok else '❌'} 第{i//mid+1}组")
            html = HTML_HEAD(today)
    print("✅ 完成")
