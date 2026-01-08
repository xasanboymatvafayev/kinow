import telebot
from telebot import types
import sqlite3
import os
from datetime import datetime

# ============= SOZLAMALAR =============
TOKEN = "8329981586:AAHfUTH1u0Ut6fBYdgZjkTBy5ORMv95pDSI"
MAIN_ADMIN_ID = 6365371142  # Asosiy admin (o'chirib bo'lmaydi)

bot = telebot.TeleBot(TOKEN)

# ============= DATABASE =============
def init_db():
    conn = sqlite3.connect('triokino.db', check_same_thread=False)
    c = conn.cursor()
    
    # Users jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        join_date TEXT,
        is_banned INTEGER DEFAULT 0
    )''')
    
    # Admins jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER UNIQUE,
        added_by INTEGER,
        added_date TEXT
    )''')
    
    # Channels jadvali (Majburiy obuna kanallari)
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id INTEGER UNIQUE,
        channel_username TEXT,
        added_by INTEGER,
        added_date TEXT,
        is_active INTEGER DEFAULT 1
    )''')
    
    # Movies jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        title TEXT,
        type TEXT,
        description TEXT,
        file_id TEXT,
        year INTEGER,
        country TEXT,
        genre TEXT,
        added_by INTEGER,
        added_date TEXT,
        views INTEGER DEFAULT 0
    )''')
    
    # Serials jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS serials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        title TEXT,
        description TEXT,
        total_episodes INTEGER DEFAULT 0,
        added_date TEXT
    )''')
    
    # Episodes jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_code TEXT,
        episode_number INTEGER,
        title TEXT,
        file_id TEXT,
        added_date TEXT,
        FOREIGN KEY (serial_code) REFERENCES serials(code)
    )''')
    
    # Statistics jadvali
    c.execute('''CREATE TABLE IF NOT EXISTS statistics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        movie_code TEXT,
        watch_date TEXT
    )''')
    
    # Asosiy adminni qo'shish
    c.execute('INSERT OR IGNORE INTO admins (admin_id, added_by, added_date) VALUES (?, ?, ?)', 
              (MAIN_ADMIN_ID, MAIN_ADMIN_ID, datetime.now().strftime("%Y-%m-%d %H:%M")))
    
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect('triokino.db', check_same_thread=False)

# Database ni ishga tushirish
if os.path.exists('triokino.db'):
    print("📂 Database topildi: triokino.db")
else:
    print("🆕 Yangi database yaratilmoqda...")

init_db()
print("✅ Database tayyor!")

