import telebot
from config import BOT_TOKEN, OWNER_ID, WELCOME_MSG

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

users = set()
banned_users = set()
reply_map = {}  # owner_message_id : user_id

# ---------- START ----------
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id in banned_users:
        return

    users.add(message.from_user.id)
    bot.send_message(
        message.chat.id,
        WELCOME_MSG.format(name=message.from_user.first_name)
    )

# ---------- USER -> OWNER ----------
@bot.message_handler(
    func=lambda m: m.chat.type == "private"
    and m.from_user.id != OWNER_ID
    and m.from_user.id not in banned_users,
    content_types=['text','photo','video','document','audio','voice','sticker']
)
def forward_to_owner(message):

    users.add(message.from_user.id)

    forwarded = bot.forward_message(
        OWNER_ID,
        message.chat.id,
        message.message_id
    )

    reply_map[forwarded.message_id] = message.from_user.id

    bot.send_message(
        message.chat.id,
        "✅ Message sent to admin.\n⏳ Please wait for reply."
    )

# ---------- OWNER REPLY -> USER ----------
@bot.message_handler(
    func=lambda m: m.from_user.id == OWNER_ID and m.reply_to_message
)
def owner_reply(message):

    replied_id = message.reply_to_message.message_id

    if replied_id not in reply_map:
        return

    user_id = reply_map[replied_id]

    try:
        bot.copy_message(
            user_id,
            message.chat.id,
            message.message_id
        )
        bot.send_message(OWNER_ID, "✅ Reply delivered")
    except:
        bot.send_message(OWNER_ID, "❌ Failed to send reply")

# ---------- TOTAL USERS ----------
@bot.message_handler(commands=['total'])
def total_users(message):
    if message.from_user.id == OWNER_ID:
        bot.send_message(message.chat.id, f"👥 Total Users: {len(users)}")

# ---------- BAN ----------
@bot.message_handler(commands=['ban'])
def ban(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.text.split()[1])
        banned_users.add(uid)
        bot.send_message(message.chat.id, f"🚫 User {uid} banned")
    except:
        bot.send_message(message.chat.id, "❌ Usage: /ban user_id")

# ---------- UNBAN ----------
@bot.message_handler(commands=['unban'])
def unban(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.text.split()[1])
        banned_users.discard(uid)
        bot.send_message(message.chat.id, f"✅ User {uid} unbanned")
    except:
        bot.send_message(message.chat.id, "❌ Usage: /unban user_id")

# ---------- USER DP ----------
@bot.message_handler(commands=['dp'])
def dp(message):
    user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    photos = bot.get_user_profile_photos(user.id)

    if photos.total_count > 0:
        bot.send_photo(message.chat.id, photos.photos[0][0].file_id)
    else:
        bot.send_message(message.chat.id, "😕 No profile photo")

# ---------- BROADCAST ----------
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != OWNER_ID:
        return

    if not message.reply_to_message:
        bot.send_message(message.chat.id, "❌ Reply to a message to broadcast")
        return

    success = 0
    for uid in users:
        try:
            bot.copy_message(uid, message.chat.id, message.reply_to_message.message_id)
            success += 1
        except:
            pass

    bot.send_message(message.chat.id, f"📢 Broadcast sent to {success} users")

print("🔥 Premium Support Bot Running...")
bot.infinity_polling(skip_pending=True)
