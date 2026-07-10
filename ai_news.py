#!/usr/bin/env python3
"""AI Agent 每日晚间新闻 - 由 GitHub Actions 每天 20:00 运行，推送到微信"""
import os, json
from datetime import datetime
from urllib.request import Request, urlopen

ARK_API_KEY = os.environ["ARK_API_KEY"]
ARK_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
ENDPOINT_ID = os.environ.get("ARK_ENDPOINT", "ep-m-20260703163123-ll2fh")
PUSHPLUS_TOKEN = os.environ["PUSHPLUS_TOKEN"]

def call_doubao(prompt: str) -> str:
    req = Request(ARK_URL, data=json.dumps({
        "model": ENDPOINT_ID,
        "messages": [
            {"role": "system", "content": f"你是专业AI新闻主播。今天是{datetime.now().strftime('%Y年%m月%d日')}。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7, "max_tokens": 1200
    }).encode(), headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ARK_API_KEY}"
    })
    return json.loads(urlopen(req, timeout=60).read())["choices"][0]["message"]["content"]

def push_wechat(title: str, content: str):
    req = Request("http://pushplus.plus/send", data=json.dumps({
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content.replace("\n", "<br>"),
        "template": "html"
    }).encode(), headers={"Content-Type": "application/json"})
    resp = json.loads(urlopen(req, timeout=10).read())
    print(f"推送: {'✅' if resp.get('code')==200 else resp.get('msg','失败')}")

PROMPT = """请搜索并整理过去24小时内AI Agent（人工智能代理/智能体）领域重大新闻，生成晚间新闻播报。

格式：
晚上好，欢迎收看【今日AI Agent晚间新闻】

🏷️ 头条新闻
1-2条最重要的AI Agent消息

🔬 技术前沿
框架、工具、模型的最新突破

🏭 产业落地
实际场景应用案例

📊 趋势观察
简要点评（1-2句）

以上是今天的AI Agent晚间新闻，我们明天同一时间再见。

要求：500字以内，简明扼要，优先中文来源。直接输出新闻，不要额外说明。"""

if __name__ == "__main__":
    today = datetime.now().strftime("%Y年%m月%d日")
    print(f"🕗 生成 {today} AI Agent 晚间新闻...")
    news = call_doubao(PROMPT)
    push_wechat(f"🤖 AI Agent 晚间新闻 | {today}", news)
