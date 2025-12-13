from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import sys
from . import config


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("bot")
    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        config.LOG_FILE.as_posix(), maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(fmt)
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))

    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    logging.getLogger("discord.client").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)

    return logger