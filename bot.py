"""
灵感捕捉 Telegram Bot
记录灵感，AI 整理成思维模型
"""

import os
import logging
import base64
from pathlib import Path
from datetime import time, datetime

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from vault import ObsidianVault
from ai import create_analyzer

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# 全局变量
vault: ObsidianVault = None
analyzer: IdeaAnalyzer = None
ALLOWED_USERS: set = set()

# 临时存储待确认的灵感
pending_ideas: dict = {}
# 临时存储待确认的新模型
pending_models: dict = {}


def is_authorized(user_id: int) -> bool:
    """检查用户是否授权"""
    if not ALLOWED_USERS:
        return True  # 如果没有配置限制，则允许所有人
    return user_id in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ 你没有使用此 Bot 的权限")
        return

    welcome_text = """💡 **灵感捕捉 Bot**

随时记录你的灵感，我会帮你整理成思维模型。

**记录灵感：**
• 发送文字 → 记录灵感
• 发送语音 → 语音转文字记录
• 发送图片 → OCR 提取文字记录

**查看回顾：**
• /recent → 最近的灵感
• /random → 随机回顾
• /connect → 发现灵感关联
• /summary → 生成周报

**思维模型：**
• /models → 查看模型库
• /addmodel 关键词 → 搜索添加新模型
• /delmodel 名称 → 删除模型

• /stats → 统计信息
• /help → 帮助信息

开始记录你的第一个灵感吧！"""

    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    if not is_authorized(update.effective_user.id):
        return

    help_text = """💡 **灵感捕捉 Bot 帮助**

**记录灵感**
• 发送文字消息 → AI 分析并保存
• 发送语音消息 → 转文字后分析保存
• 发送图片 → OCR 提取文字后分析保存

**查看回顾**
• /recent - 最近 10 条灵感
• /random - 随机回顾一条旧灵感
• /search <关键词> - 搜索灵感
• /connect - 随机找两条灵感的关联
• /summary - 生成本周思维周报

**思维模型管理**
• /models - 查看所有思维模型
• /addmodel <关键词> - 搜索并添加新模型
• /delmodel <名称> - 删除一个模型

**其他**
• /stats - 查看统计信息
• /myid - 获取你的 Telegram ID

**小技巧**
• 灵感不用写太长，几句话即可
• AI 会自动推荐新的思维模型
• 定期用 /random 和 /connect 激发新想法"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """获取用户 ID"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"你的 Telegram ID: `{user_id}`\n\n"
        "将此 ID 添加到 .env 文件的 ALLOWED_USER_IDS 可限制 Bot 仅对你可用",
        parse_mode="Markdown",
    )


async def models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看思维模型库"""
    if not is_authorized(update.effective_user.id):
        return

    model_list = vault.get_model_names()
    if not model_list:
        await update.message.reply_text("思维模型库为空")
        return

    text = "🧠 **思维模型库**\n\n"
    for i, name in enumerate(sorted(model_list), 1):
        text += f"{i}. {name}\n"

    text += f"\n共 {len(model_list)} 个模型"
    text += "\n\n💡 使用 `/addmodel 关键词` 搜索添加新模型"
    await update.message.reply_text(text, parse_mode="Markdown")


async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看最近的灵感"""
    if not is_authorized(update.effective_user.id):
        return

    ideas = vault.get_recent_ideas(10)
    if not ideas:
        await update.message.reply_text("还没有记录任何灵感，发送一条消息开始吧！")
        return

    text = "💡 **最近的灵感**\n\n"
    for idea in ideas:
        date = idea.get("date", "")[:10]
        preview = idea.get("preview", "")[:50]
        text += f"• [{date}] {preview}...\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def random_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """随机回顾一条灵感"""
    if not is_authorized(update.effective_user.id):
        return

    idea = vault.get_random_idea()
    if not idea:
        await update.message.reply_text("还没有记录任何灵感")
        return

    text = f"🎲 **随机灵感回顾**\n\n{idea.get('content', '')}\n\n_来自: {idea.get('name', '')}_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """搜索灵感"""
    if not is_authorized(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("请提供搜索关键词，例如: /search 产品")
        return

    keyword = " ".join(context.args)
    results = vault.search_ideas(keyword)

    if not results:
        await update.message.reply_text(f"没有找到包含「{keyword}」的灵感")
        return

    text = f"🔍 **搜索「{keyword}」的结果**\n\n"
    for r in results[:10]:
        text += f"• {r.get('name', '')[:30]}\n"
        text += f"  _{r.get('match', '')[:40]}_\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """统计信息"""
    if not is_authorized(update.effective_user.id):
        return

    ideas_count = vault.get_ideas_count()
    models_count = vault.get_models_count()

    text = f"""📊 **统计信息**

