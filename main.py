from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
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

async def fetch_formats(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=False))

    formats = {}
    for f in info['formats']:
        if f['ext'] in ['mp4', 'webm']:
            height = f.get('height', 0)
            if height not in formats:
                formats[height] = {}
            formats[height][f['ext']] = f['format_id']

    formats['best_video'] = 'bestvideo+bestaudio'
    return formats

async def download_audio(url, message, format_id):
    """Download YouTube audio and convert to MP3/WAV"""
    filename = None
    try:        
        ydl_opts = {
            'format': 'bestaudio/best',
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
            filename = ydl.prepare_filename(info)

        mp3_file = filename.rsplit(".", 1)[0] + ".mp3"
        wav_file = filename.rsplit(".", 1)[0] + ".wav"

        subprocess.run(['ffmpeg', '-i', filename, '-acodec', 'libmp3lame', '-b:a', '192k', mp3_file], check=True)
        subprocess.run(['ffmpeg', '-i', filename, wav_file], check=True)

        for audio_file, ext in [(mp3_file, 'mp3'), (wav_file, 'wav')]:
            file_size = os.path.getsize(audio_file)
            file_size_mb = file_size / (1024 * 1024)

            if file_size > MAX_TG_SIZE:
                progress_msg = await message.edit_text(f"📤 {ext.upper()} file too large for Telegram. Uploading to Gofile...")

                try:
                    upload_start = time.time()
                    last_update = upload_start

                    while True:
                        current_time = time.time()
                        if current_time - last_update >= 5:
                            elapsed = int(current_time - upload_start)
                            await progress_msg.edit_text(f"Uploading to Gofile... ({elapsed}s elapsed)\nPlease wait, large files may take several minutes.")
                            last_update = current_time

                        try:
                            gofile_url = await asyncio.wait_for(
                                asyncio.get_event_loop().run_in_executor(None, lambda: upload_to_gofile(audio_file)),
                                timeout=1000
                            )
                            break
                        except asyncio.TimeoutError:
                            raise Exception("Upload timed out after 10 minutes")

                    await app.send_message(
                        chat_id=message.chat.id,
                        text=f"<b>✅ Upload Successful</b>\n\n"
                             f"<b>🎵 Title:</b> {info['title']}\n"
                             f"<b>📊 Size:</b> {file_size_mb:.2f}MB\n"
                             f"<b>📥 Download:</b> <a href='{gofile_url}'>Click Here</a>\n\n"
                             f"<i>Note: Gofile links will expire after some time.</i>",
                        disable_web_page_preview=True,
                    )
                    try:
                        await progress_msg.delete()
                    except:
                        pass

                except Exception as e:
                    await message.reply_text(f"❌ {ext.upper()} upload failed!\nError: {str(e)}\nSize: {file_size_mb:.2f}MB")
            else:
                await message.edit_text(f"📤 Uploading {ext.upper()} file to Telegram...")

                await app.send_document(
                    chat_id=message.chat.id,
                    document=audio_file,
                    caption=f"🎵 {info['title']} ({ext.upper()})",
                    force_document=True
                )

        await message.edit_text("✅ Download and conversion completed!")
        time.sleep(5)
        await message.delete()

    except Exception as e:
        await message.edit_text(f"❌ Error: {str(e)}")
    
    finally:
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
            if mp3_file and os.path.exists(mp3_file):
                os.remove(mp3_file)
            if wav_file and os.path.exists(wav_file):
                os.remove(wav_file)
        except:
            pass

async def download_video(url, message, format_id):
    """Download YouTube video"""
    filename = None
    try:        
        ydl_opts = {
            'format': format_id,
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
            filename = ydl.prepare_filename(info)

        file_size = os.path.getsize(filename)
        file_size_mb = file_size / (1024 * 1024)

        if file_size > MAX_TG_SIZE:
            progress_msg = await message.edit_text("📤 Video file too large for Telegram. Uploading to Gofile...")

            try:
                upload_start = time.time()
                last_update = upload_start

                while True:
                    current_time = time.time()
                    if current_time - last_update >= 5:
                        elapsed = int(current_time - upload_start)
                        await progress_msg.edit_text(f"Uploading to Gofile... ({elapsed}s elapsed)\nPlease wait, large files may take several minutes.")
                        last_update = current_time

                    try:
                        gofile_url = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(None, lambda: upload_to_gofile(filename)),
                            timeout=1000
                        )
                        break
                    except asyncio.TimeoutError:
                        raise Exception("Upload timed out after 10 minutes")

                await app.send_message(
                    chat_id=message.chat.id,
                    text=f"<b>✅ Upload Successful</b>\n\n"
                         f"<b>🎥 Title:</b> {info['title']}\n"
                         f"<b>📊 Size:</b> {file_size_mb:.2f}MB\n"
                         f"<b>📥 Download:</b> <a href='{gofile_url}'>Click Here</a>\n\n"
                         f"<i>Note: Gofile links will expire after some time.</i>",
                    disable_web_page_preview=True,
                )
                try:
                    await progress_msg.delete()
                except:
                    pass

            except Exception as e:
                await message.reply_text(f"❌ Video upload failed!\nError: {str(e)}\nSize: {file_size_mb:.2f}MB")
        else:
            await message.edit_text("📤 Uploading video file to Telegram...")

            await app.send_document(
                chat_id=message.chat.id,
                document=filename,
                caption=f"🎥 {info['title']}",
                force_document=True
            )

        await message.edit_text("✅ Download completed!")
        time.sleep(5)
        await message.delete()

    except Exception as e:
        await message.edit_text(f"❌ Error: {str(e)}")
    
    finally:
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
    status_message = await message.reply_text("🔍 Fetching available formats...")
    
    try:
        formats = await fetch_formats(url)
        
        buttons = [
            [
                InlineKeyboardButton("🎵 MP3", callback_data="download_mp3"),
                InlineKeyboardButton("🎵 WAV", callback_data="download_wav")  
            ]
        ]

        heights = [1080, 720, 480, 360, 240, 144]
        for height in heights:
            if height in formats:
                row = []
                if 'mp4' in formats[height]:
                    row.append(InlineKeyboardButton(f"{height}p MP4", callback_data=f"download_{formats[height]['mp4']}"))
                if 'webm' in formats[height]:
                    row.append(InlineKeyboardButton(f"{height}p WEBM", callback_data=f"download_{formats[height]['webm']}"))
                if row:
                    buttons.append(row)

        buttons.append([InlineKeyboardButton("Best Video", callback_data=f"download_{formats['best_video']}")])

        await status_message.edit_text("Select a format to download:", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        await status_message.edit_text(f"❌ Error: {str(e)}")

@app.on_callback_query(filters.regex("^download_"))
async def download_button_handler(client, callback_query):
    format_id = callback_query.data.split("_")[1]
    message = callback_query.message
    
    if not message.reply_to_message or not message.reply_to_message.text:
        await callback_query.answer("❌ Invalid message format")
        return
    
    url = message.reply_to_message.text.strip()
    
    if not url.startswith("http"):
        await callback_query.answer("❌ Invalid URL")
        return
    
    if format_id in ['mp3', 'wav']:
        await callback_query.message.edit_text(f"⏳ Downloading {format_id.upper()}...")
        await download_audio(url, callback_query.message, format_id)
    else:
        await callback_query.message.edit_text(f"⏳ Downloading {format_id}...")
        await download_video(url, callback_query.message, format_id)

if __name__ == "__main__":
    print("Bot Started!")
    app.run()