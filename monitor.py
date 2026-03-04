import asyncio
import aiohttp
import logging
from typing import Callable, Awaitable

from config import DEX_API_URL, CHECK_INTERVAL, PRICE_CHANGE_THRESHOLD

logger = logging.getLogger(__name__)

# Stores last known price and subscribers
_last_price: float | None = None
_subscribers: list[int] = []  # list of chat_ids


def subscribe(chat_id: int) -> bool:
    """Add chat_id to notification list. Returns True if newly added."""
    if chat_id not in _subscribers:
        _subscribers.append(chat_id)
        return True
    return False


def unsubscribe(chat_id: int) -> bool:
    """Remove chat_id from notification list. Returns True if was subscribed."""
    if chat_id in _subscribers:
        _subscribers.remove(chat_id)
        return True
    return False


def get_subscribers() -> list[int]:
    return list(_subscribers)


def get_last_price() -> float | None:
    return _last_price


async def fetch_price(session: aiohttp.ClientSession) -> float | None:
    """Fetch current USD price from DEX Screener API."""
    try:
        async with session.get(DEX_API_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.warning(f"API returned status {resp.status}")
                return None
            data = await resp.json()

            pairs = data.get("pairs")
            if not pairs or len(pairs) == 0:
                logger.warning("No pairs found in API response")
                return None

            pair = pairs[0]
            liquidity = pair.get("liquidity", {})
            price_usd = liquidity.get("usd")

            if price_usd is None:
                # fallback: try priceUsd field directly
                price_usd = pair.get("priceUsd")

            if price_usd is None:
                logger.warning("Could not find USD price in response")
                return None

            return float(price_usd)

    except asyncio.TimeoutError:
        logger.error("Request to DEX API timed out")
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error fetching price: {e}")
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error parsing API response: {e}")

    return None


async def price_monitor_loop(
    notify_callback: Callable[[list[int], float, float, float], Awaitable[None]]
) -> None:
    """
    Background loop that checks price every CHECK_INTERVAL seconds.
    Calls notify_callback(subscribers, old_price, new_price, change) when threshold exceeded.
    """
    global _last_price

    async with aiohttp.ClientSession() as session:
        logger.info("Price monitor started")

        while True:
            try:
                price = await fetch_price(session)
                print(f"Checked price: {price:.2f} USD" if price is not None else "Checked price: None", flush=True)

                if price is not None:
                    if _last_price is not None:
                        change = price - _last_price
                        if abs(change) >= PRICE_CHANGE_THRESHOLD:
                            direction = "▲ ЗРОСЛА" if change > 0 else "▼ ВПАЛА"
                            logger.info(
                                f"Price changed: {_last_price:.6f} → {price:.6f} "
                                f"(Δ {change:+.6f})"
                            )
                            print(
                                f"\n{'='*45}\n"
                                f"  💰 ЦІНА {direction}\n"
                                f"  Було:   {_last_price:.6f} USD\n"
                                f"  Стало:  {price:.6f} USD\n"
                                f"  Зміна:  {change:+.6f} USD\n"
                                f"{'='*45}\n",
                                flush=True,
                            )
                            if _subscribers:
                                await notify_callback(
                                    list(_subscribers),
                                    _last_price,
                                    price,
                                    change,
                                )
                    else:
                        logger.info(f"Initial price recorded: {price:.6f}")

                    _last_price = price

            except Exception as e:
                logger.error(f"Unexpected error in monitor loop: {e}")

            await asyncio.sleep(CHECK_INTERVAL)