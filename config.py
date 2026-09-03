import os
import secrets

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.environ.get("DB_PATH", "kitchen.db")
SECRET_KEY = os.environ.get("SECRET_KEY") or "chef_chat_secure_persistent_session_key_2026"

# Legacy WhatsApp bot config — unused by the website, kept for whatsapp_client.py
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
API_VERSION = os.environ.get("API_VERSION", "v22.0")
