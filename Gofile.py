import os
import requests
import asyncio
from datetime import datetime

class GofileUploader:
    def __init__(self):
        self.MAX_RETRIES = 3

    def get_server(self):
        """Get best available server for upload with debug info"""
        try:
            # Updated API endpoint
            response = requests.get('https://api.gofile.io/accounts/servers')
            print(f"Server Response Status: {response.status_code}")
            print(f"Server Response: {response.text}")

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok' and data.get('data'):
                    # Return the first available server
                    return data['data'][0]
            # Fallback to direct server
            return 'store1'
        except Exception as e:
            print(f"Error getting server: {str(e)}")
            # Fallback servers list
            return 'store1'

    async def upload_to_gofile(self, filepath, progress_callback=None):
        """Upload file to Gofile and return download link"""
        try:
            server = self.get_server()
            upload_url = f'https://{server}.gofile.io/uploadFile'
            
            for retry in range(self.MAX_RETRIES):
                try:
                    with open(filepath, 'rb') as f:
                        files = {'file': (os.path.basename(filepath), f)}
                        headers = {'Accept': 'application/json'}
                        
                        # If progress callback is provided
                        if progress_callback:
                            total_size = os.path.getsize(filepath)
                            current_size = 0
                            
                            class ProgressFile:
                                def __init__(self, file, total, callback):
                                    self.file = file
                                    self.total = total
                                    self.current = 0
                                    self.callback = callback
                                
                                def read(self, size):
                                    data = self.file.read(size)
                                    self.current += len(data)
                                    if self.callback:
                                        asyncio.create_task(
                                            self.callback(self.current, self.total)
                                        )
                                    return data

                            files['file'] = (
                                os.path.basename(filepath),
                                ProgressFile(f, total_size, progress_callback)
                            )
                        
                        response = requests.post(
                            upload_url,
                            files=files,
                            headers=headers,
                            timeout=300
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('status') == 'ok':
                                return {
                                    'success': True,
                                    'link': data['data']['downloadPage'],
                                    'directLink': data['data'].get('directLink'),
                                    'fileName': data['data'].get('fileName')
                                }
                        
                        print(f"Upload attempt {retry + 1} failed. Status: {response.status_code}")
                        
                except Exception as e:
                    print(f"Upload attempt {retry + 1} failed: {str(e)}")
                    if retry < self.MAX_RETRIES - 1:
                        await asyncio.sleep(5)  # Wait before retry
                    continue
            
            return {
                'success': False,
                'error': 'Max retries exceeded'
            }
            
        except Exception as e:
            print(f"Gofile upload error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def format_size(self, size):
        """Format size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f}{unit}"
            size /= 1024
        return f"{size:.2f}PB"

    async def upload_with_progress(self, filepath, message):
        """Upload file with progress updates"""
        start_time = datetime.now()
        
        async def progress_callback(current, total):
            try:
                percentage = (current * 100) / total
                elapsed_time = (datetime.now() - start_time).seconds
                speed = current / elapsed_time if elapsed_time > 0 else 0
                
                await message.edit_text(
                    f"📤 Uploading to Gofile...\n"
                    f"📊 Progress: {percentage:.1f}%\n"
                    f"📦 Size: {self.format_size(current)}/{self.format_size(total)}\n"
                    f"⚡️ Speed: {self.format_size(speed)}/s\n"
                    f"⏱ Elapsed: {elapsed_time}s"
                )
            except Exception as e:
                print(f"Progress update error: {str(e)}")
        
        result = await self.upload_to_gofile(filepath, progress_callback)
        return result