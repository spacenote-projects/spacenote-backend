import logging

import structlog


def setup_logging(debug: bool) -> None:
    # Set log level based on debug mode
    log_level = logging.DEBUG if debug else logging.INFO

    # Configure standard library logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )

    # Suppress verbose MongoDB logs
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
    logging.getLogger("pymongo.connection").setLevel(logging.WARNING)
    logging.getLogger("pymongo.pool").setLevel(logging.WARNING)
    logging.getLogger("pymongo.server").setLevel(logging.WARNING)
    logging.getLogger("pymongo.command").setLevel(logging.WARNING)

    # Base processors for all environments
    processors: list[structlog.types.Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if debug:
        # Beautiful colored console output for development
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
