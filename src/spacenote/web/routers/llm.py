from fastapi import APIRouter
from pydantic import BaseModel

from spacenote.core.modules.llm.models import ParsedApiCall
from spacenote.web.deps import AppDep, AuthTokenDep

router = APIRouter(prefix="/llm", tags=["llm"])


class ParseRequest(BaseModel):
    text: str


@router.post("/parse", response_model=ParsedApiCall)
async def parse_intent(
    request: ParseRequest,
    app: AppDep,
    auth_token: AuthTokenDep,
) -> ParsedApiCall:
    """Parse natural language into ready API call"""
    return await app.parse_llm_intent(auth_token, request.text)
