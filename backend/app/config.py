import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "").strip() or None
DEFAULT_LOOKBACK_DAYS = int(os.environ.get("DEFAULT_LOOKBACK_DAYS", "365"))

DB_PATH = Path(__file__).resolve().parent.parent / "activity.db"
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

GITHUB_API_URL = "https://api.github.com"
MAX_CONCURRENT_REQUESTS = 8
