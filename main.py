from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
import os
import asyncio
from gofile_uploader import GofileUploader
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
            
            # Check file size
            file_size = os.path.getsize(filename)
            MAX_TG_SIZE = 1932735283  # 1.8 GB

            if file_size > MAX_TG_SIZE:
                await message.edit_text("📤 File too large for Telegram. Uploading to Gofile...")
                
                # Initialize Gofile uploader
                uploader = GofileUploader(message)
                
                # Upload to Gofile
                gofile_link = await uploader.upload_file(filename)
                
                success_msg = (
                    f"✅ File uploaded successfully!\n\n"
                    f"🎵 {info['title']}\n"
                    f"📥 Download: {gofile_link}\n\n"
                    f"Note: Gofile links may expire after some time."
                )
                await message.edit_text(success_msg)
                
                # Log message
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
                await message.edit_text("📤 Uploading WAV file...")
                await app.send_chat_action(message.chat.id, ChatAction.UPLOAD_AUDIO)
                
                sent_audio = await app.send_audio(
                    chat_id=message.chat.id,
                    audio=filename,
                    caption=f"🎵 {info['title']}"
                )
                
                await message.edit_text("✅ Download and conversion completed!")

    except Exception as e:
        await message.edit_text(f"❌ Error: {str(e)}")
    
    finally:
        # Cleanup
        if filename and os.path.exists(filename):
            os.remove(filename)

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