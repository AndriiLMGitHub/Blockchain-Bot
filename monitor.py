import asyncio
import aiohttp
import logging
from dataclasses import dataclass
from typing import Callable, Awaitable

from config import DEX_API_URL, CHECK_INTERVAL, BASE_UP_QUOTE_DOWN_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass
class LiquiditySnapshot:
    base: float
    quote: float


@dataclass
class AlertEvent:
    condition: int  # 1 або 2
    old: LiquiditySnapshot
    new: LiquiditySnapshot
    base_change: float
    quote_change: float


# ── State ─────────────────────────────────────────────────────────────────────

_last_snapshot: LiquiditySnapshot | None = None
_subscribers: list[int] = []


def subscribe(chat_id: int) -> bool:
    if chat_id not in _subscribers:
        _subscribers.append(chat_id)
        return True
    return False


def unsubscribe(chat_id: int) -> bool:
    if chat_id in _subscribers:
        _subscribers.remove(chat_id)
        return True
    return False


def get_subscribers() -> list[int]:
    return list(_subscribers)


def get_last_snapshot() -> LiquiditySnapshot | None:
    return _last_snapshot


# ── API fetch ─────────────────────────────────────────────────────────────────

async def fetch_snapshot(session: aiohttp.ClientSession) -> LiquiditySnapshot | None:
    try:
        async with session.get(DEX_API_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.warning(f"API returned status {resp.status}")
                return None

            data = await resp.json()
            pairs = data.get("pairs")
            if not pairs:
                logger.warning("No pairs in API response")
                return None

            liquidity = pairs[0].get("liquidity", {})
            base  = liquidity.get("base")
            quote = liquidity.get("quote")

            if None in (base, quote):
                logger.warning(f"Missing liquidity fields: {liquidity}")
                return None

            return LiquiditySnapshot(base=float(base), quote=float(quote))

    except asyncio.TimeoutError:
        logger.error("Request timed out")
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error: {e}")
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Parse error: {e}")

    return None


# ── Condition checks ──────────────────────────────────────────────────────────

def check_conditions(old: LiquiditySnapshot, new: LiquiditySnapshot) -> AlertEvent | None:
    base_change  = new.base  - old.base
    quote_change = new.quote - old.quote

    # Умова 1: base росте, quote падає, сумарна різниця >= порогу
    if base_change > 0 and quote_change < 0:
        diff = base_change + abs(quote_change)
        if diff >= BASE_UP_QUOTE_DOWN_THRESHOLD:
            return AlertEvent(1, old, new, base_change, quote_change)

    # Умова 2: обидва одночасно падають
    if base_change < 0 and quote_change < 0:
        return AlertEvent(2, old, new, base_change, quote_change)

    return None


# ── Monitor loop ──────────────────────────────────────────────────────────────

async def price_monitor_loop(
    notify_callback: Callable[[list[int], AlertEvent], Awaitable[None]]
) -> None:
    global _last_snapshot

    async with aiohttp.ClientSession() as session:
        logger.info("Price monitor started")

        while True:
            try:
                snapshot = await fetch_snapshot(session)

                if snapshot is not None:
                    if _last_snapshot is not None:
                        event = check_conditions(_last_snapshot, snapshot)

                        if event:
                            _print_alert(event)
                            if _subscribers:
                                await notify_callback(list(_subscribers), event)
                    else:
                        logger.info(
                            f"Initial snapshot — base: {snapshot.base:.2f} | "
                            f"quote: {snapshot.quote:.2f}"
                        )

                    _last_snapshot = snapshot

            except Exception as e:
                logger.error(f"Unexpected error in monitor loop: {e}")

            await asyncio.sleep(CHECK_INTERVAL)


def _print_alert(event: AlertEvent) -> None:
    label = (
        "BASE ↑  /  QUOTE ↓  (різниця ≥ 5000$)"
        if event.condition == 1
        else "BASE ↓  /  QUOTE ↓  (обидва падають)"
    )
    print(
        f"\n{'='*50}\n"
        f"  🚨 УМОВА {event.condition}: {label}\n"
        f"  BASE:   {event.old.base:.2f}  →  {event.new.base:.2f}  ({event.base_change:+.2f})\n"
        f"  QUOTE:  {event.old.quote:.2f}  →  {event.new.quote:.2f}  ({event.quote_change:+.2f})\n"
        f"{'='*50}\n",
        flush=True,
    )
    logger.info(
        f"Alert condition {event.condition} | "
        f"base {event.base_change:+.2f} | quote {event.quote_change:+.2f}"
    )