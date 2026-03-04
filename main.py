import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from config import BOT_TOKEN, CHECK_INTERVAL, BASE_UP_QUOTE_DOWN_THRESHOLD
from monitor import (
    price_monitor_loop,
    subscribe,
    unsubscribe,
    get_last_snapshot,
    get_subscribers,
    AlertEvent,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

dp = Dispatcher()


# ── Notification ──────────────────────────────────────────────────────────────

async def notify_subscribers(bot: Bot, chat_ids: list[int], alert: AlertEvent) -> None:
    o, n = alert.old, alert.new

    if alert.condition == 1:
        title = "🚨 <b>УМОВА 1: BASE ↑ і QUOTE ↓</b>"
        diff_line = f"📐 Різниця: <code>{alert.base_change + abs(alert.quote_change):+.2f}</code>\n"
    else:
        title = "🚨 <b>УМОВА 2: BASE ↓ і QUOTE ↓</b> (обидва падають)"
        diff_line = ""

    text = (
        f"{title}\n\n"
        f"BASE   було: <code>{o.base:.2f}</code>\n"
        f"BASE  стало: <code>{n.base:.2f}</code>  (<code>{alert.base_change:+.2f}</code>)\n\n"
        f"QUOTE  було: <code>{o.quote:.2f}</code>\n"
        f"QUOTE стало: <code>{n.quote:.2f}</code>  (<code>{alert.quote_change:+.2f}</code>)\n\n"
        f"{diff_line}"
    )

    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Failed to notify {chat_id}: {e}")


# ── Handlers ──────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    is_new = subscribe(message.chat.id)
    if is_new:
        await message.answer(
            "✅ <b>Підписка активована!</b>\n\n"
            f"Пара: <code>DehSVMLfV4fjyn9JAfgvDbT9kE2t97WnGJTXFnk7EkQx</code>\n"
            f"⏱ Перевірка кожні <b>{CHECK_INTERVAL} сек</b>\n\n"
            "🔔 <b>Сповіщення при:</b>\n"
            f"1️⃣ BASE ↑ і QUOTE ↓  з різницею ≥ <b>{BASE_UP_QUOTE_DOWN_THRESHOLD:,.0f}</b>\n"
            "2️⃣ BASE ↓ і QUOTE ↓  одночасно\n\n"
            "Команди:\n"
            "/price — поточні значення\n"
            "/stop  — відписатись",
            parse_mode="HTML",
        )
    else:
        await message.answer("Ви вже підписані. /stop — відписатись.")


@dp.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    if unsubscribe(message.chat.id):
        await message.answer("🔕 Підписку скасовано. /start — підписатись знову.")
    else:
        await message.answer("Ви не підписані. /start — підписатись.")


@dp.message(Command("price"))
async def cmd_price(message: Message) -> None:
    snap = get_last_snapshot()
    if snap is None:
        await message.answer("⏳ Дані ще не отримані, зачекайте...")
    else:
        await message.answer(
            f"💧 <b>Поточна Liquidity</b>\n"
            f"BASE:  <code>{snap.base:.2f}</code>\n"
            f"QUOTE: <code>{snap.quote:.2f}</code>",
            parse_mode="HTML",
        )


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    snap = get_last_snapshot()
    subs = get_subscribers()
    snap_text = (
        f"\n\n<b>Останній знімок:</b>\n"
        f"BASE:  <code>{snap.base:.2f}</code>\n"
        f"QUOTE: <code>{snap.quote:.2f}</code>"
        if snap else "\n\nДані ще не отримані"
    )
    await message.answer(
        f"📡 <b>Статус монітора</b>\n\n"
        f"Підписників: <b>{len(subs)}</b>\n"
        f"Інтервал: <b>{CHECK_INTERVAL} сек</b>\n\n"
        f"<b>Умови сповіщення:</b>\n"
        f"1️⃣ BASE↑ + QUOTE↓ різниця ≥ <b>{BASE_UP_QUOTE_DOWN_THRESHOLD:,.0f}</b>\n"
        f"2️⃣ BASE↓ + QUOTE↓ одночасно"
        f"{snap_text}",
        parse_mode="HTML",
    )


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    bot = Bot(token=BOT_TOKEN)

    async def on_alert(chat_ids: list[int], alert: AlertEvent) -> None:
        await notify_subscribers(bot, chat_ids, alert)

    await asyncio.gather(
        price_monitor_loop(on_alert),
        dp.start_polling(bot),
    )


if __name__ == "__main__":
    logger.info("Bot is starting...")
    asyncio.run(main())