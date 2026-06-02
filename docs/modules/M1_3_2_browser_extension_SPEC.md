# M1.3.2 — 瀏覽器擴充功能 (Chrome, Firefox, Edge MV3)

**標籤**: `[MVP]`
**版本**: `1.1`
**最後更新**: 2026-06-03

---

## 1. Purpose (目的)

以跨瀏覽器 (Chrome, Firefox, Edge) Manifest V3 擴充形式，追蹤瀏覽器分頁焦點變化與閱讀停留時間，將頁面分類為「學習/社交/娛樂/工具」等桶位，供下游 AI 推論使用者的注意力分佈。

> 一句話：「**從瀏覽器內部觀察閱讀行為的時間分佈與主題分類**」。

---

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R02 | §時間動力學 §1.2 | 頁面停留時間作為閱讀深度指標;頻繁切換 Tab = 分心;長停留 = 沉浸閱讀 |
| R06 | §數位表型 §2.1 | 瀏覽行為模式 (社交 vs 學習比例) 作為數位表型的一部分 |

---

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| WebExtensions `tabs.onActivated` API | `activeInfo: { tabId, windowId }` | 使用者切換至某個 Tab |
| WebExtensions `tabs.onUpdated` API | `changeInfo: { status, url, title }` | 頁面載入完成,可取得 URL domain |
| WebExtensions `idle.onStateChanged` API | `newState: "active" \| "idle" \| "locked"` | 使用者是否離開電腦 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| Tauri (via Native Messaging) → M0.4 → `raw_tracking_logs` | `BrowseActivityEvent` | `{ module: "M1.3.2", action: "tab_stay", payload: { domain: "github.com", url_path: "/issues/1", title: "Refactoring Telemetry", domain_bucket: "coding", stay_s: 600 } }` |
| Tauri (via Native Messaging) → M0.4 → `raw_tracking_logs` | `TabSwitchEvent` | `{ module: "M1.3.2", action: "tab_switch", payload: { from_domain: "youtube.com", from_bucket: "entertainment", to_domain: "github.com", to_bucket: "coding" } }` |

---

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.2** (Tauri IPC): Native Messaging Host 由 Tauri Rust 層提供
- **M0.4** (結構化日誌): 所有事件經 M0.4 寫入 `raw_tracking_logs`

### 下游 (誰依賴我)

- **M4.8** (隱性狀態推論): 閱讀行為模式 (社交 vs 學習比例) 作為隱性狀態特徵
- **M4.4** (深夜草稿): 統計「今日瀏覽了哪些專案網頁、各停留多久」，並利用標題與路徑生成日報

> ⚠️ **M1.1 與 M1.3.2 的關係說明**:M1.3.2 **不是** M1.1 的下游。兩者是並列的感測器層，各自採集不同維度的訊號：M1.1 採集 OS 層視窗切換（process 粒度），M1.3.2 採集瀏覽器內部分頁（domain/URL 粒度）。M1.3.2 的 `CaptureConsent` 同意機制**參照** M1.1 定義的 `CaptureConsent` 結構（Opt-in 模式下讀取頁面標題/內文），共享 M6.1 定義的 `user_consents` 表（`consent_type = 'content_capture_all'` 或 `'content_capture_selected'`），但 M1.3.2 是 M1.1 定義該機制的**使用者**，不是 M1.1 的消費者。

---

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| (無直接 RISK-xx) | 瀏覽器擴充權限過度 → 使用者拒絕安裝 | 僅申請 `tabs` 與 `idle` 權限；不申請 `<all_urls>` 或 `webRequest` |
| (無直接 RISK-xx) | URL 含敏感資訊 (如 email subject, token) → 隱私洩漏 | **不記錄 URL 敏感參數**；僅擷取 domain (如 `youtube.com`) 與過濾參數後的相對路徑（如 `/issues/1`）；且僅保留在本地 L1，絕不上傳雲端 |
| RISK-15 | 若 Opt-in 模式開啟，頁面標題與擷取之內文可能含敏感資訊 | 標題與內文記錄遵循 M1.1 的 `CaptureConsent` 機制，全數限於 L1 本地資料庫儲存，絕不上傳 L3 雲端；未授權時僅能記錄 domain_bucket 與 domain |

---

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m1_3_2/test_browser_extension.py

