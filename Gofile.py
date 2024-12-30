import os
import requests
from datetime import datetime

def upload_to_gofile(file_path):
    try:
        # Get best server
        server_response = requests.get('https://api.gofile.io/getServer')
        server = server_response.json()['data']['server']
        
        # Upload URL
        upload_url = f'https://{server}.gofile.io/uploadFile'
        
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