# ============= YORDAMCHI FUNKSIYALAR =============
def is_admin(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM admins WHERE admin_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def is_banned(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

def get_active_channels():
    """Faol kanallarni olish"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT channel_id, channel_username FROM channels WHERE is_active = 1')
    channels = c.fetchall()
    conn.close()
    return channels

def check_subscription(user_id):
    """Foydalanuvchi barcha faol kanallarga obuna bo'lganini tekshirish"""
    channels = get_active_channels()
    
    if not channels:
        return True, None
    
    for channel in channels:
        try:
            status = bot.get_chat_member(channel[0], user_id).status
            if status in ['left', 'kicked']:
                return False, channel[1]
        except Exception as e:
            print(f"Kanal tekshirishda xatolik: {e}")
            pass
    return True, None

def subscription_keyboard():
    """Obuna tugmalari"""
    channels = get_active_channels()
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for channel in channels:
        username = channel[1]
        markup.add(types.InlineKeyboardButton(
            f"📢 {username}", 
            url=f"https://t.me/{username[1:]}" if username.startswith('@') else f"https://t.me/{username}"
        ))
    
    markup.add(types.InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub"))
    return markup

def main_keyboard(user_id):
    """Asosiy menyu"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎬 Kino", "📺 Serial")
    markup.row("🔍 Qidiruv", "ℹ️ Ma'lumot")
    if is_admin(user_id):
        markup.row("👑 Admin Panel")
    return markup

def admin_keyboard():
    """Admin panel tugmalari"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Kino qo'shish", "➕ Serial qo'shish")
    markup.row("✏️ Tahrirlash", "🗑 O'chirish")
    markup.row("👤 Adminlar", "📢 Kanallar")
    markup.row("🚫 Ban/Unban", "📊 Statistika")
    markup.row("📣 Reklama", "🔙 Orqaga")
    return markup

# ============= OBUNA TEKSHIRUVI =============
def check_sub_decorator(func):
    """Obuna tekshirish dekoratori"""
    def wrapper(msg):
        user_id = msg.from_user.id if hasattr(msg, 'from_user') else msg.message.chat.id
        
        # Adminlar uchun tekshirmaslik
        if is_admin(user_id):
            return func(msg)
        
        # Ban tekshiruvi
        if is_banned(user_id):
            bot.send_message(user_id, "🚫 Siz bloklangansiz!")
            return
        
        # Obuna tekshiruvi
        subscribed, channel = check_subscription(user_id)
        if not subscribed:
            bot.send_message(
                user_id,
                f"⚠️ Botdan foydalanish uchun kanallarimizga obuna bo'ling!\n\n"
                f"Obuna bo'lmagan kanal: {channel}",
                reply_markup=subscription_keyboard()
            )
            return
        
        return func(msg)
    return wrapper

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    user_id = call.from_user.id
    subscribed, channel = check_subscription(user_id)
    
    if subscribed:
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message)
    else:
        bot.answer_callback_query(call.id, f"❌ {channel} ga obuna bo'lmadingiz!", show_alert=True)

# ============= START =============
@bot.message_handler(commands=['start'])
@check_sub_decorator
def start(msg):
    user_id = msg.from_user.id
    username = msg.from_user.username or "Username yo'q"
    first_name = msg.from_user.first_name or ""
    last_name = msg.from_user.last_name or ""
    
    # Foydalanuvchini bazaga qo'shish
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, 0)''',
              (user_id, username, first_name, last_name, 
               datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    
    welcome = (
        f"👋 Salom, {first_name}!\n\n"
        f"🎬 Kino Yuklovchi BOT ga xush kelibsiz!\n\n"
        f"📽 Minglab kino va seriallar sizni kutmoqda!\n"
        f"🔍 Qidiruv orqali kerakli kontentni toping.\n\n"
        f"💡 Tugmalardan foydalaning:"
    )
    
    bot.send_message(msg.chat.id, welcome, reply_markup=main_keyboard(user_id))

# ============= ADMIN PANEL =============
@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
@check_sub_decorator
def admin_panel(msg):
    if not is_admin(msg.from_user.id):
        bot.send_message(msg.chat.id, "🚫 Sizda ruxsat yo'q!")
        return
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users')
    users_count = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM movies')
    movies_count = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM serials')
    serials_count = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM admins')
    admins_count = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM channels WHERE is_active = 1')
    channels_count = c.fetchone()[0]
    
    conn.close()
    
    panel_text = (
        f"👑 *ADMIN PANEL*\n\n"
        f"📊 Statistika:\n"
        f"👥 Foydalanuvchilar: {users_count}\n"
        f"🎬 Kinolar: {movies_count}\n"
        f"📺 Seriallar: {serials_count}\n"
        f"👮 Adminlar: {admins_count}\n"
        f"📢 Kanallar: {channels_count}\n\n"
        f"Kerakli bo'limni tanlang:"
    )
    
    bot.send_message(msg.chat.id, panel_text, parse_mode="Markdown", 
                     reply_markup=admin_keyboard())

# ============= ADMINLAR BOSHQARUVI =============
@bot.message_handler(func=lambda m: m.text == "👤 Adminlar")
@check_sub_decorator
def admins_menu(msg):
    if not is_admin(msg.from_user.id):
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Admin qo'shish", "🗑 Admin o'chirish")
    markup.row("📋 Adminlar ro'yxati", "🔙 Orqaga")
    
    bot.send_message(msg.chat.id, "👤 Adminlar bo'limi:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Admin qo'shish")
@check_sub_decorator
def add_admin_start(msg):
    if msg.from_user.id != MAIN_ADMIN_ID:
        bot.send_message(msg.chat.id, "🚫 Faqat asosiy admin adminlar qo'sha oladi!")
        return
    
    bot.send_message(msg.chat.id, "🆔 Yangi admin ID raqamini kiriting:")
    bot.register_next_step_handler(msg, add_admin_id)

def add_admin_id(msg):
    try:
        new_admin_id = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, "❌ ID raqam kiriting!")
        return
    
    if new_admin_id == MAIN_ADMIN_ID:
        bot.send_message(msg.chat.id, "⚠️ Bu asosiy admin!")
        return
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('INSERT INTO admins (admin_id, added_by, added_date) VALUES (?, ?, ?)',
                  (new_admin_id, msg.from_user.id, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        bot.send_message(msg.chat.id, f"✅ Admin qo'shildi: {new_admin_id}")
    except:
        bot.send_message(msg.chat.id, "⚠️ Bu ID allaqachon admin!")
    
    conn.close()

@bot.message_handler(func=lambda m: m.text == "🗑 Admin o'chirish")
@check_sub_decorator
def remove_admin_start(msg):
    if msg.from_user.id != MAIN_ADMIN_ID:
        bot.send_message(msg.chat.id, "🚫 Faqat asosiy admin!")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT admin_id FROM admins WHERE admin_id != ?', (MAIN_ADMIN_ID,))
    admins = c.fetchall()
    conn.close()
    
    if not admins:
        bot.send_message(msg.chat.id, "❌ O'chiriladigan adminlar yo'q!")
        return
    
    text = "📋 Adminlar:\n\n"
    for admin in admins:
        text += f"• `{admin[0]}`\n"
    
    text += "\n🆔 O'chirish uchun ID kiriting:"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, remove_admin_id)

def remove_admin_id(msg):
    try:
        admin_id = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, "❌ ID raqam kiriting!")
        return
    
    if admin_id == MAIN_ADMIN_ID:
        bot.send_message(msg.chat.id, "🚫 Asosiy adminni o'chirib bo'lmaydi!")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM admins WHERE admin_id = ?', (admin_id,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        bot.send_message(msg.chat.id, f"✅ Admin o'chirildi: {admin_id}")
    else:
        bot.send_message(msg.chat.id, "❌ Admin topilmadi!")

@bot.message_handler(func=lambda m: m.text == "📋 Adminlar ro'yxati")
@check_sub_decorator
def list_admins(msg):
    if not is_admin(msg.from_user.id):
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT admin_id, added_date FROM admins ORDER BY added_date')
    admins = c.fetchall()
    conn.close()
    
    text = "👮 *ADMINLAR RO'YXATI*\n\n"
    for i, admin in enumerate(admins, 1):
        emoji = "👑" if admin[0] == MAIN_ADMIN_ID else "👤"
        text += f"{i}. {emoji} `{admin[0]}`\n   └ {admin[1]}\n"
    
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

# ============= KANALLAR BOSHQARUVI =============
@bot.message_handler(func=lambda m: m.text == "📢 Kanallar")
@check_sub_decorator
def channels_menu(msg):
    if not is_admin(msg.from_user.id):
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Kanal qo'shish", "🗑 Kanal o'chirish")
    markup.row("🔄 Kanal o'chirish/yoqish", "📋 Kanallar ro'yxati")
    markup.row("🔙 Orqaga")
    
    bot.send_message(msg.chat.id, "📢 Kanallar bo'limi:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "➕ Kanal qo'shish")
@check_sub_decorator
def add_channel_start(msg):
    if not is_admin(msg.from_user.id):
        return
    
    bot.send_message(msg.chat.id, 
        "📢 Kanal username kiriting (masalan: @kanal)\n\n"
        "💡 Botni avval kanalga admin qiling!")
    bot.register_next_step_handler(msg, add_channel_username)

def add_channel_username(msg):
    username = msg.text.strip()
    
    if not username.startswith('@'):
        username = '@' + username
    
    bot.send_message(msg.chat.id, "🆔 Kanal ID sini kiriting (masalan: -1001234567890):")
    bot.register_next_step_handler(msg, lambda m: add_channel_id(m, username))

def add_channel_id(msg, username):
    try:
        channel_id = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, "❌ ID raqam kiriting!")
        return
    
    # Kanalni tekshirish
    try:
        chat = bot.get_chat(channel_id)
        bot.send_message(msg.chat.id, f"✅ Kanal topildi: {chat.title}")
    except:
        bot.send_message(msg.chat.id, "⚠️ Kanal topilmadi yoki bot admin emas!")
        return
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('INSERT INTO channels (channel_id, channel_username, added_by, added_date) VALUES (?, ?, ?, ?)',
                  (channel_id, username, msg.from_user.id, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        bot.send_message(msg.chat.id, f"✅ Kanal qo'shildi: {username}")
    except:
        bot.send_message(msg.chat.id, "⚠️ Bu kanal allaqachon mavjud!")
    
    conn.close()

@bot.message_handler(func=lambda m: m.text == "🗑 Kanal o'chirish")
@check_sub_decorator
def remove_channel_start(msg):
    if not is_admin(msg.from_user.id):
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, channel_username, channel_id FROM channels')
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        bot.send_message(msg.chat.id, "❌ Kanallar yo'q!")
        return
    
    text = "📋 Kanallar:\n\n"
    for ch in channels:
        text += f"{ch[0]}. {ch[1]} (ID: `{ch[2]}`)\n"
    
    text += "\n🔢 O'chirish uchun kanal raqamini (1, 2, 3...) kiriting:"
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, remove_channel_id)

def remove_channel_id(msg):
    try:
        row_id = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, "❌ Raqam kiriting!")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM channels WHERE id = ?', (row_id,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        bot.send_message(msg.chat.id, f"✅ Kanal o'chirildi!")
    else:
        bot.send_message(msg.chat.id, "❌ Kanal topilmadi!")

@bot.message_handler(func=lambda m: m.text == "🔄 Kanal o'chirish/yoqish")
@check_sub_decorator
def toggle_channel_start(msg):
    if not is_admin(msg.from_user.id):
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, channel_username, is_active FROM channels')
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        bot.send_message(msg.chat.id, "❌ Kanallar yo'q!")
        return
    
    text = "📋 Kanallar:\n\n"
    for ch in channels:
        status = "✅ Faol" if ch[2] == 1 else "❌ O'chiq"
        text += f"{ch[0]}. {ch[1]} - {status}\n"
    
    text += "\n🔢 O'zgartirish uchun kanal raqamini kiriting:"
    bot.send_message(msg.chat.id, text)
    bot.register_next_step_handler(msg, toggle_channel_id)

def toggle_channel_id(msg):
    try:
        row_id = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, "❌ Raqam kiriting!")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT is_active FROM channels WHERE id = ?', (row_id,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        bot.send_message(msg.chat.id, "❌ Kanal topilmadi!")
        return
    
    new_status = 0 if result[0] == 1 else 1
    c.execute('UPDATE channels SET is_active = ? WHERE id = ?', (new_status, row_id))
    conn.commit()
    conn.close()
    
    status_text = "yoqildi" if new_status == 1 else "o'chirildi"
    bot.send_message(msg.chat.id, f"✅ Kanal {status_text}!")

@bot.message_handler(func=lambda m: m.text == "📋 Kanallar ro'yxati")
@check_sub_decorator
def list_channels(msg):
    if not is_admin(msg.from_user.id):
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT channel_username, channel_id, is_active, added_date FROM channels ORDER BY added_date')
    channels = c.fetchall()
    conn.close()
    
    if not channels:
        bot.send_message(msg.chat.id, "❌ Kanallar yo'q!")
        return
    
    text = "📢 *KANALLAR RO'YXATI*\n\n"
    for i, ch in enumerate(channels, 1):
        status = "✅" if ch[2] == 1 else "❌"
        text += f"{i}. {status} {ch[0]}\n   ID: `{ch[1]}`\n   └ {ch[3]}\n\n"
    
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

# ============= KINO QO'SHISH =============
@bot.message_handler(func=lambda m: m.text == "➕ Kino qo'shish")
@check_sub_decorator
def add_movie_start(msg):
    if not is_admin(msg.from_user.id):
        return
    
    bot.send_message(msg.chat.id, "🆔 Film kodini kiriting (masalan: K001):")
    bot.register_next_step_handler(msg, add_movie_code)

def add_movie_code(msg):
    code = msg.text.strip().upper()
    
    if len(code) < 2:
        bot.send_message(msg.chat.id, "❌ Kod juda qisqa. Qaytadan:")
        bot.register_next_step_handler(msg, add_movie_code)
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM movies WHERE code = ?', (code,))
    if c.fetchone():
        conn.close()
        bot.send_message(msg.chat.id, f"⚠️ {code} kodi allaqachon mavjud!")
        return
    conn.close()
    
    bot.send_message(msg.chat.id, f"✅ Kod: `{code}`\n\n📝 Film nomini kiriting:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: add_movie_title(m, code))

def add_movie_title(msg, code):
    title = msg.text.strip()
    bot.send_message(msg.chat.id, f"📄 Tavsifini kiriting (yoki /skip):")
    bot.register_next_step_handler(msg, lambda m: add_movie_description(m, code, title))

def add_movie_description(msg, code, title):
    description = "Tavsif yo'q" if msg.text == "/skip" else msg.text.strip()
    bot.send_message(msg.chat.id, f"📹 Endi video faylni yuboring:")
    bot.register_next_step_handler(msg, lambda m: save_movie(m, code, title, description))

def save_movie(msg, code, title, description):
    if not msg.video:
        bot.send_message(msg.chat.id, "❌ Video yuborilmadi! Qaytadan:")
        bot.register_next_step_handler(msg, lambda m: save_movie(m, code, title, description))
        return
    
    file_id = msg.video.file_id
    user_id = msg.from_user.id
    
    bot.send_message(msg.chat.id, "⏳ Bazaga saqlanmoqda...")
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO movies (code, title, type, description, file_id, year, country, genre, added_by, added_date) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (code, title, "movie", description, file_id, 2024, "Noma'lum", "Noma'lum", user_id,
                   datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        
        success = (
            f"✅ *KINO MUVAFFAQIYATLI QO'SHILDI!*\n\n"
            f"🆔 Kod: `{code}`\n"
            f"🎬 Nomi: {title}\n"
            f"📄 Tavsif: {description}\n"
            f"📦 File ID: `{file_id[:30]}...`\n"
            f"📅 Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"👥 Foydalanuvchilar endi `{code}` kodi bilan bu filmni olishlari mumkin!"
        )
        
        bot.send_message(msg.chat.id, success, parse_mode="Markdown")
        
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Bazaga saqlashda xatolik: {e}")
    
    conn.close()

# ============= SERIAL QO'SHISH =============
@bot.message_handler(func=lambda m: m.text == "➕ Serial qo'shish")
@check_sub_decorator
def add_serial_start(msg):
    if not is_admin(msg.from_user.id):
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📺 Yangi serial", "➕ Qism qo'shish")
    markup.row("🔙 Orqaga")
    
    bot.send_message(msg.chat.id, "Tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📺 Yangi serial")
@check_sub_decorator
def create_serial(msg):
    if not is_admin(msg.from_user.id):
        return
    
    bot.send_message(msg.chat.id, "🆔 Serial kodini kiriting (masalan: S001):")
    bot.register_next_step_handler(msg, create_serial_code)

def create_serial_code(msg):
    code = msg.text.strip().upper()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM serials WHERE code = ?', (code,))
    if c.fetchone():
        conn.close()
        bot.send_message(msg.chat.id, f"⚠️ {code} kodi mavjud!")
        return
    conn.close()
    
    bot.send_message(msg.chat.id, f"📝 Serial nomini kiriting:")
    bot.register_next_step_handler(msg, lambda m: create_serial_title(m, code))

def create_serial_title(msg, code):
    title = msg.text.strip()
    bot.send_message(msg.chat.id, f"📄 Tavsifini kiriting:")
    bot.register_next_step_handler(msg, lambda m: save_serial(m, code, title))

def save_serial(msg, code, title):
    description = msg.text.strip()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO serials (code, title, description, added_date) VALUES (?, ?, ?, ?)''',
              (code, title, description, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    
    bot.send_message(msg.chat.id, 
        f"✅ *SERIAL YARATILDI!*\n\n🆔 Kod: `{code}`\n📺 Nomi: {title}\n\n"
        f"Endi qismlarni qo'shishingiz mumkin.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Qism qo'shish")
@check_sub_decorator
def add_episode_start(msg):
    if not is_admin(msg.from_user.id):
        return
    
    bot.send_message(msg.chat.id, "🆔 Serial kodini kiriting:")
    bot.register_next_step_handler(msg, add_episode_serial_code)

def add_episode_serial_code(msg):
    code = msg.text.strip().upper()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM serials WHERE code = ?', (code,))
    serial = c.fetchone()
    conn.close()
    
    if not serial:
        bot.send_message(msg.chat.id, f"❌ {code} kodli serial topilmadi!")
        return
    
    bot.send_message(msg.chat.id, f"📺 Serial: {serial[2]}\n\n🔢 Qism raqamini kiriting:")
    bot.register_next_step_handler(msg, lambda m: add_episode_number(m, code))

def add_episode_number(msg, serial_code):
    try:
        episode_num = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, "❌ Raqam kiriting!")
        return
    
    bot.send_message(msg.chat.id, f"📹 {episode_num}-qism videosini yuboring:")
    bot.register_next_step_handler(msg, lambda m: save_episode(m, serial_code, episode_num))

