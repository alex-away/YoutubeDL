import os
import asyncio
import logging
import requests
import time
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatAction
import yt_dlp
from config import *

# Initialize bot
class YoutubeBot(Client):
    def __init__(self):
        super().__init__(
            name="youtube_wav_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
        self.LOGGER = LOGGER
        self.MAX_TG_FILE_SIZE = 1932735283  # 1.8 GB in bytes

    async def start(self):
        await super().start()
        self.LOGGER.info("Bot started")
        
    async def stop(self):
        await super().stop()
        self.LOGGER.info("Bot stopped")

app = YoutubeBot()

def get_gofile_server():
    """Get best available server for upload"""
    try:
        response = requests.get('https://api.gofile.io/accounts/servers')
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok' and data.get('data'):
                return data['data'][0]
        return 'store1'
    except:
        return 'store1'

def upload_to_gofile(filepath):
    """Upload file to Gofile and return download link"""
    try:
        server = get_gofile_server()
        upload_url = f'https://{server}.gofile.io/uploadFile'
        
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f)}
            headers = {'Accept': 'application/json'}
            
            response = requests.post(
                upload_url,
                files=files,
                headers=headers,
                timeout=300
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    return data['data']['downloadPage']
        return None
    except Exception as e:
        LOGGER.error(f"Gofile upload error: {str(e)}")
        return None

async def progress(current, total, message):
    try:
        percent = (current * 100 / total)
        await message.edit_text(f"📤 Uploading: {percent:.1f}%")
    except:
        pass

async def download_youtube_wav(url, message):
    """Downloads audio from a YouTube video and converts it to WAV format."""
    filename = None
    try:
        await message.edit_text("🔍 Processing YouTube link...")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'cookiesfrombrowser': ('chrome',),  # Gets cookies directly from Chrome
            'extract_flat': False,
            'ignoreerrors': True
        }

        await message.edit_text("⏳ Downloading and converting to WAV...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: ydl.extract_info(url, download=False)
            )
            
            if not info:
                await message.edit_text("❌ Failed to extract video info. Possibly private or age-restricted video.")
                return
            
            filename = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".wav"
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ydl.download([url])
            )

        file_size = os.path.getsize(filename)
        
        if file_size > app.MAX_TG_FILE_SIZE:
            await message.edit_text("📤 File too large for Telegram. Uploading to Gofile...")
            
            gofile_link = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: upload_to_gofile(filename)
            )
            
            if gofile_link:
                success_msg = (
                    f"✅ File uploaded successfully!\n\n"
                    f"🎵 {info['title']}\n"
                    f"📥 Download: {gofile_link}"
                )
                await message.edit_text(success_msg)
                
                log_text = (
                    f"#NEW_DOWNLOAD #GOFILE\n\n"
                    f"**👤 User:** {message.from_user.mention}\n"
                    f"**🆔 User ID:** `{message.from_user.id}`\n"
                    f"**🔗 Source URL:** {url}\n"
                    f"**📤 Output Type:** Gofile Upload\n"
                    f"**📥 Download Link:** {gofile_link}\n"
                    f"**⏰ Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                await app.send_message(LOG_CHANNEL, log_text)
            else:
                await message.edit_text("❌ Failed to upload file to Gofile.")
        else:
            await message.edit_text("📤 Uploading WAV file...")
            await app.send_chat_action(message.chat.id, ChatAction.UPLOAD_AUDIO)
            
            sent_audio = await app.send_audio(
                chat_id=message.chat.id,
                audio=filename,
                caption=f"🎵 {info['title']}",
                progress=progress,
                progress_args=(message,)
            )
            
            await message.edit_text("✅ Download and conversion completed!")
            
            log_text = (
                f"#NEW_DOWNLOAD #TELEGRAM\n\n"
                f"**👤 User:** {message.from_user.mention}\n"
                f"**🆔 User ID:** `{message.from_user.id}`\n"
                f"**🔗 Source URL:** {url}\n"
                f"**📤 Output Type:** Telegram Audio\n"
                f"**⏰ Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await app.send_message(LOG_CHANNEL, log_text)
            await sent_audio.forward(LOG_CHANNEL)

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        LOGGER.error(f"Download error: {str(e)}")
        await message.edit_text(error_msg)
        
        log_text = (
            f"#ERROR\n\n"
            f"**👤 User:** {message.from_user.mention}\n"
            f"**🆔 User ID:** `{message.from_user.id}`\n"
            f"**🔗 Source URL:** {url}\n"
            f"**❌ Error:** {str(e)}\n"
            f"**⏰ Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await app.send_message(LOG_CHANNEL, log_text)
    
    finally:
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
        except:
            pass

@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text(
        "👋 Welcome to YouTube WAV Downloader Bot!\n\n"
        "Send me a YouTube link and I'll convert it to WAV format for you.\n"
        "Use /help to see available commands."
    )

@app.on_message(filters.command("help"))
async def help_command(client, message):
    await message.reply_text(
        "📖 Available commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "Just send a YouTube link to download and convert to WAV format.\n\n"
        "Features:\n"
        "• Converts to WAV format\n"
        "• Supports private/age-restricted videos\n"
        "• Automatic Gofile upload for large files\n\n"
        "Note: Files larger than 1.8GB will be uploaded to Gofile."
    )

@app.on_message(filters.regex(r'(https?:\/\/)?((www\.)?youtube\.com|youtu\.be)\/.*'))
async def youtube_link_handler(client, message):
    url = message.text.strip()
    status_message = await message.reply_text("🔍 Processing YouTube link...")
    
    try:
        await download_youtube_wav(url, status_message)
    except Exception as e:
        LOGGER.error(f"Handler error: {str(e)}")
        await status_message.edit_text(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    try:
        LOGGER.info("Starting bot...")
        app.run()
    except Exception as e:
        LOGGER.error(f"Bot error: {str(e)}")