# 💡 灵感捕捉 Bot

一个 Telegram Bot，帮你随时记录灵感，AI 自动整理成思维模型，存储到 Obsidian。

## 功能

### 记录灵感
- **文字输入**：发送文字消息，AI 自动分析
- **语音输入**：发送语音，自动转文字后分析
- **图片输入**：发送图片，OCR 提取文字后分析
- **智能分析**：自动匹配思维模型、推荐标签
- **智能推荐**：当现有模型匹配度不高时，AI 会推荐新模型

### 回顾与连接
- **随机回顾**：随机查看历史灵感
- **灵感关联**：AI 分析两条灵感的潜在联系
- **周报生成**：自动生成思维周报
- **每日提醒**：每天 9:00 推送随机灵感回顾

### 模型管理
- **预置模型**：内置 20 个经典思维模型
- **搜索添加**：AI 联网搜索新思维模型
- **自定义管理**：添加、删除思维模型

### 存储
- **Obsidian 存储**：所有数据保存为 Markdown
- **双向链接**：灵感与思维模型自动建立双向链接，在 Obsidian 图谱中可视化关联
- **本地安全**：数据完全存储在本地

## 架构

```
Telegram Bot ←→ Google Gemini 2.5 Flash ←→ Obsidian Vault
  (交互)              (分析)                  (存储)
    ↓
  文字/语音/图片
```

## 快速开始

### 1. 准备工作

- 一台一直在线的 Mac（或 Linux）
- Python 3.9+
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

# 安装依赖（国内用户建议使用镜像）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
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
ALLOWED_USER_IDS=你的Telegram用户ID（可选，配置后启用每日提醒）
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

### 6. 代理设置（国内用户）

如果无法连接 Telegram，需要设置代理：

```bash
export https_proxy=http://127.0.0.1:你的代理端口
export http_proxy=http://127.0.0.1:你的代理端口
python bot.py
```

### 7. 后台运行（可选）

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

### 记录灵感

| 操作 | 说明 |
|------|------|
| 发送文字 | AI 分析并保存灵感 |
| 发送语音 | 转文字后分析保存 |
| 发送图片 | OCR 提取文字后分析保存 |

### 查看回顾

| 命令 | 说明 |
|------|------|
| `/recent` | 最近 10 条灵感 |
| `/random` | 随机回顾一条旧灵感 |
| `/search 关键词` | 搜索灵感 |
| `/connect` | AI 分析两条灵感的关联 |
| `/summary` | 生成本周思维周报 |

### 思维模型管理

| 命令 | 说明 |
|------|------|
| `/models` | 查看思维模型库 |
| `/addmodel 关键词` | 搜索并添加新模型 |
| `/delmodel 名称` | 删除指定模型 |

### 其他

| 命令 | 说明 |
|------|------|
| `/stats` | 统计信息 |
| `/myid` | 获取你的 Telegram ID |
| `/help` | 帮助信息 |

## 灵感笔记格式

```markdown
---
date: 2025-12-11 14:30
tags: [产品, 设计]
models: [[奥卡姆剃刀]], [[第一性原理]]
---

# 好的产品都是在做减法

今天发现，好的产品都是在做减法，不是堆功能...

## AI 分析

这个想法体现了奥卡姆剃刀原则——如无必要，勿增实体...

## 相关灵感
```

保存灵感时，关联的思维模型文件会自动更新，在「相关灵感」部分添加反向链接：

```markdown
## 相关灵感

- [[2025-12-11-143000-好的产品都是在做减法...]]
- [[2025-12-10-091500-简单才是最好的设计...]]
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

> 💡 使用 `/addmodel 关键词` 可以搜索并添加更多思维模型

## 项目结构

```
.
├── bot.py              # Telegram Bot 主程序
├── ai.py               # AI 分析模块（Gemini）
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
- 灵感内容会发送到 Google Gemini API 进行分析

## License

MIT
