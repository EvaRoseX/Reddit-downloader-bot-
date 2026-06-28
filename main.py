import os
import glob
import time
import subprocess
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
from threading import Thread
from flask import Flask

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running 24/7 via Powerful Video Frame Extractor!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# --- TELEGRAM CONFIGURATION ---
API_ID = 33361737
API_HASH = "7cd3bda26b08957a7205bbe8a51e6e90"
BOT_TOKEN = "8948688470:AAGE-wXEbRjuMcXpiCJEFOFTKdg6xWxClls"

app = Client("reddit_dl_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def make_progress_bar(percentage):
    completed_blocks = int(percentage / 10)
    remaining_blocks = 10 - completed_blocks
    return "█" * completed_blocks + "░" * remaining_blocks

async def upload_progress(current, total, status_msg, last_update_time):
    now = time.time()
    if now - last_update_time[0] < 3 or current == total:
        return
    last_update_time[0] = now
    percentage = (current / total) * 100
    progress_bar = make_progress_bar(percentage)
    try:
        await status_msg.edit_text(
            f"📤 **Uploading to Telegram...**\n\n"
            f"⚡ `{progress_bar}` **{percentage:.1f}%**"
        )
    except:
        pass

# FFmpeg utility to strictly extract 1st second scene from downloaded video
def extract_frame_via_ffmpeg(video_path, out_thumb_path):
    try:
        command = [
            'ffmpeg', '-y', '-i', video_path,
            '-ss', '00:00:01.000', '-vframes', '1',
            out_thumb_path
        ]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(out_thumb_path):
            img = Image.open(out_thumb_path)
            img = img.convert('RGB')
            img.thumbnail((320, 320))
            img.save(out_thumb_path, 'JPEG', quality=85)
            return img.width, img.height
    except Exception as e:
        print(f"FFmpeg Video Extract Error: {e}")
    return None, None

@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text("👋 **Ultimate Video Extractor Active! Ab har video ka thumbnail 100% aayega. Link bhejiye!**")

@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_reddit_link(client: Client, message: Message):
    url = message.text.strip()
    if "reddit.com" not in url and "redd.it" not in url:
        return

    status_msg = await message.reply_text("📥 **Downloading Video from Reddit...**")
    
    unique_id = int(time.time())
    final_thumb_path = f"downloads/thumb_{unique_id}.jpg"
    outtmpl = "downloads/%(id)s.%(ext)s"
    
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
                        app.loop.create_task(status_msg.edit_text(
                            f"⏳ **Downloading Video...**\n\n"
                            f"⚡ `{progress_bar}` **{percentage:.1f}%**"
                        ))
                except:
                    pass

    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo+bestaudio/best', # High quality merge via FFmpeg
        'progress_hooks': [yt_dlp_hook],
    }

    try:
        # Download Video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base_name = os.path.splitext(filename)[0]
            
            all_files = glob.glob(base_name + ".*")
            actual_filename = None
            for f in all_files:
                if f.endswith(('.mp4', '.mkv', '.mov', '.webm')):
                    actual_filename = f
                    
            duration = int(info.get('duration', 0))

        await status_msg.edit_text("⚙️ **Extracting Thumbnail from Video Frame...**")
        
        # Extract thumbnail directly from video file using native FFmpeg
        t_width, t_height = None, None
        if actual_filename and os.path.exists(actual_filename):
            t_width, t_height = extract_frame_via_ffmpeg(actual_filename, final_thumb_path)

        await status_msg.edit_text("📤 **Uploading with extracted thumbnail...**")
        
        if actual_filename:
            last_ul_update = [0]
            await message.reply_video(
                video=actual_filename,
                duration=duration,
                width=t_width if t_width else 480,
                height=t_height if t_height else 480,
                thumb=final_thumb_path if (t_width and os.path.exists(final_thumb_path)) else None,
                caption="✨ **Downloaded via Cloud Reddit Bot**",
                progress=upload_progress,
                progress_args=(status_msg, last_ul_update)
            )
        else:
            await message.reply_text("❌ Video download nahi ho saki.")

        if os.path.exists(final_thumb_path): os.remove(final_thumb_path)
        for f in glob.glob(base_name + "*"):
            if os.path.exists(f): os.remove(f)
        await status_msg.delete()

    except Exception as e:
        try:
            await status_msg.edit_text(f"❌ **Error:** `{str(e)[:100]}`")
        except:
            pass

if __name__ == "__main__":
    Thread(target=run_flask).start()
    app.run()
