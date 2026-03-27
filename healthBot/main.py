"""
main.py — CLI entry point for blogger-health-checker.

Usage (run from healthBot/ directory):
    python main.py                     # full check (images + links)
    python main.py --check images      # broken images only
    python main.py --check links       # broken links only
    python main.py --refresh-cache     # force re-fetch all posts first
    python main.py --help
"""

import argparse
import sys
import os

# Ensure healthBot/ is on sys.path so submodules import correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.post_crawler import get_all_posts
from checkers.image_checker import check_images
from checkers.link_checker import check_links
from reporter.report_builder import build_report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description=(
            "blogger-health-checker — 掃描 Blogger 部落格的破圖與失效外部連結，\n"
            "產出 TXT / JSON / HTML 三種格式報告。\n\n"
            "執行前請確認 repo 根目錄存在有效的 .env 與 token.pickle。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--check",
        choices=["all", "images", "links"],
        default="all",
        metavar="{all,images,links}",
        help="檢查範圍：all（預設）、images（僅破圖）、links（僅連結）",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        default=False,
        help="忽略快取，強制重新從 Blogger API 抓取所有文章",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    print()
    print("=" * 60)
    print("  Blogger Health Checker")
    print("=" * 60)
    print()

    # 1. Fetch posts ----------------------------------------------------------
    posts = get_all_posts(force_refresh=args.refresh_cache)
    print(f"  共 {len(posts)} 篇文章納入掃描範圍")
    print()

    # 2. Run checkers ---------------------------------------------------------
    broken_images: list[dict] = []
    broken_links:  list[dict] = []
    warned_links:  list[dict] = []

    if args.check in ("all", "images"):
        print("【破圖偵測】")
        broken_images = check_images(posts)
        print()

    if args.check in ("all", "links"):
        print("【外部連結偵測】")
        broken_links, warned_links = check_links(posts)
        print()

    # 3. Build reports --------------------------------------------------------
    print("【產出報告】")
    paths = build_report(broken_images, broken_links, warned_links)
    print()

    # 4. Print summary --------------------------------------------------------
    print("=" * 60)
    print("  掃描結果摘要")
    print("=" * 60)
    print(f"  破圖：         {len(broken_images):>4} 張")
    print(f"  失效連結：     {len(broken_links):>4} 個")
    print(f"  需人工確認：   {len(warned_links):>4} 個")
    print()

    has_issues = broken_images or broken_links or warned_links
    if has_issues:
        print("  ⚠️  發現問題，請查看報告並手動修復。")
    else:
        print("  ✅ 一切正常！所有圖片與連結均可存取。")
    print()
    print(f"  HTML 報告：{paths['html']}")
    print("=" * 60)
    print()

    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
