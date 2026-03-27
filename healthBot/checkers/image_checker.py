"""
image_checker.py — Detect broken images across all blog posts.

Strategy:
  • Parse each post's HTML with BeautifulSoup
  • Prefer data-src over src (lazy-load compatibility)
  • Skip base64 / known placeholder URLs
  • HEAD → GET fallback on 405
  • ThreadPoolExecutor for concurrency
  • De-duplicate: same URL is only checked once
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    CHECK_TIMEOUT,
    MAX_WORKERS,
    TRANSPARENT_BASE64_PREFIX,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_skippable_url(url: str) -> bool:
    """Return True for URLs we should never check (base64, placeholders, empty)."""
    if not url:
        return True
    if url.startswith("data:"):
        return True
    if url.startswith(TRANSPARENT_BASE64_PREFIX):
        return True
    return False


def _check_url(url: str) -> dict:
    """
    Perform HEAD (then GET fallback) request.

    Returns:
        {"url": str, "status_code": int} on HTTP response
        {"url": str, "error": str}       on network/timeout failure
    """
    headers = {"User-Agent": "Mozilla/5.0 (healthBot/1.0; +https://blog.icekimo.idv.tw)"}
    try:
        resp = requests.head(url, timeout=CHECK_TIMEOUT, allow_redirects=True, headers=headers)
        if resp.status_code == 405:
            # Server doesn't accept HEAD — fallback to GET stream
            resp = requests.get(url, timeout=CHECK_TIMEOUT, stream=True, headers=headers)
            resp.close()
        return {"url": url, "status_code": resp.status_code}
    except requests.exceptions.Timeout:
        return {"url": url, "error": "TIMEOUT"}
    except requests.exceptions.SSLError:
        return {"url": url, "error": "SSL_ERROR"}
    except requests.exceptions.ConnectionError:
        return {"url": url, "error": "CONNECTION_ERROR"}
    except Exception as exc:
        return {"url": url, "error": str(exc)[:80]}


def _is_broken(result: dict) -> bool:
    if "error" in result:
        return True
    code = result["status_code"]
    return code < 200 or code >= 400


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _extract_images(post: dict) -> list[dict]:
    """
    Return list of {"url", "alt", "post_title", "post_url"} from one post.
    Skips base64 / placeholder URLs.
    """
    soup  = BeautifulSoup(post["content"], "lxml")
    found = []
    for img in soup.find_all("img"):
        url = img.get("data-src") or img.get("src") or ""
        if _is_skippable_url(url):
            continue
        found.append({
            "url":        url.strip(),
            "alt":        img.get("alt", ""),
            "post_title": post["title"],
            "post_url":   post["url"],
        })
    return found


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_images(posts: list[dict]) -> list[dict]:
    """
    Scan all posts for broken images.

    Args:
        posts: List of post dicts from post_crawler.get_all_posts()

    Returns:
        List of broken image records:
        {
            "post_title": str,
            "post_url":   str,
            "url":        str,
            "alt":        str,
            "status_code": int   # present on HTTP error
            "error":       str   # present on network error
        }
    """
    # Collect all image references
    all_imgs: list[dict] = []
    for post in posts:
        all_imgs.extend(_extract_images(post))

    # De-duplicate: url → list of {post_title, post_url, alt}
    url_to_refs: dict[str, list[dict]] = {}
    for img in all_imgs:
        url_to_refs.setdefault(img["url"], []).append({
            "post_title": img["post_title"],
            "post_url":   img["post_url"],
            "alt":        img["alt"],
        })

    unique_urls  = list(url_to_refs.keys())
    total        = len(unique_urls)
    done_counter = [0]
    lock         = threading.Lock()
    url_results: dict[str, dict] = {}

    print(f"[image] Checking {total} unique image URL(s) with {MAX_WORKERS} workers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(_check_url, url): url for url in unique_urls}
        for future in as_completed(future_map):
            result = future.result()
            url    = future_map[future]
            url_results[url] = result
            with lock:
                done_counter[0] += 1
                n = done_counter[0]
            print(f"\rChecking images: {n}/{total}", end="", flush=True)

    print(f"\r[image] Done. Checked {total} image(s).                    ")

    # Build broken list — expand back to per-post references
    broken: list[dict] = []
    for url, result in url_results.items():
        if _is_broken(result):
            for ref in url_to_refs[url]:
                record = {
                    "post_title": ref["post_title"],
                    "post_url":   ref["post_url"],
                    "url":        url,
                    "alt":        ref["alt"],
                }
                if "error" in result:
                    record["error"] = result["error"]
                else:
                    record["status_code"] = result["status_code"]
                broken.append(record)

    return broken
