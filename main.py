import os, json, time, threading
from flask import Flask
import telebot

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("OWNER_ID"))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

USERS_FILE = "users.json"

# ---------------- STORAGE ----------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- FLASK ----------------
@app.route("/")
def home():
    return "Bot running", 200

def run_bot():
    bot.infinity_polling(skip_pending=True)

# ---------------- HELPERS ----------------
def register_user(user):
    users = load_users()
    uid = str(user.id)
    if uid not in users:
        users[uid] = {
            "id": user.id,
            "name": user.first_name,
            "username": user.username,
            "joined": int(time.time()),
            "blocked": False,
            "messages": 0
        }
    users[uid]["messages"] += 1
    save_users(users)

def is_blocked(uid):
    users = load_users()
    return str(uid) in users and users[str(uid)]["blocked"]

# ---------------- START ----------------
@bot.message_handler(commands=["start"])
def start(m):
    register_user(m.from_user)
    bot.send_message(
        m.chat.id,
        f"👋 Welcome <b>{m.from_user.first_name}</b>\n\n🤖 Professional Support Bot\n📩 Send any message."
    )

# ---------------- USER MESSAGE ----------------
@bot.message_handler(func=lambda m: m.from_user.id != ADMIN_ID)
def user_msg(m):
    if is_blocked(m.from_user.id):
        return

    register_user(m.from_user)

    info = (
        f"👤 <b>User Message</b>\n"
        f"🆔 <code>{m.from_user.id}</code>\n"
        f"👤 {m.from_user.first_name}\n"
        f"🔗 @{m.from_user.username}\n\n"
    )

    bot.send_message(ADMIN_ID, info)
    bot.copy_message(ADMIN_ID, m.chat.id, m.message_id)

# ---------------- ADMIN COMMANDS ----------------

@bot.message_handler(commands=["users"])
def users(m):
    if m.from_user.id != ADMIN_ID:
        return
    data = load_users()
    bot.send_message(m.chat.id, f"👥 Total Users: {len(data)}")

@bot.message_handler(commands=["ban"])
def ban(m):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        uid = m.text.split()[1]
        users = load_users()
        users[uid]["blocked"] = True
        save_users(users)
        bot.send_message(m.chat.id, f"🚫 User {uid} banned")
    except:
        bot.send_message(m.chat.id, "❌ Use: /ban USER_ID")

@bot.message_handler(commands=["unban"])
def unban(m):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        uid = m.text.split()[1]
        users = load_users()
        users[uid]["blocked"] = False
        save_users(users)
        bot.send_message(m.chat.id, f"✅ User {uid} unbanned")
    except:
        bot.send_message(m.chat.id, "❌ Use: /unban USER_ID")

@bot.message_handler(commands=["profile"])
def profile(m):
    if m.from_user.id != ADMIN_ID:
        return
    try:
        uid = m.text.split()[1]
        users = load_users()
        u = users[uid]
        bot.send_message(
            m.chat.id,
            f"""
👤 <b>User Profile</b>
🆔 <code>{u['id']}</code>
👤 {u['name']}
🔗 @{u['username']}
💬 Messages: {u['messages']}
"""
        )
    except:
        bot.send_message(m.chat.id, "❌ Use: /profile USER_ID")

@bot.message_handler(commands=["broadcast"])
def broadcast(m):
    if m.from_user.id != ADMIN_ID:
        return
    text = m.text.replace("/broadcast", "").strip()
    if not text:
        bot.send_message(m.chat.id, "❌ /broadcast message")
        return

    users = load_users()
    sent = 0
    for uid in users:
        if not users[uid]["blocked"]:
            try:
                bot.send_message(int(uid), text)
                sent += 1
            except:
                pass
    bot.send_message(m.chat.id, f"📢 Sent to {sent} users")

# ---------------- RUN ----------------
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
