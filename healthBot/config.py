"""
config.py — Central configuration for healthBot.
All tunable constants live here. Edit freely.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# This file lives at:  <repo_root>/healthBot/config.py
# Repo root is two levels up.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(_THIS_DIR)          # repo root

ENV_PATH   = os.path.join(BASE_DIR, '.env')
TOKEN_PATH = os.path.join(BASE_DIR, 'token.pickle')

CACHE_DIR  = os.path.join(_THIS_DIR, 'cache')
CACHE_FILE = os.path.join(CACHE_DIR, 'posts_cache.json')

REPORTS_DIR = os.path.join(_THIS_DIR, 'reports')

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
CACHE_MAX_AGE_DAYS: int = 1   # How many days before posts cache is considered stale

# ---------------------------------------------------------------------------
# HTTP health check
# ---------------------------------------------------------------------------
MAX_WORKERS:    int = 10   # ThreadPoolExecutor worker count
CHECK_TIMEOUT:  int = 10   # Seconds before a single URL is marked TIMEOUT

# ---------------------------------------------------------------------------
# Blog identity
# ---------------------------------------------------------------------------
BLOG_DOMAIN: str = "blog.icekimo.idv.tw"

# Blogger API fields to fetch (minimise payload)
BLOGGER_FIELDS: str = "items(id,title,url,content,published),nextPageToken"

# ---------------------------------------------------------------------------
# Link-checker domain lists
# ---------------------------------------------------------------------------

# These domains are always skipped (Blogger internals / Google auth etc.)
SKIP_DOMAINS: list[str] = [
    "blogger.com",
    "blogspot.com",
    "google.com",
    "goo.gl",
    "googleapis.com",
    "accounts.google.com",
    "youtube.com",
    "youtu.be",
]

# URLs from these domains get flagged as "需人工確認" (warn) instead of
# "確認失效" (broken) because they commonly block bots / scrapers.
FALSE_POSITIVE_DOMAINS: list[str] = [
    "facebook.com",
    "fb.com",
    "twitter.com",
    "x.com",
    "t.co",
    "instagram.com",
    "linkedin.com",
    "pansci.asia",
    "pixnet.net",
]

# ---------------------------------------------------------------------------
# Image checker — URLs to skip unconditionally
# ---------------------------------------------------------------------------
# Known transparent base64 placeholder produced by blogger_toolchain.py
TRANSPARENT_BASE64_PREFIX: str = "data:image/png;base64,R0lGODlhAQABAAAAACH5BAEK"
