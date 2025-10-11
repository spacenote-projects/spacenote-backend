from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from spacenote.core.modules.llm.models import LLMLog, ParsedApiCall
from spacenote.core.pagination import PaginationResult
from spacenote.web.deps import AppDep, AuthTokenDep
from spacenote.web.openapi import ErrorResponse

router = APIRouter(prefix="/llm", tags=["llm"])


class ParseRequest(BaseModel):
    text: str


@router.post("/parse")
async def parse_intent(request: ParseRequest, app: AppDep, auth_token: AuthTokenDep) -> ParsedApiCall:
    """Parse natural language into ready API call"""
    return await app.parse_llm_intent(auth_token, request.text)


@router.get(
    "/logs",
    summary="List LLM logs",
    description="Get paginated LLM logs. Admin only.",
    operation_id="listLLMLogs",
    responses={
        200: {"description": "Paginated list of LLM logs"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Admin privileges required"},
    },
)
async def list_llm_logs(
    app: AppDep,
    auth_token: AuthTokenDep,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
) -> PaginationResult[LLMLog]:
    return await app.get_llm_logs(auth_token, limit, offset)
