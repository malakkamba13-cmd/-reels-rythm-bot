import os
import asyncio
import logging
import json
import subprocess
import time
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, ReplyKeyboardMarkup, KeyboardButton, MenuButtonWebApp, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler, filters, ContextTypes
from gtts import gTTS
from dotenv import load_dotenv

from dotenv import load_dotenv

import keep_alive
keep_alive.keep_alive()

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Dynamic yt-dlp path
YT_DLP_PATH = "yt-dlp"


# VIP Persistence
VIP_FILE = "vip_users.json"
TRON_FILE = "tron_wallets.json"
ADMIN_FILE = "admin_config.json"

def load_admin():
    if os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, 'r') as f: return json.load(f).get("admin_id")
    return None

def save_admin(user_id):
    with open(ADMIN_FILE, 'w') as f: json.dump({"admin_id": user_id}, f)

async def notify_admin(app, user):
    admin_id = load_admin()
    if admin_id:
        try:
            text = f"🔔 *Bot Access Alert* 🌈\n\n👤 *User:* {user.full_name}\n🆔 *ID:* `{user.id}`\n🏷️ *Username:* @{user.username if user.username else 'None'}\n\nhas just opened the bot dashboard! ✨"
            await app.bot.send_message(chat_id=admin_id, text=text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Admin Notify Error: {e}")

def load_vips():
    if os.path.exists(VIP_FILE):
        with open(VIP_FILE, 'r') as f: return json.load(f)
    return []

def save_vip(user_id):
    vips = load_vips()
    if user_id not in vips:
        vips.append(user_id)
        with open(VIP_FILE, 'w') as f: json.dump(vips, f)

def is_vip(user_id):
    return user_id in load_vips()

def save_tron_wallet(user_id, wallet):
    wallets = {}
    if os.path.exists(TRON_FILE):
        with open(TRON_FILE, 'r') as f: wallets = json.load(f)
    wallets[str(user_id)] = wallet
    with open(TRON_FILE, 'w') as f: json.dump(wallets, f)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a dashboard message and sets a persistent keyboard."""
    # Inline buttons for immediate interaction
    inline_keyboard = [
        [InlineKeyboardButton("Trending Music 🎵", callback_data="browse_music")],
        [InlineKeyboardButton("New Movies 🎬", callback_data="browse_movies")],
        [InlineKeyboardButton("Live Radio 📻", callback_data="browse_radio")],
        [InlineKeyboardButton("⭐ VIP/Premium", callback_data="monetize_vip"), InlineKeyboardButton("❤️ Support", callback_data="monetize_support")],
        [InlineKeyboardButton("Open Search Widget 🚀", switch_inline_query_current_chat="")]
    ]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    # Persistent Reply Keyboard for the "Telegram Window"
    reply_keyboard = [
        [KeyboardButton("Music 🎵"), KeyboardButton("Movies 🎬")],
        [KeyboardButton("TV Shows 📺"), KeyboardButton("Live Radio 📻")],
        [KeyboardButton("⭐ VIP/Premium"), KeyboardButton("❤️ Support")]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Welcome to the Reels&Rythm Hub! 🎵🎬\n\nI've added the quick-access menu to your keyboard below. You can also use the buttons here:",
        reply_markup=reply_markup
    )
    
    # Send Mascot
    try:
        # Try relative path first, then hardcoded fallback
        mascot_path = os.path.join(os.getcwd(), "reels_rythm_mascot.png")
        if not os.path.exists(mascot_path):
            mascot_path = r"C:\Users\Malak\.gemini\antigravity\brain\1a2720b0-f4d9-4589-b63a-efc7f5263697\reels_rythm_mascot_1773228008312.png"
            
        if os.path.exists(mascot_path):
            with open(mascot_path, 'rb') as m:
                await update.message.reply_photo(photo=m, caption="Meet Rythmia! Your magical guide to Movies & Music! ✨👧")
    except Exception as e:
        logging.error(f"Mascot Error: {e}")

    # Voice Greeting
    try:
        tts = gTTS(text="Welcome to Reels and Rythm. Your ultimate media hub. How can I help you today?", lang='en')
        voice_path = "welcome.mp3"
        tts.save(voice_path)
        with open(voice_path, 'rb') as v:
            await update.message.reply_voice(voice=v)
        os.remove(voice_path)
    except Exception as e:
        logging.error(f"TTS Error: {e}")

    await update.message.reply_text("Tap below to browse:", reply_markup=inline_markup)
    
    # Notify Admin
    await notify_admin(context.application, update.effective_user)

async def set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sets the admin ID. Only works if no admin is set or by existing admin."""
    current_admin = load_admin()
    user_id = update.effective_user.id
    
    if current_admin is None:
        save_admin(user_id)
        await update.message.reply_text(f"✅ *Admin Registered!* 🌈\n\nYour ID `{user_id}` has been set as the Bot Admin. You will now receive notifications when users access the bot!", parse_mode="Markdown")
    elif current_admin == user_id:
        await update.message.reply_text("You are already the registered Admin! 👑")
    else:
        await update.message.reply_text("❌ *Unauthorized*\n\nAn admin is already registered for this bot. If you need to reset this, please contact technical support.")

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles clicks from the persistent ReplyKeyboardMarkup."""
    text = update.message.text
    if text == "Music 🎵": await run_browse(update.message, "browse_music")
    elif text == "Movies 🎬": await run_browse(update.message, "browse_movies")
    elif text == "TV Shows 📺": await run_browse(update.message, "browse_tv")
    elif text == "Live Radio 📻": await run_radio(update.message)
    elif text == "⭐ VIP/Premium": await run_premium(update.message)
    elif text == "❤️ Support": await run_support(update.message)
    elif text == "Search 🚀":
        await update.message.reply_text("🌈 *Vibrant Search Mode* 🌈\n\nType `@SongBrand_bot` to open the colorful widget!", 
                                       parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open Widget 🚀", switch_inline_query_current_chat="")]]))

async def run_premium(message):
    text = (
        "⭐ *Reels&Rythm VIP Premium* 🌈\n\n"
        "Upgrade for the ultimate entertainment experience:\n"
        "✅ *No Ads* - seamless browsing\n"
        "✅ *Fast Track* - priority download speeds\n"
        "✅ *Exclusive Content* - early access to 2026 hits\n"
        "✅ *Bypass Limits* - higher file size tolerance\n\n"
        "💰 *Only $4.99/month*\n\n"
        "Tap below to upgrade instantly via Telegram Stars or reach out to @Admin!"
    )
    keyboard = [[InlineKeyboardButton("Upgrade Now 💎", callback_data="vip_upgrade")]]
    await message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def run_support(message):
    text = (
        "❤️ *Support the Bot* 🌈\n\n"
        "Help us keep the servers running and the library updated! Your support means the world to us.\n\n"
        "💎 *TRON (TRC20):* `TGgBQmatueQexqXT6aHm2tN1teow8mgxQq` (Tap to copy)\n"
        "💎 *USDT (BEP20):* `0xYourWalletAddressHere`\n\n"
        "Every donation unlocks a 'Supporter' badge in your profile! ✨\n\n"
        "Want to receive rewards? Submit your Tron wallet below! 👇"
    )
    keyboard = [[InlineKeyboardButton("Submit My Tron Wallet 📝", callback_data="tron_submit")]]
    await message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_tron_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user's Tron wallet address submission."""
    wallet = update.message.text.strip()
    # Basic Tron address validation
    if len(wallet) == 34 and wallet.startswith('T'):
        save_tron_wallet(update.effective_user.id, wallet)
        context.user_data['awaiting_tron'] = False
        await update.message.reply_text("✅ *Wallet Saved!* 🌈\n\nYour Tron address has been securely linked to your profile. Thank you for being part of Reels&Rythm!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ *Invalid Address*\n\nPlease send a valid Tron wallet address (starts with 'T' and is 34 characters long).")

async def run_radio(message):
    stations = [
        ("🎤 BBC World Service", "https://stream.live.vc.bbcmedia.co.uk/bbc_world_service"),
        ("⚡ Capital FM UK", "https://icecast.media-ice.musicradio.com/CapitalMP3"),
        ("🎷 Jazz FM UK", "https://icecast.media-ice.musicradio.com/JazzFMMP3"),
        ("🌈 Radio Paradise", "https://stream.radioparadise.com/mellow-128"),
        ("🔥 Absolute Radio", "https://icecast.media-ice.musicradio.com/AbsoluteRadioMP3")
    ]
    
    keyboard = []
    rainbow = ["🔴", "🟠", "🟡", "🟢", "🔵"]
    for i, (name, url) in enumerate(stations):
        theme = rainbow[i % len(rainbow)]
        keyboard.append([InlineKeyboardButton(f"{theme} {name}", url=url)])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "📻 *Live Radio Hub* 🌈\n\nSelect a station below to start streaming vibrant sounds direct to your device!",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def run_apps(message):
    await message.reply_text("📱 *App & Software Store* 🌈\n\n1. 🛠️ [Tool Chest](https://example.com/apps)\n2. 🎮 [Gaming Hub](https://example.com/games)\n3. 🔐 [Privacy Suite](https://example.com/privacy)\n\nMore apps coming soon! Use the widget for search.", parse_mode="Markdown")

async def run_browse(message, category):
    search_map = {
        "browse_music": "popular songs 2026",
        "browse_movies": "popular full movies 2026",
        "browse_tv": "best new tv show episodes"
    }
    search_q = search_map.get(category, "trending")
    results = search_content(search_q, limit=5)
    for res in results:
        await send_result(message, res)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the inline query widget experience."""
    query = update.inline_query.query
    search_q = query if query else "trending 2024"
    
    results = search_content(search_q, limit=15)
    inline_results = []
    
    # Colourful theme emojis
    rainbow = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "⚪"]
    
    for i, res in enumerate(results):
        icon = "🎵"
        theme = rainbow[i % len(rainbow)]
        if "trailer" in res['title'].lower() or "movie" in res['title'].lower():
            icon = "🎬"
        elif "show" in res['title'].lower() or "tv" in res['title'].lower():
            icon = "📺"
            
        inline_results.append(
            InlineQueryResultArticle(
                id=res['id'],
                title=f"{theme} {icon} {res['title']}",
                thumbnail_url=res.get('thumbnail'),
                description=f"✨ {theme} Tap to Download/Play this vibrant item!",
                input_message_content=InputTextMessageContent(f"/get_{res['id']}")
            )
        )
    
    await update.inline_query.answer(inline_results, cache_time=60)

async def handle_get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered by clicking an item in the inline widget."""
    video_id = update.message.text.replace("/get_", "")
    # Fetch metadata for this specific ID
    res = search_content(video_id, limit=1)
    if res:
        await send_result(update.message, res[0])
    await update.message.delete()

async def browse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles 'Trending' button clicks from inline keys."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "browse_radio":
        await run_radio(query.message)
        return
    elif query.data == "monetize_vip":
        await run_premium(query.message)
        return
    elif query.data == "monetize_support":
        await run_support(query.message)
        return
    elif query.data == "tron_submit":
        context.user_data['awaiting_tron'] = True
        await query.message.reply_text("📝 *Submit Your Tron Wallet*\n\nPlease paste your Tron (TRC20) wallet address below. We'll use this to reward our top contributors! ✨", parse_mode="Markdown")
        return
    elif query.data == "vip_upgrade":
        save_vip(query.from_user.id)
        await query.answer("💎 Welcome to VIP Premium! 💎", show_alert=True)
        await query.message.edit_text("✅ *VIP Status Activated!*\n\nYou now have Ad-Free access, Fast Track downloads, and High Quality streams. Enjoy the Reels&Rythm Premium experience!", parse_mode="Markdown")
        return

    await run_browse(query.message, query.data)

async def send_result(message, res):
    """Sends a visual result with buttons."""
    is_video = any(x in res['title'].lower() for x in ["trailer", "movie", "tv", "show", "episode", "season"])
    mode = "movie" if is_video else "music"
    url = f"https://www.youtube.com/watch?v={res['id']}"
    
    vip = is_vip(message.from_user.id if hasattr(message, 'from_user') else 0)
    
    keyboard = [
        [
            InlineKeyboardButton("📥 Download (Best)", callback_data=f"{mode}_dl_{res['id']}"),
            InlineKeyboardButton("▶️ Play (Speed)", callback_data=f"{mode}_pl_{res['id']}")
        ],
        [InlineKeyboardButton("🌐 Watch Online", url=url)]
    ]
    
    if not vip:
        keyboard.append([InlineKeyboardButton("🔥 Sponsored: Get Free Content", url="https://example.com/ad")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = f"✨ *{res['title']}*\n"
    if vip: caption += "💎 _VIP Premium Result_\n"
    
    if res.get('duration'):
        caption += f"⏱️ Duration: {res['duration']}\n"
    caption += "\nSelect an option below:\n"
    
    if mode == "movie":
        caption += "⚠️ _Note: Files >50MB will provide a Watch Online link due to Telegram limits._"
    
    thumb = res.get('thumbnail')
    
    try:
        if thumb:
            await message.reply_photo(
                photo=thumb,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            await message.reply_text(
                text=caption,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    except Exception as e:
        logging.error(f"Error sending result: {e}")
        await message.reply_text(text=caption, parse_mode="Markdown", reply_markup=reply_markup)

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the actual download/play requests with progress updates."""
    query = update.callback_query
    data = query.data.split("_", 2)
    mode, action, video_id = data[0], data[1], data[2]
    
    vip = is_vip(query.from_user.id)
    await query.answer("Starting... 🚀")
    
    # Monetization: Brief Ad Delay / Sponsor Message (Skipped for VIP)
    if not vip:
        status_msg = await query.message.reply_text("⏳ Processing through secure server...\n_Sponsored by reels-rythm-hub.com_", parse_mode="Markdown")
        await asyncio.sleep(1.5) # Simulated ad/verification delay
    else:
        status_msg = await query.message.reply_text("💎 *VIP Fast-Track Active...*", parse_mode="Markdown")
    
    temp_dir = "downloads"
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)
    
    ext = "mp4" if mode == "movie" else "m4a"
    output = os.path.join(temp_dir, f"{video_id}.{ext}")
    
    last_update = 0
    async def update_progress(percent):
        nonlocal last_update
        now = time.time()
        if now - last_update < 2: return # Only update every 2 seconds
        last_update = now
        try:
            await status_msg.edit_text(f"⏳ Processing... {percent}\n{mode.title()} is being prepared!")
        except: pass

    try:
        success = await download_async(video_id, output, mode, action == "pl", update_progress, vip=vip)
        
        if success:
            file_size = os.path.getsize(output) / (1024 * 1024)
            
            # Smart Progressive Downgrade for Movies/TV
            if file_size > 50 and mode == "movie":
                resolutions = [360, 240, 144]
                for res in resolutions:
                    await status_msg.edit_text(f"✨ Optimizing for your device ({res}p)...")
                    if os.path.exists(output): os.remove(output)
                    success = await download_async(video_id, output, mode, progress_callback=update_progress, force_res=res, vip=vip)
                    if not success: break
                    file_size = os.path.getsize(output) / (1024 * 1024)
                    if file_size <= 50: break
                
                # Final Fallback: If 144p is still > 50MB, switch to Audio Only
                if file_size > 50:
                    await status_msg.edit_text("✨ Fine-tuning high-quality audio... 🎵")
                    if os.path.exists(output): os.remove(output)
                    mode = "music"
                    output = os.path.join(temp_dir, f"{video_id}.m4a")
                    success = await download_async(video_id, output, mode, progress_callback=update_progress, vip=vip)
                    if success:
                        file_size = os.path.getsize(output) / (1024 * 1024)
            
            if file_size > 50:
                url = f"https://www.youtube.com/watch?v={video_id}"
                await status_msg.edit_text(
                    "✨ This content is best viewed online! Tap below to watch:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Watch Online 🌐", url=url)]])
                )
                if os.path.exists(output): os.remove(output)
                return

            await status_msg.edit_text(f"✅ Your {'Audio' if mode == 'music' else 'Video'} is ready!")
            try:
                with open(output, 'rb') as f:
                    if mode == "movie":
                        await query.message.reply_video(video=f, supports_streaming=True, write_timeout=120)
                    else:
                        await query.message.reply_audio(audio=f, write_timeout=120)
                await status_msg.delete()
            except Exception as e:
                logging.error(f"Upload error: {e}")
                await status_msg.edit_text(f"❌ Upload failed. The file might be slightly too big for your connection.")
        else:
            await status_msg.edit_text("Failed to process request. ❌ Restricted or unavailable.")
    finally:
        # Global cleanup for the specific ID
        for f in os.listdir(temp_dir):
            if video_id in f:
                try: os.remove(os.path.join(temp_dir, f))
                except: pass

async def download_async(video_id, output_path, mode, fast_preview=False, progress_callback=None, force_res=None, vip=False):
    """Executes yt-dlp asynchronously with progressive size optimizations."""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        base = output_path.replace(".mp3", "").replace(".mp4", "").replace(".m4a", "").replace(".webm", "")
        
        # Optimization & Compatibility flags
        flags = [
            "--no-playlist", "--quiet", "--no-warnings", "--progress", "--newline",
            "--no-check-certificates", "--geo-bypass", 
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # For VIP, we can try to push slightly higher quality if possible
        q_limit = "50M" if not vip else "100M"  # VIPs get a higher file size limit for direct downloads
    
        if mode == "movie":
            # Progressive quality selection with size hinting
            if force_res:
                quality = f"best[height<={force_res}][filesize<{q_limit}]/best[height<={force_res}]"
            elif fast_preview:
                quality = f"best[height<=360][filesize<{q_limit}]/best[height<=360]"
            else:
                # VIP preference for 720p if small enough, otherwise fallback to 480p
                quality = f"best[height<=720][filesize<{q_limit}]/best[height<=480][filesize<{q_limit}]/best[height<=480]"
            cmd = [YT_DLP_PATH] + flags + ["-f", quality, "-o", f"{base}.%(ext)s", url]
        else:
            # Audio optimization: Prefer m4a (aac) for speed as it usually needs no conversion
            cmd = [YT_DLP_PATH] + flags + ["-f", "bestaudio[ext=m4a]/bestaudio/best", "-o", f"{base}.%(ext)s", url]
            
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async def read_stderr(pipe):
            err_data = await pipe.read()
            if err_data:
                logging.error(f"yt-dlp stderr: {err_data.decode()}")

        asyncio.create_task(read_stderr(process.stderr))

        while True:
            line = await process.stdout.readline()
            if not line: break
            text = line.decode().strip()
            if "[download]" in text and "%" in text:
                parts = text.split()
                for p in parts:
                    if "%" in p:
                        if progress_callback: await progress_callback(p)
                        break

        await process.wait()
        
        # Clean up extension issues
        for e in [".mp3", ".mp4", ".m4a", ".webm"]:
            if os.path.exists(f"{base}{e}"):
                if f"{base}{e}" != output_path:
                    if os.path.exists(output_path): os.remove(output_path)
                    os.rename(f"{base}{e}", output_path)
                    break
                    
        return os.path.exists(output_path)
    except Exception as e:
        logging.error(f"Async Download error: {e}")
        return False

def search_content(query, limit=5):
    """Executes yt-dlp search and returns list of items."""
    try:
        # If it's an 11-char video ID, fetch it directly; otherwise use ytsearch
        if len(query) == 11 and all(c.isalnum() or c in '-_' for c in query):
            cmd = [YT_DLP_PATH, "--dump-json", "--flat-playlist", query]
        else:
            cmd = [YT_DLP_PATH, "--dump-json", "--flat-playlist", f"ytsearch{limit}:{query}"]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
        
        results = []
        for line in output.strip().split('\n'):
            if line:
                data = json.loads(line)
                duration = data.get('duration')
                duration_str = ""
                if duration:
                    m, s = divmod(int(duration), 60)
                    h, m = divmod(m, 60)
                    duration_str = f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

                results.append({
                    'id': data.get('id'),
                    'title': data.get('title'),
                    'thumbnail': data.get('thumbnail'),
                    'duration': duration_str
                })
        return results
    except Exception as e:
        logging.error(f"Search error: {e}")
        return []

async def main():
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    app = ApplicationBuilder().token(TOKEN).read_timeout(60).write_timeout(120).connect_timeout(60).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_admin", set_admin))
    
    # Wallet submission toggle handler (must be prioritized)
    async def global_text_handler(update, context):
        if context.user_data.get('awaiting_tron'):
            await handle_tron_submission(update, context)
            return
        # If not awaiting something specific, run the standard button handler
        await handle_text_buttons(update, context)

    app.add_handler(MessageHandler(filters.Regex("^(Music 🎵|Movies 🎬|TV Shows 📺|Live Radio 📻|⭐ VIP/Premium|❤️ Support)$"), global_text_handler))

    # General text handler: only handle wallet submission if awaiting_tron is set
    async def general_text_handler(update, context):
        if context.user_data.get('awaiting_tron'):
            await handle_tron_submission(update, context)

    app.add_handler(MessageHandler(filters.TEXT & ~(filters.COMMAND | filters.Regex("^(Music 🎵|Movies 🎬|TV Shows 📺|Live Radio 📻|⭐ VIP/Premium|❤️ Support)$")), general_text_handler), group=1)
    
    app.add_handler(MessageHandler(filters.Regex("^/get_"), handle_get_command))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(CallbackQueryHandler(browse_callback, pattern="^browse_"))
    app.add_handler(CallbackQueryHandler(download_callback, pattern="^(music|movie)_"))
    app.add_handler(CallbackQueryHandler(browse_callback, pattern="^monetize_"))
    app.add_handler(CallbackQueryHandler(browse_callback, pattern="^vip_"))
    app.add_handler(CallbackQueryHandler(browse_callback, pattern="^tron_"))
    
    print("Reels&Rythm Bot is starting...")
    await app.initialize()
    
    # Register commands for the Telegram menu button / slash menu
    from telegram import BotCommand
    commands = [
        BotCommand("start", "Open Main Dashboard"),
        BotCommand("search", "Open Search Widget")
    ]
    await app.bot.set_my_commands(commands)
    
    await app.start()
    await app.updater.start_polling()
    
    # Run until the process is stopped
    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
