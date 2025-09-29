"""Template rendering for Telegram notifications."""

import structlog
from liquid import Environment

from spacenote.core.modules.telegram.models import TelegramTemplateContext

logger = structlog.get_logger(__name__)


def render_telegram_template(template: str, context: TelegramTemplateContext) -> str:
    """Render a Liquid template with the given context.

    Args:
        template: Liquid template string
        context: Strongly-typed template context for the specific event

    Returns:
        Rendered HTML string for Telegram

    Raises:
        ValueError: If template rendering fails
    """
    try:
        env = Environment()
        tmpl = env.from_string(template)
        return tmpl.render(**context.model_dump(mode="json"))
    except Exception as e:
        logger.exception("template_render_failed", error=str(e), template=template[:100])
        raise ValueError(f"Failed to render template: {e}") from e
