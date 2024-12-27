from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
import os
import asyncio
from config import *

# Initialize bot
app = Client(
    "yt_dl_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Create download directory if not exists
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def setup_cookies():
    """Setup cookies file"""
    cookies_path = os.path.join(DOWNLOAD_DIR, "cookies.txt")
    with open(cookies_path, 'w') as f:
        f.write(YOUTUBE_COOKIES)
    return cookies_path

async def download_audio(url, message):
    """Download YouTube audio"""
    filename = None
    cookies_path = None
    try:
        # Setup cookies
        cookies_path = setup_cookies()
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'cookiefile': cookies_path,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True
        }

        await message.edit_text("⏳ Downloading...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: ydl.extract_info(url, download=True)
            )
            
            filename = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".wav"
            
            await message.edit_text("📤 Uploading...")
            
            await app.send_audio(
                chat_id=message.chat.id,
                audio=filename,
                caption=f"🎵 {info['title']}"
            )
            
            await message.edit_text("✅ Done!")

    except Exception as e:
        await message.edit_text(f"❌ Error: {str(e)}")
    
    finally:
        # Cleanup
        if filename and os.path.exists(filename):
            os.remove(filename)
        if cookies_path and os.path.exists(cookies_path):
            os.remove(cookies_path)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text(
        "👋 Send me a YouTube link to download it as WAV audio.\n"
        "Use /help for more information."
    )

@app.on_message(filters.command("help"))
async def help_command(client, message):
    await message.reply_text(
        "📖 How to use:\n\n"
        "Just send me a YouTube link and I'll convert it to WAV format."
    )

@app.on_message(filters.regex(r'(https?:\/\/)?((www\.)?youtube\.com|youtu\.be)\/.*'))
async def youtube_link_handler(client, message):
    url = message.text.strip()
    status_message = await message.reply_text("🔍 Processing...")
    
    try:
        await download_audio(url, status_message)
    except Exception as e:
        await status_message.edit_text(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("Bot Started!")
    app.run()