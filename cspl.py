import sqlite3
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import os
import threading
from flask import Flask

TOKEN = "8755413906:AAFsgBjGnktsMBoTVFttTidtnuefaiQ-oN8"
ADMIN_IDS = [6620360093, 7687078555]

# Flask for Render
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "CSPL Bot is running!"

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

def get_db():
    return sqlite3.connect('cspl.db')

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, name TEXT, is_admin INTEGER DEFAULT 0)''')
    
    # Achievements table
    c.execute('''CREATE TABLE IF NOT EXISTS achievements 
                 (user_id INTEGER, achievement TEXT)''')
    
    # HOF (Hall of Fame) table
    c.execute('''CREATE TABLE IF NOT EXISTS hof 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, entry TEXT)''')
    
    # Admins table (track bot admins)
    c.execute('''CREATE TABLE IF NOT EXISTS bot_admins 
                 (user_id INTEGER PRIMARY KEY)''')
    
    # Insert default admins
    for admin_id in ADMIN_IDS:
        c.execute("INSERT OR IGNORE INTO bot_admins (user_id) VALUES (?)", (admin_id,))
        c.execute("INSERT OR IGNORE INTO users (user_id, name, is_admin) VALUES (?, ?, 1)", (admin_id, "Admin"))
    
    conn.commit()
    conn.close()

init_db()

def is_admin(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bot_admins WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

# ============ START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    name = user.first_name if user.first_name else user.username or "User"
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    existing = c.fetchone()
    
    if not existing:
        c.execute("INSERT INTO users (user_id, name, is_admin) VALUES (?, ?, 0)", (user_id, name))
        conn.commit()
    
    conn.close()
    
    is_admin_user = is_admin(user_id)
    admin_text = " 👑 ADMIN" if is_admin_user else ""
    
    await update.message.reply_text(
        f"🏆 **CSPL - CRICKET SPORTS PREMIER LEAGUE** 🏆\n\n"
        f"🌿 Welcome {name}{admin_text}! 🌿\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Commands:**\n"
        f"   /achievements - Your badges\n"
        f"   /hof - Hall of Fame\n"
        f"   /help - All commands\n\n"
        f"🌿 Made with passion for CSPL 🌿",
        parse_mode='Markdown'
    )

# ============ HELP ==========
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin_user = is_admin(user_id)
    
    msg = (
        "🏆 **CSPL COMMANDS** 🏆\n\n"
        "👤 **USER COMMANDS:**\n"
        "   /start - Start the bot\n"
        "   /help - Show this menu\n"
        "   /profile - Your profile\n"
        "   /achievements - Your badges 🏅\n"
        "   /hof - Hall of Fame 🏆\n\n"
    )
    
    if is_admin_user:
        msg += (
            "👑 **ADMIN COMMANDS:**\n"
            "   /ach @user <name> - Give achievement\n"
            "   /rmach @user <number> - Remove achievement\n"
            "   /promoteadmin @user - Make user admin\n"
            "   /demoteadmin @user - Remove admin\n"
            "   /add_hof <text> - Add to Hall of Fame\n"
            "   /rm_hof <number> - Remove from HOF\n"
            "   /hof_list - List all HOF entries\n\n"
        )
    
    msg += "🌿 *Keep the spirit of cricket alive!* 🌿"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ============ PROFILE ==========
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    name = user.first_name if user.first_name else user.username or "User"
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    is_admin_user = row[0] if row else 0
    
    c.execute("SELECT COUNT(*) FROM achievements WHERE user_id=?", (user_id,))
    ach_count = c.fetchone()[0]
    conn.close()
    
    admin_badge = " 👑 ADMIN" if is_admin_user else ""
    
    await update.message.reply_text(
        f"👤 **PROFILE**\n\n"
        f"🌿 **Name:** {name}{admin_badge}\n"
        f"🏅 **Achievements:** {ach_count}\n"
        f"🆔 **ID:** `{user_id}`\n\n"
        f"🌿 *Keep achieving greatness!* 🌿",
        parse_mode='Markdown'
    )

# ============ ACHIEVEMENTS ==========
async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    name = user.first_name if user.first_name else user.username or "User"
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT achievement FROM achievements WHERE user_id=?", (user_id,))
    ach = c.fetchall()
    conn.close()
    
    if not ach:
        await update.message.reply_text(
            f"🏅 **{name}'s ACHIEVEMENTS** 🏅\n\n"
            f"🌿 No achievements yet! 🌿\n\n"
            f"*Keep participating in CSPL events!*",
            parse_mode='Markdown'
        )
        return
    
    msg = f"🏅 **{name}'s ACHIEVEMENTS** 🏅\n\n"
    for i, a in enumerate(ach, 1):
        msg += f"🌿 {i}. {a[0]} 🏆\n"
    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━\n📊 **Total:** {len(ach)} achievements"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# ============ ACHIEVE (ADMIN) ==========
async def achieve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text('❌ **Admin only command!**', parse_mode='Markdown')
        return
    
    # Check if reply to user or mention @user
    target = None
    achievement_name = None
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        args = context.args
        if len(args) < 1:
            await update.message.reply_text('❌ Usage: /ach <achievement_name> (reply to user)\nExample: /ach CSPL WINNER', parse_mode='Markdown')
            return
        achievement_name = ' '.join(args)
    else:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text('❌ Usage: /ach @username <achievement_name>\nExample: /ach @user CSPL WINNER', parse_mode='Markdown')
            return
        username = args[0].replace('@', '')
        achievement_name = ' '.join(args[1:])
        
        # Find user by username
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE name LIKE ?", (f'%{username}%',))
        row = c.fetchone()
        conn.close()
        
        if not row:
            await update.message.reply_text(f'❌ User @{username} not found!', parse_mode='Markdown')
            return
        target_id = row[0]
        target = type('', (), {})()
        target.id = target_id
        target.first_name = username
    
    if not target:
        await update.message.reply_text('❌ User not found!', parse_mode='Markdown')
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO achievements (user_id, achievement) VALUES (?, ?)", (target.id, achievement_name))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ **ACHIEVEMENT GIVEN!** 🏆\n\n"
        f"🌿 **User:** {target.first_name}\n"
        f"🏅 **Achievement:** {achievement_name}\n\n"
        f"🌿 *Well deserved!* 🌿",
        parse_mode='Markdown'
    )

# ============ RMACHIEVE (ADMIN) ==========
async def rmachieve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text('❌ **Admin only command!**', parse_mode='Markdown')
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text('❌ Usage: /rmach <number>\nExample: /rmach 2\n\nUse /achievements to see numbers', parse_mode='Markdown')
        return
    
    try:
        num = int(args[0])
    except:
        await update.message.reply_text('❌ Invalid number!', parse_mode='Markdown')
        return
    
    # Check if reply or mention
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        target_id = target.id
    else:
        if len(args) < 2:
            await update.message.reply_text('❌ Usage: /rmach @username <number> or reply to user', parse_mode='Markdown')
            return
        username = args[0].replace('@', '')
        num = int(args[1])
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE name LIKE ?", (f'%{username}%',))
        row = c.fetchone()
        conn.close()
        
        if not row:
            await update.message.reply_text(f'❌ User @{username} not found!', parse_mode='Markdown')
            return
        target_id = row[0]
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT rowid, achievement FROM achievements WHERE user_id=?", (target_id,))
    ach = c.fetchall()
    
    if num < 1 or num > len(ach):
        await update.message.reply_text(f'❌ Invalid number! Choose 1-{len(ach)}', parse_mode='Markdown')
        conn.close()
        return
    
    removed = ach[num-1]
    c.execute("DELETE FROM achievements WHERE rowid=?", (removed[0],))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ **ACHIEVEMENT REMOVED!** 🏆\n\n"
        f"🌿 Removed: {removed[1]}\n\n"
        f"🌿 *Achievement revoked* 🌿",
        parse_mode='Markdown'
    )

# ============ PROMOTE ADMIN ==========
async def promoteadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text('❌ **Admin only command!**', parse_mode='Markdown')
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text('❌ Reply to user with /promoteadmin', parse_mode='Markdown')
        return
    
    target = update.message.reply_to_message.from_user
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO bot_admins (user_id) VALUES (?)", (target.id,))
    c.execute("UPDATE users SET is_admin = 1 WHERE user_id=?", (target.id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ **PROMOTED TO ADMIN!** 👑\n\n"
        f"🌿 **User:** {target.first_name}\n"
        f"👑 Now has admin privileges\n\n"
        f"🌿 *Trusted member of CSPL* 🌿",
        parse_mode='Markdown'
    )

# ============ DEMOTE ADMIN ==========
async def demoteadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text('❌ **Admin only command!**', parse_mode='Markdown')
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text('❌ Reply to user with /demoteadmin', parse_mode='Markdown')
        return
    
    target = update.message.reply_to_message.from_user
    
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM bot_admins WHERE user_id=?", (target.id,))
    c.execute("UPDATE users SET is_admin = 0 WHERE user_id=?", (target.id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ **DEMOTED FROM ADMIN!** 🥀\n\n"
        f"🌿 **User:** {target.first_name}\n"
        f"👑 Admin privileges removed\n\n"
        f"🌿 *Standard user now* 🌿",
        parse_mode='Markdown'
    )

# ============ HALL OF FAME ==========
async def hof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, entry FROM hof ORDER BY id")
    entries = c.fetchall()
    conn.close()
    
    if not entries:
        await update.message.reply_text(
            f"🏆 **HALL OF FAME** 🏆\n\n"
            f"🌿 No entries yet! 🌿\n\n"
            f"*CSPL legends will be added soon*",
            parse_mode='Markdown'
        )
        return
    
    msg = "🏆 **CSPL HALL OF FAME** 🏆\n\n"
    for e in entries:
        msg += f"🌿 {e[0]}. {e[1]}\n"
    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━\n📊 **Total:** {len(entries)} legends"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# ============ ADD HOF (ADMIN) ==========
async def add_hof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text('❌ **Admin only command!**', parse_mode='Markdown')
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text('❌ Usage: /add_hof <text>\nExample: /add_hof Season 1 Winner: India', parse_mode='Markdown')
        return
    
    entry = ' '.join(args)
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO hof (entry) VALUES (?)", (entry,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ **ADDED TO HALL OF FAME!** 🏆\n\n"
        f"🌿 **Entry:** {entry}\n\n"
        f"🌿 *CSPL legend immortalized* 🌿",
        parse_mode='Markdown'
    )

# ============ REMOVE HOF (ADMIN) ==========
async def rm_hof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text('❌ **Admin only command!**', parse_mode='Markdown')
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text('❌ Usage: /rm_hof <number>\nExample: /rm_hof 1', parse_mode='Markdown')
        return
    
    try:
        num = int(args[0])
    except:
        await update.message.reply_text('❌ Invalid number!', parse_mode='Markdown')
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, entry FROM hof ORDER BY id")
    entries = c.fetchall()
    
    if num < 1 or num > len(entries):
        await update.message.reply_text(f'❌ Invalid number! Choose 1-{len(entries)}', parse_mode='Markdown')
        conn.close()
        return
    
    removed = entries[num-1]
    c.execute("DELETE FROM hof WHERE id=?", (removed[0],))
    
    # Reorder remaining entries
    c.execute("SELECT id, entry FROM hof ORDER BY id")
    remaining = c.fetchall()
    for new_id, (old_id, entry) in enumerate(remaining, 1):
        c.execute("UPDATE hof SET id = ? WHERE id = ?", (new_id, old_id))
    
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ **REMOVED FROM HALL OF FAME!** 🥀\n\n"
        f"🌿 **Removed:** {removed[1]}\n\n"
        f"🌿 *Entry deleted* 🌿",
        parse_mode='Markdown'
    )

# ============ HOF LIST (ADMIN) ==========
async def hof_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text('❌ **Admin only command!**', parse_mode='Markdown')
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, entry FROM hof ORDER BY id")
    entries = c.fetchall()
    conn.close()
    
    if not entries:
        await update.message.reply_text('📭 No HOF entries yet!', parse_mode='Markdown')
        return
    
    msg = "📋 **HOF ENTRIES LIST**\n\n"
    for e in entries:
        msg += f"🌿 {e[0]}. {e[1]}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

# ============ MAIN ==========
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("achievements", achievements))
    app.add_handler(CommandHandler("hof", hof))
    
    # Admin commands
    app.add_handler(CommandHandler("ach", achieve))
    app.add_handler(CommandHandler("rmach", rmachieve))
    app.add_handler(CommandHandler("promoteadmin", promoteadmin))
    app.add_handler(CommandHandler("demoteadmin", demoteadmin))
    app.add_handler(CommandHandler("add_hof", add_hof))
    app.add_handler(CommandHandler("rm_hof", rm_hof))
    app.add_handler(CommandHandler("hof_list", hof_list))
    
    print("🤖 CSPL Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()


