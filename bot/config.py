import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

DEFAULT_COLOR = "ff0000"
VISIBILITY_PERCENT = 75
FALLBACK_SIZE_M = 10