💡 灵感总数: {ideas_count}
🧠 思维模型: {models_count}

继续记录，让思维更有体系！"""

    await update.message.reply_text(text, parse_mode="Markdown")


async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """找两条灵感的关联"""
    if not is_authorized(update.effective_user.id):
        return

    idea1, idea2 = vault.get_two_random_ideas()
    if not idea1 or not idea2:
        await update.message.reply_text("需要至少 2 条灵感才能进行关联分析")
        return

    thinking_msg = await update.message.reply_text("🔗 正在分析两条灵感的关联...")

    try:
        connection = analyzer.generate_connection(idea1["content"], idea2["content"])

        text = f"""🔗 **灵感关联分析**

**灵感 1:**
_{idea1['content'][:100]}{'...' if len(idea1['content']) > 100 else ''}_

**灵感 2:**
_{idea2['content'][:100]}{'...' if len(idea2['content']) > 100 else ''}_

**关联分析:**
{connection}"""

        await thinking_msg.edit_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"关联分析出错: {e}")
        await thinking_msg.edit_text(f"❌ 分析出错: {str(e)}")


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """生成周报"""
    if not is_authorized(update.effective_user.id):
        return

    ideas = vault.get_recent_ideas(50)  # 获取最近的灵感
    if not ideas:
        await update.message.reply_text("还没有记录任何灵感，无法生成周报")
        return

    thinking_msg = await update.message.reply_text("📊 正在生成周报...")

    try:
        # 简单统计（实际可以更复杂）
        models_used = {}
        summary_text = analyzer.generate_weekly_summary(ideas, models_used)

        # 保存周报
        vault.save_summary(summary_text)

        text = f"""📊 **本周思维周报**

{summary_text}

_周报已保存到 Obsidian_"""

        await thinking_msg.edit_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"生成周报出错: {e}")
        await thinking_msg.edit_text(f"❌ 生成出错: {str(e)}")


async def addmodel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """搜索并添加新思维模型"""
    if not is_authorized(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "请提供搜索关键词，例如:\n"
            "`/addmodel 决策偏见`\n"
            "`/addmodel 创新方法`",
            parse_mode="Markdown"
        )
        return

    keyword = " ".join(context.args)
    user_id = update.effective_user.id

    # 检查是否已存在
    existing_models = vault.get_model_names()
    if keyword in existing_models:
        await update.message.reply_text(f"「{keyword}」已经在模型库中了")
        return

    thinking_msg = await update.message.reply_text(f"🔍 正在搜索「{keyword}」相关的思维模型...")

    try:
        result = analyzer.search_mental_model(keyword)

        if not result:
            await thinking_msg.edit_text(f"没有找到与「{keyword}」相关的思维模型")
            return

        # 检查是否已存在
        if result["name"] in existing_models:
            await thinking_msg.edit_text(f"「{result['name']}」已经在模型库中了")
            return

        # 保存待确认的模型
        pending_models[user_id] = result

        # 构建确认消息
        text = f"""🧠 **找到思维模型**

**{result['name']}**

**定义:** {result['definition']}

