import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # postgresql://user:pass@host:5432/dbname
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
