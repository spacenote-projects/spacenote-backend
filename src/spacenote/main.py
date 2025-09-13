"""Application entry point for SpaceNote backend server."""

from spacenote.app import App
from spacenote.config import Config
from spacenote.logging import setup_logging
from spacenote.web.runner import run_server


def main() -> None:
    config = Config()
    setup_logging(config.debug)
    app = App(config)
    run_server(app, config)


if __name__ == "__main__":
    main()
