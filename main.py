import threading
import time
from flask import Flask
import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from config import BOT_TOKEN, OWNER_ID, WELCOME_MSG

# ---------------- INIT ----------------
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ---------------- DATA (RAM) ----------------
users = {}              # user_id : info
banned_users = set()
silent_users = set()
reply_map = {}          # admin_forwarded_msg_id : user_id
last_msg_time = {}
admin_online = True

# ---------------- FLASK ----------------
@app.route("/")
def home():
    return "Bot is running", 200

def run_bot():
    bot.infinity_polling(skip_pending=True)

# ---------------- HELPERS ----------------
def save_user(user):
    if user.id not in users:
        users[user.id] = {
            "name": user.first_name,
            "username": user.username,
            "joined": time.strftime("%d-%m-%Y %H:%M")
        }

def is_spam(uid):
    now = time.time()
    if uid in last_msg_time and now - last_msg_time[uid] < 2:
        return True
    last_msg_time[uid] = now
    return False

# ---------------- USER KEYBOARD ----------------
def user_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton("ℹ️ Help"),
        KeyboardButton("📩 Contact Admin")
    )
    return kb

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid in banned_users:
        return

    save_user(message.from_user)

    bot.send_message(
        message.chat.id,
        WELCOME_MSG.format(name=message.from_user.first_name),
        reply_markup=user_keyboard()
    )

# ---------------- USER BUTTONS ----------------
@bot.message_handler(func=lambda m: m.text == "ℹ️ Help")
def help_msg(message):
    bot.send_message(
        message.chat.id,
        "🆘 Bas apna message bhejo.\nAdmin jaldi reply karega."
    )

@bot.message_handler(func=lambda m: m.text == "📩 Contact Admin")
def contact_admin(message):
    bot.send_message(
        message.chat.id,
        "✍️ Apna message type karo, admin ko forward ho jayega."
    )

# ---------------- USER -> ADMIN ----------------
@bot.message_handler(
    func=lambda m: m.chat.type == "private" and m.from_user.id != OWNER_ID,
    content_types=['text','photo','video','document','audio','voice','sticker']
)
def user_message(message):
    uid = message.from_user.id

    if uid in banned_users or is_spam(uid) or uid in silent_users:
        return

    save_user(message.from_user)

    if not admin_online:
        bot.send_message(message.chat.id, "⚠️ Admin offline hai, reply late ho sakta hai")

    fwd = bot.forward_message(
        OWNER_ID,
        message.chat.id,
        message.message_id
    )

    # 🔑 IMPORTANT
    reply_map[fwd.message_id] = uid

    bot.send_message(message.chat.id, "✅ Message admin ko bhej diya gaya hai")

# ---------------- ADMIN REPLY ----------------
@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.reply_to_message)
def admin_reply(message):
    mid = message.reply_to_message.message_id
    uid = reply_map.get(mid)
    if not uid:
        return
    bot.copy_message(uid, message.chat.id, message.message_id)

# ---------------- ADMIN PANEL ----------------
def admin_panel():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🚫 Ban", callback_data="ban"),
        InlineKeyboardButton("✅ Unban", callback_data="unban"),
        InlineKeyboardButton("🤫 Silent", callback_data="silent"),
        InlineKeyboardButton("👤 Info", callback_data="info"),
        InlineKeyboardButton("🖼 DP", callback_data="dp"),
        InlineKeyboardButton("👥 Users", callback_data="total"),
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
        "⚙️ <b>Admin Panel</b>\n\nUser ke forwarded message par reply karke button dabao.",
        reply_markup=admin_panel()
    )

# ---------------- BUTTON ACTIONS (REAL WORKING) ----------------
@bot.callback_query_handler(func=lambda c: True)
def buttons(call):
    if call.from_user.id != OWNER_ID:
        return

    bot.answer_callback_query(call.id)

    cid = call.message.chat.id

    # jis forwarded msg par reply hai, usse user nikalo
    uid = None
    if call.message.reply_to_message:
        uid = reply_map.get(call.message.reply_to_message.message_id)

    if call.data == "ban" and uid:
        banned_users.add(uid)
        bot.send_message(cid, f"🚫 User {uid} banned")

    elif call.data == "unban" and uid:
        banned_users.discard(uid)
        bot.send_message(cid, f"✅ User {uid} unbanned")

    elif call.data == "silent" and uid:
        silent_users.add(uid)
        bot.send_message(cid, f"🤫 User {uid} silenced")

    elif call.data == "info" and uid:
        u = users.get(uid, {})
        bot.send_message(
            cid,
            f"""
👤 <b>User Info</b>
🆔 <code>{uid}</code>
👤 {u.get('name')}
🔗 @{u.get('username')}
📅 {u.get('joined')}
"""
        )

    elif call.data == "dp" and uid:
        photos = bot.get_user_profile_photos(uid)
        if photos.total_count:
            bot.send_photo(cid, photos.photos[0][0].file_id)
        else:
            bot.send_message(cid, "😕 No profile photo")

    elif call.data == "total":
        bot.send_message(cid, f"👥 Total Users: {len(users)}")

    elif call.data == "broadcast":
        bot.send_message(cid, "📢 Kisi bhi message par reply karke /broadcast likho")

    elif call.data == "admin_on":
        global admin_online
        admin_online = True
        bot.send_message(cid, "🟢 Admin ONLINE")

    elif call.data == "admin_off":
        admin_online = False
        bot.send_message(cid, "🔴 Admin OFFLINE")

    else:
        bot.send_message(cid, "❗ Pehle kisi user ke forwarded message par reply karo")

# ---------------- BROADCAST ----------------
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

# ---------------- BAN BY USER ID (EXTRA POWER) ----------------
@bot.message_handler(commands=['banid'])
def ban_by_id(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.text.split()[1])
        banned_users.add(uid)
        bot.send_message(message.chat.id, f"🚫 User {uid} banned")
    except:
        bot.send_message(message.chat.id, "❌ Use: /banid USER_ID")

@bot.message_handler(commands=['unbanid'])
def unban_by_id(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.text.split()[1])
        banned_users.discard(uid)
        bot.send_message(message.chat.id, f"✅ User {uid} unbanned")
    except:
        bot.send_message(message.chat.id, "❌ Use: /unbanid USER_ID")

# ---------------- RUN ----------------
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
