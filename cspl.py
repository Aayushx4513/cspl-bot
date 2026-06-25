import asyncpg
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import threading
from flask import Flask

TOKEN = "8264711416:AAE_uuhdNTnFWzzPTEugPNQuLxbFCBNxxeg"
ADMIN_IDS = [7687078555, 6966073511]
OWNER_ID = 7687078555  # Sirf ek owner

# ============ DATABASE URL ============
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://username:password@localhost/cspl_db")

# ============ FLASK ============
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

# ============ DATABASE CONNECTION ============
db_conn = None

async def get_db():
    global db_conn
    if db_conn is None or db_conn.is_closed():
        db_conn = await asyncpg.connect(DATABASE_URL)
    return db_conn

# ============ INIT DB ============
async def init_db():
    db = await get_db()
    
    # Users table
    await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            name TEXT,
            balance INT DEFAULT 0,
            points INT DEFAULT 0,
            photo TEXT
        )
    ''')
    
    # Achievements table
    await db.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            achievement TEXT,
            date TEXT
        )
    ''')
    
    # Hall of Fame table
    await db.execute('''
        CREATE TABLE IF NOT EXISTS hof (
            id SERIAL PRIMARY KEY,
            name TEXT
        )
    ''')
    
    print("✅ PostgreSQL tables created!")
    await db.close()

# ============ HELPER FUNCTIONS ============
async def is_registered(user_id):
    db = await get_db()
    result = await db.fetchval("SELECT user_id FROM users WHERE user_id = $1", user_id)
    await db.close()
    return result is not None

async def get_user(user_id, name=""):
    db = await get_db()
    user = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    if not user:
        await db.execute(
            "INSERT INTO users (user_id, name, balance, points) VALUES ($1, $2, 0, 0)",
            user_id, name
        )
        user = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    await db.close()
    return user

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user.first_name else user.username or "User"
    user_id = user.id
    
    db = await get_db()
    existing = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    
    if not existing:
        await db.execute(
            "INSERT INTO users (user_id, name, balance, points) VALUES ($1, $2, 0, 0)",
            user_id, name
        )
    
    await db.close()
    
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
        f"   /add_hof <name> - Add to Hall of Fame\n\n"
        f"🌿 Made with passion for CFL 🌿"
    )

# ============ ACHIEVEMENTS ============
async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    db = await get_db()
    ach = await db.fetch(
        "SELECT achievement FROM achievements WHERE user_id = $1 ORDER BY id DESC",
        user_id
    )
    await db.close()
    
    if not ach:
        await update.message.reply_text(
            f"CFL ACHIEVEMENTS:\n\n"
            f"No achievements yet!\n"
            f"Participate in CFL events to earn badges."
        )
        return
    
    msg = f"CFL ACHIEVEMENTS:\n\n"
    for i, a in enumerate(ach, 1):
        msg += f"{i}. {a['achievement']}\n"
    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━\nTotal: {len(ach)} achievements"
    await update.message.reply_text(msg)

# ============ ADD ACHIEVEMENT ============
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
    
    db = await get_db()
    await db.execute(
        "INSERT INTO achievements (user_id, achievement, date) VALUES ($1, $2, $3)",
        target.id, achievement, now
    )
    await db.close()
    
    await update.message.reply_text(
        f"CFL ACHIEVEMENTS:\n"
        f"✅ Achievement given to {target.first_name}!\n\n"
        f"{achievement}"
    )

# ============ REMOVE ACHIEVEMENT ============
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
    
    db = await get_db()
    ach = await db.fetch(
        "SELECT id, achievement FROM achievements WHERE user_id = $1 ORDER BY id",
        target.id
    )
    
    if num < 1 or num > len(ach):
        await update.message.reply_text(f"❌ Choose 1-{len(ach)}")
        await db.close()
        return
    
    removed = ach[num-1]
    await db.execute("DELETE FROM achievements WHERE id = $1", removed['id'])
    await db.close()
    
    await update.message.reply_text(f"✅ Achievement removed from {target.first_name}!\n\nRemoved: {removed['achievement']}")

# ============ ADD HOF ============
async def add_hof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❌ Usage: /add_hof <season_winner>\nExample: /add_hof CSPL SEASON 1 WINNER - AUSTRALIA")
        return
    
    season_winner = ' '.join(args)
    
    db = await get_db()
    await db.execute("INSERT INTO hof (name) VALUES ($1)", season_winner)
    await db.close()
    
    await update.message.reply_text(
        f"✅ Added to Hall of Fame!\n\n"
        f"🏆 {season_winner}"
    )

# ============ REMOVE HOF ============
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
    
    db = await get_db()
    hof_list = await db.fetch("SELECT id, name FROM hof ORDER BY id")
    
    if num < 1 or num > len(hof_list):
        await update.message.reply_text(f"❌ Choose 1-{len(hof_list)}")
        await db.close()
        return
    
    removed = hof_list[num-1]
    await db.execute("DELETE FROM hof WHERE id = $1", removed['id'])
    await db.close()
    
    await update.message.reply_text(
        f"✅ Removed from Hall of Fame!\n\n"
        f"Removed: {removed['name']}"
    )

# ============ HOF ============
async def hof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await get_db()
    hof_list = await db.fetch("SELECT id, name FROM hof ORDER BY id")
    await db.close()
    
    if not hof_list:
        await update.message.reply_text(
            f"🏆 HALL OF FAME 🏆\n\n"
            f"No entries yet!\n"
            f"Use /add_hof to add season winners."
        )
        return
    
    msg = f"🏆 HALL OF FAME 🏆\n\n"
    for i, h in enumerate(hof_list, 1):
        msg += f"{i}. {h['name']}\n"
    msg += f"\n━━━━━━━━━━━━━━━━━━━━━━\n🏆 CFL Legends"
    await update.message.reply_text(msg)

# ============ PROMOTE ADMIN ============
OWNER_IDS = [7687078555, 6966073511]  # Dono owners
ADMIN_IDS = [7687078555, 6966073511]  # Dono owners + other admins

async def promoteadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
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
    if update.effective_user.id not in OWNER_IDS:
        await update.message.reply_text("❌ Only bot owner can demote admins!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to user with /demoteadmin")
        return
    
    target = update.message.reply_to_message.from_user
    
    # 🔥 OWNER KO DEMOTE NAHI KAR SAKTE
    if target.id in OWNER_IDS:
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


# ============ MAIN ============
async def main():
    await init_db()
    
    app = Application.builder().token(TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("achievements", achievements))
    app.add_handler(CommandHandler("hof", hof))
    
    # Admin commands
    app.add_handler(CommandHandler("add_achievement", add_achievement))
    app.add_handler(CommandHandler("remove_achievement", remove_achievement))
    app.add_handler(CommandHandler("add_hof", add_hof))
    app.add_handler(CommandHandler("rm_hof", rm_hof))
    app.add_handler(CommandHandler("promoteadmin", promoteadmin))
    app.add_handler(CommandHandler("demoteadmin", demoteadmin))
    
    print("🤖 CSPL Bot is running...")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await app.stop()
        await app.shutdown()

# ============ RUN ============
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
