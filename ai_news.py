#!/usr/bin/env python3
"""AI Agent 每日晚间新闻 - GitHub Actions 每天 20:00 → WxPusher → 微信"""
import os, json
from datetime import datetime
from urllib.request import Request, urlopen

ARK_KEY, EP = os.environ["ARK_API_KEY"], os.environ.get("ARK_ENDPOINT", "ep-m-20260703163123-ll2fh")
WX_TOKEN, WX_UID = os.environ["WXPUSHER_TOKEN"], os.environ["WXPUSHER_UID"]
ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
WX_URL = "https://wxpusher.zjiecode.com/api/send/message"

def doubao(prompt: str) -> str:
    req = Request(ARK_URL, data=json.dumps({
        "model": EP, "temperature": 0.7, "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": f"专业AI新闻主播。{datetime.now().strftime('%Y年%m月%d日')}。"},
            {"role": "user", "content": prompt}
        ]
    }).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {ARK_KEY}"})
    return json.loads(urlopen(req, timeout=60).read())["choices"][0]["message"]["content"]

def wxpush(title: str, content: str):
    resp = json.loads(urlopen(Request(WX_URL, data=json.dumps({
        "appToken": WX_TOKEN, "content": f"[{title}]\n\n{content}",
        "contentType": 1, "uids": [WX_UID]
    }).encode(), headers={"Content-Type": "application/json"}), timeout=10).read())
    print(f"推送: {'✅' if resp['code'] == 1000 else resp.get('msg', '失败')}")

PROMPT = """搜索过去24小时AI Agent领域重大新闻，生成晚间播报。

晚上好，欢迎收看【今日AI Agent晚间新闻】

🏷️ 头条新闻（1-2条）
🔬 技术前沿
🏭 产业落地
📊 趋势观察（1-2句）

以上是今天的AI Agent晚间新闻，我们明天同一时间再见。

要求：500字以内，简明扼要，优先中文来源。直接输出。"""

if __name__ == "__main__":
    today = datetime.now().strftime("%Y年%m月%d日")
    print(f"🕗 生成 {today} 新闻...")
    wxpush(f"🤖 AI Agent 晚间新闻 | {today}", doubao(PROMPT))
