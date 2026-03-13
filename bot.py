import telebot
from telebot import types
import sqlite3
import random
import string

TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789  # o'z Telegram ID ingiz

required_channels = [
    "@bazarelon",
    "@abdulumar2025",
    "@navzarmedia",
    "@abdulhamidumar2026"
]

bot = telebot.TeleBot(TOKEN)

# DATABASE
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS videos(
code TEXT PRIMARY KEY,
title TEXT,
file_id TEXT,
premium INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS premium_users(
user_id INTEGER PRIMARY KEY
)
""")

conn.commit()

# -----------------
# KOD GENERATOR
# -----------------
def generate_code():
    return ''.join(random.choices(string.digits, k=5))

def generate_codes(n=1000):
    codes = set()
    while len(codes) < n:
        codes.add(generate_code())
    return list(codes)

# -----------------
# OBUNA TEKSHIRISH
# -----------------
def check_subscription(user_id):
    for channel in required_channels:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def subscription_markup():
    markup = types.InlineKeyboardMarkup()
    for ch in required_channels:
        markup.add(types.InlineKeyboardButton(
            f"📢 {ch}",
            url=f"https://t.me/{ch[1:]}"
        ))
    markup.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return markup

# -----------------
# START
# -----------------
@bot.message_handler(commands=['start'])
def start(message):

    if not check_subscription(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "❗ Botdan foydalanish uchun kanallarga obuna bo‘ling",
            reply_markup=subscription_markup()
        )
        return

    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Kino qo‘shish", "📊 Statistika")
        markup.add("⚡ 1000 kod yaratish")
        bot.send_message(message.chat.id, "🛠 Admin panel", reply_markup=markup)
    else:
        bot.send_message(message.chat.id,
        "🎬 Kino kodini yuboring yoki nomini yozib qidiring")

# -----------------
# OBUNA TEKSHIRISH
# -----------------
@bot.callback_query_handler(func=lambda call: call.data=="check_sub")
def check_sub(call):

    if check_subscription(call.from_user.id):
        bot.edit_message_text(
            "✅ Obuna tasdiqlandi\n\n/start ni bosing",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "❌ Hali obuna bo‘lmadingiz")

# -----------------
# 1000 KOD GENERATOR
# -----------------
@bot.message_handler(func=lambda m: m.text=="⚡ 1000 kod yaratish")
def create_codes(message):

    if message.from_user.id != ADMIN_ID:
        return

    codes = generate_codes(1000)

    txt = "\n".join(codes[:50])

    bot.send_message(
        message.chat.id,
        f"✅ 1000 ta kod yaratildi\n\nNamuna:\n{txt}"
    )

# -----------------
# KINO QO‘SHISH
# -----------------
@bot.message_handler(func=lambda m: m.text=="➕ Kino qo‘shish")
def add_movie(message):

    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(message.chat.id,
    "🎬 Video yuboring\nCaptionga kino nomini yozing")
    bot.register_next_step_handler(msg, save_movie)

def save_movie(message):

    if message.content_type != "video":
        bot.send_message(message.chat.id, "❌ Video yuboring")
        return

    title = message.caption if message.caption else "Nomsiz"
    code = generate_code()

    cursor.execute(
        "INSERT INTO videos VALUES(?,?,?,?)",
        (code, title.lower(), message.video.file_id, 0)
    )

    conn.commit()

    bot.send_message(
        message.chat.id,
        f"✅ Kino saqlandi\n\n🎬 {title}\n📀 Kod: {code}"
    )

# -----------------
# PREMIUM KINO
# -----------------
@bot.message_handler(commands=['premiumcode'])
def premium_code(message):

    if message.from_user.id != ADMIN_ID:
        return

    code = message.text.split()[1]

    cursor.execute(
        "UPDATE videos SET premium=1 WHERE code=?",
        (code,)
    )

    conn.commit()

    bot.send_message(message.chat.id,"🔒 Premium qilindi")

# -----------------
# PREMIUM USER
# -----------------
@bot.message_handler(commands=['addpremium'])
def add_premium(message):

    if message.from_user.id != ADMIN_ID:
        return

    user = int(message.text.split()[1])

    cursor.execute(
        "INSERT OR IGNORE INTO premium_users VALUES(?)",
        (user,)
    )

    conn.commit()

    bot.send_message(message.chat.id,"⭐ Premium user qo‘shildi")

# -----------------
# STATISTIKA
# -----------------
@bot.message_handler(func=lambda m: m.text=="📊 Statistika")
def stats(message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM videos")
    movies = cursor.fetchone()[0]

    bot.send_message(
        message.chat.id,
        f"🎬 Kinolar soni: {movies}"
    )

# -----------------
# KINO QIDIRUV
# -----------------
@bot.message_handler(func=lambda message: True)
def search_or_code(message):

    text = message.text.lower()

    cursor.execute(
        "SELECT code,title,file_id,premium FROM videos WHERE code=?",
        (text,)
    )

    result = cursor.fetchone()

    if result:
        code,title,file_id,premium = result

        if premium:
            cursor.execute(
                "SELECT user_id FROM premium_users WHERE user_id=?",
                (message.from_user.id,)
            )
            if not cursor.fetchone():
                bot.send_message(message.chat.id,"🔒 Bu kino premium")
                return

        bot.send_video(message.chat.id,file_id)
        return

    # QIDIRUV
    cursor.execute(
        "SELECT code,title FROM videos WHERE title LIKE ? LIMIT 5",
        (f"%{text}%",)
    )

    results = cursor.fetchall()

    if results:
        msg = "🔍 Topilgan kinolar:\n\n"
        for code,title in results:
            msg += f"🎬 {title}\n📀 Kod: {code}\n\n"

        bot.send_message(message.chat.id,msg)
    else:
        bot.send_message(message.chat.id,"❌ Hech narsa topilmadi")

print("Bot ishga tushdi...")
bot.infinity_polling()
