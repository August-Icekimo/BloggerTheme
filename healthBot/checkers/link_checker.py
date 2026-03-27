"""
link_checker.py — Detect broken external hyperlinks across all blog posts.

Strategy:
  • Parse each post's HTML with BeautifulSoup
  • Only check http:// and https:// links
  • Skip internal BLOG_DOMAIN links and SKIP_DOMAINS
  • De-duplicate: one URL is checked once, but all referencing posts are recorded
  • FALSE_POSITIVE_DOMAINS → "需人工確認" (warned), not "確認失效" (broken)
  • Errors: TooManyRedirects, SSLError, ConnectionError all categorised
  • ThreadPoolExecutor for concurrency
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    BLOG_DOMAIN,
    CHECK_TIMEOUT,
    FALSE_POSITIVE_DOMAINS,
    MAX_WORKERS,
    SKIP_DOMAINS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def _domain_matches(domain: str, domain_list: list[str]) -> bool:
    """True if domain is or is a subdomain of any entry in domain_list."""
    for d in domain_list:
        if domain == d or domain.endswith("." + d):
            return True
    return False


def _should_skip(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return True
    domain = _get_domain(url)
    if domain == BLOG_DOMAIN or domain.endswith("." + BLOG_DOMAIN):
        return True
    if _domain_matches(domain, SKIP_DOMAINS):
        return True
    return False


def _is_false_positive(url: str) -> bool:
    return _domain_matches(_get_domain(url), FALSE_POSITIVE_DOMAINS)


def _check_url(url: str) -> dict:
    """
    Perform GET request; follow redirects.

    Returns:
        {"url": str, "status_code": int}
        {"url": str, "error": str}
    """
    headers = {"User-Agent": "Mozilla/5.0 (healthBot/1.0; +https://blog.icekimo.idv.tw)"}
    try:
        resp = requests.get(
            url,
            timeout=CHECK_TIMEOUT,
            allow_redirects=True,
            stream=True,
            headers=headers,
        )
        resp.close()
        return {"url": url, "status_code": resp.status_code}
    except requests.exceptions.TooManyRedirects:
        return {"url": url, "error": "TOO_MANY_REDIRECTS"}
    except requests.exceptions.Timeout:
        return {"url": url, "error": "TIMEOUT"}
    except requests.exceptions.SSLError:
        return {"url": url, "error": "SSL_ERROR"}
    except requests.exceptions.ConnectionError:
        return {"url": url, "error": "CONNECTION_ERROR"}
    except Exception as exc:
        return {"url": url, "error": str(exc)[:80]}


def _is_ok(result: dict) -> bool:
    if "error" in result:
        return False
    return 200 <= result["status_code"] < 400


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _extract_links(post: dict) -> list[dict]:
    """Return list of {"url", "post_title", "post_url"} from one post."""
    soup  = BeautifulSoup(post["content"], "lxml")
    found = []
    for a in soup.find_all("a", href=True):
        url = a["href"].strip()
        if _should_skip(url):
            continue
        found.append({
            "url":        url,
            "post_title": post["title"],
            "post_url":   post["url"],
        })
    return found


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_links(posts: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Scan all posts for broken external links.

    Args:
        posts: List of post dicts from post_crawler.get_all_posts()

    Returns:
        (broken_links, warned_links)

        broken_links — confirmed dead:
        {
            "url":         str,
            "status_code": int | absent,
            "error":       str | absent,
            "posts":       [{"title": str, "url": str}, ...]
        }

        warned_links — possibly dead but domain blocks bots:
        {
            "url":     str,
            "status_code" | "error": ...,
            "posts":   [...],
            "warning": str
        }
    """
    # Collect all link references, de-duplicate
    url_to_refs: dict[str, list[dict]] = {}
    for post in posts:
        for link in _extract_links(post):
            url_to_refs.setdefault(link["url"], []).append({
                "title": link["post_title"],
                "url":   link["post_url"],
            })

    unique_urls  = list(url_to_refs.keys())
    total        = len(unique_urls)
    done_counter = [0]
    lock         = threading.Lock()
    url_results: dict[str, dict] = {}

    print(f"[links] Checking {total} unique external link(s) with {MAX_WORKERS} workers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(_check_url, url): url for url in unique_urls}
        for future in as_completed(future_map):
            result = future.result()
            url    = future_map[future]
            url_results[url] = result
            with lock:
                done_counter[0] += 1
                n = done_counter[0]
            print(f"\rChecking links: {n}/{total}", end="", flush=True)

    print(f"\r[links] Done. Checked {total} link(s).                     ")

    broken_links: list[dict] = []
    warned_links: list[dict] = []

    for url, result in url_results.items():
        if _is_ok(result):
            continue

        record: dict = {"url": url, "posts": url_to_refs[url]}
        if "error" in result:
            record["error"] = result["error"]
        else:
            record["status_code"] = result["status_code"]

        if _is_false_positive(url):
            record["warning"] = "社群網站或反爬蟲網站可能阻擋 bot，請人工開啟確認"
            warned_links.append(record)
        else:
            broken_links.append(record)

    return broken_links, warned_links
