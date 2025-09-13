"""Uvicorn server runner with custom configuration."""

import uvicorn
from uvicorn.config import LOGGING_CONFIG

from spacenote.app import App
from spacenote.config import Config
from spacenote.web.server import create_fastapi_app


def run_server(app: App, config: Config) -> None:
    """Run the Uvicorn server with custom logging configuration."""
    fastapi_app = create_fastapi_app(app, config)

    log_config = LOGGING_CONFIG.copy()
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s - "%(request_line)s" %(status_code)s'
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"

    uvicorn.run(fastapi_app, host=config.host, port=config.port, log_config=log_config, access_log=True)
