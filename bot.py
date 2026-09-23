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
BOT_TOKEN = "8937376122:AAGANyLhdJLZyOZNVr62MaJ-OHxn7Avn6T0"
ADMIN_ID = 8671410379

CHANNELS = [
    {"chat_id": -1004447562202, "link": "https://t.me/Ox2MODS", "name": "Join 1"},
    {"chat_id": -1004374951317, "link": "https://t.me/Ox1MODS", "name": "Join 2"},
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
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    username TEXT
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

# Table to track broadcasted ads so they can be deleted later
cursor.execute("""
CREATE TABLE IF NOT EXISTS sent_ads (
    ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message_id INTEGER
)
""")

# Table to store the currently active ad for new/returning users
cursor.execute("""
CREATE TABLE IF NOT EXISTS active_ad (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER,
    message_id INTEGER,
    custom_text TEXT
)
""")
conn.commit()

# In-memory caches for multi-step admin flows
upload_cache = {}
ad_cache = {}

# ================= ADMIN KEYBOARD =================
def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_upload = types.KeyboardButton("📤 Upload File")
    btn_files = types.KeyboardButton("📁 File Library")
    btn_delete = types.KeyboardButton("🗑️ Delete File")
    btn_broadcast = types.KeyboardButton("📢 Broadcast")
    btn_ads = types.KeyboardButton("📢 Ads System")
    btn_user_info = types.KeyboardButton("ℹ️ User Info")
    btn_info = types.KeyboardButton("🛠 Admin Guide")
    
    markup.add(btn_upload, btn_files)
    markup.add(btn_delete, btn_broadcast)
    markup.add(btn_ads, btn_user_info)
    markup.add(btn_info)
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

# ================= DELAYED AD SENDER (20 SECONDS) =================
def send_delayed_ad(user_id, delay_seconds=20):
    time.sleep(delay_seconds)
    try:
        cursor.execute("SELECT chat_id, message_id, custom_text FROM active_ad WHERE id = 1")
        active = cursor.fetchone()
        if active:
            src_chat_id, src_msg_id, custom_txt = active
            if custom_txt:
                sent_msg = bot.send_message(user_id, custom_txt)
            else:
                sent_msg = bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=src_chat_id,
                    message_id=src_msg_id
                )
            # Record it in sent_ads so Admin can delete it later if needed
            cursor.execute("INSERT INTO sent_ads (user_id, message_id) VALUES (?, ?)", (user_id, sent_msg.message_id))
            conn.commit()
    except Exception:
        pass

