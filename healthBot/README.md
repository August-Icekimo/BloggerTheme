# blogger-health-checker (`healthBot`)

> 掃描 Blogger 部落格的破圖與失效外部連結，並產出 TXT / JSON / HTML 三種格式報告。

---

## 目錄

- [功能概覽](#功能概覽)
- [專案結構](#專案結構)
- [前置需求](#前置需求)
- [安裝說明](#安裝說明)
- [使用方式](#使用方式)
- [報告格式說明](#報告格式說明)
- [設定檔說明](#設定檔說明)
- [注意事項](#注意事項)

---

## 功能概覽

| 功能 | 說明 |
|---|---|
| 🖼 破圖偵測 | 解析文章 HTML，抽取圖片 URL（含 lazy-load `data-src`），HTTP 驗證能否存取 |
| 🔗 失效連結偵測 | 抽取所有外部超連結，略過內部網域與黑名單，驗證有效性 |
| ⚠️ 誤報分類 | Facebook、Twitter、Pixnet 等反爬蟲網站自動列為「需人工確認」，不誤判為失效 |
| 💾 文章快取 | API 結果快取 1 天，加速重複執行（`--refresh-cache` 可強制重抓） |
| 📄 三種報告 | TXT（純文字）、JSON（程式可讀）、HTML（瀏覽器閱讀，含深色模式） |
| ⚡ 並發檢查 | `ThreadPoolExecutor`（10 workers），大幅縮短掃描時間 |

---

## 專案結構

```
healthBot/
├── main.py               # CLI 入口
├── config.py             # 所有可調整常數（worker 數、逾時、domain 清單…）
├── auth.py               # OAuth 認證（共用 repo 根目錄的 token.pickle / .env）
├── requirements.txt      # Python 套件清單
│
├── crawler/
│   └── post_crawler.py   # Blogger API v3 文章抓取 + JSON 快取
│
├── checkers/
│   ├── image_checker.py  # 破圖偵測（BeautifulSoup + ThreadPoolExecutor）
│   └── link_checker.py   # 外部連結偵測（de-dup、false-positive 白名單）
│
├── reporter/
│   └── report_builder.py # 產出 TXT / JSON / HTML 報告
│
├── cache/                # 文章快取（自動建立，git-ignored）
└── reports/              # 報告輸出目錄（自動建立，git-ignored）
```

---

## 前置需求

- Python **3.10+**
- Repo 根目錄存在有效的 **`.env`** 與 **`token.pickle`**（與 `publishBot` 共用）

`.env` 必須包含以下三個變數：

```env
CLIENT_ID=your-google-oauth-client-id
CLIENT_SECRET=your-google-oauth-client-secret
BLOG_ID=your-blogger-blog-id
```

---

## 安裝說明

本工具與 `publishBot` 共用 repo 根目錄的 **虛擬環境（venv）**。

### 方法一：使用 repo 根目錄的 venv（推薦）

```bash
# 從 repo 根目錄執行
./venv/bin/pip install -r healthBot/requirements.txt
```

### 方法二：建立 healthBot 專屬 venv（選用）

如果你想讓 healthBot 有獨立的環境：

```bash
cd healthBot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
```

之後執行時改用：

```bash
healthBot/.venv/bin/python healthBot/main.py
```

### 首次授權

若 repo 根目錄尚無有效的 `token.pickle`，首次執行時程式會自動開啟瀏覽器進行 Google OAuth 授權，並將 token 儲存至 repo 根目錄供 `publishBot` 共用。

---

## 使用方式

> **重要：** 以下指令均從 **repo 根目錄**（`BloggerTheme/`）執行。

### 完整掃描（破圖 + 連結）

```bash
./venv/bin/python healthBot/main.py
```

### 只掃描破圖

```bash
./venv/bin/python healthBot/main.py --check images
```

### 只掃描外部連結

```bash
./venv/bin/python healthBot/main.py --check links
```

### 強制重新抓取所有文章（忽略快取）

```bash
./venv/bin/python healthBot/main.py --refresh-cache
```

### 查看所有參數說明

```bash
./venv/bin/python healthBot/main.py --help
```

---

### 執行結果範例

```
============================================================
  Blogger Health Checker
============================================================

[crawler] Fetched 147 posts (8 page(s)).
  共 147 篇文章納入掃描範圍

【破圖偵測】
[image] Checking 120 unique image URL(s) with 10 workers...
[image] Done. Checked 120 image(s).

【外部連結偵測】
[links] Checking 212 unique external link(s) with 10 workers...
[links] Done. Checked 212 link(s).

============================================================
  掃描結果摘要
============================================================
  破圖：            7 張
  失效連結：       52 個
  需人工確認：      0 個

  ⚠️  發現問題，請查看報告並手動修復。

  HTML 報告：/path/to/healthBot/reports/health_report_20260327_153046.html
============================================================
```

> **結束碼說明：**
> - `exit 0` — 無任何問題
> - `exit 1` — 發現破圖或失效連結（可用於 CI/CD 整合）

---

## 報告格式說明

報告檔案產出於 `healthBot/reports/`，檔名格式為 `health_report_YYYYMMDD_HHMMSS.{ext}`。

### TXT 報告

純文字，適合快速閱覽。每個問題類別包含：
- 問題數量
- **⚑ 修復動作**（說明下一步該怎麼做）
- 逐項列出文章標題、文章 URL、問題 URL、狀態碼

### JSON 報告

機器可讀格式，頂層結構如下：

```json
{
  "generated_at": "2026-03-27 15:30:46",
  "summary": {
    "broken_images": 7,
    "broken_links": 52,
    "warned_links": 0
  },
  "broken_images": [...],
  "broken_links": [...],
  "warned_links": [...]
}
```

### HTML 報告

在瀏覽器開啟，功能最完整：

- 摘要卡片（數量為 0 時顯示綠色，有問題時顯示紅色）
- 每個問題區塊頂部有**修復動作說明**
- 狀態碼以顏色徽章顯示（綠色 2xx、紫色 3xx、紅色 4xx/error）
- 文章標題可點擊直接跳至該文章
- 支援 **深色模式**（跟隨系統 `prefers-color-scheme`）
- 零外部依賴，單一 HTML 檔案可直接分享

---

## 設定檔說明

所有可調整參數集中於 `config.py`：

| 常數 | 預設值 | 說明 |
|---|---|---|
| `CACHE_MAX_AGE_DAYS` | `1` | 文章快取有效天數 |
| `MAX_WORKERS` | `10` | 並發 HTTP 檢查的 worker 數量 |
| `CHECK_TIMEOUT` | `10` | 單一 URL 的最長等待秒數 |
| `SKIP_DOMAINS` | `["blogger.com", ...]` | 永遠跳過不檢查的 domain |
| `FALSE_POSITIVE_DOMAINS` | `["facebook.com", "pixnet.net", ...]` | 誤報白名單：失敗列為「需人工確認」而非「確認失效」 |

---

## 注意事項

- 工具**不會修改**任何文章內容，僅提供唯讀檢查與報告。
- **草稿文章**不在掃描範圍內（僅掃描已發布文章）。
- 社群媒體連結（Facebook、Twitter 等）常對 bot 回傳非 2xx，已自動列入白名單。若要新增其他反爬蟲網站，請編輯 `config.py` 的 `FALSE_POSITIVE_DOMAINS`。
- 快取檔案（`cache/`）與報告（`reports/`）已列入 `.gitignore`，不會被 commit。
- 在網路頻寬受限環境下，`CHECK_TIMEOUT` 可適當調高以避免誤判。
