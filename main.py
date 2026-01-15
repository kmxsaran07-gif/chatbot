import threading
import time
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, OWNER_ID, WELCOME_MSG

# ---------- INIT ----------
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ---------- MEMORY DATA ----------
users = {}          # user_id : info
banned_users = set()
silent_users = set()
reply_map = {}      # forwarded_msg_id : user_id
last_msg_time = {}
admin_online = True

# ---------- FLASK ----------
@app.route("/")
def home():
    return "Bot is running successfully!", 200

def run_bot():
    bot.infinity_polling(skip_pending=True)

# ---------- HELPERS ----------
def is_spam(uid):
    now = time.time()
    if uid in last_msg_time and now - last_msg_time[uid] < 2:
        return True
    last_msg_time[uid] = now
    return False

def save_user(user):
    uid = user.id
    if uid not in users:
        users[uid] = {
            "name": user.first_name,
            "username": user.username,
            "joined": time.strftime("%d-%m-%Y %H:%M")
        }

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid in banned_users:
        return

    save_user(message.from_user)

    bot.send_message(
        message.chat.id,
        WELCOME_MSG.format(name=message.from_user.first_name)
    )

# ---------- USER MESSAGE ----------
@bot.message_handler(
    func=lambda m: m.chat.type == "private" and m.from_user.id != OWNER_ID,
    content_types=['text','photo','video','document','audio','voice','sticker']
)
def user_message(message):
    uid = message.from_user.id

    if uid in banned_users or is_spam(uid):
        return

    save_user(message.from_user)

    if uid in silent_users:
        return

    if not admin_online:
        bot.send_message(
            message.chat.id,
            "⚠️ Admin offline hai, reply thoda late ho sakta hai"
        )

    fwd = bot.forward_message(
        OWNER_ID,
        message.chat.id,
        message.message_id
    )

    reply_map[fwd.message_id] = uid

    bot.send_message(
        message.chat.id,
        "✅ Message admin ko bhej diya gaya hai.\n⏳ Please wait."
    )

# ---------- ADMIN REPLY ----------
@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.reply_to_message)
def admin_reply(message):
    mid = message.reply_to_message.message_id
    if mid not in reply_map:
        return

    uid = reply_map[mid]
    bot.copy_message(uid, message.chat.id, message.message_id)

# ---------- ADMIN PANEL ----------
def admin_panel():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🚫 Ban", callback_data="ban"),
        InlineKeyboardButton("✅ Unban", callback_data="unban"),
        InlineKeyboardButton("🤫 Silent", callback_data="silent"),
        InlineKeyboardButton("👤 User Info", callback_data="info"),
        InlineKeyboardButton("🖼 User DP", callback_data="dp"),
        InlineKeyboardButton("👥 Total Users", callback_data="total"),
        InlineKeyboardButton("📊 Stats", callback_data="stats"),
        InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
        InlineKeyboardButton("🟢 Admin ON", callback_data="admin_on"),
        InlineKeyboardButton("🔴 Admin OFF", callback_data="admin_off")
    )
    return kb

@bot.message_handler(commands=['panel'])
def panel(message):
    if message.from_user.id != OWNER_ID:
        return
    bot.send_message(
        message.chat.id,
        "⚙️ <b>Admin Control Panel</b>\n\nReply to forwarded user message where needed.",
        reply_markup=admin_panel()
    )

# ---------- PANEL CALLBACKS ----------
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    if call.from_user.id != OWNER_ID:
        return

    bot.answer_callback_query(call.id)

    cid = call.message.chat.id

    if call.data == "total":
        bot.send_message(cid, f"👥 Total Users: {len(users)}")

    elif call.data == "stats":
        bot.send_message(
            cid,
            f"""
📊 <b>Bot Stats</b>
👥 Users: {len(users)}
🚫 Banned: {len(banned_users)}
🤫 Silent: {len(silent_users)}
"""
        )

    elif call.data == "ban":
        bot.send_message(cid, "🚫 Reply to forwarded message with:\n/ban")

    elif call.data == "unban":
        bot.send_message(cid, "✅ Reply to forwarded message with:\n/unban")

    elif call.data == "silent":
        bot.send_message(cid, "🤫 Reply to forwarded message with:\n/silent")

    elif call.data == "info":
        bot.send_message(cid, "👤 Reply to forwarded message with:\n/info")

    elif call.data == "dp":
        bot.send_message(cid, "🖼 Reply to forwarded message with:\n/dp")

    elif call.data == "broadcast":
        bot.send_message(cid, "📢 Reply to any message with:\n/broadcast")

    elif call.data == "admin_on":
        global admin_online
        admin_online = True
        bot.send_message(cid, "🟢 Admin is now ONLINE")

    elif call.data == "admin_off":
        admin_online = False
        bot.send_message(cid, "🔴 Admin is now OFFLINE")

# ---------- ADMIN COMMANDS ----------
@bot.message_handler(commands=['ban'])
def ban(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    uid = message.reply_to_message.forward_from.id
    banned_users.add(uid)
    bot.send_message(message.chat.id, f"🚫 User {uid} banned")

@bot.message_handler(commands=['unban'])
def unban(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    uid = message.reply_to_message.forward_from.id
    banned_users.discard(uid)
    bot.send_message(message.chat.id, f"✅ User {uid} unbanned")

@bot.message_handler(commands=['silent'])
def silent(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    uid = message.reply_to_message.forward_from.id
    silent_users.add(uid)
    bot.send_message(message.chat.id, f"🤫 User {uid} silenced")

@bot.message_handler(commands=['info'])
def info(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    u = message.reply_to_message.forward_from
    data = users.get(u.id, {})
    bot.send_message(
        message.chat.id,
        f"""
👤 <b>User Info</b>
🆔 ID: <code>{u.id}</code>
👤 Name: {data.get('name')}
🔗 Username: @{data.get('username')}
📅 Joined: {data.get('joined')}
"""
    )

@bot.message_handler(commands=['dp'])
def dp(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    u = message.reply_to_message.forward_from
    photos = bot.get_user_profile_photos(u.id)
    if photos.total_count > 0:
        bot.send_photo(message.chat.id, photos.photos[0][0].file_id)
    else:
        bot.send_message(message.chat.id, "😕 No profile photo")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    sent = 0
    for uid in users:
        try:
            bot.copy_message(uid, message.chat.id, message.reply_to_message.message_id)
            sent += 1
        except:
            pass
    bot.send_message(message.chat.id, f"📢 Broadcast sent to {sent} users")

# ---------- RUN ----------
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