**核心要点:**
"""
        for point in result.get("key_points", []):
            text += f"• {point}\n"

        text += "\n**应用场景:**\n"
        for app in result.get("applications", []):
            text += f"• {app}\n"

        if result.get("representatives"):
            text += f"\n**代表人物:** {result['representatives']}"

        # 创建确认按钮
        keyboard = [
            [
                InlineKeyboardButton("✅ 添加到模型库", callback_data="add_model"),
                InlineKeyboardButton("❌ 取消", callback_data="cancel_model"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await thinking_msg.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"搜索模型出错: {e}")
        await thinking_msg.edit_text(f"❌ 搜索出错: {str(e)}")


async def delmodel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """删除思维模型"""
    if not is_authorized(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("请提供要删除的模型名称，例如: `/delmodel 第一性原理`", parse_mode="Markdown")
        return

    name = " ".join(context.args)

    if vault.delete_model(name):
        await update.message.reply_text(f"✅ 已删除思维模型「{name}」")
    else:
        await update.message.reply_text(f"❌ 未找到思维模型「{name}」")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通消息（记录灵感）"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ 你没有使用此 Bot 的权限")
        return

    idea_text = update.message.text.strip()
    if not idea_text:
        return

    await process_idea(update, context, idea_text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理语音消息"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ 你没有使用此 Bot 的权限")
        return

    thinking_msg = await update.message.reply_text("🎤 正在转录语音...")

    try:
        # 下载语音文件
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        voice_bytes = await file.download_as_bytearray()

        # 转录
        transcribed_text = analyzer.transcribe_audio(bytes(voice_bytes), "audio/ogg")

        if transcribed_text.startswith("语音转录出错"):
            await thinking_msg.edit_text(f"❌ {transcribed_text}")
            return

        await thinking_msg.delete()
        await update.message.reply_text(f"🎤 语音转录: _{transcribed_text}_", parse_mode="Markdown")

        # 处理为灵感
        await process_idea(update, context, transcribed_text)

    except Exception as e:
        logger.error(f"语音处理出错: {e}")
        await thinking_msg.edit_text(f"❌ 语音处理出错: {str(e)}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理图片消息"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ 你没有使用此 Bot 的权限")
        return

    thinking_msg = await update.message.reply_text("🖼️ 正在分析图片...")

    try:
        # 下载图片（获取最大尺寸）
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        # 分析图片
        extracted_text = analyzer.analyze_image(bytes(photo_bytes), "image/jpeg")

        if extracted_text.startswith("图片分析出错"):
            await thinking_msg.edit_text(f"❌ {extracted_text}")
            return

        await thinking_msg.delete()
        await update.message.reply_text(f"🖼️ 图片内容: _{extracted_text[:200]}{'...' if len(extracted_text) > 200 else ''}_", parse_mode="Markdown")

        # 处理为灵感
        await process_idea(update, context, extracted_text)

    except Exception as e:
        logger.error(f"图片处理出错: {e}")
        await thinking_msg.edit_text(f"❌ 图片处理出错: {str(e)}")


async def process_idea(update: Update, context: ContextTypes.DEFAULT_TYPE, idea_text: str):
    """处理灵感文本"""
    user_id = update.effective_user.id

    # 发送「正在分析」提示
    thinking_msg = await update.message.reply_text("🤔 正在分析你的灵感...")

    try:
        # AI 分析
        available_models = vault.get_model_names()
        analysis = analyzer.analyze_idea(idea_text, available_models)

        matched_models = analysis.get("matched_models", [])
        tags = analysis.get("tags", [])
        ai_analysis = analysis.get("analysis", "")
        suggested_new_model = analysis.get("suggested_new_model")

        # 构建确认消息
        confirm_text = "💡 **灵感已分析**\n\n"
        confirm_text += f"_{idea_text[:100]}{'...' if len(idea_text) > 100 else ''}_\n\n"

        if matched_models:
            confirm_text += f"**关联思维模型**: {', '.join(matched_models)}\n"
        if tags:
            confirm_text += f"**标签**: {', '.join(tags)}\n"
        if ai_analysis:
            confirm_text += f"\n**AI 分析**: {ai_analysis}\n"

        # 如果有推荐新模型
        if suggested_new_model:
            confirm_text += f"\n💡 **推荐新模型**: {suggested_new_model['name']}\n"
            confirm_text += f"_{suggested_new_model['description']}_\n"

        # 保存待确认的灵感
        pending_ideas[user_id] = {
            "content": idea_text,
            "models": matched_models,
            "tags": tags,
            "analysis": ai_analysis,
            "suggested_new_model": suggested_new_model,
        }

        # 创建确认按钮
        buttons = [
            [
                InlineKeyboardButton("✅ 保存", callback_data="save_idea"),
                InlineKeyboardButton("📝 仅保存原文", callback_data="save_plain"),
            ],
        ]

        # 如果有推荐新模型，添加按钮
        if suggested_new_model:
            buttons.append([
                InlineKeyboardButton(f"➕ 同时添加「{suggested_new_model['name'][:10]}」模型", callback_data="save_idea_with_model"),
            ])

        buttons.append([InlineKeyboardButton("❌ 取消", callback_data="cancel_idea")])

        reply_markup = InlineKeyboardMarkup(buttons)

        # 删除「正在分析」消息，发送确认消息
        await thinking_msg.delete()
        await update.message.reply_text(
            confirm_text, parse_mode="Markdown", reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"处理消息时出错: {e}")
        await thinking_msg.edit_text(f"❌ 处理时出错: {str(e)}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    # 处理灵感相关的回调
    if data in ["save_idea", "save_plain", "cancel_idea", "save_idea_with_model"]:
        if user_id not in pending_ideas:
            await query.edit_message_text("❌ 灵感已过期，请重新发送")
            return

        idea_data = pending_ideas[user_id]

        if data == "save_idea":
            # 保存完整灵感（包含 AI 分析）
            vault.save_idea(
                content=idea_data["content"],
                models=idea_data["models"],
                tags=idea_data["tags"],
                ai_analysis=idea_data["analysis"],
            )
            del pending_ideas[user_id]

            # 构建保留分析内容的回复
            reply_text = "✅ **灵感已保存**\n\n"
            reply_text += f"_{idea_data['content'][:100]}{'...' if len(idea_data['content']) > 100 else ''}_\n\n"

            if idea_data["models"]:
                reply_text += f"**关联思维模型**: {', '.join(idea_data['models'])}\n"
            if idea_data["tags"]:
                reply_text += f"**标签**: {', '.join(idea_data['tags'])}\n"
            if idea_data["analysis"]:
                reply_text += f"\n**AI 分析**: {idea_data['analysis']}\n"

            await query.edit_message_text(reply_text, parse_mode="Markdown")

        elif data == "save_idea_with_model":
            # 添加新模型 - 先搜索获取完整信息
            new_model = idea_data.get("suggested_new_model")
            model_msg = ""
            new_model_name = None

            if new_model:
                # 使用 AI 搜索获取完整的模型信息
                full_model_info = analyzer.search_mental_model(new_model["name"])

                if full_model_info:
                    new_model_name = full_model_info["name"]
                    # 使用搜索到的完整信息
                    result = vault.save_model(
                        name=full_model_info["name"],
                        definition=full_model_info["definition"],
                        key_points=full_model_info.get("key_points"),
                        applications=full_model_info.get("applications"),
                        representatives=full_model_info.get("representatives"),
                    )
                else:
                    new_model_name = new_model["name"]
                    # 搜索失败，使用原始信息
                    result = vault.save_model(
                        name=new_model["name"],
                        definition=new_model["description"],
                    )

                if result:
                    model_msg = f"\n✅ **已添加新模型「{new_model_name}」**"
                else:
                    model_msg = f"\n⚠️ 模型「{new_model_name}」已存在，跳过添加"
                    new_model_name = None  # 模型已存在，不需要再添加链接

            # 保存灵感 - 把新模型也加入关联列表
            models_to_link = list(idea_data["models"]) if idea_data["models"] else []
            if new_model_name and new_model_name not in models_to_link:
                models_to_link.append(new_model_name)

            vault.save_idea(
                content=idea_data["content"],
                models=models_to_link,
                tags=idea_data["tags"],
                ai_analysis=idea_data["analysis"],
            )

            del pending_ideas[user_id]

            # 构建保留分析内容的回复
            reply_text = f"✅ **灵感已保存**{model_msg}\n\n"
            reply_text += f"_{idea_data['content'][:100]}{'...' if len(idea_data['content']) > 100 else ''}_\n\n"

            if models_to_link:
                reply_text += f"**关联思维模型**: {', '.join(models_to_link)}\n"
            if idea_data["tags"]:
                reply_text += f"**标签**: {', '.join(idea_data['tags'])}\n"
            if idea_data["analysis"]:
                reply_text += f"\n**AI 分析**: {idea_data['analysis']}\n"

            await query.edit_message_text(reply_text, parse_mode="Markdown")

        elif data == "save_plain":
            # 仅保存原文
            vault.save_idea(content=idea_data["content"])
            del pending_ideas[user_id]
            await query.edit_message_text("✅ **灵感已保存**（仅原文）", parse_mode="Markdown")

        elif data == "cancel_idea":
            del pending_ideas[user_id]
            await query.edit_message_text("❌ 已取消")

    # 处理模型相关的回调
    elif data in ["add_model", "cancel_model"]:
        if user_id not in pending_models:
            await query.edit_message_text("❌ 操作已过期")
            return

        model_data = pending_models[user_id]

        if data == "add_model":
            vault.save_model(
                name=model_data["name"],
                definition=model_data["definition"],
                key_points=model_data.get("key_points"),
                applications=model_data.get("applications"),
                representatives=model_data.get("representatives"),
            )
            del pending_models[user_id]
            await query.edit_message_text(
                f"✅ **已添加思维模型「{model_data['name']}」**\n\n现在可以在灵感分析中使用这个模型了！",
                parse_mode="Markdown",
            )

        elif data == "cancel_model":
            del pending_models[user_id]
            await query.edit_message_text("❌ 已取消")


async def daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    """每日灵感回顾提醒"""
    if not ALLOWED_USERS:
        return

    idea = vault.get_random_idea()
    if not idea:
        return

    text = f"""🌅 **每日灵感回顾**

