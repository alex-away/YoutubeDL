from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatAction
import yt_dlp
import os
import asyncio
import requests
import time
from config import *

# Initialize bot
app = Client(
    "yt_wav_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

DOWNLOAD_DIR = "downloads/"
MAX_TG_FILE_SIZE = 1.8 * 1024 * 1024 * 1024  # 1.8 GB in bytes

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
        print(f"Gofile upload error: {str(e)}")
        return None

async def download_youtube_wav(url, message):
    """
    Downloads audio from a YouTube video and converts it to WAV format.
    """
    filename = None
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'quiet': True,
        }

        await message.edit_text("⏳ Downloading and converting to WAV...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: ydl.extract_info(url, download=False)
            )
            
            filename = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".wav"
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: ydl.download([url])
            )

        # Check file size
        file_size = os.path.getsize(filename)
        
        if file_size > MAX_TG_FILE_SIZE:
            await message.edit_text("📤 File too large for Telegram. Uploading to Gofile...")
            
            # Upload to Gofile
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
                
                # Send log for Gofile upload
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
            # Send via Telegram
            await message.edit_text("📤 Uploading WAV file...")
            await app.send_chat_action(message.chat.id, ChatAction.UPLOAD_AUDIO)
            
            # Send to user
            sent_audio = await app.send_audio(
                chat_id=message.chat.id,
                audio=filename,
                caption=f"🎵 {info['title']}"
            )
            
            await message.edit_text("✅ Download and conversion completed!")
            
            # Forward the audio to log channel with additional info
            log_text = (
                f"#NEW_DOWNLOAD #TELEGRAM\n\n"
                f"**👤 User:** {message.from_user.mention}\n"
                f"**🆔 User ID:** `{message.from_user.id}`\n"
                f"**🔗 Source URL:** {url}\n"
                f"**📤 Output Type:** Telegram Audio\n"
                f"**⏰ Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # First send the log message
            await app.send_message(LOG_CHANNEL, log_text)
            
            # Then forward the audio file
            await sent_audio.forward(LOG_CHANNEL)

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        await message.edit_text(error_msg)
        
        # Log the error
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
        # Cleanup
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
        "Note: Files larger than 1.8GB will be uploaded to Gofile."
    )

@app.on_message(filters.regex(r'(https?:\/\/)?((www\.)?youtube\.com|youtu\.be)\/.*'))
async def youtube_link_handler(client, message):
    url = message.text.strip()
    status_message = await message.reply_text("🔍 Processing YouTube link...")
    
    try:
        with yt_dlp.YoutubeDL() as ydl:
            try:
                ydl.extract_info(url, download=False)
            except:
                await status_message.edit_text("❌ Invalid YouTube URL!")
                return
        
        await download_youtube_wav(url, status_message)
        
    except Exception as e:
        await status_message.edit_text(f"❌ Error: {str(e)}")

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    print("Starting bot...")
    app.run()

if __name__ == "__main__":
    main()