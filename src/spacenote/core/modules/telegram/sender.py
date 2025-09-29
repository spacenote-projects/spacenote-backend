"""Simple Telegram message sender."""

import structlog
from telegram import Bot
from telegram.error import TelegramError

logger = structlog.get_logger(__name__)


async def send_telegram_message(bot_token: str, chat_id: str, text: str) -> tuple[bool, str | None]:
    """Send a simple text message to Telegram.

    Args:
        bot_token: Telegram bot API token
        chat_id: Telegram chat ID (can be numeric or @username)
        text: Message text to send

    Returns:
        Tuple of (success, error_message)
        - success: True if message was sent successfully
        - error_message: Error details if failed, None if successful
    """
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=text)
    except TelegramError as e:
        error_msg = str(e)
        logger.exception("telegram_send_failed", chat_id=chat_id, error=error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = str(e)
        logger.exception("telegram_send_error", chat_id=chat_id, error=error_msg)
        return False, error_msg
    else:
        logger.info("telegram_message_sent", chat_id=chat_id)
        return True, None
