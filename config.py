import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

DEX_API_URL = "https://api.dexscreener.com/latest/dex/pairs/solana/DehSVMLfV4fjyn9JAfgvDbT9kE2t97WnGJTXFnk7EkQx"

CHECK_INTERVAL = 10

# Умова 1: base росте, quote падає — мінімальна сумарна різниця
BASE_UP_QUOTE_DOWN_THRESHOLD = 5000.0  # змінюй тут

# Умова 2: обидва падають — без додаткового порогу