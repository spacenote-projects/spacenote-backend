"""Template rendering for Telegram notifications."""

from typing import Any

import structlog
from liquid import Environment

logger = structlog.get_logger(__name__)


def render_telegram_template(template: str, context: dict[str, Any]) -> str:
    """Render a Liquid template with the given context.

    Args:
        template: Liquid template string
        context: Template context variables

    Returns:
        Rendered HTML string for Telegram

    Raises:
        ValueError: If template rendering fails
    """
    try:
        env = Environment()
        tmpl = env.from_string(template)
        return tmpl.render(**context)
    except Exception as e:
        logger.exception("template_render_failed", error=str(e), template=template[:100])
        raise ValueError(f"Failed to render template: {e}") from e
