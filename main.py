from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
import os
import requests
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

def get_cookies():
    """Download cookies from Gist URL"""
    try:
        response = requests.get(COOKIES_GIST_URL)
        if response.status_code == 200:
            cookies_path = os.path.join(DOWNLOAD_DIR, "cookies.txt")
            with open(cookies_path, "w") as f:
                f.write(response.text)
            return cookies_path
        return None
    except Exception as e:
        print(f"Error getting cookies: {str(e)}")
        return None

async def download_audio(url, message, cookies_path):
    """Download YouTube audio using cookies"""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'cookiefile': cookies_path,
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
            
            # Cleanup
            if os.path.exists(filename):
                os.remove(filename)

    except Exception as e:
        await message.edit_text(f"❌ Error: {str(e)}")

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
        "Just send me a YouTube link and I'll convert it to WAV format.\n"
        "The bot uses pre-configured cookies for accessing age-restricted videos."
    )

@app.on_message(filters.regex(r'(https?:\/\/)?((www\.)?youtube\.com|youtu\.be)\/.*'))
async def youtube_link_handler(client, message):
    url = message.text.strip()
    status_message = await message.reply_text("🔍 Processing...")
    
    # Get cookies from Gist
    cookies_path = get_cookies()
    if not cookies_path:
        await status_message.edit_text("❌ Failed to get cookies!")
        return
    
    try:
        await download_audio(url, status_message, cookies_path)
    except Exception as e:
        await status_message.edit_text(f"❌ Error: {str(e)}")
    finally:
        # Cleanup cookies file
        if os.path.exists(cookies_path):
            os.remove(cookies_path)

if __name__ == "__main__":
    print("Bot Started!")
    app.run()