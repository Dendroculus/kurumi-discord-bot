from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv  
    load_dotenv()
except Exception:
    pass

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parent

LOG_DIR = PROJECT_ROOT / "logs"
ASSETS_DIR = PROJECT_ROOT / "assets"

LOG_DIR.mkdir(parents=True, exist_ok=True)

POSTGRES_CONN_STRING = os.environ.get("POSTGRE_CONN_STRING")  # e.g. postgres://user:pass@host:port/dbname
USE_POSTGRES = bool(POSTGRES_CONN_STRING)  # switch based on presence of the conn string

LOG_FILE = LOG_DIR / os.environ.get("LOG_FILENAME", "bot.log")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# USING ENV VARS FOR BOT CONFIGURATION THESE ARE DEFAULTS IF NOT SET
PREFIX = os.environ.get("BOT_PREFIX", "k!")
WELCOME_CHANNEL_NAME = os.environ.get("WELCOME_CHANNEL_NAME", "💬-general")

MAX_TRACKED_USERS = int(os.environ.get("MAX_TRACKED_USERS", "5000"))
MAX_WARNINGS = int(os.environ.get("MAX_WARNINGS", "10"))
TIMEOUT_AT_WARNINGS = int(os.environ.get("TIMEOUT_AT_WARNINGS", "3"))
KICK_AT_WARNINGS = int(os.environ.get("KICK_AT_WARNINGS", "5"))
BAN_AT_WARNINGS = int(os.environ.get("BAN_AT_WARNINGS", "10"))
TIMEOUT_SECONDS_ON_THRESHOLD = int(os.environ.get("TIMEOUT_SECONDS_ON_THRESHOLD", "60"))

SPAM_TRACK_MESSAGE_COUNT = int(os.environ.get("SPAM_TRACK_MESSAGE_COUNT", "5"))
SPAM_WINDOW_SECONDS = int(os.environ.get("SPAM_WINDOW_SECONDS", "3"))

GIF_ATTACHMENTS_URL = {
    "Kurumi_URL" : "attachment://kurumi.gif",
    "Kurumi_URL_1" : "attachment://kurumi1.gif",
    "Kurumi_URL_2" : "attachment://kurumi2.gif",
    "Kurumi_URL_3" : "attachment://kurumi3.gif",
    "Kurumi_URL_4" : "attachment://kurumi4.gif",
}

GIF_ASSETS = {
    "Kurumi" : "kurumi.gif",
    "Kurumi_1" : "kurumi1.gif",
    "Kurumi_2" : "kurumi2.gif",
    "Kurumi_3" : "kurumi3.gif",
    "Kurumi_4" : "kurumi4.gif",
}

ANILIST_API = "https://graphql.anilist.co"
ANILIST_SEARCH_QUERY = """
query ($search: String) {
  Page(perPage: 5) {
    media(search: $search, type: ANIME) {
      id
      title { romaji english native }
      description(asHtml: false)
      episodes
      status
      duration
      startDate { year month day }
      endDate { year month day }
      season
      averageScore
      popularity
      favourites
      format
      source
      studios(isMain: true) { nodes { name } }
      genres
      coverImage { large medium }
      bannerImage
      siteUrl
    }
  }
}
"""

ANILIST_CHARACTER_SEARCH_QUERY = """
query ($search: String) {
  Page(perPage: 5) {
    characters(search: $search) {
      id
      name {
        full
        native
      }
      description
      image {
        large
        medium
      }
      gender
      dateOfBirth {
        year
        month
        day
      }
      age
      bloodType
      siteUrl
      favourites
      media(perPage: 4, sort: POPULARITY_DESC) {
        nodes {
          title {
            romaji
            english
          }
        }
      }
    }
  }
}
"""