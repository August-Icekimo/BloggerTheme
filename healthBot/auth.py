"""
auth.py — OAuth 2.0 credential management for healthBot.

Shares token.pickle and .env with publishBot/blogger_toolchain.py.
Both files must live at the repo root (one level above healthBot/).
"""

import os
import pickle
import sys

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import ENV_PATH, TOKEN_PATH

# ---------------------------------------------------------------------------
# Scopes — read-only is enough for health checking
# ---------------------------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/blogger.readonly']


def _load_env() -> tuple[str, str, str]:
    """Load CLIENT_ID, CLIENT_SECRET, BLOG_ID from .env at repo root."""
    load_dotenv(ENV_PATH)

    client_id     = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    blog_id       = os.getenv("BLOG_ID")

    missing = [k for k, v in
               [("CLIENT_ID", client_id), ("CLIENT_SECRET", client_secret), ("BLOG_ID", blog_id)]
               if not v]
    if missing:
        print(f"[auth] ERROR: Missing required variable(s) in .env: {', '.join(missing)}")
        print(f"[auth]        Expected .env path: {ENV_PATH}")
        sys.exit(1)

    return client_id, client_secret, blog_id


def get_credentials():
    """
    Return valid Google OAuth2 credentials.

    - Loads token.pickle from repo root if it exists and is valid.
    - Auto-refreshes expired tokens.
    - Launches browser OAuth flow if no valid token is found,
      then saves the new token to token.pickle.
    """
    client_id, client_secret, _ = _load_env()

    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as fh:
            creds = pickle.load(fh)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[auth] Token expired — refreshing...")
            creds.refresh(Request())
        else:
            print("[auth] No valid token found — launching browser OAuth flow...")
            client_config = {
                "installed": {
                    "client_id":     client_id,
                    "client_secret": client_secret,
                    "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                    "token_uri":     "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                }
            }
            flow  = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'wb') as fh:
            pickle.dump(creds, fh)
        print("[auth] Token saved.")

    return creds


def get_blog_id() -> str:
    """Return BLOG_ID from .env (validates presence)."""
    _, _, blog_id = _load_env()
    return blog_id


def build_service():
    """Convenience: return an authenticated Blogger API v3 service."""
    return build('blogger', 'v3', credentials=get_credentials())
