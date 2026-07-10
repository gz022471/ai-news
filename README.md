# AI Agent 每日晚间新闻

每天 20:00（北京时间）自动搜索 AI Agent 领域最新动态，生成晚间新闻播报，发送到指定邮箱。

## 工作原理

- **GitHub Actions** 每天 20:00 CST 自动触发
- 调用 **豆包大模型 API** 搜索并生成新闻
- 通过 **QQ邮箱 SMTP** 发送到你的邮箱

## 配置步骤

### 1. Fork/创建此仓库到你的 GitHub

### 2. 设置 GitHub Secrets（Settings → Secrets and variables → Actions）

| Secret | 说明 |
|--------|------|
| `ARK_API_KEY` | 火山引擎 Ark API Key |
| `EMAIL_PASS` | QQ邮箱 SMTP 授权码（不是登录密码！） |

### 3. 获取 QQ 邮箱授权码
QQ邮箱 → 设置 → 账户 → POP3/SMTP服务 → 开启 → 生成授权码

### 4. 手动测试
Actions → "AI Agent 每日晚间新闻" → Run workflow

## 文件说明

- `ai_news.py` - 核心脚本，调用豆包 API 生成新闻
- `.github/workflows/ai-news.yml` - GitHub Actions 定时触发配置
