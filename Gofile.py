import os
import requests
from datetime import datetime

class GofileUploader:
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

    def upload_to_gofile(self, filepath, server):  # Changed method name to match what's being called
        """Upload a single file and return the download link"""
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return None

        try:
            # Test server connection before upload
            try:
                test_conn = requests.get(f'https://{server}.gofile.io', timeout=5)
            except:
                print(f"Cannot connect to {server}, trying alternate server...")
                server = 'store1'  # Fallback server

            print(f"Uploading to server: {server}")

            with open(filepath, 'rb') as f:
                # Updated API endpoint
                upload_url = f'https://{server}.gofile.io/uploadFile'
                files = {'file': (os.path.basename(filepath), f)}

                # Add headers and longer timeout
                headers = {
                    'Accept': 'application/json',
                }

                response = requests.post(
                    upload_url,
                    files=files,
                    headers=headers,
                    timeout=300  # 5 minute timeout for large files
                )

                print(f"Upload Response Status: {response.status_code}")
                print(f"Upload Response: {response.text[:200]}...")  # Print first 200 chars of response

                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'ok':
                        return data['data']['downloadPage']
                print(f"Upload failed for {filepath}")
                return None
        except requests.exceptions.Timeout:
            print(f"Timeout uploading {filepath} - file may be too large")
            return None
        except requests.exceptions.ConnectionError:
            print(f"Connection error uploading {filepath} - check your internet connection")
            return None
        except Exception as e:
            print(f"Error uploading {filepath}: {str(e)}")
            return None

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