class TestTabStayTracking:
    def test_tab_stay_10min_recorded(self, ext):
        """驗收條件 1: 停留在 YouTube 10 分鐘 → 正確記錄"""
        ext.simulate_tab_active("https://youtube.com/watch?v=abc", title="Funny Cats", duration_s=600)
        event = ext.get_event("tab_stay")
        assert event.payload["stay_s"] >= 600
        assert event.payload["domain"] == "youtube.com"
        assert event.payload["domain_bucket"] == "entertainment"

    def test_short_tab_under_5s_not_recorded(self, ext):
        """驗收條件 2: 停留不足 5 秒的分頁不記錄 (防止快速切換雜訊)"""
        ext.simulate_tab_active("https://google.com", title="Google", duration_s=3)
        assert ext.event_count("tab_stay") == 0

class TestDomainBucketing:
    def test_github_classified_as_coding(self, ext):
        """驗收條件 3: github.com → coding"""
        ext.simulate_tab_active("https://github.com/user/repo", title="Repo", duration_s=60)
        assert ext.last_event().payload["domain"] == "github.com"
        assert ext.last_event().payload["domain_bucket"] == "coding"

    def test_stackoverflow_classified_as_learning(self, ext):
        """驗收條件 4: stackoverflow.com → learning"""
        ext.simulate_tab_active("https://stackoverflow.com/questions/123", title="Question", duration_s=60)
        assert ext.last_event().payload["domain_bucket"] == "learning"

class TestPrivacy:
    def test_domain_and_scrubbed_path_recorded_but_query_params_ignored(self, ext):
        """驗收條件 5: 僅記錄 domain 與去除敏感參數的相對路徑，不含完整 URL 敏感參數"""
        ext.simulate_tab_active("https://github.com/user/repo/issues/1?token=secret123", title="Bug Report", duration_s=60)
        event = ext.last_event()
        assert event.payload["domain"] == "github.com"
        assert event.payload["url_path"] == "/user/repo/issues/1"
        assert "secret123" not in str(event.payload)
        # Opt-in 關閉時 title 不應出現在 payload
        assert event.payload.get("title") is None

    def test_title_recorded_only_when_optin_enabled(self, ext):
        """驗收條件 5.1: 頁面標題僅在 CaptureMode::SelectedApps 或 AllApps 時寫入 payload"""
        ext.set_capture_mode("all_apps")
        ext.simulate_tab_active("https://github.com/user/repo/issues/1", title="Bug Report", duration_s=60)
        event = ext.last_event()
        assert event.payload["title"] == "Bug Report"  # Opt-in 開啟時保留，僅存 L1

class TestNativeMessaging:
    def test_message_sent_on_tab_switch(self, ext, mock_native_host):
        """驗收條件 6: Tab 切換時透過 Native Messaging 發送事件"""
        ext.simulate_tab_switch("https://github.com", "https://youtube.com")
        assert mock_native_host.received_count >= 1
```

---

## 7. Implementation Notes

### 7.1 Domain Bucketing 規則與動態配置擴充

為了讓使用者能自由調整和擴充分類規則（例如將 `reddit.com` 從 `social` 移至 `learning`，或新增自訂分類），M1.3.2 捨棄靜態硬編碼設計，改由本地 SQLite 資料庫與 Local Cache 雙軌驅動：

1. **SQLite 儲存（Tauri L1）**：
   Tauri 核心提供 `browser_classification_rules` 本地資料表，格式為 `(pattern VARCHAR PRIMARY KEY, bucket VARCHAR)`。
2. **啟動載入機制**：
   擴充功能初始化時，向 Native Messaging Host 發送 `get_rules` 請求，Tauri 會查詢該資料表並返回 JSON，擴充功能在 Service Worker 記憶體中建立快取。
3. **動態更新與自訂**：
   當使用者在 coOS 設定介面新增/修改分類時，Tauri 更新 SQLite 後向擴充功能廣播 `update_rules`，即時更新快取。
4. **除分類外，必須同時記錄網域名稱 (domain) 與網頁標題 (title, Opt-in 開啟時)**。

```javascript
// background.js (Service Worker) 快取載入與分類機制
let cachedRules = {}; // 格式如: { "github.com": "coding", "stackoverflow.com": "learning" }

// 從 Tauri 載入動態配置
function loadRulesFromHost() {
    chrome.runtime.sendNativeMessage('coos_native_host', { command: 'get_rules' }, (response) => {
        if (response && response.rules) {
            cachedRules = response.rules;
        }
    });
}

function classifyDomain(url) {
    const hostname = new URL(url).hostname.replace("www.", "");
    
    // 精確或後綴比對
    for (const [pattern, bucket] of Object.entries(cachedRules)) {
        if (hostname === pattern || hostname.endsWith("." + pattern)) {
            return bucket;
        }
    }
    return "unknown"; // 預設歸類為未歸類，將在 Tauri 端引導使用者自訂
}