{idea.get('content', '')}

_来自: {idea.get('name', '')}_

回复 /random 查看更多灵感"""

    for user_id in ALLOWED_USERS:
        try:
            await context.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"发送提醒失败: {e}")


def main():
    """主函数"""
    global vault, analyzer, ALLOWED_USERS

    # 读取配置
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    allowed_users_str = os.getenv("ALLOWED_USER_IDS", "")

    # AI 配置
    ai_provider = os.getenv("AI_PROVIDER", "gemini").lower()
    ai_model = os.getenv("AI_MODEL", "")

    # 根据提供商获取对应的 API Key
    ai_key_map = {
        "gemini": os.getenv("GOOGLE_AI_API_KEY"),
        "openai": os.getenv("OPENAI_API_KEY"),
        "claude": os.getenv("ANTHROPIC_API_KEY"),
    }
    ai_key = ai_key_map.get(ai_provider)

    # 验证配置
    if not token:
        print("❌ 请在 .env 文件中设置 TELEGRAM_BOT_TOKEN")
        return

    if not ai_key:
        key_name = {
            "gemini": "GOOGLE_AI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
        }.get(ai_provider, "API_KEY")
        print(f"❌ 请在 .env 文件中设置 {key_name}")
        return

    if not vault_path:
        print("❌ 请在 .env 文件中设置 OBSIDIAN_VAULT_PATH")
        return

    # 解析授权用户
    if allowed_users_str:
        ALLOWED_USERS = {
            int(uid.strip()) for uid in allowed_users_str.split(",") if uid.strip()
        }
        print(f"✅ 授权用户: {ALLOWED_USERS}")

    # 初始化 vault
    vault = ObsidianVault(vault_path)

    # 获取脚本所在目录，用于找到 vault_templates
    script_dir = Path(__file__).parent
    templates_dir = script_dir / "vault_templates"

    vault.init_vault(str(templates_dir))
    print(f"✅ Vault 路径: {vault_path}")

    # 初始化 AI
    analyzer = create_analyzer(ai_provider, ai_key, ai_model if ai_model else None)
    print(f"✅ AI 分析器已初始化 ({ai_provider}: {ai_model or '默认模型'})")

    # 创建 Bot
    app = Application.builder().token(token).build()

    # 注册命令处理器
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("models", models))
    app.add_handler(CommandHandler("recent", recent))
    app.add_handler(CommandHandler("random", random_idea))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("addmodel", addmodel))
    app.add_handler(CommandHandler("delmodel", delmodel))

    # 注册消息处理器
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # 注册回调处理器
    app.add_handler(CallbackQueryHandler(handle_callback))

    # 设置每日提醒（每天早上 9 点）
    if ALLOWED_USERS:
        job_queue = app.job_queue
        job_queue.run_daily(daily_reminder, time=time(hour=9, minute=0))
        print("✅ 已设置每日 9:00 灵感回顾提醒")

    # 启动 Bot
    print("🚀 Bot 启动中...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
