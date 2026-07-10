#!/usr/bin/env python3
"""AI Agent 每日晚间新闻 - 由 GitHub Actions 每天 20:00 运行"""
import os, json, smtplib
from email.mime.text import MIMEText
from datetime import datetime
from urllib.request import Request, urlopen

# 豆包 API 配置
ARK_API_KEY = os.environ["ARK_API_KEY"]
ENDPOINT_ID = os.environ.get("ARK_ENDPOINT", "ep-m-20260703163123-ll2fh")
ARK_URL = f"https://ark.cn-beijing.volces.com/api/v3/chat/completions"

EMAIL_TO = os.environ.get("EMAIL_TO", "295129003@qq.com")
EMAIL_PASS = os.environ.get("EMAIL_PASS", "")

def call_doubao(prompt: str) -> str:
    """调用豆包 API 生成新闻"""
    req = Request(
        ARK_URL,
        data=json.dumps({
            "model": ENDPOINT_ID,
            "messages": [
                {"role": "system", "content": f"你是专业AI新闻主播。今天是{datetime.now().strftime('%Y年%m月%d日')}。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1200
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ARK_API_KEY}"
        }
    )
    resp = urlopen(req, timeout=60)
    data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]

def send_email(subject: str, body: str):
    """发送邮件"""
    if not EMAIL_PASS:
        print(f"\n{'='*50}\n  {subject}\n{'='*50}\n{body}")
        return
    
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = "295129003@qq.com"
    msg["To"] = EMAIL_TO
    
    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login("295129003@qq.com", EMAIL_PASS)
    server.sendmail("295129003@qq.com", [EMAIL_TO], msg.as_string())
    server.quit()
    print("✅ 邮件已发送")

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
    subject = f"🤖 AI Agent 晚间新闻 | {today}"
    
    send_email(subject, news)
    print("✅ 完成")
