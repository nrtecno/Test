import os, time, glob, threading
import yt_dlp
import telebot
from telebot import types
from flask import Flask, request

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
CHANNEL_USERNAME = "@nrtecno2"
CHANNEL_LINK = "https://t.me/nrtecno2"

app = Flask(__name__)
user_links = {}

def is_user_joined(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ['member', 'administrator', 'creator']
    except:
        return False

def find_cookie_file():
    possible_paths = ["cookies.txt", "./cookies.txt", "/etc/secrets/cookies.txt", "/opt/render/project/src/cookies.txt", os.path.join(os.getcwd(), "cookies.txt")]
    for p in possible_paths:
        if os.path.exists(p):
            print(f"COOKIE FOUND AT: {p}")
            return p
    print("COOKIE NOT FOUND")
    return None

def get_ydl_opts(quality, url=""):
    cookie_path = find_cookie_file()
    is_insta = "instagram.com" in url
    opts = {
        'quiet': False,
        'no_warnings': False,
        'outtmpl': '%(id)s.%(ext)s',
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    if cookie_path:
        opts['cookiefile'] = cookie_path

    if is_insta:
        opts['format'] = "best"
    elif quality == "yt_mp3":
        opts['format'] = "bestaudio/best"
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        opts['format'] = "best"
    return opts

def do_download(chat_id, url, quality, status_id):
    filename = None
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(quality, url)) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            filename = ydl.prepare_filename(info)
            base = os.path.splitext(filename)[0]
            if not os.path.exists(filename):
                for f in glob.glob(base + ".*"):
                    filename = f
                    break
                if not os.path.exists(filename):
                    files = glob.glob("*.mp4") + glob.glob("*.jpg") + glob.glob("*.mp3") + glob.glob("*.mkv") + glob.glob("*.webm")
                    if files:
                        filename = files[0]

        caption = f"✅ Downloaded\nJoin {CHANNEL_USERNAME}"
        with open(filename, 'rb') as f:
            if filename.endswith(('.mp3', '.m4a', '.webm', '.opus')):
                bot.send_audio(chat_id, f, caption=caption)
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                bot.send_photo(chat_id, f, caption=caption)
            else:
                bot.send_video(chat_id, f, caption=caption, supports_streaming=True)

        if os.path.exists(filename):
            os.remove(filename)
        try: bot.delete_message(chat_id, status_id)
        except: pass

    except Exception as e:
        print(f"ERROR: {e}")
        try: bot.edit_message_text(f"❌ Failed: {e}", chat_id, status_id)
        except: bot.send_message(chat_id, f"❌ Failed: {e}")

@bot.message_handler(commands=['start'])
def start_h(m):
    if not is_user_joined(m.from_user.id):
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("💎 Join Channel 💎", url=CHANNEL_LINK))
        mk.add(types.InlineKeyboardButton("✅ Check Now", callback_data="check_join"))
        bot.send_message(m.chat.id, f"👋 Bot use karne ke liye {CHANNEL_USERNAME} join karo.", reply_markup=mk)
    else:
        bot.send_message(m.chat.id, "👋 Ready! YouTube / Insta / FB ka link bhejo.")

@bot.callback_query_handler(func=lambda c: True)
def cb_h(call):
    if call.data == "check_join":
        if is_user_joined(call.from_user.id):
            bot.edit_message_text("✅ Joined! Ab link bhejo.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Abhi join nahi kiya!", show_alert=True)
        return
    if call.data.startswith("yt_"):
        url = user_links.get(call.from_user.id)
        if not url:
            bot.answer_callback_query(call.id, "Link expire ho gaya, dobara bhejo.")
            return
        bot.edit_message_text(f"⏳ Downloading {call.data}...", call.message.chat.id, call.message.message_id)
        threading.Thread(target=do_download, args=(call.message.chat.id, url, call.data, call.message.message_id)).start()

@bot.message_handler(func=lambda m: True)
def link_h(message):
    txt = message.text.strip()
    if "instagram.com" not in txt and "youtu" not in txt and "facebook.com" not in txt and "fb.watch" not in txt and "twitter.com" not in txt and "x.com" not in txt:
        return
    if not is_user_joined(message.from_user.id):
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("💎 Join Channel 💎", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, "🚫 Pehle channel join karo.", reply_markup=mk)
        return
    if "youtu" in txt:
        user_links[message.from_user.id] = txt
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(types.InlineKeyboardButton("Best", callback_data="yt_best"), types.InlineKeyboardButton("MP3 🎵", callback_data="yt_mp3"))
        bot.send_message(message.chat.id, "🎬 YouTube - Quality Select Karo:", reply_markup=mk)
    else:
        s = bot.send_message(message.chat.id, "⏳ Downloading...")
        threading.Thread(target=do_download, args=(message.chat.id, txt, "yt_best", s.message_id)).start()

@app.route('/')
def home(): return "Bot Alive ✅"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return ''

if __name__ == "__main__":
    # Agar Render pe hai to Webhook, agar Termux pe hai to Polling
    if WEBHOOK_URL:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    else:
        print("Running in POLLING mode (Termux)")
        bot.remove_webhook()
        bot.infinity_polling()
