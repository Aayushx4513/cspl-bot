import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import threading
from flask import Flask

TOKEN = "8264711416:AAE_uuhdNTnFWzzPTEugPNQuLxbFCBNxxeg"
ADMIN_IDS = [7687078555, 6966073511]

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
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, name TEXT, balance INTEGER, points INTEGER, photo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS achievements 
                 (user_id INTEGER, achievement TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hof 
                 (user_id INTEGER, name TEXT, points INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hof 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')

    conn.commit()
    conn.close()

init_db()

def is_registered(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user is not None

def get_user(user_id, name=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, name, balance, points) VALUES (?, ?, 0, 0)", (user_id, name))
        conn.commit()
        user = (user_id, name, 0, 0, None)
    conn.close()
    return user

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user.first_name else user.username or "User"
    user_id = user.id
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    existing = c.fetchone()
    
    if not existing:
        c.execute("INSERT INTO users (user_id, name, balance, points) VALUES (?, ?, 0, 0)", (user_id, name))
        conn.commit()
    
    is_admin = "👑 ADMIN" if user_id in ADMIN_IDS else ""
    
    await update.message.reply_text(
        f"🏆 CFL - CRICKET FANTASY LEAGUE 🏆\n\n"
        f"🌿 Welcome {name} {is_admin}! 🌿\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 Commands:\n"
        f"   /achievements - Your badges\n"
        f"   /hof - Hall of Fame\n"
        f"   /help - All commands\n\n"
        f"🌿 Made with passion for CFL 🌿"
    )
    conn.close()

# ============ HELP ============
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🏆 CFL COMMANDS 🏆\n\n"
        f"📌 User Commands:\n"
        f"   /start - Start the bot\n"
        f"   /achievements - View your badges\n"
        f"   /hof - Hall of Fame leaderboard\n"
        f"   /help - Show this menu\n\n"
        f"👑 Admin Commands:\n"
        f"   /add_achievement @user <name> - Give achievement\n"
        f"   /remove_achievement @user <id> - Remove achievement\n"
        f"   /add_hof @user <points> - Add to Hall of Fame\n\n"
        f"🌿 Made with passion for CFL 🌿"
    )

# ============ ACHIEVEMENTS ============
async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT achievement, date FROM achievements WHERE user_id=? ORDER BY date DESC", (user_id,))
    ach = c.fetchall()
    conn.close()
    
    if not ach:
        await update.message.reply_text(
            f"CSPL ACHIEVEMENTS:\n\n"
            f"No achievements yet!\n"
            f"Participate in CFL events to earn badges."
        )
        return
    
    msg = f"CSPL ACHIEVEMENTS:\n\n"
    for i, a in enumerate(ach, 1):
        msg += f"{i}. {a[0]}\n"
    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━\nTotal: {len(ach)} achievements"
    await update.message.reply_text(msg)


# ============ ADMIN COMMANDS ============
async def add_achievement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to user with /add_achievement <name>")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Usage: /add_achievement <achievement_name> (reply to user)")
        return
    
    achievement = ' '.join(args)
    target = update.message.reply_to_message.from_user
    now = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO achievements (user_id, achievement, date) VALUES (?, ?, ?)", (target.id, achievement, now))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"CSPL ACHIEVEMENTS:\n"
        f"✅ Achievement given to {target.first_name}!\n\n"
        f"{achievement}"
    )


async def remove_achievement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to user with /remove_achievement <number>")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Usage: /remove_achievement <achievement_number>")
        return
    
    try:
        num = int(args[0])
    except:
        await update.message.reply_text("❌ Invalid number")
        return
    
    target = update.message.reply_to_message.from_user
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT rowid, achievement FROM achievements WHERE user_id=?", (target.id,))
    ach = c.fetchall()
    
    if num < 1 or num > len(ach):
        await update.message.reply_text(f"❌ Choose 1-{len(ach)}")
        conn.close()
        return
    
    removed = ach[num-1]
    c.execute("DELETE FROM achievements WHERE rowid=?", (removed[0],))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Achievement removed from {target.first_name}!\n\nRemoved: {removed[1]}")

