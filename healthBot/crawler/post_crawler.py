"""
post_crawler.py — Fetches all published posts via Blogger API v3.

Cache behaviour:
  - Cache lives at CACHE_FILE (healthBot/cache/posts_cache.json)
  - Cache is valid for CACHE_MAX_AGE_DAYS days
  - force_refresh=True bypasses cache and always re-fetches
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

from config import (
    BLOG_DOMAIN,
    BLOGGER_FIELDS,
    CACHE_DIR,
    CACHE_FILE,
    CACHE_MAX_AGE_DAYS,
)
from auth import build_service, get_blog_id


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _load_cache() -> dict | None:
    """Return cached data if it exists and is still fresh, else None."""
    if not os.path.exists(CACHE_FILE):
        return None
    with open(CACHE_FILE, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    fetched_at = datetime.fromisoformat(data.get("fetched_at", "2000-01-01T00:00:00+00:00"))
    age = datetime.now(timezone.utc) - fetched_at
    if age < timedelta(days=CACHE_MAX_AGE_DAYS):
        return data
    return None


def _save_cache(posts: list[dict]):
    _ensure_cache_dir()
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "posts": posts,
    }
    with open(CACHE_FILE, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# API fetch
# ---------------------------------------------------------------------------

def _fetch_from_api() -> list[dict]:
    """Call Blogger API v3 with pagination, return full post list."""
    blog_id = get_blog_id()
    service = build_service()

    posts = []
    page_token = None
    page_num   = 0

    while True:
        page_num += 1
        print(f"\rFetching page {page_num}...", end="", flush=True)

        kwargs = dict(
            blogId=blog_id,
            status='LIVE',
            fields=BLOGGER_FIELDS,
            maxResults=20,
        )
        if page_token:
            kwargs['pageToken'] = page_token

        try:
            result    = service.posts().list(**kwargs).execute()
        except Exception as exc:
            print(f"\n[crawler] ERROR fetching page {page_num}: {exc}")
            print("[crawler] Cache NOT updated. Exiting.")
            sys.exit(1)

        items = result.get('items', [])
        for item in items:
            posts.append({
                "id":        item.get("id", ""),
                "title":     item.get("title", ""),
                "url":       item.get("url", ""),
                "content":   item.get("content", ""),
                "published": item.get("published", ""),
            })

        page_token = result.get('nextPageToken')
        if not page_token:
            break

    print(f"\r[crawler] Fetched {len(posts)} posts ({page_num} page(s)).          ")
    return posts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_posts(force_refresh: bool = False) -> list[dict]:
    """
    Return list of all published posts.

    Each post: {"id", "title", "url", "content", "published"}

    Args:
        force_refresh: If True, ignore cache and fetch fresh from API.
    """
    if not force_refresh:
        cached = _load_cache()
        if cached is not None:
            posts = cached["posts"]
            print(f"[crawler] Using cached data ({len(posts)} posts). "
                  f"Use --refresh-cache to force re-fetch.")
            return posts

    posts = _fetch_from_api()
    _save_cache(posts)
    return posts
