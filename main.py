from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatAction
import yt_dlp
import os
import asyncio
import requests
import time
from datetime import datetime
from config import *

def check_cookies():
    """Check if cookies file exists and is valid"""
    try:
        if not os.path.exists(COOKIES_FILE):
            print("❌ Cookies file not found!")
            return False
            
        # Try to read and validate cookies file
        with open(COOKIES_FILE, 'r') as f:
            content = f.read().strip()
            if not content or len(content.splitlines()) < 5:
                print("❌ Cookies file is empty or invalid!")
                return False
            
            # Check if file contains essential YouTube cookies
            essential_cookies = ['CONSENT', 'VISITOR_INFO1_LIVE', 'LOGIN_INFO']
            found_cookies = [cookie for cookie in essential_cookies if cookie in content]
            
            if len(found_cookies) < len(essential_cookies):
                print("❌ Missing essential YouTube cookies!")
                return False
                
        print("✅ Cookies loaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error checking cookies: {str(e)}")
        return False

# Initialize bot only if cookies are valid
if check_cookies():
    app = Client(
        "yt_wav_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
else:
    print("Bot startup cancelled due to cookie validation failure!")
    exit(1)

async def verify_cookie_access(url):
    """Verify if cookies are being used for download"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'cookiefile': COOKIES_FILE,
            'extract_flat': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info.get('age_limit', 0) > 0:
                return True
            if info.get('view_count') is not None:
                return True
            return False
    except:
        return False

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
    """Downloads audio from a YouTube video and converts it to WAV format."""
    filename = None
    try:
        # First verify cookie access
        cookie_status = await verify_cookie_access(url)
        cookie_info = "✅ Using cookies" if cookie_status else "⚠️ Cookies not active"
        
        await message.edit_text(f"🔍 Processing...\n{cookie_info}")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'quiet': True,
            'cookiefile': COOKIES_FILE,
            'extract_flat': False,
            'no_warnings': True,
            'ignoreerrors': True
        }

        await message.edit_text(f"⏳ Downloading and converting to WAV...\n{cookie_info}")
        
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
        
        if file_size > MAX_TG_FILE_SIZE:
            await message.edit_text(f"📤 File too large for Telegram. Uploading to Gofile...\n{cookie_info}")
            
            gofile_link = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: upload_to_gofile(filename)
            )
            
            if gofile_link:
                success_msg = (
                    f"✅ File uploaded successfully!\n\n"
                    f"🎵 {info['title']}\n"
                    f"📥 Download: {gofile_link}\n\n"
                    f"{cookie_info}"
                )
                await message.edit_text(success_msg)
                
                log_text = (
                    f"#NEW_DOWNLOAD #GOFILE\n\n"
                    f"**👤 User:** {message.from_user.mention}\n"
                    f"**🆔 User ID:** `{message.from_user.id}`\n"
                    f"**🔗 Source URL:** {url}\n"
                    f"**📤 Output Type:** Gofile Upload\n"
                    f"**📥 Download Link:** {gofile_link}\n"
                    f"**🍪 Cookie Status:** {cookie_info}\n"
                    f"**⏰ Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                await app.send_message(LOG_CHANNEL, log_text)
            else:
                await message.edit_text("❌ Failed to upload file to Gofile.")
        else:
            await message.edit_text(f"📤 Uploading WAV file...\n{cookie_info}")
            await app.send_chat_action(message.chat.id, ChatAction.UPLOAD_AUDIO)
            
            sent_audio = await app.send_audio(
                chat_id=message.chat.id,
                audio=filename,
                caption=f"🎵 {info['title']}\n\n{cookie_info}"
            )
            
            await message.edit_text(f"✅ Download and conversion completed!\n{cookie_info}")
            
            log_text = (
                f"#NEW_DOWNLOAD #TELEGRAM\n\n"
                f"**👤 User:** {message.from_user.mention}\n"
                f"**🆔 User ID:** `{message.from_user.id}`\n"
                f"**🔗 Source URL:** {url}\n"
                f"**📤 Output Type:** Telegram Audio\n"
                f"**🍪 Cookie Status:** {cookie_info}\n"
                f"**⏰ Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await app.send_message(LOG_CHANNEL, log_text)
            await sent_audio.forward(LOG_CHANNEL)

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        await message.edit_text(f"{error_msg}\n{cookie_info}")
        
        log_text = (
            f"#ERROR\n\n"
            f"**👤 User:** {message.from_user.mention}\n"
            f"**🆔 User ID:** `{message.from_user.id}`\n"
            f"**🔗 Source URL:** {url}\n"
            f"**❌ Error:** {str(e)}\n"
            f"**🍪 Cookie Status:** {cookie_info}\n"
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
        "Use /help to see available commands.\n\n"
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
    
    print("\nStarting bot with cookie validation...")
    if not check_cookies():
        print("❌ Cookie validation failed! Bot will not start.")
        return
        
    print("✅ Cookie validation successful!")
    print("🤖 Bot is running...")
    app.run()

if __name__ == "__main__":
    main()