# ================= HELPER FUNCTIONS =================
def register_user(user):
    user_id = user.id
    first_name = user.first_name or "Unknown"
    username = f"@{user.username}" if user.username else "No Username"
    
    cursor.execute("""
    INSERT INTO users (user_id, first_name, username) 
    VALUES (?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET 
        first_name=excluded.first_name,
        username=excluded.username
    """, (user_id, first_name, username))
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
    user = message.from_user
    register_user(user)

    # Admin Panel
    if user.id == ADMIN_ID:
        bot.send_message(
            ADMIN_ID,
            "👑 Welcome Boss! Admin Dashboard is active. Manage your tasks using the buttons below:",
            reply_markup=get_admin_keyboard()
        )
        return

    # User ke liye 20 second ke delay ke baad active ad bhejne ka background thread
    threading.Thread(target=send_delayed_ad, args=(user.id, 20), daemon=True).start()

    # Normal user file query
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("file_"):
        file_db_id = args[1].replace("file_", "")
        
        if not is_subscribed(user.id):
            bot.send_message(
                user.id,
                "🔒 **Access Locked!**\n\n"
                "Please join all our official channels below to unlock and receive your file instantly.\n"
                "After joining all of them, tap the **Verify & Access File** button.",
                reply_markup=get_force_sub_markup(file_db_id)
            )
            return

        deliver_file(user.id, file_db_id)
    else:
        bot.send_message(
            user.id,
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

# ================= ADMIN ACTION: USER INFO =================
@bot.message_handler(func=lambda msg: msg.text in ["ℹ️ User Info", "/users"])
def show_users_info(message):
    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT user_id, first_name, username FROM users")
    records = cursor.fetchall()
    total_users = len(records)

    if total_users == 0:
        bot.send_message(ADMIN_ID, "👥 Total Active Users: `0`\nNo users found in database.")
        return

    header = f"👥 **Total Active Users:** `{total_users}`\n\n📋 **User List:**\n"
    current_chunk = header

    for uid, name, uname in records:
        entry = f"• **ID:** `{uid}` | **Name:** {name} | **User:** {uname}\n"
        if len(current_chunk) + len(entry) > 4000:
            bot.send_message(ADMIN_ID, current_chunk, parse_mode="Markdown")
            current_chunk = entry
        else:
            current_chunk += entry

    if current_chunk:
        bot.send_message(ADMIN_ID, current_chunk, parse_mode="Markdown")

# ================= ADMIN ACTION: ADS SYSTEM =================
@bot.message_handler(func=lambda msg: msg.text in ["📢 Ads System", "/ads"])
def ads_menu(message):
    if message.from_user.id != ADMIN_ID:
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 Upload Ad", callback_data="ad_action_upload"),
        types.InlineKeyboardButton("🗑️ Delete Ad", callback_data="ad_action_delete")
    )
    bot.send_message(
        ADMIN_ID,
        "📢 **Ads Control Panel**\n\nChoose an action below to post an advertisement or delete the previously posted ad:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ["ad_action_upload", "ad_action_delete"])
def handle_ads_panel(call):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "ad_action_upload":
        bot.send_message(ADMIN_ID, "📤 Send your ad content now (Text, Photo, Video, Document, Link, or Audio):")
        bot.register_next_step_handler(call.message, capture_ad_content)

    elif call.data == "ad_action_delete":
        cursor.execute("SELECT user_id, message_id FROM sent_ads")
        ads_to_remove = cursor.fetchall()

        if not ads_to_remove:
            # Active ad table bhi clear kar dete hain
            cursor.execute("DELETE FROM active_ad WHERE id = 1")
            conn.commit()
            bot.send_message(ADMIN_ID, "⚠️ No active broadcasted ads found to delete.")
            return

        bot.send_message(ADMIN_ID, f"⏳ Removing ad from {len(ads_to_remove)} user chats...")
        deleted_count = 0

        for uid, mid in ads_to_remove:
            try:
                bot.delete_message(chat_id=uid, message_id=mid)
                deleted_count += 1
            except Exception:
                pass

        # Clear both sent list and currently active ad
        cursor.execute("DELETE FROM sent_ads")
        cursor.execute("DELETE FROM active_ad WHERE id = 1")
        conn.commit()
        bot.send_message(ADMIN_ID, f"✅ Done! Ad deleted from {deleted_count} active chats and removed from new user queue.")

def capture_ad_content(message):
    if message.from_user.id != ADMIN_ID:
        return

    ad_cache[ADMIN_ID] = {
        "message_id": message.message_id,
        "chat_id": message.chat.id,
        "custom_text": None
    }

    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("🌐 Publish", callback_data="ad_btn_publish"),
        types.InlineKeyboardButton("✏️ Edit", callback_data="ad_btn_edit"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="ad_btn_cancel")
    )

    bot.send_message(
        ADMIN_ID,
        "📢 Ad captured successfully! What would you like to do?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ["ad_btn_publish", "ad_btn_edit", "ad_btn_cancel"])
def handle_ad_lifecycle(call):
    if call.from_user.id != ADMIN_ID:
        return

    action = call.data
    cached = ad_cache.get(ADMIN_ID)

    if action == "ad_btn_cancel":
        ad_cache.pop(ADMIN_ID, None)
        bot.edit_message_text("❌ Ad creation cancelled.", ADMIN_ID, call.message.message_id)

    elif action == "ad_btn_edit":
        msg = bot.send_message(ADMIN_ID, "✏️ Send the modified text/caption for this ad:")
        bot.register_next_step_handler(msg, edit_ad_text)

    elif action == "ad_btn_publish":
        if not cached:
            bot.send_message(ADMIN_ID, "❌ Session expired. Please send your ad again.")
            return

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        bot.send_message(ADMIN_ID, f"🚀 Publishing ad to {len(users)} users...")

        sent_records = []
        custom_txt = cached.get("custom_text")

        for (uid,) in users:
            try:
                if custom_txt:
                    sent_msg = bot.send_message(uid, custom_txt)
                else:
                    sent_msg = bot.copy_message(
                        chat_id=uid,
                        from_chat_id=cached["chat_id"],
                        message_id=cached["message_id"]
                    )
                sent_records.append((uid, sent_msg.message_id))
            except Exception:
                pass

        # Purana ad record clear karke naya track karte hain
        cursor.execute("DELETE FROM sent_ads")
        cursor.executemany("INSERT INTO sent_ads (user_id, message_id) VALUES (?, ?)", sent_records)

        # Active Ad table me store karte hain taaki naye users ko 20 second bad yahi ad mile
        cursor.execute("""
        INSERT INTO active_ad (id, chat_id, message_id, custom_text) 
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET 
            chat_id=excluded.chat_id,
            message_id=excluded.message_id,
            custom_text=excluded.custom_text
        """, (cached["chat_id"], cached["message_id"], custom_txt))
        
        conn.commit()
        ad_cache.pop(ADMIN_ID, None)
        bot.send_message(ADMIN_ID, f"✅ Ad published to {len(sent_records)} users and set active for all /start users after 20 seconds!")

def edit_ad_text(message):
    if message.from_user.id != ADMIN_ID:
        return
    if ADMIN_ID in ad_cache:
        ad_cache[ADMIN_ID]["custom_text"] = message.text

        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("🌐 Publish", callback_data="ad_btn_publish"),
            types.InlineKeyboardButton("✏️ Edit", callback_data="ad_btn_edit"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="ad_btn_cancel")
        )
        bot.send_message(ADMIN_ID, f"Updated Ad Text:\n\n\"{message.text}\"\n\nChoose an action:", reply_markup=markup)

