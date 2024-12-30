import os
import time
import aiohttp
import requests

class GofileUploader:
    def __init__(self, status_msg):
        self.status_msg = status_msg
        self.last_update_time = 0
        self.update_interval = 3  # seconds

    async def update_progress(self, current, total):
        current_time = time.time()
        if current_time - self.last_update_time > self.update_interval:
            percentage = (current / total) * 100
            speed = current / (current_time - self.start_time)
            
            def format_size(size):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024:
                        return f"{size:.2f}{unit}"
                    size /= 1024
                return f"{size:.2f}TB"
            
            current_size = format_size(current)
            total_size = format_size(total)
            speed_str = format_size(speed) + "/s"
            
            try:
                await self.status_msg.edit_text(
                    f"📤 Uploading to Gofile...\n"
                    f"📊 Progress: {percentage:.1f}%\n"
                    f"📦 Size: {current_size}/{total_size}\n"
                    f"⚡️ Speed: {speed_str}"
                )
            except Exception:
                pass
            
            self.last_update_time = current_time

    async def upload_file(self, file_path):
        try:
            # Get best server
            server_response = requests.get('https://api.gofile.io/getServer')
            if server_response.status_code != 200:
                raise Exception("Failed to get Gofile server")
            
            server = server_response.json()['data']['server']
            upload_url = f'https://{server}.gofile.io/uploadFile'

            # Get file size
            total_size = os.path.getsize(file_path)
            
            # Initialize upload
            self.start_time = time.time()
            
            class ProgressFile:
                def __init__(self, path, callback):
                    self.path = path
                    self.callback = callback
                    self.current_size = 0
                    self.total_size = os.path.getsize(path)

                async def read(self, chunk_size):
                    with open(self.path, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            self.current_size += len(chunk)
                            await self.callback(self.current_size, self.total_size)
                            yield chunk

            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                form.add_field('file',
                             ProgressFile(file_path, self.update_progress),
                             filename=os.path.basename(file_path))
                
                async with session.post(upload_url, data=form) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result['status'] == 'ok':
                        return result['data']['downloadPage']
                    else:
                        raise Exception(f'Upload failed: {result.get("status")}')
                        
        except Exception as e:
            raise Exception(f'Gofile upload error: {str(e)}')