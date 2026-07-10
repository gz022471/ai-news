#!/usr/bin/env python3
"""每日热点新闻聚合 - 每天 20:00 推送微信"""
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

def wxpush(content: str):
    resp = json.loads(urlopen(Request(WX_URL, data=json.dumps({
        "appToken": WX_TOKEN, "content": content,
        "contentType": 2, "uids": [WX_UID]
    }).encode(), headers={"Content-Type": "application/json"}), timeout=10).read())
    print(f"推送: {'✅' if resp['code'] == 1000 else resp.get('msg', '失败')}")
    return resp['code'] == 1000

TASKS = [
    ("🌍 国际热点", "搜索今天全球最重要的10条国际热点新闻。每条格式：<b>【标题】</b> — 简述（15字内）<br/>按重要性排序，直接输出。"),
    ("🇨🇳 国内热点", "搜索今天中国10条最重要的国内热点新闻。每条格式：<b>【标题】</b> — 简述（15字内）<br/>按热度排序，直接输出。"),
    ("🏙️ 兰州本地", "搜索今天兰州市10条本地热点（民生/交通/政策/天气/城建）。每条：<b>【标题】</b> — 简述（15字内）<br/>直接输出。"),
    ("🤖 AI Agent", "搜索今天AI Agent领域5条重要动态（技术/应用/行业）。每条：<b>【标题】</b> — 简述（25字内）<br/>直接输出。"),
    ("⚽ 体育热点", "搜索今天5条体育热点（足球/篮球/电竞等）。每条：<b>【标题】</b> — 简述（15字内）<br/>直接输出。"),
    ("🏠 兰州二手房", "汇总兰州城关/七里河/安宁三区二手房均价。格式：<br/><b>城关区</b>：均价约X元/㎡，环比±X%，热门：XX、XX<br/><b>七里河区</b>：均价约X元/㎡，环比±X%，热门：XX、XX<br/><b>安宁区</b>：均价约X元/㎡，环比±X%，热门：XX、XX<br/>注明数据来源。"),
]

CSS = """
body{margin:0;padding:0;font-size:14px;color:#e0e0e0;background:#0d1117}
h2{color:#ffd700;text-align:center;margin:12px 0 4px;font-size:17px}
.sub{color:#888;text-align:center;font-size:11px;margin:0 0 10px}
.sec{margin:0;padding:10px 14px;border-bottom:1px solid #21262d}
.st{font-size:14px;font-weight:bold;margin:0 0 6px;color:#ffd700;border-left:3px solid #ffd700;padding-left:8px}
.item{margin:4px 0;line-height:1.5}
.ft{text-align:center;color:#555;font-size:11px;padding:10px}
"""

HEADER = """<div class="sub">{{date}} · 6大板块新闻推送</div>"""
FOOTER = """<div class="ft">每晚 20:00 自动推送 · AI 聚合 · 仅供参考</div>"""

SECTION_HTML = """<div class="sec">
<div class="st">📌 {title}</div>
{content}
</div>"""

if __name__ == "__main__":
    today = datetime.now().strftime("%Y年%m月%d日")
    print(f"🕗 生成 {today} 新闻...")

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(doubao, prompt): section for section, prompt in TASKS}
        for f in as_completed(futures, timeout=300):
            section = futures[f]
            try:
                results[section] = f.result(timeout=180)
                print(f"  ✅ {section}")
            except Exception as e:
                print(f"  ❌ {section}: {e}，10秒后重试...")
                time.sleep(10)
                # 重试失败板块
                prompt = dict(TASKS)[section]
                try:
                    results[section] = doubao(prompt)
                    print(f"  ✅ {section} (重试成功)")
                except Exception as e2:
                    results[section] = f"⚠️ 本板块暂时无法生成，明天见"
                    print(f"  ❌ {section}: 重试也失败")

    # 拼接板块，分2条消息防止截断
    html_head = f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>{CSS}</style></head><body><h2>📡 {today}</h2>{HEADER.replace('{{date}}', today)}"
    html_foot = "</body></html>"
    
    mid = len(TASKS) // 2
    for i, (title, prompt) in enumerate(TASKS):
        content = results.get(title, "生成失败")
        section = SECTION_HTML.format(title=title, content=content)
        if i == 0:
            html = html_head
        html += section
        if i == mid - 1 or i == len(TASKS) - 1:
            html += FOOTER + html_foot
            ok = wxpush(html)
            print(f"  推送{'✅' if ok else '❌'} 第{i//mid + 1}组 ({i+1}板块)")
            html = html_head  # reset for next msg
    
    print("✅ 完成")
