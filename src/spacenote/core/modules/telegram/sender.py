"""Telegram message sending via Bot API."""

import structlog
from telegram import Bot
from telegram.error import TelegramError

logger = structlog.get_logger(__name__)


async def send_telegram_message(token: str, chat_id: str, text: str, parse_mode: str | None = None) -> tuple[bool, str | None]:
    """Send a text message to Telegram.

    Args:
        token: Telegram Bot API token
        chat_id: Target chat ID (numeric or @username)
        text: Message text to send
        parse_mode: Optional parse mode (HTML, Markdown, etc.)

    Returns:
        Tuple of (success: bool, error_message: str | None)
        - (True, None) on success
        - (False, error_message) on failure
    """
    try:
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except TelegramError as e:
        error_msg = str(e)
        logger.exception("telegram_send_failed", chat_id=chat_id, error=error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = str(e)
        logger.exception("telegram_send_error", chat_id=chat_id, error=error_msg)
        return False, error_msg
    else:
        logger.debug("telegram_message_sent", chat_id=chat_id, parse_mode=parse_mode)
        return True, None