// 敏感參數過濾與相對路徑提取
function getCleanPathAndDomain(urlStr) {
    try {
        const url = new URL(urlStr);
        const domain = url.hostname.replace("www.", "");
        // 移除 Query parameters (如 ?token=123) 與 Hash 以防止隱私洩漏
        const url_path = url.pathname; 
        return { domain, url_path };
    } catch (e) {
        return { domain: "unknown", url_path: "" };
    }
}
```

> **跨瀏覽器注意事項**: 核心代碼統一使用 `chrome.*` API。Firefox 與 Edge 均支援 `chrome.*` 命名空間。在 Firefox 環境下，打包時 manifest 會被配置為 `"background": { "scripts": ["background.js"] }` 以提升在非 Service Worker 核心下的執行穩定度。

---

### 7.2 Native Messaging 通訊與 Windows 登錄檔註冊

- **Native Messaging Host**: Tauri Rust 層提供的 `coos_native_host` 可執行檔。
- **訊息格式**: JSON (系統自動在通訊前加上 4-byte 長度前綴)。
- **Windows 登錄檔註冊路徑**:
  為了讓 Chrome, Firefox, Edge 皆能與 Tauri Host 連線，Tauri 核心在安裝時須在 Windows Registry 寫入以下路徑：
  - **Chrome**: `HKCU\Software\Google\Chrome\NativeMessagingHosts\coos_native_host`
  - **Edge**: `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\coos_native_host`
  - **Firefox**: `HKCU\Software\Mozilla\NativeMessagingHosts\coos_native_host`
  - 各路徑的預設值皆需指向 Tauri 生成的 `coos_native_host.json` 描述檔路徑（通常位於 `%LOCALAPPDATA%\coos\native_hosts\`）。
- **描述檔設定**:
  - Chrome 與 Edge 使用 `allowed_origins` 清單限制連線 ID。
  - Firefox 使用 `allowed_extensions` 清單限制連線 ID，且 Firefox 的 `manifest.json` 必須宣告 `browser_specific_settings.gecko.id` 欄位（例如 `"coos_extension@coos.local"`）。

---

### 7.3 異常處理

| 例外情況 | 處理方式 |
| -------- | -------- |
| Native Messaging Host 未安裝 | Extension 顯示 badge "!" 提示使用者安裝;事件暫存 `chrome.storage.local` (max 200) |
| 使用者進入隱私模式 (Incognito) | Extension 在 Incognito 模式下**完全停用**,不記錄任何事件 |
| `idle.onStateChanged` 回報 locked | 立即結束當前 tab_stay 計時,記錄為 idle 中斷 |

---

## 8. Anti-patterns (反模式)

- ❌ **不要記錄或上傳完整帶有敏感引數的 URL 至 L3 雲端** — 只能在本地 L1/L2 層級記錄 domain、網頁標題與過濾掉 Query string/Hash 的純淨相對路徑（如 `/issues/1`）。
- ❌ **不要申請 `<all_urls>` 權限** — 僅需 `tabs`、`idle` 權限。過度權限會被使用者拒絕且違反最小權限原則。
- ❌ **不要在沒有 Opt-in 授權下讀取頁面 DOM 內容** — 未開啟 `content_capture` 時不得注入 Content Script。若使用者 Opt-in 開啟，則允許在本地安全擷取網頁主體文字（不含輸入欄位與密碼）用作本機摘要，且嚴禁傳離本地。
- ❌ **不要在 Incognito 模式下運作** — 即使使用者勾選允許，也絕不在隱私模式記錄。

---

## 9. Open Questions

- [x] ~~**Q1: domain_bucket 清單是否可由使用者自訂?**~~ → 確定採用**由本地 SQLite 配置規則、Service Worker 在啟動與更新時快取**的機制，完全支援使用者自訂分類與新增自訂 bucket。
- [x] ~~**Q2: 是否支援 Firefox/Edge?**~~ → 確定於 MVP 階段即**全面支援 Chrome, Firefox 與 Edge**。核心 Native Messaging 機制相同，僅註冊登錄檔路徑與 manifest 打包配置有微調。
- [x] ~~**Q3: 是否發布到各瀏覽器應用程式商店?**~~ → MVP 階段採用**開發者模式手動載入（Unpacked Extension / Firefox Temporary Add-on）**或經由 Tauri 安裝檔自動註冊本機路徑。上架 Web Store / Add-ons Store 將作為後期發布規劃。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責
- [x] §2 至少 1 個 `Rxx` 引用 (R02 §1.2, R06 §2.1)
- [x] §3 Schema 定義完整
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,觸發 RISK-15
- [x] §6 測試先於程式碼,覆蓋 6 個驗收條件
- [x] §8 至少 4 條反模式
- [x] §9 至少 3 個開放問題
