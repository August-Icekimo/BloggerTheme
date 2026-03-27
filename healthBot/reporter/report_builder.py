"""
report_builder.py — Generate TXT / JSON / HTML health reports.

Output files:
    reports/health_report_YYYYMMDD_HHMMSS.txt
    reports/health_report_YYYYMMDD_HHMMSS.json
    reports/health_report_YYYYMMDD_HHMMSS.html
"""

import json
import os
from datetime import datetime, timezone

from config import REPORTS_DIR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _badge_label(record: dict) -> str:
    """Return short status string for TXT / HTML badge."""
    if "error" in record:
        return record["error"]
    return str(record.get("status_code", "?"))


def _ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# TXT report
# ---------------------------------------------------------------------------

def _build_txt(
    generated_at: str,
    broken_images: list[dict],
    broken_links: list[dict],
    warned_links: list[dict],
) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("  Blogger Health Report")
    lines.append(f"  產出時間：{generated_at}")
    lines.append("=" * 70)
    lines.append("")

    # --- Summary ---
    lines.append("【摘要】")
    lines.append(f"  破圖：      {len(broken_images)} 張")
    lines.append(f"  失效連結：  {len(broken_links)} 個")
    lines.append(f"  需人工確認：{len(warned_links)} 個")
    lines.append("")

    # --- Broken images ---
    lines.append("-" * 70)
    lines.append(f"▶ 破圖清單 ({len(broken_images)} 張)")
    lines.append("-" * 70)
    if not broken_images:
        lines.append("  （無）")
    else:
        lines.append("")
        lines.append("  ⚑ 修復動作：重新上傳圖片至 Blogger / Google Photos，並更新文章中的圖片 URL。")
        lines.append("")
        for i, img in enumerate(broken_images, 1):
            lines.append(f"  [{i}] {img['post_title']}")
            lines.append(f"      文章：{img['post_url']}")
            lines.append(f"      圖片：{img['url']}")
            lines.append(f"      alt ：{img.get('alt', '')}")
            lines.append(f"      狀態：{_badge_label(img)}")
            lines.append("")

    # --- Broken links ---
    lines.append("-" * 70)
    lines.append(f"▶ 失效外部連結 ({len(broken_links)} 個)")
    lines.append("-" * 70)
    if not broken_links:
        lines.append("  （無）")
    else:
        lines.append("")
        lines.append("  ⚑ 修復動作：以人工方式開啟連結確認，考慮改連 archive.org 備份，或直接移除連結。")
        lines.append("")
        for i, link in enumerate(broken_links, 1):
            lines.append(f"  [{i}] {link['url']}")
            lines.append(f"      狀態：{_badge_label(link)}")
            lines.append(f"      引用文章：")
            for ref in link["posts"]:
                lines.append(f"        • {ref['title']}")
                lines.append(f"          {ref['url']}")
            lines.append("")

    # --- Warned links ---
    lines.append("-" * 70)
    lines.append(f"▶ 需人工確認連結 ({len(warned_links)} 個)")
    lines.append("-" * 70)
    if not warned_links:
        lines.append("  （無）")
    else:
        lines.append("")
        lines.append("  ⚑ 修復動作：手動在瀏覽器中開啟各連結，確認頁面是否仍正常存在。若已失效，同上處理。")
        lines.append("")
        for i, link in enumerate(warned_links, 1):
            lines.append(f"  [{i}] {link['url']}")
            lines.append(f"      狀態：{_badge_label(link)}  ⚠ {link.get('warning', '')}")
            lines.append(f"      引用文章：")
            for ref in link["posts"]:
                lines.append(f"        • {ref['title']}")
                lines.append(f"          {ref['url']}")
            lines.append("")

    # --- Footer ---
    lines.append("=" * 70)
    if not broken_images and not broken_links and not warned_links:
        lines.append("  ✅ 一切正常！所有圖片與連結均可存取。")
    else:
        lines.append("  ⚠️  發現問題，請依以上清單逐項修復。")
    lines.append("=" * 70)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def _build_json(
    generated_at: str,
    broken_images: list[dict],
    broken_links: list[dict],
    warned_links: list[dict],
) -> str:
    payload = {
        "generated_at": generated_at,
        "summary": {
            "broken_images": len(broken_images),
            "broken_links":  len(broken_links),
            "warned_links":  len(warned_links),
        },
        "broken_images": broken_images,
        "broken_links":  broken_links,
        "warned_links":  warned_links,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def _status_badge_class(record: dict) -> str:
    if "error" in record:
        return "badge-error"
    code = record.get("status_code", 0)
    if 200 <= code < 300:
        return "badge-ok"
    if 300 <= code < 400:
        return "badge-redirect"
    if code >= 400:
        return "badge-error"
    return "badge-error"


def _html_escape(s: str) -> str:
    return (s
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _card_class(count: int, warn: bool = False) -> str:
    if count == 0:
        return "card-ok"
    return "card-warn" if warn else "card-error"


def _build_html(
    generated_at: str,
    broken_images: list[dict],
    broken_links: list[dict],
    warned_links: list[dict],
) -> str:
    all_ok = not broken_images and not broken_links and not warned_links

    # ---- CSS ----------------------------------------------------------------
    css = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:          #f4f6f9;
      --surface:     #ffffff;
      --border:      #e2e8f0;
      --text:        #1a202c;
      --text-muted:  #718096;
      --ok:          #38a169;
      --warn:        #d69e2e;
      --error:       #e53e3e;
      --redirect:    #805ad5;
      --shadow:      0 2px 8px rgba(0,0,0,.08);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg:         #0f1117;
        --surface:    #1a1d27;
        --border:     #2d3748;
        --text:       #e2e8f0;
        --text-muted: #718096;
        --shadow:     0 2px 8px rgba(0,0,0,.4);
      }
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      font-size: 14px;
      line-height: 1.6;
    }

    /* ---- Layout ---- */
    .container { max-width: 960px; margin: 0 auto; padding: 24px 16px 64px; }
    header { margin-bottom: 32px; }
    header h1 { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
    header time { color: var(--text-muted); font-size: 12px; }

    /* ---- Summary cards ---- */
    .cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px; }
    @media (max-width: 600px) { .cards { grid-template-columns: 1fr; } }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px 24px;
      box-shadow: var(--shadow);
      display: flex; flex-direction: column; gap: 8px;
    }
    .card-label  { font-size: 12px; font-weight: 600; text-transform: uppercase;
                   letter-spacing: .06em; color: var(--text-muted); }
    .card-count  { font-size: 36px; font-weight: 800; line-height: 1; }
    .card-ok     .card-count { color: var(--ok); }
    .card-warn   .card-count { color: var(--warn); }
    .card-error  .card-count { color: var(--error); }
    .card-ok     { border-top: 4px solid var(--ok); }
    .card-warn   { border-top: 4px solid var(--warn); }
    .card-error  { border-top: 4px solid var(--error); }

    /* ---- All-ok banner ---- */
    .all-ok {
      background: var(--surface);
      border: 1px solid var(--border);
      border-left: 4px solid var(--ok);
      border-radius: 8px;
      padding: 20px 24px;
      font-size: 16px;
      font-weight: 600;
      color: var(--ok);
      margin-bottom: 32px;
    }

    /* ---- Section ---- */
    section { margin-bottom: 40px; }
    .section-header {
      display: flex; align-items: center; gap: 12px;
      margin-bottom: 16px;
    }
    .section-header h2 { font-size: 16px; font-weight: 700; }
    .section-count {
      font-size: 12px; font-weight: 600; padding: 2px 8px;
      border-radius: 99px; background: var(--border); color: var(--text-muted);
    }
    .section-action {
      background: var(--surface);
      border: 1px solid var(--border);
      border-left: 4px solid var(--warn);
      border-radius: 6px;
      padding: 10px 16px;
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 12px;
    }
    .section-action strong { color: var(--text); }
    .empty {
      color: var(--text-muted);
      font-style: italic;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      text-align: center;
    }

    /* ---- Tables ---- */
    .table-wrap { overflow-x: auto; border-radius: 8px; box-shadow: var(--shadow); }
    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
      font-size: 13px;
    }
    thead th {
      background: var(--border);
      padding: 10px 14px;
      text-align: left;
      font-weight: 600;
      font-size: 11px;
      letter-spacing: .05em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    tbody td {
      padding: 10px 14px;
      border-top: 1px solid var(--border);
      vertical-align: top;
      word-break: break-all;
    }
    tbody tr:hover { background: rgba(127,127,127,.05); }
    a { color: #4299e1; text-decoration: none; }
    a:hover { text-decoration: underline; }

    /* ---- Badges ---- */
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 99px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .04em;
      white-space: nowrap;
    }
    .badge-ok       { background: #c6f6d5; color: #276749; }
    .badge-redirect { background: #e9d8fd; color: #553c9a; }
    .badge-warn     { background: #fefcbf; color: #744210; }
    .badge-error    { background: #fed7d7; color: #9b2c2c; }
    @media (prefers-color-scheme: dark) {
      .badge-ok       { background: #1c4532; color: #9ae6b4; }
      .badge-redirect { background: #322659; color: #d6bcfa; }
      .badge-warn     { background: #3d2d00; color: #fbd38d; }
      .badge-error    { background: #3d1515; color: #feb2b2; }
    }

    /* ---- Post list inside cells ---- */
    .post-list { list-style: none; display: flex; flex-direction: column; gap: 4px; }
    .post-list li::before { content: "• "; color: var(--text-muted); }
    """

    # ---- Card data ----------------------------------------------------------
    img_cc  = _card_class(len(broken_images))
    lnk_cc  = _card_class(len(broken_links))
    wrn_cc  = _card_class(len(warned_links), warn=True)

    # ---- Broken-image rows --------------------------------------------------
    def img_rows():
        rows = []
        for img in broken_images:
            badge_cls = _status_badge_class(img)
            rows.append(f"""
            <tr>
              <td><a href="{_html_escape(img['post_url'])}" target="_blank" rel="noopener">{_html_escape(img['post_title'])}</a></td>
              <td><a href="{_html_escape(img['url'])}" target="_blank" rel="noopener">{_html_escape(img['url'])}</a></td>
              <td>{_html_escape(img.get('alt',''))}</td>
              <td><span class="badge {badge_cls}">{_html_escape(_badge_label(img))}</span></td>
            </tr>""")
        return "\n".join(rows)

    # ---- Link rows (shared template) ----------------------------------------
    def link_rows(links: list[dict]):
        rows = []
        for link in links:
            badge_cls = _status_badge_class(link)
            post_items = "".join(
                f'<li><a href="{_html_escape(ref["url"])}" target="_blank" rel="noopener">'
                f'{_html_escape(ref["title"])}</a></li>'
                for ref in link["posts"]
            )
            warning_html = ""
            if "warning" in link:
                warning_html = f'<br><span class="badge badge-warn">⚠ {_html_escape(link["warning"])}</span>'
            rows.append(f"""
            <tr>
              <td><a href="{_html_escape(link['url'])}" target="_blank" rel="noopener">{_html_escape(link['url'])}</a>{warning_html}</td>
              <td><span class="badge {badge_cls}">{_html_escape(_badge_label(link))}</span></td>
              <td><ul class="post-list">{post_items}</ul></td>
            </tr>""")
        return "\n".join(rows)

    # ---- Section render helper ----------------------------------------------
    def render_section(title: str, count: int, action_html: str, table_html: str) -> str:
        if count == 0:
            return f"""
        <section>
          <div class="section-header">
            <h2>{title}</h2>
            <span class="section-count">{count}</span>
          </div>
          <p class="empty">✅ 無問題</p>
        </section>"""
        return f"""
        <section>
          <div class="section-header">
            <h2>{title}</h2>
            <span class="section-count">{count}</span>
          </div>
          <div class="section-action">{action_html}</div>
          <div class="table-wrap">{table_html}</div>
        </section>"""

    # ---- Image section -------------------------------------------------------
    img_table = f"""
        <table>
          <thead><tr>
            <th>文章</th><th>圖片 URL</th><th>Alt</th><th>狀態</th>
          </tr></thead>
          <tbody>{img_rows()}</tbody>
        </table>"""
    img_action = "<strong>修復動作：</strong>重新上傳圖片至 Blogger / Google Photos，並更新文章中的圖片 URL。"
    img_section = render_section(f"破圖", len(broken_images), img_action, img_table)

    # ---- Broken-link section ------------------------------------------------
    lnk_table = f"""
        <table>
          <thead><tr>
            <th>連結 URL</th><th>狀態</th><th>引用文章</th>
          </tr></thead>
          <tbody>{link_rows(broken_links)}</tbody>
        </table>"""
    lnk_action = ("<strong>修復動作：</strong>"
                  "以人工方式開啟連結確認，考慮改連 "
                  '<a href="https://archive.org" target="_blank" rel="noopener">archive.org</a> 備份，或直接移除連結。')
    lnk_section = render_section("失效外部連結", len(broken_links), lnk_action, lnk_table)

    # ---- Warned-link section ------------------------------------------------
    wrn_table = f"""
        <table>
          <thead><tr>
            <th>連結 URL</th><th>狀態</th><th>引用文章</th>
          </tr></thead>
          <tbody>{link_rows(warned_links)}</tbody>
        </table>"""
    wrn_action = "<strong>修復動作：</strong>手動在瀏覽器中開啟各連結，確認頁面是否仍正常存在。若已失效，同「失效連結」處理。"
    wrn_section = render_section("需人工確認連結", len(warned_links), wrn_action, wrn_table)

    # ---- All-ok banner ------------------------------------------------------
    ok_banner = ""
    if all_ok:
        ok_banner = '<div class="all-ok">✅ 一切正常！所有圖片與連結均可存取。</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blogger Health Report — {_html_escape(generated_at)}</title>
  <style>{css}</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>📋 Blogger Health Report</h1>
      <time>{_html_escape(generated_at)}</time>
    </header>

    <div class="cards">
      <div class="card {img_cc}">
        <span class="card-label">破圖</span>
        <span class="card-count">{len(broken_images)}</span>
      </div>
      <div class="card {lnk_cc}">
        <span class="card-label">失效連結</span>
        <span class="card-count">{len(broken_links)}</span>
      </div>
      <div class="card {wrn_cc}">
        <span class="card-label">需人工確認</span>
        <span class="card-count">{len(warned_links)}</span>
      </div>
    </div>

    {ok_banner}
    {img_section}
    {lnk_section}
    {wrn_section}
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_report(
    broken_images: list[dict],
    broken_links: list[dict],
    warned_links: list[dict],
) -> dict[str, str]:
    """
    Write TXT / JSON / HTML reports to the reports/ directory.

    Returns:
        {"txt": path, "json": path, "html": path}
    """
    _ensure_reports_dir()

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stamp        = datetime.now().strftime("%Y%m%d_%H%M%S")
    base         = os.path.join(REPORTS_DIR, f"health_report_{stamp}")

    txt_path  = base + ".txt"
    json_path = base + ".json"
    html_path = base + ".html"

    txt  = _build_txt(generated_at, broken_images, broken_links, warned_links)
    jsn  = _build_json(generated_at, broken_images, broken_links, warned_links)
    htm  = _build_html(generated_at, broken_images, broken_links, warned_links)

    for path, content in [(txt_path, txt), (json_path, jsn), (html_path, htm)]:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)

    print(f"[report] TXT  → {txt_path}")
    print(f"[report] JSON → {json_path}")
    print(f"[report] HTML → {html_path}")

    return {"txt": txt_path, "json": json_path, "html": html_path}
