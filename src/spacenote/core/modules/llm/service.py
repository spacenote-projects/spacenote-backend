from uuid import UUID

from spacenote.core.core import Service
from spacenote.core.modules.llm.models import ParsedApiCall
from spacenote.core.modules.space.models import Space


class LLMService(Service):
    """LLM service for parsing natural language into API calls"""

    def parse_intent(self, text: str, available_spaces: list[Space], current_user_id: UUID) -> ParsedApiCall:
        """
        Parse natural language into ready-to-use API call.

        Args:
            text: User's natural language input
            available_spaces: List of Space objects user has access to
            current_user_id: Current user UUID (for context)

        Returns:
            ParsedApiCall with method, path, and body
        """
        raise NotImplementedError("LLM integration not implemented yet")
