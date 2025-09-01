from spacenote.config import Config
from spacenote.logging import setup_logging


def main() -> None:
    config = Config()
    setup_logging(config.debug)


if __name__ == "__main__":
    main()
