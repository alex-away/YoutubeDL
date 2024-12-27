import os
from logging.handlers import RotatingFileHandler
import logging

# config.py
API_ID = 21851558
API_HASH = "045a99f29cbc003618d9786d0b4683d0"
SESSION_STRING = "AQFNbaYADerHlJEzoFs2v7I5pXNFWD8Alm2_gXdJPCPA-L_k8i1b4Yby4qRP0U74UFLlxeRPZDzLOfV1hD5Cv9BbbKJPCqAlrEWtqVqWH1AdQ6VezrBGdgdmh5SrjG49W5yd5S5XKHTtABmYWS-VpW-fNX8jkpADufZA9iefTuq7nQVY-m5C9tt3om0nDimIdeNCWnHzxTtPbGpaDwM-LXBThWZxKEweecDkqqPJgEyzmaqjlVmqqMfNEAf7Mc-bUbQzTjAz3MdN6YTKgrA1NhkYudlbbc1wavPQ44xQwyrsXncfarIiYyhHCS0YzWhNEw22MOAkx7FO-0ig7EtgZHQQ5lte2gAAAAAkChxkAA"
BOT_TOKEN = "7647640739:AAGk1I_QdLdj9ym8g8Qz3Bk0BK5id5fKYsc"
COOKIES_GIST_URL = "https://gist.githubusercontent.com/dvrajput/8d76c1c85e9f9bf6035ee4a14884121a/raw/a186db5de73d8be8800cfba2fb51d9506a239ef1/ytcookies.txt"  # Replace with your gist raw URL
LOG_CHANNEL = -1002237500924
DOWNLOAD_DIR = "downloads/"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
