import os
import glob
import time
import requests
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
from threading import Thread
from flask import Flask

# --- FLASK WEB SERVER FOR RENDER ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running 24/7 on Render with Live Progress Bar!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# --- TELEGRAM CONFIGURATION ---
API_ID = 33361737
API_HASH = "7cd3bda26b08957a7205bbe8a51e6e90"
BOT_TOKEN = "8948688470:AAGE-wXEbRjuMcXpiCJEFOFTKdg6xWxClls"

app = Client("reddit_dl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- HELPER FUNCTIONS ---

# Progress bar generator helper
def make_progress_bar(percentage):
    completed_blocks = int(percentage / 10)
    remaining_blocks = 10 - completed_blocks
    return "█" * completed_blocks + "░" * remaining_blocks

# 1. Upload Progress Hook (Telegram Upload)
async def upload_progress(current, total, status_msg, last_update_time):
    # Telegram rate limits se bachne ke liye har 3 second me ek baar message edit hoga
    now = time.time()
    if now - last_update_time[0] < 3 or current == total:
        return
    last_update_time[0] = now
    
    percentage = (current / total) * 100
    progress_bar = make_progress_bar(percentage)
    
    # Bytes to MB conversion
    current_mb = current / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    
    try:
        await status_msg.edit_text(
            f"📤 **Uploading to Telegram...**\n\n"
            f"⚡ `{progress_bar}` **{percentage:.1f}%**\n"
            f"📊 **Size:** `{current_mb:.1f} MB` / `{total_mb:.1f} MB`"
        )
    except:
        pass

# 2. Thumbnail Format Converter
def convert_to_jpg(image_path):
    try:
        img = Image.open(image_path)
        img = img.convert('RGB')
        jpg_path = os.path.splitext(image_path)[0] + "_final_thumb.jpg"
        img.save(jpg_path, 'JPEG')
        return jpg_path
    except:
        return None

# 3. Direct Reddit Thumbnail Extractor
def get_reddit_thumbnail_direct(reddit_url):
    try:
        clean_url = reddit_url.split('?')[0].rstrip('/') + ".json"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(clean_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            post_data = data[0]['data']['children'][0]['data']
            if 'preview' in post_data and 'images' in post_data['preview']:
                source_img = post_data['preview']['images'][0]['source']['url']
                return source_img.replace("&amp;", "&")
            elif 'thumbnail' in post_data and post_data['thumbnail'].startswith('http'):
                return post_data['thumbnail']
    except:
        pass
    return None

# --- BOT COMMANDS & HANDLERS ---

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text("👋 **Bot Active Hai! Ab aapko download aur upload dono ka live progress status dikhega. Link bhejiye!**")

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_reddit_link(client: Client, message: Message):
    url = message.text.strip()
    if "reddit.com" not in url and "redd.it" not in url:
        return

    status_msg = await message.reply_text("📥 **Processing link...**")
    outtmpl = "downloads/%(id)s.%(ext)s"
    
    # Download Progress Hook Function for yt-dlp
    last_dl_update = [0]
    def yt_dlp_hook(d):
        if d['status'] == 'downloading':
            now = time.time()
            if now - last_dl_update[0] >= 3:
                last_dl_update[0] = now
                try:
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    
                    if total_bytes > 0:
                        percentage = (downloaded_bytes / total_bytes) * 100
                        progress_bar = make_progress_bar(percentage)
                        # Async function inside sync hook trick
                        app.loop.create_task(status_msg.edit_text(
                            f"⏳ **Downloading from Reddit...**\n\n"
                            f"⚡ `{progress_bar}` **{percentage:.1f}%**\n"
                            f"📁 **Speed:** `{d.get('_speed_str', 'N/A')}` | **ETA:** `{d.get('_eta_str', 'N/A')}`"
                        ))
                except:
                    pass

    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'writethumbnail': True,
        'format': 'balthom/best',
        'progress_hooks': [yt_dlp_hook] # Attaching the download hook
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base_name = os.path.splitext(filename)[0]
            
            all_files = glob.glob(base_name + ".*")
            actual_filename = None
            raw_thumbnail = None
            
            for f in all_files:
                if f.endswith(('.jpg', '.jpeg', '.webp', '.png')):
                    raw_thumbnail = f
                elif f.endswith(('.mp4', '.mkv', '.mov', '.webm')):
                    actual_filename = f
                    
            duration = int(info.get('duration', 0))

        # Backup Thumbnail Logic
        if not raw_thumbnail and info.get('thumbnail'):
            try:
                thumb_url = get_reddit_thumbnail_direct(url) or info.get('thumbnail')
                r = requests.get(thumb_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                if r.status_code == 200:
                    raw_thumbnail = base_name + "_raw.png"
                    with open(raw_thumbnail, 'wb') as f:
                        f.write(r.content)
            except:
                pass

        final_thumbnail = None
        if actual_filename:
            if raw_thumbnail and os.path.exists(raw_thumbnail):
                final_thumbnail = convert_to_jpg(raw_thumbnail)

            # Uploading with dynamic upload hook
            last_ul_update = [0]
            await message.reply_video(
                video=actual_filename,
                duration=duration,
                thumb=final_thumbnail if final_thumbnail and os.path.exists(final_thumbnail) else None,
                caption="✨ **Downloaded via Cloud Reddit Bot**",
                progress=upload_progress,
                progress_args=(status_msg, last_ul_update)
            )
        else:
            await message.reply_text("❌ Video download fail ho gayi.")

        # Cleanup files
        for f in glob.glob(base_name + "*"):
            if os.path.exists(f): os.remove(f)
        await status_msg.delete()

    except Exception as e:
        print(f"Error: {e}")
        try:
            await status_msg.edit_text(f"❌ **Error:** `{str(e)[:100]}`")
        except:
            pass

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("🤖 Starting Pyrogram Bot with Status Bars...")
    app.run()
