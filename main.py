import threading, time
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN, OWNER_ID, WELCOME_MSG

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ---------------- DATA ----------------
users = {}
banned_users = set()
silent_users = set()
reply_map = {}        # admin_forwarded_msg_id : user_id
last_msg_time = {}
admin_online = True

# ---------------- FLASK ----------------
@app.route("/")
def home():
    return "Bot running", 200

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

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id in banned_users:
        return
    save_user(message.from_user)
    bot.send_message(
        message.chat.id,
        WELCOME_MSG.format(name=message.from_user.first_name)
    )

# ---------------- USER -> ADMIN ----------------
@bot.message_handler(
    func=lambda m: m.chat.type == "private" and m.from_user.id != OWNER_ID,
    content_types=['text','photo','video','document','audio','voice','sticker']
)
def user_msg(message):
    uid = message.from_user.id

    if uid in banned_users or is_spam(uid):
        return

    save_user(message.from_user)

    if uid in silent_users:
        return

    fwd = bot.forward_message(
        OWNER_ID,
        message.chat.id,
        message.message_id
    )

    # 🔑 REAL KEY FIX
    reply_map[fwd.message_id] = uid

    bot.send_message(message.chat.id, "✅ Message sent to admin")

# ---------------- ADMIN REPLY ----------------
@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.reply_to_message)
def admin_reply(message):
    mid = message.reply_to_message.message_id
    if mid not in reply_map:
        return
    uid = reply_map[mid]
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
        InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")
    )
    return kb

@bot.message_handler(commands=['panel'])
def panel(message):
    if message.from_user.id != OWNER_ID:
        return
    bot.send_message(
        message.chat.id,
        "⚙️ <b>Admin Panel</b>\nReply to forwarded message.",
        reply_markup=admin_panel()
    )

# ---------------- BUTTON HANDLER ----------------
@bot.callback_query_handler(func=lambda c: True)
def buttons(call):
    if call.from_user.id != OWNER_ID:
        return
    bot.answer_callback_query(call.id)

    if call.data == "total":
        bot.send_message(call.message.chat.id, f"👥 Users: {len(users)}")
    else:
        bot.send_message(call.message.chat.id, f"Reply to forwarded msg with /{call.data}")

# ---------------- ADMIN COMMANDS ----------------
@bot.message_handler(commands=['ban'])
def ban(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    mid = message.reply_to_message.message_id
    uid = reply_map.get(mid)
    if not uid:
        return
    banned_users.add(uid)
    bot.send_message(message.chat.id, f"🚫 User {uid} banned")

@bot.message_handler(commands=['unban'])
def unban(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    mid = message.reply_to_message.message_id
    uid = reply_map.get(mid)
    if not uid:
        return
    banned_users.discard(uid)
    bot.send_message(message.chat.id, f"✅ User {uid} unbanned")

@bot.message_handler(commands=['silent'])
def silent(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    uid = reply_map.get(message.reply_to_message.message_id)
    if not uid:
        return
    silent_users.add(uid)
    bot.send_message(message.chat.id, f"🤫 User {uid} silenced")

@bot.message_handler(commands=['info'])
def info(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    uid = reply_map.get(message.reply_to_message.message_id)
    if not uid:
        return
    u = users.get(uid, {})
    bot.send_message(
        message.chat.id,
        f"""
👤 <b>User Info</b>
🆔 {uid}
👤 {u.get('name')}
🔗 @{u.get('username')}
📅 {u.get('joined')}
"""
    )

@bot.message_handler(commands=['dp'])
def dp(message):
    if message.from_user.id != OWNER_ID or not message.reply_to_message:
        return
    uid = reply_map.get(message.reply_to_message.message_id)
    if not uid:
        return
    photos = bot.get_user_profile_photos(uid)
    if photos.total_count:
        bot.send_photo(message.chat.id, photos.photos[0][0].file_id)
    else:
        bot.send_message(message.chat.id, "😕 No DP")

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
    bot.send_message(message.chat.id, f"📢 Sent to {sent} users")

# ---------------- RUN ----------------
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
