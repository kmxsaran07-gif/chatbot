import threading
from flask import Flask
import telebot
from config import BOT_TOKEN, OWNER_ID, WELCOME_MSG

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

users = set()
banned_users = set()
reply_map = {}  # owner_msg_id : user_id


# ---------- TELEGRAM BOT LOGIC ----------

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id in banned_users:
        return
    users.add(message.from_user.id)
    bot.send_message(
        message.chat.id,
        WELCOME_MSG.format(name=message.from_user.first_name)
    )


@bot.message_handler(
    func=lambda m: m.chat.type == "private"
    and m.from_user.id != OWNER_ID
    and m.from_user.id not in banned_users,
    content_types=['text','photo','video','document','audio','voice','sticker']
)
def forward_to_owner(message):
    users.add(message.from_user.id)

    fwd = bot.forward_message(
        OWNER_ID,
        message.chat.id,
        message.message_id
    )
    reply_map[fwd.message_id] = message.from_user.id

    bot.send_message(
        message.chat.id,
        "✅ Message sent to admin.\n⏳ Please wait for reply."
    )


@bot.message_handler(
    func=lambda m: m.from_user.id == OWNER_ID and m.reply_to_message
)
def owner_reply(message):
    replied_id = message.reply_to_message.message_id
    if replied_id not in reply_map:
        return

    user_id = reply_map[replied_id]
    bot.copy_message(
        user_id,
        message.chat.id,
        message.message_id
    )


@bot.message_handler(commands=['total'])
def total_users(message):
    if message.from_user.id == OWNER_ID:
        bot.send_message(message.chat.id, f"👥 Total Users: {len(users)}")


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


# ---------- FLASK PART (FAKE WEB SERVER) ----------

@app.route("/")
def home():
    return "Bot is running successfully!", 200


def run_bot():
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
