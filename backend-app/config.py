import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "lycee-muhura-secure-key-2026")
    # An empty DATABASE_URL (as left in .env for the local setup) must not
    # override the SQLite default: dotenv still defines the variable.
    SQLALCHEMY_DATABASE_URI = (os.environ.get("DATABASE_URL") or "").strip() \
        or "sqlite:///lyceedemuhura.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Supabase and other hosted PostgreSQL services can close idle pooled
    # connections. Check a connection before reuse and periodically recycle it.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 100 * 1024 * 1024))
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    RFID_DEVICE_TOKEN = os.environ.get("RFID_DEVICE_TOKEN", "")
    RFID_DEVICE_CLASS = os.environ.get("RFID_DEVICE_CLASS", "").strip()
    # Optional: the full URL the ESP32 polls, used by the RFID scanner help page
    # so the configured value can be checked against the firmware.
    RFID_STATUS_URL = os.environ.get("RFID_STATUS_URL", "").strip()
    ROOM_CAPACITY_LIMITS = os.environ.get("ROOM_CAPACITY_LIMITS", "{}")
    MS_GRAPH_TENANT_ID = os.environ.get("MS_GRAPH_TENANT_ID", "")
    MS_GRAPH_CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID", "")
    MS_GRAPH_CLIENT_SECRET = os.environ.get("MS_GRAPH_CLIENT_SECRET", "")
    MS_GRAPH_CALENDAR_MAILBOX = os.environ.get("MS_GRAPH_CALENDAR_MAILBOX", "")
    MS_GRAPH_TIME_ZONE = os.environ.get("MS_GRAPH_TIME_ZONE", "South Africa Standard Time")
    MS_GRAPH_CREATE_TEAMS_MEETINGS = os.environ.get("MS_GRAPH_CREATE_TEAMS_MEETINGS", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