# ================= ADMIN ACTIONS: FILE MANAGEMENT =================
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
    bot.send_message(ADMIN_ID, f"✅ File `{row[0]}` (ID: {file_id_input}) has been permanently deleted.")

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

# ================= BROADCAST ANY CONTENT =================
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

# ================= ADMIN GUIDE =================
@bot.message_handler(func=lambda msg: msg.text in ["🛠 Admin Guide", "/com"])
def admin_commands_info(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = (
        "🛠 **Admin Guide & Controls:**\n\n"
        "• 📤 **Upload File** - Upload any file to generate a 30-min timer direct link.\n"
        "• 📁 **File Library** - View all files currently saved with their IDs.\n"
        "• 🗑️ **Delete File** - Delete any file permanently from the database.\n"
        "• 📢 **Broadcast** - Direct broadcast of media/text to all users.\n"
        "• 📢 **Ads System** - Upload ads with Publish/Edit/Cancel buttons or Delete active ads.\n"
        "• ℹ️ **User Info** - View active users count along with User ID, Name, and Username.\n"
        "• ⏱️ **Auto-Ad** - Active ads are automatically delivered to users 20s after `/start`.\n"
        "• 🛠 **Admin Guide** - View this instructions panel."
    )
    bot.send_message(ADMIN_ID, text, parse_mode="Markdown")

# ================= RUN BOT =================
if __name__ == "__main__":
    print("Bot is up and running...")
    bot.infinity_polling(skip_pending=True)
