import os
from logging.handlers import RotatingFileHandler
import logging

# config.py
API_ID = 123456
API_HASH = "045a99f29cbc009786d0b4683d0"
BOT_TOKEN = "7647640739:AAGk1I_QdL8g8Qz3Bk0BK5id5fKYsc"
LOG_CHANNEL = -1002285450924
AUTHORIZED_USERS = [1722652154, 413652438]
DOWNLOAD_DIR = "downloads/"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
