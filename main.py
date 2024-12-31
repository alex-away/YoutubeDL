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
        # Updated API endpoint
        server_response = requests.get(
            'https://api.gofile.io/servers',
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if not server_response.ok:
            raise Exception(f'Server request failed: {server_response.status_code} - {server_response.text}')

        server_data = server_response.json()
        if server_data.get('status') != 'ok' or 'data' not in server_data:
            raise Exception(f'Invalid server response: {server_data}')

        server = server_data['data']['servers'][0]['name']

        # Upload file
        upload_url = f'https://{server}.gofile.io/uploadFile'

        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
            response = requests.post(
                upload_url,
                files=files,
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=300
            )

            if not response.ok:
                raise Exception(f'Upload failed: {response.status_code} - {response.text}')

            data = response.json()
            if data.get('status') != 'ok' or 'data' not in data:
                raise Exception(f'Invalid upload response: {data}')

            return data['data']['downloadPage']

    except requests.exceptions.RequestException as e:
        raise Exception(f'Network error: {str(e)}')
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
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".wav"
            file_size = os.path.getsize(filename)
            file_size_mb = file_size / (1024 * 1024)

            if file_size > MAX_TG_SIZE:
                progress_msg = await message.edit_text("📤 File too large for Telegram. Uploading to Gofile...")

                try:
                    # Keep session alive with progress updates
                    upload_start = time.time()
                    last_update = upload_start

                    while True:
                        current_time = time.time()
                        if current_time - last_update >= 5:  # Update every 5 seconds
                            elapsed = int(current_time - upload_start)
                            await progress_msg.edit_text(f"Uploading to Gofile... ({elapsed}s elapsed)\nPlease wait, large files may take several minutes.")
                            last_update = current_time

                        # Try upload with timeout
                        try:
                            gofile_url = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(None, lambda: upload_to_gofile(filename)),
                                timeout=1000  # 10 minute timeout
                            )
                            break
                        except asyncio.TimeoutError:
                            raise Exception("Upload timed out after 10 minutes")

                    # Send new message instead of editing
                    await app.send_message(
                        chat_id=message.chat.id,
                        text=f"<b>✅ Upload Successful</b>\n\n"
                             f"<b>🎵 Title:</b> {info['title']}\n"
                             f"<b>📊 Size:</b> {file_size_mb:.2f}MB\n"
                             f"<b>📥 Download:</b> <a href='{gofile_url}'>Click Here</a>\n\n"
                             f"<i>Note: Gofile links will expire after some time.</i>",
                        disable_web_page_preview=True,
                    )
                    # Log successful Gofile upload
                    await app.send_message(
                        LOG_CHANNEL,
                        f"#GOFILE_UPLOAD\n"
                        f"User: {message.chat.title or message.chat.first_name} [`{message.chat.id}`]\n"
                        f"Title: {info['title']}\n"
                        f"Size: {file_size_mb:.2f}MB\n"
                        f"Link: {gofile_url}"
                    )
                    # Try to delete progress message after sending new message
                    try:
                        await progress_msg.delete()
                    except:
                        pass

                except Exception as e:
                    await message.reply_text(f"❌ Upload failed!\nError: {str(e)}\nSize: {file_size_mb:.2f}MB")
            else:
                await message.edit_text("📤 Uploading WAV file to Telegram...")

                await app.send_document(
                    chat_id=message.chat.id,
                    document=filename,
                    caption=f"🎵 {info['title']}",
                    force_document=True
                )
                # Send to log channel
                await app.send_document(
                    chat_id=LOG_CHANNEL,
                    document=filename,
                    caption=f"#TELEGRAM_UPLOAD\n"
                            f"🎵 {info['title']}\n"
                            f"Requested by: {message.from_user.mention}\n"
                            f"Size: {file_size_mb:.2f}MB"
                )

                await message.edit_text("✅ Download and conversion completed!")
                time.sleep(5)  # Wait for 1 second before deleting the message
                await message.delete()
    except Exception as e:
        await message.edit_text(f"❌ Error: {str(e)}")
    
    finally:
        # Cleanup
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
        except:
            pass

def check_auth(func):
    async def wrapper(client, message):
        user_id = message.from_user.id
        if user_id not in AUTHORIZED_USERS:
            await message.reply_text("❌ You are not authorized to use this bot.")
            return
        return await func(client, message)
    return wrapper

@app.on_message(filters.command("start"))
@check_auth
async def start_command(client, message):
    user = message.from_user
    # Log to channel
    await app.send_message(
        LOG_CHANNEL,
        f"#USER_START\n"
        f"User: {user.mention} [`{user.id}`]\n"
        f"Username: @{user.username}"
    )

    await message.reply_text(
        f"👋 Hello {message.from_user.mention}!\n\n"
        f"Send me a YouTube link to download it as WAV audio.\n"
    )

@app.on_message(filters.command("help"))
@check_auth
async def help_command(client, message):
    await message.reply_text(
        "📖 How to use:\n\n"
        "Just send me a YouTube link and I'll convert it to WAV format. if file is too large, I'll automatically upload it to Gofile."
    )

@app.on_message(filters.regex(r'(https?:\/\/)?((www\.)?youtube\.com|youtu\.be)\/.*'))
@check_auth
async def youtube_link_handler(client, message):
    url = message.text.strip()
    user = message.from_user
    status_message = await message.reply_text("🔍 Processing...")

    # Log download start
    await app.send_message(
        LOG_CHANNEL,
        f"#NEW_DOWNLOAD\n"
        f"User: {user.mention} [`{user.id}`]\n"
        f"URL: {url}"
    )
    
    try:
        await download_audio(url, status_message)
    except Exception as e:
        # Log error
        await app.send_message(
            LOG_CHANNEL,
            f"#DOWNLOAD_ERROR\n"
            f"User: {user.mention} [`{user.id}`]\n"
            f"URL: {url}\n"
            f"Error: {str(e)}"
        )
        await status_message.edit_text(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("Bot Started!")
    app.run()