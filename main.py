from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
import os
import asyncio
import subprocess
import json
import time
import requests
# from Gofile import GofileUploader
from datetime import datetime
from config import *

# Initialize bot
app = Client(
    "yt_dl_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Constants
MAX_TG_SIZE = 1932735283  # 1.8 GB in bytes


# Create download directory if not exists
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def upload_to_gofile(file_path):
    try:
        # Get best server
        server_response = requests.get('https://api.gofile.io/getServer')
        server = server_response.json()['data']['server']
        
        # Upload URL
        upload_url = f'https://store1.gofile.io/uploadFile'
        
        # Upload file
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(upload_url, files=files)
            
        if response.status_code == 200 and response.json()['status'] == 'ok':
            return response.json()['data']['downloadPage']
        else:
            raise Exception('Upload failed')
    except Exception as e:
        raise Exception(f'Gofile upload error: {str(e)}')

async def download_audio(url, message):
    """Download YouTube audio"""
    filename = None
    try:        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'cookiefile': "cookies.txt",
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
            file_size = os.path.getsize(filename)
            file_size_mb = file_size / (1024 * 1024)  # Convert to MB
            
            # Check file size
            file_size = os.path.getsize(filename)

            if file_size > MAX_TG_SIZE:
                await message.edit_text("📤 File too large for Telegram. Uploading to Gofile...")
                try:
                    # Upload to Gofile
                    gofile_url = upload_to_gofile(filename)
                
                    # Send message with download link
                    await message.reply_text(
                        f"File was too large for Telegram (Size: {file_size_mb:.2f}MB)\n"
                        f"You can download it from Gofile:\n{gofile_url}"
                    )
                except Exception as e:
                    await message.reply_text(
                        f"Error uploading to Gofile: {str(e)}\n"
                        f"File size: {file_size_mb:.2f}MB"
                    )
            else:
                await message.edit_text("📤 Uploading WAV file...")
                
                await app.send_document(
                    chat_id=message.chat.id,
                    document=filename,
                    caption=f"🎵 {info['title']}",
                    force_document=True
                )
                
                await message.edit_text("✅ Download and conversion completed!")

    except Exception as e:
        await message.edit_text(f"❌ Error: {str(e)}")
    
    finally:
        # Cleanup
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
        except:
            pass

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