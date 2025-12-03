# 💡 灵感捕捉 Bot

一个 Telegram Bot，帮你随时记录灵感，AI 自动整理成思维模型，存储到 Obsidian。

## 功能

- **快速记录**：在 Telegram 发消息即可记录灵感
- **AI 分析**：自动识别灵感涉及的思维模型
- **智能标签**：AI 推荐相关标签
- **Obsidian 存储**：所有数据保存为 Markdown，支持双向链接
- **预置模型**：内置 20 个经典思维模型

## 架构

```
Telegram Bot ←→ Google Gemini AI ←→ Obsidian Vault
    (输入)          (分析)            (存储)
```

## 快速开始

### 1. 准备工作

- 一台一直在线的 Mac（或 Linux）
- Python 3.10+
- Telegram 账号
- Google AI API Key（免费）

### 2. 获取 API Keys

**Telegram Bot Token:**
1. 在 Telegram 搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示创建，获取 Token

**Google AI API Key:**
1. 访问 https://aistudio.google.com/apikey
2. 创建 API Key（免费）

### 3. 安装

```bash
# 克隆项目
git clone <repo-url>
cd <repo-name>

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 配置

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，填入你的配置
```

**.env 文件内容：**
```
TELEGRAM_BOT_TOKEN=你的Telegram Bot Token
GOOGLE_AI_API_KEY=你的Google AI Key
OBSIDIAN_VAULT_PATH=/Users/你的用户名/Documents/Obsidian/你的Vault名
ALLOWED_USER_IDS=你的Telegram用户ID（可选）
```

> 💡 不知道你的 Telegram ID？启动 Bot 后发送 `/myid` 即可获取

### 5. 运行

```bash
python bot.py
```

首次运行会自动在你的 Obsidian vault 中创建：
- `💡 灵感/` - 存放灵感笔记
- `🧠 思维模型/` - 预置的 20 个思维模型
- `📊 总结/` - 周报等总结

### 6. 后台运行（可选）

使用 `nohup` 让 Bot 在后台持续运行：

```bash
nohup python bot.py > bot.log 2>&1 &
```

或使用 `screen`：

```bash
screen -S idea-bot
python bot.py
# 按 Ctrl+A+D 分离会话
```

## 使用方法

| 操作 | 说明 |
|------|------|
| 发送任意消息 | 记录灵感，AI 自动分析 |
| `/models` | 查看思维模型库 |
| `/recent` | 最近 10 条灵感 |
| `/random` | 随机回顾一条旧灵感 |
| `/search 关键词` | 搜索灵感 |
| `/stats` | 统计信息 |
| `/myid` | 获取你的 Telegram ID |
| `/help` | 帮助信息 |

## 灵感笔记格式

```markdown
---
date: 2024-01-15 14:30
tags: [产品, 设计]
models: [[奥卡姆剃刀]], [[第一性原理]]
---

# 好的产品都是在做减法

今天发现，好的产品都是在做减法，不是堆功能...

## AI 分析

这个想法体现了奥卡姆剃刀原则——如无必要，勿增实体...

## 相关灵感
```

## 预置思维模型

| 类别 | 模型 |
|------|------|
| 分析 | 第一性原理、奥卡姆剃刀 |
| 策略 | 逆向思维、能力圈、护城河 |
| 效率 | 二八法则、杠杆思维 |
| 决策 | 机会成本、概率思维 |
| 认知偏差 | 确认偏误、沉没成本、锚定效应、幸存者偏差 |
| 系统 | 系统思维、飞轮效应、反脆弱 |
| 长期 | 复利思维、边际效用递减 |
| 其他 | 类比思维、心智模型 |

## 项目结构

```
.
├── bot.py              # Telegram Bot 主程序
├── ai.py               # AI 分析模块
├── vault.py            # Obsidian Vault 读写
├── vault_templates/    # 思维模型模板
├── requirements.txt    # Python 依赖
├── .env.example        # 配置示例
└── .gitignore
```

## 安全说明

- API Keys 存储在 `.env` 文件，已加入 `.gitignore`
- 可通过 `ALLOWED_USER_IDS` 限制只有你能使用 Bot
- 所有数据存储在本地 Obsidian vault

## License

MIT
