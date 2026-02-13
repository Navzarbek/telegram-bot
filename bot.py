import telebot
from telebot import types
import json
import os
import time

TOKEN = "8227543322:AAEtWyIHLiUe-2oPLv1x1IhIQHEoLfpoxqE"
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 1317771276  # O‘Z TELEGRAM ID INGIZNI YOZING

required_channels = [
    "@bazarelon",
    "@abdulumar2025",
    "@navzarmedia",
    "@abdulhamidumar2026"
]

DATA_FILE = "videos.json"

# JSON fayl yaratish
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_videos():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_videos(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def check_subscription(user_id):
    for channel in required_channels:
        status = bot.get_chat_member(channel, user_id).status
        if status not in ["member", "administrator", "creator"]:
            return False
    return True

pending_code = {}
premium_users = set()

# START
@bot.message_handler(commands=['start'])
def start(message):
    if not check_subscription(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for channel in required_channels:
            markup.add(types.InlineKeyboardButton("📢 Kanalga obuna", url=f"https://t.me/{channel[1:]}"))
        markup.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        bot.send_message(message.chat.id, "❗ Avval kanalga obuna bo‘ling", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "📩 Kod yuboring")

# Tekshirish tugmasi
@bot.callback_query_handler(func=lambda call: call.data == "check")
def callback_check(call):
    bot.send_chat_action(call.message.chat.id, "typing")
    time.sleep(1.5)

    if check_subscription(call.from_user.id):
        bot.edit_message_text(
            "✅ Obuna tasdiqlandi!\n\n📩 Endi kod yuboring.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "❌ Hali barcha kanallarga obuna bo‘lmagansiz")

# Admin: yangi kod qo‘shish
@bot.message_handler(commands=['add'])
def add_video(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        code = message.text.split()[1]
        pending_code[message.from_user.id] = code
        bot.send_message(message.chat.id, f"📥 {code} kodi uchun videoni yuboring")
    except:
        bot.send_message(message.chat.id, "❗ Format: /add 101")

# Video saqlash
@bot.message_handler(content_types=['video'])
def save_video(message):
    if message.from_user.id == ADMIN_ID and message.from_user.id in pending_code:
        code = pending_code[message.from_user.id]
        videos = load_videos()
        videos[code] = {
            "file_id": message.video.file_id,
            "premium": False
        }
        save_videos(videos)
        bot.send_message(message.chat.id, f"✅ {code} kodi saqlandi")
        del pending_code[message.from_user.id]

# Kodni premium qilish
@bot.message_handler(commands=['premiumcode'])
def make_premium(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        code = message.text.split()[1]
        videos = load_videos()

        if code in videos:
            videos[code]["premium"] = True
            save_videos(videos)
            bot.send_message(message.chat.id, f"🔒 {code} premium qilindi")
        else:
            bot.send_message(message.chat.id, "❌ Bunday kod yo‘q")
    except:
        bot.send_message(message.chat.id, "❗ Format: /premiumcode 500")

# Foydalanuvchini premium qilish
@bot.message_handler(commands=['addpremium'])
def add_premium_user(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        user_id = int(message.text.split()[1])
        premium_users.add(user_id)
        bot.send_message(message.chat.id, f"⭐ {user_id} premium qilindi")
    except:
        bot.send_message(message.chat.id, "❗ Format: /addpremium 123456789")

# Kod yozilganda
@bot.message_handler(func=lambda message: not message.text.startswith("/"))
def send_video(message):

    videos = load_videos()

    if message.text in videos:
        video_data = videos[message.text]

        if video_data["premium"] and message.from_user.id not in premium_users:
            bot.send_message(message.chat.id, "🔒 Bu kod premium.")
            return

        bot.send_video(message.chat.id, video_data["file_id"])
    else:
        bot.send_message(message.chat.id, "❌ Bunday kod yo‘q")


bot.polling()


