from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# Optional: load .env if available
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# Project root = directory of this file's parent
ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
ASSETS_DIR = PROJECT_ROOT / "assets"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / os.environ.get("DB_FILENAME", "automod.db")

LOG_FILE = LOG_DIR / os.environ.get("LOG_FILENAME", "bot.log")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

PREFIX = os.environ.get("BOT_PREFIX", "k!")
WELCOME_CHANNEL_NAME = os.environ.get("WELCOME_CHANNEL_NAME", "💬-general")

MAX_WARNINGS = int(os.environ.get("MAX_WARNINGS", "10"))
TIMEOUT_AT_WARNINGS = int(os.environ.get("TIMEOUT_AT_WARNINGS", "3"))
KICK_AT_WARNINGS = int(os.environ.get("KICK_AT_WARNINGS", "5"))
BAN_AT_WARNINGS = int(os.environ.get("BAN_AT_WARNINGS", "10"))
TIMEOUT_SECONDS_ON_THRESHOLD = int(os.environ.get("TIMEOUT_SECONDS_ON_THRESHOLD", "60"))

SPAM_TRACK_MESSAGE_COUNT = int(os.environ.get("SPAM_TRACK_MESSAGE_COUNT", "5"))
SPAM_WINDOW_SECONDS = int(os.environ.get("SPAM_WINDOW_SECONDS", "5"))