# ============ HALL OF FAME (SEASON WINNER) ==========

async def add_hof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Usage: /add_hof <season_winner>\nExample: /add_hof CSPL SEASON 1 WINNER - AUSTRALIA")
        return
    
    season_winner = ' '.join(args)
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO hof (name) VALUES (?)", (season_winner,))
    conn.commit()
    hof_id = c.lastrowid
    conn.close()
    
    await update.message.reply_text(
        f"✅ Added to Hall of Fame!\n\n"
        f"🏆 {season_winner}"
    )

async def rm_hof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Usage: /rm_hof <number>\nUse /hof to see numbers")
        return
    
    try:
        num = int(args[0])
    except:
        await update.message.reply_text("❌ Invalid number")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT rowid, name FROM hof")
    hof_list = c.fetchall()
    
    if num < 1 or num > len(hof_list):
        await update.message.reply_text(f"❌ Choose 1-{len(hof_list)}")
        conn.close()
        return
    
    removed = hof_list[num-1]
    c.execute("DELETE FROM hof WHERE rowid=?", (removed[0],))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ Removed from Hall of Fame!\n\n"
        f"Removed: {removed[1]}"
    )

async def hof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT rowid, name FROM hof ORDER BY rowid ASC")
    hof_list = c.fetchall()
    conn.close()
    
    if not hof_list:
        await update.message.reply_text(
            f"🏆 HALL OF FAME 🏆\n\n"
            f"No entries yet!\n"
            f"Use /add_hof to add season winners."
        )
        return
    
    msg = f"🏆 HALL OF FAME 🏆\n\n"
    for i, (rowid, name) in enumerate(hof_list, 1):
        msg += f"{i}. {name}\n"
    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━\n🏆 CFL Legends"
    await update.message.reply_text(msg)

OWNER_ID = [7687078555, 6966073511]  # Tera ID

async def promoteadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only bot owner can promote admins!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to user with /promoteadmin")
        return
    
    target = update.message.reply_to_message.from_user
    
    if target.id in ADMIN_IDS:
        await update.message.reply_text(f"❌ {target.first_name} is already an admin!")
        return
    
    ADMIN_IDS.append(target.id)
    
    with open("admin_ids.txt", "w") as f:
        for uid in ADMIN_IDS:
            f.write(f"{uid}\n")
    
    await update.message.reply_text(f"✅ {target.first_name} is now an admin!")

async def demoteadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only bot owner can demote admins!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to user with /demoteadmin")
        return
    
    target = update.message.reply_to_message.from_user
    
    if target.id == OWNER_ID:
        await update.message.reply_text("❌ Cannot demote the bot owner!")
        return
    
    if target.id not in ADMIN_IDS:
        await update.message.reply_text(f"❌ {target.first_name} is not an admin!")
        return
    
    ADMIN_IDS.remove(target.id)
    
    with open("admin_ids.txt", "w") as f:
        for uid in ADMIN_IDS:
            f.write(f"{uid}\n")
    
    await update.message.reply_text(f"✅ {target.first_name} is no longer an admin!")




# ============ MAIN ==========
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("achievements", achievements))
    app.add_handler(CommandHandler("hof", hof))
    app.add_handler(CommandHandler("add_achievement", add_achievement))
    app.add_handler(CommandHandler("remove_achievement", remove_achievement))
    app.add_handler(CommandHandler("add_hof", add_hof))
    app.add_handler(CommandHandler("rm_hof", rm_hof))
    app.add_handler(CommandHandler("promoteadmin", promoteadmin))
    app.add_handler(CommandHandler("demoteadmin", demoteadmin))
    
    print("🤖 CSPL Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
