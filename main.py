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
    return "Bot is running 24/7 on Render!"

def run_flask():
    # Render automatic PORT provide karta hai, default 8080 use hoga
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# --- TELEGRAM CONFIGURATION ---
API_ID = 33361737
API_HASH = "7cd3bda26b08957a7205bbe8a51e6e90"
BOT_TOKEN = "8948688470:AAGE-wXEbRjuMcXpiCJEFOFTKdg6xWxClls"

app = Client("reddit_dl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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
    except Exception as e:
        print(f"Thumbnail Error: {e}")
    return None

def convert_to_jpg(image_path):
    try:
        img = Image.open(image_path)
        img = img.convert('RGB')
        jpg_path = os.path.splitext(image_path)[0] + "_final_thumb.jpg"
        img.save(jpg_path, 'JPEG')
        return jpg_path
    except:
        return None

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text("👋 **Hello! Main Render Cloud par 24/7 active hoon. Reddit video link bhejiye!**")

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_reddit_link(client: Client, message: Message):
    url = message.text.strip()
    if "reddit.com" not in url and "redd.it" not in url:
        return

    status_msg = await message.reply_text("📥 **Processing link on cloud...**")
    outtmpl = "downloads/%(id)s.%(ext)s"
    
    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'format': 'balthom/best', 
    }

    try:
        await status_msg.edit_text("⏳ **Downloading & Extracting Thumbnail...**")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base_name = os.path.splitext(filename)[0]
            video_files = glob.glob(base_name + ".*")
            
            actual_filename = None
            for f in video_files:
                if f.endswith(('.mp4', '.mkv', '.mov', '.webm')):
                    actual_filename = f
            duration = int(info.get('duration', 0))

        raw_thumbnail = None
        thumb_url = get_reddit_thumbnail_direct(url)
        if thumb_url:
            try:
                r = requests.get(thumb_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                if r.status_code == 200:
                    raw_thumbnail = base_name + "_raw.png"
                    with open(raw_thumbnail, 'wb') as f:
                        f.write(r.content)
            except:
                pass

        await status_msg.edit_text("📤 **Uploading to Telegram...**")
        final_thumbnail = None
        if actual_filename:
            if raw_thumbnail and os.path.exists(raw_thumbnail):
                final_thumbnail = convert_to_jpg(raw_thumbnail)

            await message.reply_video(
                video=actual_filename,
                duration=duration,
                thumb=final_thumbnail if final_thumbnail and os.path.exists(final_thumbnail) else None,
                caption="✨ **Downloaded via Cloud Reddit Bot**"
            )
        else:
            await message.reply_text("❌ Video nahi mil saki.")

        for f in glob.glob(base_name + "*"):
            if os.path.exists(f): os.remove(f)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** `{str(e)[:100]}`")

if __name__ == "__main__":
    # Flask server ko alag thread me start karna taaki bot ko block na kare
    Thread(target=run_flask).start()
    print("🤖 Starting Pyrogram Bot...")
    app.run()