def save_episode(msg, serial_code, episode_num):
    if not msg.video:
        bot.send_message(msg.chat.id, "❌ Video yuboring!")
        return
    
    file_id = msg.video.file_id
    title = f"{episode_num}-qism"
    
    bot.send_message(msg.chat.id, "⏳ Qism saqlanmoqda...")
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO episodes (serial_code, episode_number, title, file_id, added_date) 
                 VALUES (?, ?, ?, ?, ?)''',
              (serial_code, episode_num, title, file_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
    c.execute('UPDATE serials SET total_episodes = total_episodes + 1 WHERE code = ?', (serial_code,))
    conn.commit()
    conn.close()
    
    bot.send_message(msg.chat.id, f"✅ {episode_num}-qism muvaffaqiyatli qo'shildi!")

# ============= KINO OLISH =============
@bot.message_handler(func=lambda m: m.text == "🎬 Kino")
@check_sub_decorator
def movies_menu(msg):
    bot.send_message(msg.chat.id, "🔢 Film kodini kiriting:")
    bot.register_next_step_handler(msg, get_movie)

def get_movie(msg):
    code = msg.text.strip().upper()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM movies WHERE code = ?', (code,))
    movie = c.fetchone()
    
    if not movie:
        conn.close()
        bot.send_message(msg.chat.id, f"❌ `{code}` kodli film topilmadi!\n\n💡 Kodning to'g'riligini tekshiring.", parse_mode="Markdown")
        return
    
    # movie: 0:id, 1:code, 2:title, 3:type, 4:description, 5:file_id, 6:year, 7:country, 8:genre, 9:added_by, 10:added_date, 11:views
    
    # Statistika
    user_id = msg.from_user.id
    c.execute('INSERT INTO statistics VALUES (NULL, ?, ?, ?)',
              (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M")))
    c.execute('UPDATE movies SET views = views + 1 WHERE code = ?', (code,))
    conn.commit()
    conn.close()
    
    # Film ma'lumotlari
    movie_info = (
        f"🎬 *{movie[2]}*\n\n"
        f"📄 {movie[4]}\n"
        f"📅 Yil: {movie[6]}\n"
        f"🌍 Mamlakat: {movie[7]}\n"
        f"🎭 Janr: {movie[8]}\n"
        f"👁 Ko'rishlar: {movie[11] + 1}\n\n"
        f"⏳ Video yuborilmoqda..."
    )
    
    bot.send_message(msg.chat.id, movie_info, parse_mode="Markdown")
    
    # Videoni yuborish
    try:
        bot.send_video(msg.chat.id, movie[5], caption=f"🎬 {movie[2]}")
        bot.send_message(msg.chat.id, "✅ Film yuborildi! Yaxshi tomosha! 🍿")
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Video yuborishda xatolik: {e}")

# ============= SERIAL OLISH =============
@bot.message_handler(func=lambda m: m.text == "📺 Serial")
@check_sub_decorator
def serials_menu(msg):
    bot.send_message(msg.chat.id, "🔢 Serial kodini kiriting:")
    bot.register_next_step_handler(msg, get_serial)

def get_serial(msg):
    code = msg.text.strip().upper()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM serials WHERE code = ?', (code,))
    serial = c.fetchone()
    
    if not serial:
        conn.close()
        bot.send_message(msg.chat.id, f"❌ `{code}` kodli serial topilmadi!", parse_mode="Markdown")
        return
    
    c.execute('SELECT * FROM episodes WHERE serial_code = ? ORDER BY episode_number', (code,))
    episodes = c.fetchall()
    conn.close()
    
    if not episodes:
        bot.send_message(msg.chat.id, f"❌ Bu serialda hali qismlar yo'q!")
        return
    
    serial_info = (
        f"📺 *{serial[2]}*\n\n"
        f"📄 {serial[3]}\n"
        f"📊 Jami qismlar: {serial[4]}\n\n"
        f"Qaysi qismni ko'rmoqchisiz?"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = []
    for ep in episodes:
        buttons.append(types.InlineKeyboardButton(
            f"{ep[2]}", 
            callback_data=f"ep_{code}_{ep[2]}"
        ))
    
    markup.add(*buttons)
    bot.send_message(msg.chat.id, serial_info, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ep_"))
def send_episode(call):
    _, serial_code, ep_num = call.data.split("_")
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM episodes WHERE serial_code = ? AND episode_number = ?', 
              (serial_code, int(ep_num)))
    episode = c.fetchone()
    conn.close()
    
    if episode:
        try:
            bot.send_video(call.message.chat.id, episode[4], 
                          caption=f"📺 {serial_code} - {episode[3]}")
            bot.answer_callback_query(call.id, "✅ Yuborildi!")
        except:
            bot.answer_callback_query(call.id, "❌ Xatolik!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "❌ Qism topilmadi!", show_alert=True)

# ============= QIDIRUV =============
@bot.message_handler(func=lambda m: m.text == "🔍 Qidiruv")
@check_sub_decorator
def search_menu(msg):
    bot.send_message(msg.chat.id, "🔍 Film yoki serial nomini kiriting:")
    bot.register_next_step_handler(msg, search_content)

def search_content(msg):
    query = msg.text.strip().lower()
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT code, title FROM movies WHERE LOWER(title) LIKE ?', (f'%{query}%',))
    movies = c.fetchall()
    
    c.execute('SELECT code, title FROM serials WHERE LOWER(title) LIKE ?', (f'%{query}%',))
    serials = c.fetchall()
    
    conn.close()
    
    if not movies and not serials:
        bot.send_message(msg.chat.id, "❌ Hech narsa topilmadi!")
        return
    
    result = "🔍 *Qidiruv natijalari:*\n\n"
    
    if movies:
        result += "🎬 *Kinolar:*\n"
        for m in movies:
            result += f"• `{m[0]}` - {m[1]}\n"
        result += "\n"
    
    if serials:
        result += "📺 *Seriallar:*\n"
        for s in serials:
            result += f"• `{s[0]}` - {s[1]}\n"
    
    bot.send_message(msg.chat.id, result, parse_mode="Markdown")

# ============= BAN/UNBAN =============
@bot.message_handler(func=lambda m: m.text == "🚫 Ban/Unban")
@check_sub_decorator
def ban_menu(msg):
    if not is_admin(msg.from_user.id):
        return
    
    bot.send_message(msg.chat.id, "🆔 Foydalanuvchi ID raqamini kiriting:")
    bot.register_next_step_handler(msg, ban_user)

def ban_user(msg):
    try:
        user_id = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, "❌ ID raqam kiriting!")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        bot.send_message(msg.chat.id, "❌ Foydalanuvchi topilmadi!")
        return
    
    new_status = 0 if result[0] == 1 else 1
    c.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (new_status, user_id))
    conn.commit()
    conn.close()
    
    status_text = "bloklandi" if new_status == 1 else "blokdan chiqarildi"
    bot.send_message(msg.chat.id, f"✅ Foydalanuvchi {status_text}!")

# ============= STATISTIKA =============
@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
@check_sub_decorator
def show_statistics(msg):
    if not is_admin(msg.from_user.id):
        return
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
    banned_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM movies')
    total_movies = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM serials')
    total_serials = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM episodes')
    total_episodes = c.fetchone()[0]
    
    c.execute('SELECT SUM(views) FROM movies')
    total_views = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(*) FROM admins')
    total_admins = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM channels WHERE is_active = 1')
    active_channels = c.fetchone()[0]
    
    # Eng ko'p ko'rilgan filmlar
    c.execute('SELECT code, title, views FROM movies ORDER BY views DESC LIMIT 5')
    top_movies = c.fetchall()
    
    conn.close()
    
    stats = (
        f"📊 *BOT STATISTIKASI*\n\n"
        f"👥 Foydalanuvchilar:\n"
        f"  • Jami: {total_users}\n"
        f"  • Bloklangan: {banned_users}\n"
        f"  • Faol: {total_users - banned_users}\n\n"
        f"🎬 Kontent:\n"
        f"  • Kinolar: {total_movies}\n"
        f"  • Seriallar: {total_serials}\n"
        f"  • Qismlar: {total_episodes}\n\n"
        f"👁 Ko'rishlar: {total_views}\n"
        f"👮 Adminlar: {total_admins}\n"
        f"📢 Faol kanallar: {active_channels}\n\n"
        f"🏆 *TOP 5 Filmlar:*\n"
    )
    
    if top_movies:
        for i, movie in enumerate(top_movies, 1):
            stats += f"{i}. {movie[1]} - {movie[2]} ko'rish\n"
    else:
        stats += "_Hali ma'lumot yo'q_\n"
    
    bot.send_message(msg.chat.id, stats, parse_mode="Markdown")

# ============= REKLAMA =============
@bot.message_handler(func=lambda m: m.text == "📣 Reklama")
@check_sub_decorator
def broadcast_menu(msg):
    if not is_admin(msg.from_user.id):
        return
    
    bot.send_message(msg.chat.id, 
        "✍️ Barcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n"
        "💡 Rasm yoki video ham yuborishingiz mumkin.")
    bot.register_next_step_handler(msg, broadcast_message)

def broadcast_message(msg):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM users WHERE is_banned = 0')
    users = c.fetchall()
    conn.close()
    
    total = len(users)
    success = 0
    failed = 0
    
    bot.send_message(msg.chat.id, f"📤 {total} ta foydalanuvchiga yuborilmoqda...")
    
    for user in users:
        try:
            if msg.text:
                bot.send_message(user[0], f"📢 *ADMIN XABARI*\n\n{msg.text}", parse_mode="Markdown")
            elif msg.photo:
                bot.send_photo(user[0], msg.photo[-1].file_id, 
                              caption=msg.caption or "📢 ADMIN XABARI")
            elif msg.video:
                bot.send_video(user[0], msg.video.file_id, 
                              caption=msg.caption or "📢 ADMIN XABARI")
            success += 1
        except:
            failed += 1
    
    result = (
        f"✅ *Xabar yuborildi!*\n\n"
        f"📊 Natija:\n"
        f"✔️ Muvaffaqiyatli: {success}\n"
        f"❌ Xatolik: {failed}\n"
        f"📈 Jami: {total}"
    )
    bot.send_message(msg.chat.id, result, parse_mode="Markdown")

# ============= TAHRIRLASH =============
@bot.message_handler(func=lambda m: m.text == "✏️ Tahrirlash")
@check_sub_decorator
def edit_menu(msg):
    if not is_admin(msg.from_user.id):
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("✏️ Kino tahrirlash")
    markup.row("🔙 Orqaga")
    
    bot.send_message(msg.chat.id, "Tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "✏️ Kino tahrirlash")
@check_sub_decorator
def edit_movie_start(msg):
    if not is_admin(msg.from_user.id):
        return
    
    bot.send_message(msg.chat.id, "🔢 Film kodini kiriting:")
    bot.register_next_step_handler(msg, edit_movie_show)

def edit_movie_show(msg):
    code = msg.text.strip().upper()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM movies WHERE code = ?', (code,))
    movie = c.fetchone()
    conn.close()
    
    if not movie:
        bot.send_message(msg.chat.id, f"❌ {code} kodli film topilmadi!")
        return
    
    movie_info = (
        f"🎬 *Joriy ma'lumotlar:*\n\n"
        f"🆔 Kod: `{movie[1]}`\n"
        f"📝 Nomi: {movie[2]}\n"
        f"📄 Tavsif: {movie[4]}\n\n"
        f"Nimani o'zgartirmoqchisiz?"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📝 Nomi", callback_data=f"edit_title_{code}"))
    markup.add(types.InlineKeyboardButton("📄 Tavsif", callback_data=f"edit_desc_{code}"))
    
    bot.send_message(msg.chat.id, movie_info, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def edit_movie_field(call):
    parts = call.data.split("_")
    field = parts[1]
    code = parts[2]
    
    field_names = {"title": "Nomi", "desc": "Tavsif"}
    
    bot.send_message(call.message.chat.id, f"✍️ Yangi {field_names[field]} kiriting:")
    bot.register_next_step_handler(call.message, lambda m: update_movie_field(m, code, field))
    bot.answer_callback_query(call.id)

def update_movie_field(msg, code, field):
    new_value = msg.text.strip()
    
    conn = get_db()
    c = conn.cursor()
    
    field_map = {"title": "title", "desc": "description"}
    db_field = field_map[field]
    
    c.execute(f'UPDATE movies SET {db_field} = ? WHERE code = ?', (new_value, code))
    conn.commit()
    conn.close()
    
    bot.send_message(msg.chat.id, f"✅ `{code}` kodi yangilandi!", parse_mode="Markdown")

# ============= O'CHIRISH =============
@bot.message_handler(func=lambda m: m.text == "🗑 O'chirish")
@check_sub_decorator
def delete_menu(msg):
    if not is_admin(msg.from_user.id):
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🗑 Kino o'chirish", "🗑 Serial o'chirish")
    markup.row("🔙 Orqaga")
    
    bot.send_message(msg.chat.id, "Tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🗑 Kino o'chirish")
@check_sub_decorator
def delete_movie_start(msg):
    if not is_admin(msg.from_user.id):
        return
    
    bot.send_message(msg.chat.id, "🔢 O'chiriladigan film kodini kiriting:")
    bot.register_next_step_handler(msg, delete_movie)

def delete_movie(msg):
    code = msg.text.strip().upper()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT title FROM movies WHERE code = ?', (code,))
    movie = c.fetchone()
    
    if not movie:
        conn.close()
        bot.send_message(msg.chat.id, f"❌ {code} kodli film topilmadi!")
        return
    
    c.execute('DELETE FROM movies WHERE code = ?', (code,))
    c.execute('DELETE FROM statistics WHERE movie_code = ?', (code,))
    conn.commit()
    conn.close()
    
    bot.send_message(msg.chat.id, f"✅ '{movie[0]}' (`{code}`) o'chirildi!", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑 Serial o'chirish")
@check_sub_decorator
def delete_serial_start(msg):
    if not is_admin(msg.from_user.id):
        return
    
    bot.send_message(msg.chat.id, "🔢 Serial kodini kiriting:")
    bot.register_next_step_handler(msg, delete_serial)

def delete_serial(msg):
    code = msg.text.strip().upper()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT title FROM serials WHERE code = ?', (code,))
    serial = c.fetchone()
    
    if not serial:
        conn.close()
        bot.send_message(msg.chat.id, f"❌ Serial topilmadi!")
        return
    
    c.execute('DELETE FROM serials WHERE code = ?', (code,))
    c.execute('DELETE FROM episodes WHERE serial_code = ?', (code,))
    conn.commit()
    conn.close()
    
    bot.send_message(msg.chat.id, f"✅ '{serial[0]}' va barcha qismlari o'chirildi!")

# ============= MA'LUMOT =============
@bot.message_handler(func=lambda m: m.text == "ℹ️ Ma'lumot")
@check_sub_decorator
def info_menu(msg):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM movies')
    movies_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM serials')
    serials_count = c.fetchone()[0]
    conn.close()
    
    info = (
        f"ℹ️ *Kino Yuklovchi BOT haqida*\n\n"
        f"🎬 Minglab kino va seriallarni bepul ko'ring!\n\n"
        f"📊 *Bizda:*\n"
        f"• {movies_count} ta kino\n"
        f"• {serials_count} ta serial\n\n"
        f"💡 *Foydalanish:*\n"
        f"1️⃣ Film kodini kiriting\n"
        f"2️⃣ Yoki qidiruv qiling\n"
        f"3️⃣ Tomosha qiling!\n\n"
        f"👨‍💻 Murojaat: @AdminUsername"
    )
    
    bot.send_message(msg.chat.id, info, parse_mode="Markdown")

# ============= ORQAGA =============
@bot.message_handler(func=lambda m: m.text == "🔙 Orqaga")
@check_sub_decorator
def back_handler(msg):
    if is_admin(msg.from_user.id):
        admin_panel(msg)
    else:
        start(msg)

# ============= XATOLIKLARNI USHLASH =============
@bot.message_handler(content_types=['document', 'audio', 'photo', 'sticker', 'voice'])
def handle_other_content(msg):
    bot.send_message(msg.chat.id, 
        "❌ Iltimos, tugmalardan foydalaning yoki film kodini kiriting.")

# ============= BOTNI ISHGA TUSHIRISH =============
if __name__ == "__main__":
    print("="*60)
    print("🤖 Kino Yuklovchi BOT ishga tushdi!")
    print(f"👑 Asosiy Admin ID: {MAIN_ADMIN_ID}")
    print(f"💾 Database: triokino.db")
    print("="*60)
    print("\n✅ Bot ishlayapti...\n")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"\n❌ Xatolik: {e}")