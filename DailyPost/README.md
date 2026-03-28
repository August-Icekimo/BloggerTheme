# DailyPost 新聞室發布模組

`DailyPost` 是一個基於 "新聞編輯部 (Newsroom)" 概念所重構的 Blogger 發布與同步工具。它負責將您本機端的 Markdown 稿件轉換為可發佈的 HTML 格式，並支援自訂標籤 (如 SMS 氣泡框、YouTube 影片嵌入) 的自動雙向翻譯，徹底告別過去複雜難懂的 Regex 分析。

---

## 📖 目錄

1. [系統架構簡介](#系統架構簡介)
2. [環境配置與認證 (Token) 管理](#環境配置與認證-token-管理)
3. [如何獲取 Blogger Post ID](#如何獲取-blogger-post-id)
4. [指令使用指南](#指令使用指南)
   - [拉取文章 (Pull)](#1-從雲端拉取文章同步回本機-pull)
   - [推播發布文章 (Push)](#2-將單篇-markdown-推播發布至雲端-push)
   - [查詢本地稿件狀態 (List)](#3-列出本地草稿狀態-list)
5. [自訂標籤與翻譯字典](#自訂標籤與翻譯字典)

---

## 🕵️‍♂️ 系統架構簡介

DailyPost 由四個核心角色組成：
- **`publisher.py` (發行人)**： DailyPost 的單一 CLI 進入點。
- **`columnist.py` (專欄作家)**： 掃描與彙整本機端 (`posts/` 資料夾) 所有 Markdown 文檔的前置資料 (Frontmatter) 狀態。
- **`reporter.py` (記者)**： 負責向外採訪（透過 Blogger API 讀取文章），並透過翻譯引擎將 HTML 退回乾淨的 Markdown 格式。
- **`data_journalist.py` (數據記者)**： 強大的「無硬編碼」雙向翻譯引擎，其所有轉換規則皆宣告於 `translations.yaml` 字典中。

---

## 🔐 環境配置與認證 (Token) 管理

DailyPost 透過 OAuth2 連接 Google 服務。在您第一次執行任何同步操作時，程式會在專案根目錄產生或讀取環境變數與 `token.pickle`（憑證檔案）。

### 需要準備的檔案 (位於 repo 根目錄)
1. `.env` (需包含 `CLIENT_ID`, `CLIENT_SECRET`, `BLOG_ID`)
2. `token.pickle` (授權後由系統自動產生)

### 憑證過期如何強制更新 (Refresh Pickle)?
Google 的 OAuth token 一段時間後會自動失效或被撤銷 (出現 `RefreshError` 或 `invalid_grant`)。
DailyPost 的 `auth.py` 已經實作了自動修復機制：
當發生授權錯誤時，它會 **自動刪除過期的 `token.pickle`** 並立即重新啟動 OAuth 認證流程。

這時您只需要：
1. 在終端機執行任意指令 (例如 `python DailyPost/publisher.py list`)。
2. 系統會看見憑證失效並自動跳出您的本地 Google 登入瀏覽器畫面 (或提供一串 localhost 網址讓您貼進瀏覽器)。
3. 在瀏覽器中點選同意授權。
4. 網頁讀取成功後，回到終端機即可看到新的 `token.pickle` 已經被寫入。

---

## 🆔 如何獲取 Blogger Post ID

要拉取單篇文章您需要知道該文章的 `post_id`。
獲取 post_id 最直觀的方法有兩種：

1. **從 Blogger 後台網址獲取**：
   登入您的 Blogger 後台編輯特定文章，網址列會顯示類似：
   `https://www.blogger.com/blog/post/edit/您的BLOG_ID/1234567890123456789`
   最後面那一長串數字就是 `post_id`。

2. **從網頁原始碼查看**：
   在您實際的網誌頁面按右鍵 ->「檢視網頁原始碼」，並利用 `Ctrl`+`F` 搜尋 `postId`、`data-post-id` 或 `itemprop="postId"`。

---

## 🛠️ 指令使用指南

所有操作都透過 `DailyPost/publisher.py` 執行。請確保您在終端機內啟動了 `venv` 虛擬環境：
```bash
# bash, zsh, shell
source ./venv/bin/activate
```

### 1. 從雲端拉取文章同步回本機 (Pull)
`pull` 指令會透過 API 將雲端 Blogger 文章下載，剝除複雜的 HTML 外衣，依據字典轉回您熟悉的 `sms-*` 標籤 Markdown，並產生包含 Frontmatter (`title`, `post_id`, `published`) 的 `.md` 檔案。

```bash
python DailyPost/publisher.py pull --post-id <在這裡填入長串數字 postID>
```
*預設下載到 `posts/` 資料夾內，檔案名稱會自動根據您的網誌標題進行 Slugify。*

### 2. 將單篇 Markdown 推播發布至雲端 (Push)
如果本機 Markdown 已包含 `post_id` (通常是 pull 回來的草稿)，`push` 將會**更新**現有雲端的文章。
如果不包含 `post_id`，它會自動**創建一篇新文章**，並在終端機告訴您新的 ID，請務必再將新的 ID 手動放回您的 Markdown frontmatter 裡。

```bash
python DailyPost/publisher.py push "posts/用一般卡式錄音帶tape-cassette當數位儲存的媒體的發想.md"
```
*(推播後會一併顯示您的網誌前台真實 URL)*。

### 3. 列出本地草稿狀態 (List)
掃描 `posts/` 目錄下的所有文件並列出它們的 `Title`, `Post_ID` 以及目前的 `published` 狀態。

```bash
# 列出全部
python DailyPost/publisher.py list

# 只列出草稿
python DailyPost/publisher.py list --status draft

# 只列出已發布
python DailyPost/publisher.py list --status published
```

---

## 📝 自訂標籤與翻譯字典

您可以直接在 Markdown 當中使用自訂標籤 (SMS 氣泡、YouTube 等)。DailyPost 內建安全機制，如果您將這些標籤寫在 ` ```markdown ` 程式碼區塊內，它**不會**被轉換；除此之外都會被引擎抓取並發佈為對應的 HTML 版型。

所有的對應規則都在 `DailyPost/translations.yaml` 當中。
如果工程師未來需要新增標籤對應關係（例如 `{{telegram-bubble}}`），完全 **不需要** 修改任何 Python 程式碼，只要修改 `translations.yaml` 並加入新字典定義即可無縫支援從本機端 Push，也完全支援從 Web 編輯後 Pull！
