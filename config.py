import os
from dotenv import load_dotenv

load_dotenv()

# Bot token from .env
BOT_TOKEN = os.getenv("BOT_TOKEN")

# DEX API
DEX_API_URL = "https://api.dexscreener.com/latest/dex/pairs/solana/DehSVMLfV4fjyn9JAfgvDbT9kE2t97WnGJTXFnk7EkQx"

# How often to check price (seconds)
CHECK_INTERVAL = 30

# ── Умова 1: base росте, quote падає ────────────────────────────────────────
# Спрацьовує коли base_change > 0, quote_change < 0
# і різниця між ними >= BASE_UP_QUOTE_DOWN_THRESHOLD
BASE_UP_QUOTE_DOWN_THRESHOLD = 5000.0  # змінюй тут

# ── Умова 2: base і quote одночасно падають ──────────────────────────────────
# Мінімальне падіння кожного поля в USD щоб вважати що воно "падає"
# 0.0 = будь-яке падіння спрацює
BOTH_DOWN_MIN_CHANGE = 0.0  # змінюй тут