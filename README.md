# AI Company v0.1

一个**按需变形的AI公司**，通过多agent协作，帮你把模糊想法变成落地成果。

## 设计理念

这不是一个固定功能的工具，而是一个"万能公司"：
- 每次你带着新想法来，这个公司就"变形"成你需要的组织
- CEO帮你挖掘需求、补足专业知识的盲点
- 小步快跑，先做最小版本验证

## 当前版本 (v0.1)

**已实现：**
- [x] CEO Agent - 需求挖掘与规划
- [x] Web对话界面
- [x] 支持OpenAI/Claude API

**待实现：**
- [ ] CHRO Agent - 创建/管理worker agents
- [ ] COO Agent - 协调执行
- [ ] 记忆系统 - 跨项目经验积累
- [ ] CFO Agent - 成本控制

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API Key

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env，填入你的API Key
# 支持 OpenAI 或 Claude
```

### 3. 启动

```bash
python run.py
```

访问 http://localhost:8000 开始与CEO对话。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                         上帝层                              │
│    用户 + 对话模型 + 记忆系统（可更换模型，知识不丢）          │
└─────────────────────────────────┬───────────────────────────┘
                                  │
┌─────────────────────────────────┴───────────────────────────┐
│                        公司层                               │
│   C-Level: CEO / CHRO / COO / CFO(后续)                    │
│   组长层: 按需创建                                          │
│   执行者层: 动态worker agents                               │
│                                                             │
│   ※ 扁平架构，最多三级，任意层级可通信                       │
└─────────────────────────────────────────────────────────────┘
```

## CEO工作流程

1. **框架** - "做这件事通常需要这些模块..."
2. **提问** - 针对关键信息提问，帮你想清楚
3. **发散** - 提出你可能没想到的方向
4. **收敛** - 输出结构化可执行计划
5. **等你** - 你说"开始"才执行

## 配置

### LLM配置 (config/llm.yaml)

```yaml
default_provider: openai  # 或 claude

providers:
  openai:
    base_url: https://api.openai.com/v1
    model: gpt-4
  claude:
    model: claude-3-opus-20240229
```

## 目录结构

```
ai-company/
├── config/
│   ├── llm.yaml              # LLM配置
│   └── prompts/              # Agent prompt模板
│       └── ceo.md
├── src/
│   ├── core/                 # 核心模块
│   │   ├── llm.py            # LLM通用接口
│   │   └── message.py        # 消息定义
│   ├── roles/                # Agent实现
│   │   └── ceo.py
│   └── web/                  # Web界面
│       └── app.py
├── data/                     # 数据存储（记忆、会话）
├── run.py                    # 启动入口
└── requirements.txt
```

## 设计决策记录

详见 [DESIGN_DECISIONS.md](./DESIGN_DECISIONS.md)

---

*v0.1 - 验证CEO核心流程是否work*
