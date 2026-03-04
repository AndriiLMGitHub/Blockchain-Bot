import os
from dotenv import load_dotenv

load_dotenv()

# Bot token from .env
BOT_TOKEN = os.getenv("BOT_TOKEN")

# DEX API
DEX_API_URL = "https://api.dexscreener.com/latest/dex/pairs/solana/DehSVMLfV4fjyn9JAfgvDbT9kE2t97WnGJTXFnk7EkQx"

# How often to check price (seconds)
CHECK_INTERVAL = 60  # змінюй тут

# Alert threshold — notify if price changes by this USD amount or more
PRICE_CHANGE_THRESHOLD = 10000  # змінюй тут