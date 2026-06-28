import os
import glob
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
    return "Bot is running 24/7 on Render with NSFW Thumbnail Fix!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# --- TELEGRAM CONFIGURATION ---
API_ID = 33361737
API_HASH = "7cd3bda26b08957a7205bbe8a51e6e90"
BOT_TOKEN = "8948688470:AAGE-wXEbRjuMcXpiCJEFOFTKdg6xWxClls"

app = Client("reddit_dl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def convert_to_jpg(image_path):
    try:
        img = Image.open(image_path)
        img = img.convert('RGB')
        jpg_path = os.path.splitext(image_path)[0] + "_final_thumb.jpg"
        img.save(jpg_path, 'JPEG')
        return jpg_path
    except Exception as e:
        print(f"Image conversion error: {e}")
        return None

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text("👋 **Hello! Cloud Bot Active hai. Ab NSFW aur Normal dono posts ke thumbnail aayenge. Link bhejiye!**")

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_reddit_link(client: Client, message: Message):
    url = message.text.strip()
    if "reddit.com" not in url and "redd.it" not in url:
        return

    status_msg = await message.reply_text("📥 **Processing link on cloud...**")
    outtmpl = "downloads/%(id)s.%(ext)s"
    
    # Forced thumbnail options added for NSFW content
    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'writethumbnail': True,  # Forced local thumbnail download
        'format': 'balthom/best', 
    }

    try:
        await status_msg.edit_text("⏳ **Downloading Media & Thumbnail...**")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base_name = os.path.splitext(filename)[0]
            
            # Check all downloaded files in directory
            all_files = glob.glob(base_name + ".*")
            
            actual_filename = None
            raw_thumbnail = None
            
            for f in all_files:
                if f.endswith(('.jpg', '.jpeg', '.webp', '.png')):
                    raw_thumbnail = f
                elif f.endswith(('.mp4', '.mkv', '.mov', '.webm')):
                    actual_filename = f
                    
            duration = int(info.get('duration', 0))

        await status_msg.edit_text("📤 **Uploading to Telegram...**")
        final_thumbnail = None
        
        if actual_filename:
            if raw_thumbnail and os.path.exists(raw_thumbnail):
                final_thumbnail = convert_to_jpg(raw_thumbnail)

            # Upload video with the processed thumbnail
            await message.reply_video(
                video=actual_filename,
                duration=duration,
                thumb=final_thumbnail if final_thumbnail and os.path.exists(final_thumbnail) else None,
                caption="✨ **Downloaded via Cloud Reddit Bot**"
            )
        else:
            await message.reply_text("❌ Video download nahi ho saki.")

        # Cleanup files to keep cloud disk clean
        for f in glob.glob(base_name + "*"):
            if os.path.exists(f): os.remove(f)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** `{str(e)[:100]}`")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("🤖 Starting Pyrogram Bot...")
    app.run()
