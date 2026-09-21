import os
import time
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot import TeleBot, types

# ================= DUMMY WEB SERVER (RENDER & UPTIMEROBOT) =================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is operational and running!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ================= CONFIGURATION =================
BOT_TOKEN = "8937376122:AAEhnyFiFczW-L5xVco5j-9rsjW3RU9j1QY"
ADMIN_ID = 8671410379

CHANNELS = [
    {"chat_id": -1004447562202, "link": "https://t.me/+cJt33a-UDCw5YmVl", "name": "Join 1"},
    {"chat_id": -1004374951317, "link": "https://t.me/+HkOcx5kbh01iZTE1", "name": "Join 2"},
    {"chat_id": -1004291249317, "link": "https://t.me/OxRehanCyber", "name": "Join 3"},
    {"chat_id": -1003782903063, "link": "https://t.me/+852hkOgj0UNlZGU9", "name": "Join 4"}
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

upload_cache = {}

# ================= ADMIN KEYBOARD =================
def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_upload = types.KeyboardButton("📤 Upload File")
    btn_files = types.KeyboardButton("📁 File Library")
    btn_delete = types.KeyboardButton("🗑️ Delete File")
    btn_users = types.KeyboardButton("👥 Total Users")
    btn_broadcast = types.KeyboardButton("📢 Broadcast")
    btn_info = types.KeyboardButton("ℹ️ Admin Guide")
    
    markup.add(btn_upload, btn_files)
    markup.add(btn_delete, btn_users)
    markup.add(btn_broadcast, btn_info)
    return markup

# ================= AUTO DELETE FUNCTION =================
def auto_delete_file(chat_id, message_id, delay_seconds=1800):
    time.sleep(delay_seconds)
    try:
        bot.delete_message(chat_id, message_id)
        bot.send_message(
            chat_id,
            "⚠️ Notice: The requested file has been automatically removed to respect copyright policies."
        )
    except Exception:
        pass

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
    # 2 buttons per row side-by-side
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    b1 = types.InlineKeyboardButton("🔹 Join 1", url=CHANNELS[0]["link"])
    b2 = types.InlineKeyboardButton("🔸 Join 2", url=CHANNELS[1]["link"])
    b3 = types.InlineKeyboardButton("⚡ Join 3", url=CHANNELS[2]["link"])
    b4 = types.InlineKeyboardButton("👑 Join 4", url=CHANNELS[3]["link"])
    
    markup.add(b1, b2)
    markup.add(b3, b4)
    
    cb_data = f"check_{file_id}" if file_id else "check_home"
    markup.add(types.InlineKeyboardButton("✅ Verify & Access File", callback_data=cb_data))
    return markup

# ================= USER / GENERAL HANDLERS =================
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    register_user(user_id)

    if user_id == ADMIN_ID:
        bot.send_message(
            ADMIN_ID,
            "👑 Welcome Boss! Admin Dashboard is active. Manage your tasks using the quick buttons below:",
            reply_markup=get_admin_keyboard()
        )
        return

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("file_"):
        file_db_id = args[1].replace("file_", "")
        
        if not is_subscribed(user_id):
            bot.send_message(
                user_id,
                "🔒 **Access Locked!**\n\n"
                "Please join all our official channels below to unlock and receive your file instantly.\n"
                "After joining all of them, tap the **Verify & Access File** button.",
                reply_markup=get_force_sub_markup(file_db_id)
            )
            return

        deliver_file(user_id, file_db_id)
    else:
        bot.send_message(
            user_id,
            "👋 Welcome! Send or click on a valid download link to access your files directly.",
            reply_markup=types.ReplyKeyboardRemove()
        )

def deliver_file(user_id, file_db_id):
    cursor.execute("SELECT file_id, file_name, file_type FROM files WHERE id = ?", (file_db_id,))
    data = cursor.fetchone()
    if not data:
        bot.send_message(user_id, "❌ Error: The requested file could not be found or has expired.")
        return

    f_id, f_name, f_type = data
    caption = (
        f"📁 File Name: {f_name}\n\n"
        "⚠️ Important: Please download or forward this file immediately. "
        "Due to copyright rules, it will be automatically deleted in 30 minutes."
        f"{FOOTER_TEXT}"
    )

    msg = None
    if f_type == "document":
        msg = bot.send_document(user_id, f_id, caption=caption)
    elif f_type == "video":
        msg = bot.send_video(user_id, f_id, caption=caption)
    elif f_type == "audio":
        msg = bot.send_audio(user_id, f_id, caption=caption)
    elif f_type == "photo":
        msg = bot.send_photo(user_id, f_id, caption=caption)

    if msg:
        threading.Thread(target=auto_delete_file, args=(user_id, msg.message_id, 1800), daemon=True).start()

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def verify_subscription(call):
    user_id = call.from_user.id
    data = call.data.replace("check_", "")
    
    if is_subscribed(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

        if data != "home":
            deliver_file(user_id, data)
        else:
            bot.send_message(user_id, "✅ Verification confirmed! Access unlocked.")
    else:
        bot.answer_callback_query(
            call.id,
            "⚠️ Access Denied!\n\nYou have not joined all 4 required channels yet. Please join all of them and try again.",
            show_alert=True
        )

# ================= ADMIN ACTIONS =================
@bot.message_handler(func=lambda msg: msg.text in ["👥 Total Users", "/users"])
def total_users_count(message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    bot.send_message(ADMIN_ID, f"👥 **Total Registered Users:** `{count}`", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text in ["🗑️ Delete File", "/delete"])
def prompt_delete_file(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "🗑️ Send the **File Number/ID** you wish to permanently delete:")
    bot.register_next_step_handler(msg, process_delete_file)

def process_delete_file(message):
    if message.from_user.id != ADMIN_ID:
        return
    file_id_input = message.text.strip()
    if not file_id_input.isdigit():
        bot.send_message(ADMIN_ID, "❌ Invalid input. Please send a valid numeric File ID.")
        return

    cursor.execute("SELECT file_name FROM files WHERE id = ?", (file_id_input,))
    row = cursor.fetchone()
    if not row:
        bot.send_message(ADMIN_ID, f"❌ No file found with ID: `{file_id_input}`")
        return

    cursor.execute("DELETE FROM files WHERE id = ?", (file_id_input,))
    conn.commit()
    bot.send_message(ADMIN_ID, f"✅ File `{row[0]}` (ID: {file_id_input}) has been deleted successfully.")

@bot.message_handler(func=lambda msg: msg.text in ["📤 Upload File", "/upl"])
def upload_prompt(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "📤 Send the media file (Document, Video, Audio, or Photo) you wish to host:")
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
        bot.send_message(ADMIN_ID, "❌ No valid file detected. Upload session terminated.")
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
        f"Selected File: {f_name}\n\nChoose an action:",
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
        bot.edit_message_text("❌ Upload action has been cancelled.", ADMIN_ID, call.message.message_id)

    elif action == "btn_edit":
        msg = bot.send_message(ADMIN_ID, "✏️ Enter the new display name for this file:")
        bot.register_next_step_handler(msg, rename_file)

    elif action == "btn_public":
        if not cached:
            bot.send_message(ADMIN_ID, "❌ Session expired. Please upload again.")
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
            f"✅ File Published Successfully!\n\n"
            f"📁 File: {cached['file_name']}\n"
            f"🔗 Download Link: {direct_link}\n\n"
            f"⚠️ Notice: Please download your file as soon as possible. "
            f"Due to copyright issues, this file will be deleted within 30 minutes."
            f"{FOOTER_TEXT}"
        )
        bot.edit_message_text(response_text, ADMIN_ID, call.message.message_id)

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
        bot.send_message(ADMIN_ID, f"Updated Name: {new_name}\n\nChoose an action:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["📁 File Library", "/sel"])
def list_files(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT id, file_name FROM files ORDER BY id ASC")
    records = cursor.fetchall()
    
    if not records:
        bot.send_message(ADMIN_ID, "📂 The file database is currently empty.")
        return

    text = "📁 Uploaded Files Library:\n\n"
    for fid, fname in records:
        text += f"{fid}. {fname}\n"

    bot.send_message(ADMIN_ID, text)

@bot.message_handler(func=lambda msg: msg.text in ["📢 Broadcast", "/all"])
def prompt_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(
        ADMIN_ID,
        "📢 Send the content you want to broadcast.\n\nYou can send Text, Photo, Video, Document, or Audio:"
    )
    bot.register_next_step_handler(msg, send_broadcast_all)

def send_broadcast_all(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent, failed = 0, 0
    bot.send_message(ADMIN_ID, f"⏳ Broadcasting message to {len(users)} registered users...")

    for (uid,) in users:
        try:
            bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
        except Exception:
            failed += 1

    bot.send_message(ADMIN_ID, f"✅ Broadcast Finished!\n\nSuccessfully Delivered: {sent}\nFailed / Blocked: {failed}")

@bot.message_handler(func=lambda msg: msg.text in ["ℹ️ Admin Guide", "/com"])
def admin_commands_info(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = (
        "🛠 Admin Guide & Controls:\n\n"
        "• 📤 Upload File - Upload any file to generate a 30-min timer direct link.\n"
        "• 📁 File Library - View all files currently saved with their IDs.\n"
        "• 🗑️ Delete File - Delete any file permanently from the database.\n"
        "• 👥 Total Users - Check the total number of users who started the bot.\n"
        "• 📢 Broadcast - Send text, media, or files to all users.\n"
        "• ℹ️ Admin Guide - View this instructions panel."
    )
    bot.send_message(ADMIN_ID, text)

# ================= RUN BOT =================
if __name__ == "__main__":
    print("Bot is up and running...")
    bot.infinity_polling(skip_pending=True)
        
