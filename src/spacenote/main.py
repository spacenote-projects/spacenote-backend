import uvicorn

from spacenote.app import App
from spacenote.config import Config
from spacenote.logging import setup_logging
from spacenote.web.server import create_fastapi_app


def main() -> None:
    config = Config()
    setup_logging(config.debug)
    app = App(config)
    fastapi_app = create_fastapi_app(app, config)
    uvicorn.run(fastapi_app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
