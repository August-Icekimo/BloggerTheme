# Igniplex v3.1 授權重導向問題分析

> **調查日期**: 2026-03-20
> **調查者**: icekimo + AI Assistant
> **影響範圍**: blog.icekimo.idv.tw

## 問題現象

在部分瀏覽器上，使用者開啟 `blog.icekimo.idv.tw` 後會被自動重導向至：
```
https://igniplex.blogspot.com/p/contact.html?ref=blog.icekimo.idv.tw
```
這是 Igniplex 主題的購買/聯絡頁面。

---

## 混淆腳本位置

| # | 檔案位置 | 行號 | 用途 | 風險等級 |
|---|---------|------|------|---------|
| 1 | `Igniplex v3.1.xml` | **188-190** | Dark Mode / Letter 偏好初始化 | 🟢 低 |
| 2 | `Igniplex v3.1.xml` | **5732** | 主要功能腳本 + **授權驗證 + 重導向** | 🔴 高 |

詳細解碼內容請見：
- `01_dark_mode_init.js` — Block #1 完整解碼
- `02_main_script_license_check.js` — Block #2 關鍵邏輯與解碼字串

---

## 授權機制運作方式

### 1. 遠端 API 驗證

腳本會在頁面載入時發送 `fetch` 請求至 Igniel 的授權伺服器：

```
https://source.igniel.com/api?key=<blogId>&id=ign&v=3.1&url=<hostname>
```

### 2. 回應處理邏輯

```
API 回應 → 檢查 response.ref.origin === 當前網域
  ├─ 匹配 → 寫入 Cookie（快取授權），正常載入
  └─ 不匹配 → 檢查是否在白名單中
      ├─ 在白名單 → 允許（爬蟲/工具）
      └─ 不在白名單 → setTimeout 重導向至購買頁
```

### 3. Cookie 快取機制

- Cookie 名稱 = blogId 的 hex 編碼
- 授權通過後寫入 Cookie 並設定有效期
- 後續造訪只要 Cookie 存在且有效，就不會再做遠端驗證

### 4. 白名單（20 個網域）

以下網域的請求會跳過授權檢查（通常是 Google 服務、SEO 工具、CDN）：

| # | 網域 | 類別 |
|---|------|------|
| 1 | google.com | Google 搜尋 |
| 2 | adsense.com | Google AdSense |
| 3 | googleapis.com | Google API |
| 4 | google-analytics.com | Google Analytics |
| 5 | googleusercontent.com | Google 使用者內容 |
| 6 | blogger.com | Blogger 平台 |
| 7 | gstatic.com | Google 靜態資源 |
| 8 | histatsi.com | 統計服務 (有 typo) |
| 9 | cloudflare.com | CDN |
| 10 | pingdom.com | 網站監控 |
| 11 | googletagaanager.com | GTM (有 typo) |
| 12 | autoads-preview.googleusercontent.com | 廣告預覽 |
| 13 | translate.goog | Google 翻譯 |
| 14 | withgoogle.com | Google 合作網站 |
| 15 | gtmetrix.com | 效能測試 |
| 16 | web.dev | Google Web.dev |
| 17 | bing.com | Bing 搜尋 |
| 18 | neilpatel.com | SEO 工具 |
| 19 | google.co.id | Google 印尼 |
| 20 | doubleclick.net | Google 廣告 |

---

## 根本原因分析

### 為什麼在某些瀏覽器/網路環境上會觸發重導向？

重導向的觸發條件為「**API 請求失敗或回傳結果不符**」，可能的原因：

#### 🔴 原因 1: 中華電信部分對外線路異常（目前已知）
- 目前中華電信部分對外線路有問題
- 導致對 `source.igniel.com` 的 fetch 請求 **timeout 或失敗**
- 腳本在 `catch` 區塊中同樣會觸發重導向
- **這是目前最可能的根本原因**

#### 🟡 原因 2: 瀏覽器隱私設定阻擋
- 隱私模式（InPrivate / Incognito）不保留 Cookie
- 每次造訪都需要重新做遠端驗證
- 如果此時遠端 API 剛好不通，就會觸發重導向

#### 🟡 原因 3: AdBlocker / 防火牆攔截
- 部分 AdBlocker 規則可能會阻擋對 `source.igniel.com` 的請求
- 請求被攔截 → 視為驗證失敗 → 觸發重導向

#### 🟢 原因 4: DNS 解析問題
- `source.igniel.com` 的 DNS 解析在某些 ISP 上可能不穩定
- 無法解析 → fetch 失敗 → 重導向

---

## 待辦事項

- [ ] 確認 `blog.icekimo.idv.tw` 在 Igniel 後台的授權狀態
- [ ] 在出問題的網路環境下，用 DevTools Network 面板觀察 `source.igniel.com` 的請求狀態
- [ ] 評估是否需要修改腳本邏輯（例如：API 失敗時不重導向，改為靜默失敗）
- [ ] 考慮是否建立本地 fallback 機制（Cookie 有效期延長、或預設允許）
- [ ] 追蹤中華電信線路恢復狀況
