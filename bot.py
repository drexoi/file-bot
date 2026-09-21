import sqlite3
from telebot import TeleBot, types

# ================= CONFIGURATION =================
BOT_TOKEN = "8937376122:AAEhnyFiFczW-L5xVco5j-9rsjW3RU9j1QY"
ADMIN_ID = 8671410379

CHANNELS = [
    {"chat_id": -1004447562202, "link": "https://t.me/+cJt33a-UDCw5YmVl", "name": "Ox1"},
    {"chat_id": -1004374951317, "link": "https://t.me/+HkOcx5kbh01iZTE1", "name": "Ox2"},
    {"chat_id": -1004291249317, "link": "https://t.me/OxRehanCyber", "name": "Cyber Ox"},
    {"chat_id": -1003782903063, "link": "https://t.me/+852hkOgj0UNlZGU9", "name": "OX MODS"}
]

FOOTER_TEXT = "\n\nany issues / feedback @OxRehann"

bot = TeleBot(BOT_TOKEN)

# ================= DATABASE SETUP =================
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    file_name TEXT,
    file_type TEXT
)
""")
conn.commit()

# Temporary upload buffer for admin actions
upload_cache = {}

# ================= HELPER FUNCTIONS =================
def register_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def is_subscribed(user_id):
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch["chat_id"], user_id)
            if member.status not in ["member", "administrator", "creator", "restricted"]:
                return False
        except Exception:
            return False
    return True

def get_force_sub_markup(file_id=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in CHANNELS:
        markup.add(types.InlineKeyboardButton(f"Join {ch['name']}", url=ch["link"]))
    
    cb_data = f"check_{file_id}" if file_id else "check_home"
    markup.add(types.InlineKeyboardButton("🔄 Joined / Verify", callback_data=cb_data))
    return markup

# ================= USER HANDLERS =================
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    register_user(user_id)

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("file_"):
        file_db_id = args[1].replace("file_", "")
        
        if not is_subscribed(user_id):
            bot.send_message(
                user_id,
                "⚠️ **Access Denied!**\n\nPehle niche diye gaye sabhi channels ko join karein, fir verify button par click karein:",
                parse_mode="Markdown",
                reply_markup=get_force_sub_markup(file_db_id)
            )
            return

        deliver_file(user_id, file_db_id)
    else:
        bot.send_message(
            user_id,
            "👋 Welcome! Link ke zariye aakar aap files download kar sakte hain."
        )

def deliver_file(user_id, file_db_id):
    cursor.execute("SELECT file_id, file_name, file_type FROM files WHERE id = ?", (file_db_id,))
    data = cursor.fetchone()
    if not data:
        bot.send_message(user_id, "❌ File not found or has expired.")
        return

    f_id, f_name, f_type = data
    caption = (
        f"📁 **File:** `{f_name}`\n\n"
        "⚠️ Please download your file as soon as possible. "
        "Due to copyright issues, this file will be deleted within 30 minutes."
        f"{FOOTER_TEXT}"
    )

    if f_type == "document":
        bot.send_document(user_id, f_id, caption=caption, parse_mode="Markdown")
    elif f_type == "video":
        bot.send_video(user_id, f_id, caption=caption, parse_mode="Markdown")
    elif f_type == "audio":
        bot.send_audio(user_id, f_id, caption=caption, parse_mode="Markdown")
    elif f_type == "photo":
        bot.send_photo(user_id, f_id, caption=caption, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def verify_subscription(call):
    user_id = call.from_user.id
    data = call.data.replace("check_", "")
    
    if is_subscribed(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        if data != "home":
            deliver_file(user_id, data)
        else:
            bot.send_message(user_id, "✅ Verification successful!")
    else:
        bot.answer_callback_query(call.id, "❌ Sabhi channels join nahi kiye gaye hain!", show_alert=True)

# ================= ADMIN HANDLERS =================
@bot.message_handler(commands=['com'])
def admin_commands(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = (
        "🛠 **Admin Command Panel:**\n\n"
        "• `/upl` - File upload karke direct link generate karein\n"
        "• `/sel` - Database ki sabhi saved files ki numbered list dekhein\n"
        "• `/all <message>` - Sabhi registered users ko broadcast message bhejein\n"
        "• `/com` - Command list aur unka use dekhein"
    )
    bot.send_message(ADMIN_ID, text, parse_mode="Markdown")

@bot.message_handler(commands=['all'])
def broadcast_message(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        bot.send_message(ADMIN_ID, "⚠️ Format: `/all Message yahan likhein`", parse_mode="Markdown")
        return

    broadcast_text = parts[1]
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent, failed = 0, 0
    bot.send_message(ADMIN_ID, f"⏳ Broadcasting to {len(users)} users...")

    for (uid,) in users:
        try:
            bot.send_message(uid, broadcast_text)
            sent += 1
        except Exception:
            failed += 1

    bot.send_message(ADMIN_ID, f"✅ Broadcast done.\nSent: `{sent}`\nFailed: `{failed}`", parse_mode="Markdown")

@bot.message_handler(commands=['sel'])
def list_files(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT id, file_name FROM files ORDER BY id ASC")
    records = cursor.fetchall()
    
    if not records:
        bot.send_message(ADMIN_ID, "📂 Database me koi file nahi hai.")
        return

    text = "📁 **Uploaded Files List:**\n\n"
    for fid, fname in records:
        text += f"{fid}. {fname}\n"

    bot.send_message(ADMIN_ID, text)

@bot.message_handler(commands=['upl'])
def upload_prompt(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "📤 Kripya file (Document, Video, Audio ya Photo) send karein:")
    bot.register_next_step_handler(msg, process_admin_file)

def process_admin_file(message):
    if message.from_user.id != ADMIN_ID:
        return

    f_id, f_name, f_type = None, "Untitled", "document"

    if message.document:
        f_id = message.document.file_id
        f_name = message.document.file_name or "Document"
        f_type = "document"
    elif message.video:
        f_id = message.video.file_id
        f_name = message.video.file_name or "Video"
        f_type = "video"
    elif message.audio:
        f_id = message.audio.file_id
        f_name = message.audio.file_name or "Audio"
        f_type = "audio"
    elif message.photo:
        f_id = message.photo[-1].file_id
        f_name = "Photo"
        f_type = "photo"
    else:
        bot.send_message(ADMIN_ID, "❌ Koi file detect nahi hui. Process cancel.")
        return

    upload_cache[ADMIN_ID] = {"file_id": f_id, "file_name": f_name, "file_type": f_type}

    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🌐 Public", callback_data="btn_public"),
        types.InlineKeyboardButton("✏️ Edit", callback_data="btn_edit"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="btn_cancel")
    )

    bot.send_message(
        ADMIN_ID,
        f"File: `{f_name}`\n\nAap kya karna chahte hain?",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ["btn_public", "btn_edit", "btn_cancel"])
def handle_file_action(call):
    if call.from_user.id != ADMIN_ID:
        return

    action = call.data
    cached = upload_cache.get(ADMIN_ID)

    if action == "btn_cancel":
        upload_cache.pop(ADMIN_ID, None)
        bot.edit_message_text("❌ Upload cancel kar diya gaya.", ADMIN_ID, call.message.message_id)

    elif action == "btn_edit":
        msg = bot.send_message(ADMIN_ID, "✏️ Naya file name likhkar bhejein:")
        bot.register_next_step_handler(msg, rename_file)

    elif action == "btn_public":
        if not cached:
            bot.send_message(ADMIN_ID, "❌ Session expire ho gaya.")
            return

        cursor.execute(
            "INSERT INTO files (file_id, file_name, file_type) VALUES (?, ?, ?)",
            (cached["file_id"], cached["file_name"], cached["file_type"])
        )
        conn.commit()
        db_id = cursor.lastrowid
        upload_cache.pop(ADMIN_ID, None)

        bot_username = bot.get_me().username
        direct_link = f"https://t.me/{bot_username}?start=file_{db_id}"

        response_text = (
            f"✅ **File Published!**\n\n"
            f"📁 **Name:** `{cached['file_name']}`\n"
            f"🔗 **Download Link:** {direct_link}\n\n"
            f"⚠️ Please download your file as soon as possible. "
            f"Due to copyright issues, this file will be deleted within 30 minutes."
            f"{FOOTER_TEXT}"
        )
        bot.edit_message_text(response_text, ADMIN_ID, call.message.message_id, parse_mode="Markdown")

def rename_file(message):
    if message.from_user.id != ADMIN_ID:
        return
    new_name = message.text.strip()
    if ADMIN_ID in upload_cache:
        upload_cache[ADMIN_ID]["file_name"] = new_name
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("🌐 Public", callback_data="btn_public"),
            types.InlineKeyboardButton("✏️ Edit", callback_data="btn_edit"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="btn_cancel")
        )
        bot.send_message(ADMIN_ID, f"Updated Name: `{new_name}`\nAb select karein:", parse_mode="Markdown", reply_markup=markup)

# ================= RUN BOT =================
if __name__ == "__main__":
    print("Bot is starting...")
    bot.infinity_polling(skip_pending=True)
