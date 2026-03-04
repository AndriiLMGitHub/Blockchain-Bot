import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from config import BOT_TOKEN, PRICE_CHANGE_THRESHOLD, CHECK_INTERVAL
from monitor import (
    price_monitor_loop,
    subscribe,
    unsubscribe,
    get_last_price,
    get_subscribers,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

dp = Dispatcher()


# ── Notification callback ────────────────────────────────────────────────────

async def notify_subscribers(
    bot: Bot,
    chat_ids: list[int],
    old_price: float,
    new_price: float,
    change: float,
) -> None:
    direction = "📈 Зросла" if change > 0 else "📉 Впала"
    text = (
        f"{direction} на <b>{abs(change):.6f} USD</b>\n\n"
        f"💧 Liquidity USD\n"
        f"Було: <code>{old_price:.6f}</code>\n"
        f"Стало: <code>{new_price:.6f}</code>\n"
        f"Зміна: <code>{change:+.6f}</code>"
    )
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Failed to notify {chat_id}: {e}")


# ── Handlers ─────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    is_new = subscribe(message.chat.id)
    if is_new:
        await message.answer(
            "✅ <b>Підписка активована!</b>\n\n"
            f"Я стежу за ціною пари <code>DehSVMLfV4fjyn9JAfgvDbT9kE2t97WnGJTXFnk7EkQx</code>\n"
            f"📊 Поле: <b>liquidity.usd</b>\n"
            f"⏱ Перевірка кожні <b>{CHECK_INTERVAL} сек</b>\n"
            f"🔔 Сповіщення при зміні ≥ <b>{PRICE_CHANGE_THRESHOLD} USD</b>\n\n"
            "Команди:\n"
            "/price — поточна ціна\n"
            "/stop — відписатись",
            parse_mode="HTML",
        )
    else:
        await message.answer("Ви вже підписані! Використайте /stop щоб відписатись.")


@dp.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    was_subscribed = unsubscribe(message.chat.id)
    if was_subscribed:
        await message.answer("🔕 Підписку скасовано. Введіть /start щоб підписатись знову.")
    else:
        await message.answer("Ви не підписані. Введіть /start щоб підписатись.")


@dp.message(Command("price"))
async def cmd_price(message: Message) -> None:
    price = get_last_price()
    if price is None:
        await message.answer("⏳ Ціна ще не отримана, зачекайте трохи...")
    else:
        await message.answer(
            f"💧 Поточна <b>Liquidity USD</b>:\n"
            f"<code>{price:.6f}</code>",
            parse_mode="HTML",
        )


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    subs = get_subscribers()
    price = get_last_price()
    await message.answer(
        f"📡 <b>Статус монітора</b>\n\n"
        f"Підписників: <b>{len(subs)}</b>\n"
        f"Остання ціна: <code>{price:.6f if price else 'N/A'}</code>\n"
        f"Поріг сповіщення: <b>{PRICE_CHANGE_THRESHOLD} USD</b>\n"
        f"Інтервал перевірки: <b>{CHECK_INTERVAL} сек</b>",
        parse_mode="HTML",
    )


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    bot = Bot(token=BOT_TOKEN)

    # Wrap callback so it captures the bot instance
    async def on_price_change(
        chat_ids: list[int], old: float, new: float, change: float
    ) -> None:
        await notify_subscribers(bot, chat_ids, old, new, change)

    # Run monitor and polling concurrently
    await asyncio.gather(
        price_monitor_loop(on_price_change),
        dp.start_polling(bot),
    )


if __name__ == "__main__":
    logger.info("Bot is starting...")
    asyncio.run(main())