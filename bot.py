"""
灵感捕捉 Telegram Bot
记录灵感，AI 整理成思维模型
"""

import os
import logging
from pathlib import Path

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
from ai import IdeaAnalyzer

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

**使用方法：**
• 直接发送消息 → 记录灵感
• /models → 查看思维模型库
• /recent → 最近的灵感
• /random → 随机回顾一条灵感
• /search 关键词 → 搜索灵感
• /stats → 统计信息
• /myid → 查看你的用户 ID
• /help → 帮助信息

开始记录你的第一个灵感吧！"""

    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令"""
    if not is_authorized(update.effective_user.id):
        return

    help_text = """💡 **灵感捕捉 Bot 帮助**

**记录灵感**
直接发送任何文字消息，Bot 会：
1. 用 AI 分析你的灵感
2. 匹配相关的思维模型
3. 自动添加标签
4. 保存到 Obsidian

**命令列表**
• /models - 查看所有思维模型
• /recent - 最近 10 条灵感
• /random - 随机回顾一条旧灵感
• /search <关键词> - 搜索灵感
• /stats - 查看统计信息
• /myid - 获取你的 Telegram ID

**小技巧**
• 灵感不用写太长，几句话即可
• 可以记录触发灵感的场景
• 定期用 /random 回顾旧灵感"""

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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理普通消息（记录灵感）"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ 你没有使用此 Bot 的权限")
        return

    idea_text = update.message.text.strip()
    if not idea_text:
        return

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

        # 构建确认消息
        confirm_text = "💡 **灵感已分析**\n\n"
        confirm_text += f"_{idea_text[:100]}{'...' if len(idea_text) > 100 else ''}_\n\n"

        if matched_models:
            confirm_text += f"**关联思维模型**: {', '.join(matched_models)}\n"
        if tags:
            confirm_text += f"**标签**: {', '.join(tags)}\n"
        if ai_analysis:
            confirm_text += f"\n**AI 分析**: {ai_analysis}\n"

        # 保存待确认的灵感
        pending_ideas[user_id] = {
            "content": idea_text,
            "models": matched_models,
            "tags": tags,
            "analysis": ai_analysis,
        }

        # 创建确认按钮
        keyboard = [
            [
                InlineKeyboardButton("✅ 保存", callback_data="save_idea"),
                InlineKeyboardButton("📝 仅保存原文", callback_data="save_plain"),
            ],
            [InlineKeyboardButton("❌ 取消", callback_data="cancel_idea")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

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

    if user_id not in pending_ideas:
        await query.edit_message_text("❌ 灵感已过期，请重新发送")
        return

    idea_data = pending_ideas[user_id]

    if data == "save_idea":
        # 保存完整灵感（包含 AI 分析）
        filepath = vault.save_idea(
            content=idea_data["content"],
            models=idea_data["models"],
            tags=idea_data["tags"],
            ai_analysis=idea_data["analysis"],
        )
        del pending_ideas[user_id]

        models_text = ""
        if idea_data["models"]:
            models_text = f"\n关联: {', '.join(idea_data['models'])}"

        await query.edit_message_text(
            f"✅ **灵感已保存**{models_text}\n\n继续发送下一个灵感吧！",
            parse_mode="Markdown",
        )

    elif data == "save_plain":
        # 仅保存原文
        filepath = vault.save_idea(content=idea_data["content"])
        del pending_ideas[user_id]
        await query.edit_message_text("✅ **灵感已保存**（仅原文）", parse_mode="Markdown")

    elif data == "cancel_idea":
        del pending_ideas[user_id]
        await query.edit_message_text("❌ 已取消")


def main():
    """主函数"""
    global vault, analyzer, ALLOWED_USERS

    # 读取配置
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    ai_key = os.getenv("GOOGLE_AI_API_KEY")
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
    allowed_users_str = os.getenv("ALLOWED_USER_IDS", "")

    # 验证配置
    if not token:
        print("❌ 请在 .env 文件中设置 TELEGRAM_BOT_TOKEN")
        return

    if not ai_key:
        print("❌ 请在 .env 文件中设置 GOOGLE_AI_API_KEY")
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
    analyzer = IdeaAnalyzer(ai_key)
    print("✅ AI 分析器已初始化")

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

    # 注册消息处理器
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 注册回调处理器
    app.add_handler(CallbackQueryHandler(handle_callback))

    # 启动 Bot
    print("🚀 Bot 启动中...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
