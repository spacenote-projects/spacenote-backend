from typing import Annotated, cast

from fastapi import Depends, Request

from spacenote.app import App


async def get_app(request: Request) -> App:
    return cast(App, request.app.state.app)


# Type aliases for dependencies
AppDep = Annotated[App, Depends(get_app)]
