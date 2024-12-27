import os
from logging.handlers import RotatingFileHandler
import logging

# config.py
API_ID = 21851558
API_HASH = "045a99f29cbc003618d9786d0b4683d0"
SESSION_STRING = "AQFNbaYADerHlJEzoFs2v7I5pXNFWD8Alm2_gXdJPCPA-L_k8i1b4Yby4qRP0U74UFLlxeRPZDzLOfV1hD5Cv9BbbKJPCqAlrEWtqVqWH1AdQ6VezrBGdgdmh5SrjG49W5yd5S5XKHTtABmYWS-VpW-fNX8jkpADufZA9iefTuq7nQVY-m5C9tt3om0nDimIdeNCWnHzxTtPbGpaDwM-LXBThWZxKEweecDkqqPJgEyzmaqjlVmqqMfNEAf7Mc-bUbQzTjAz3MdN6YTKgrA1NhkYudlbbc1wavPQ44xQwyrsXncfarIiYyhHCS0YzWhNEw22MOAkx7FO-0ig7EtgZHQQ5lte2gAAAAAkChxkAA"
BOT_TOKEN = "7647640739:AAGk1I_QdLdj9ym8g8Qz3Bk0BK5id5fKYsc"
LOG_CHANNEL = -1002237500924
DOWNLOAD_DIR = "downloads/"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            "logs.txt",
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
LOGGER = logging.getLogger(__name__)