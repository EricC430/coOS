# 模組登記冊 (Module Registry) — 完整版

> **此文件是 Claude Code 實作任一模組前的必查權威來源。**
>
> 每個模組包含:標籤 / 職責描述 / 子模組清單 / 依賴 / 驗收標準 / 研究引用 / 整合風險。
>
> grep 用法:`grep -A 50 "^### M4.2 " docs/04_module_registry.md`

---

## 📦 M0 系統基礎與通訊核心 (Infrastructure & IPC) `[MVP]`

### M0.1 Monorepo 專案結構初始化 `[MVP]`

**Purpose**:配置 Tauri (Rust) + 前端 (React/Vite) + 後端 (Python/FastAPI) 三層工作區。

**子模組**:無 (單一任務)

**Outputs**:可執行的空殼專案、CI lint/test pipeline。
**Deps**:無
**Criteria**:`pnpm dev` 同時啟動三層;Rust ↔ Python ping/pong 訊息互通。
**Research**:無 (純工程)
**Risks**:無

---

### M0.2 Tauri IPC 與 Sidecar 行程管理 `[MVP]`

**Purpose**:管理 FastAPI 子行程生命週期與前後端即時通訊。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M0.2.1 | Rust `Command` 攔截器:管理 FastAPI 子行程啟動/關閉、Port 衝突與重啟 |
| M0.2.2 | Tauri ↔ 前端 WebSocket/SSE 本地通道,實現 0ms 對話推播 |

**Deps**:M0.1
**Criteria**:強制終止 sidecar 後 3 秒內自動恢復;前端完整接收所有事件。
**Research**:無 (純工程)
**Risks**:無

---

### M0.3 環境變數與資料庫遷移引擎 `[MVP]`

**Purpose**:統一管理 API Keys 與多資料庫遷移流程。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M0.3.1 | `.env` 統一管理 Gemini、Leonardo.ai、GitHub OAuth 等 API Keys |
| M0.3.2 | Alembic (後端) 遷移流程,單一指令建表與回滾 |

**Deps**:M0.1
**Criteria**:單一指令完成建表與回滾。
**Research**:無 (純工程)
**Risks**:無

---

### M0.4 跨層觀測與結構化日誌 `[MVP]`

**Purpose**:Rust / Python / 前端共用的統一可觀測性基礎。M4.5 (XP 結算)、M4.4 (深夜草稿)、M5.2 (NSVIF 反溯因) 全都隱性依賴它。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M0.4.1 | 三層統一的結構化 JSON log 格式定義 |
| M0.4.2 | 寫入管線:事件 → 結構化 JSON → 本地 SQLite `raw_tracking_logs` |

**Outputs**:結構化 JSON log → `raw_tracking_logs` (M6.1)
**Deps**:M0.2, M6.1
**Criteria**:三層任意事件 1 秒內落地至 `raw_tracking_logs`,可被 SQL 查詢。
**Research**:無 (純工程,但為 R02/R04/R08 模組的隱性前置)
**Risks**:無

---

## 👁️ M1 前端感知與輸入層 (Ambient Sensors)

### M1.1 OS 級別遙測守護行程 (Rust Native) `[MVP]`

**Purpose**:系統神經末梢,在 OS 層收集焦點/鍵鼠/視窗事件,即時去識別化後寫入 `raw_tracking_logs`。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M1.1.1 | UIAutomation API 橋接:抓取 Word / Notion 視窗標題與純文字 |
| M1.1.2 | 全域鍵鼠防抖監聽器:計算 WPM、即時去識別化 |
| M1.1.3 | 焦點視窗活躍時間記錄器 + **行為狀態八態分類器 (ActivityStateClassifier)**:背景持續記錄頁面焦點變化,並根據多信號融合判定 DEEP_FOCUS/ACTIVE/PASSIVE_CONSUMPTION/DOOM_SCROLLING/CONTEXT_SWITCHING/RESEARCH_READING/MEETING_CALL/IDLE 八種狀態 |
| M1.1.4 | 隱私硬體禁用約束:系統層強制屏除攝影機/麥克風/定位等實體追蹤 |

**Deps**:M0.2, M0.4, M6.1
**Criteria**:30 分鐘活躍時段正確分桶記錄;任何 PII 不會原文落盤;ActivityState 八態分類正確率 ≥80%。
**Research**:`[R02: 計算心理語言學 §1]` `[R06: 數位表型 §2.1]`
**Risks**:無

---

### M1.2 斷點偵測引擎 (Defer-to-Breakpoint Engine) `[MVP]`

**Purpose**:精準偵測使用者的「任務斷點」,在低認知負荷時才推送通知,防範破壞性中斷。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M1.2.1 | 多模態斷點偵測:游標停頓、App Switching、語音停頓、IDE 焦點離開 + M1.1 ActivityState 信號 |
| M1.2.2 | 深度工作防擾鎖定器:高認知負荷時強制攔截系統音效與通知 (Windows SetNotificationMode);離開時自動恢復 |
| M1.2.3 | 斷點事件派發器 + **錯開調度器**:向 Tauri 廣播 `BREAKPOINT_DETECTED` 事件;管理 cooldown;多 Persona L2 通知以隨機延遲 1~60s 錯開釋放 |

**Deps**:M1.1
**Consumed by**:M3.9 (通知儀表板)、M4.4 (反思草稿觸發)、M1.5 (微 nudges)
**Criteria**:深度工作期間零中斷;正確識別 ≥80% 的自然任務斷點。
**Research**:`[R08: Defer-to-Breakpoint §二]` `[R08: 警報疲勞 §三]`
**Risks**:RISK-04 (與即時 XP 慶祝的分流)

---

### M1.3 IDE / Web 擴充掛載 `[MVP]`

**Purpose**:從 VS Code 與瀏覽器採集程式碼活動與閱讀行為。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M1.3.1 | VS Code AST 攔截器:計算「源碼變更熵」(Shannon Entropy) 與停留時間,Local Socket 回傳 Tauri |
| M1.3.2 | 瀏覽器擴充 (Chrome, Firefox, Edge MV3):頁面焦點變化、閱讀停留時間 |

**Deps**:M0.2, M0.4 (M1.1 為並列感測器層,非直接上游依賴)
**Criteria**:M1.3.1 正確上報 5 分鐘視窗內的源碼變更熵與停留時間;M1.3.2 正確上報瀏覽器分頁停留時間與 domain_bucket 分類;兩者均在 Socket/NativeMessaging 斷線後能 buffer 重傳。
**Research**:`[R02: 源碼變更熵 §1.1]` `[R02: 時間動力學 §1.2]` `[R06: 數位表型 §2.1]`
**Risks**:無

---

### M1.4 Git 與工作流遙測接收器 (Git & Workflow Telemetry) `[MVP]`

**Purpose**:雙軌模式感知開發活動 — 本地 Git 掃描（離線即時）+ GitHub Webhook（雲端推送）。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M1.4.1 | OAuth 2.0 授權流程:連接 GitHub 取得 Access Token |
| M1.4.2 | Webhook Endpoints:解析 GitHub Commit Push / PR / Issues Payload |
| M1.4.3 | **本地 Git 偵測器**:定期掃描本機 `.git` 目錄,偵測離線 commit 活動,100% 離線運作 |

**Deps**:M0.2, M0.3 (MVP Webhook 連通用 `gh webhook forward`；Cloudflare Tunnel 為 Phase 6+ 選項)
**Criteria**:Webhook commit 後 5 秒內出現在 `raw_tracking_logs`;本地 commit 後 60 秒內出現在 `raw_tracking_logs`。
**Research**:`[R06: 版本控制紀錄 §2.1]` `[R02: 時間動力學 §1.2]`
**Risks**:無

---

### M1.5 經驗取樣微 nudges 引擎 (Micro-Nudges) `[進階]`

**Purpose**:在任務斷點推播極短單鍵問卷,拆解繁重日報為極低門檻微互動。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M1.5.1 | 全域微型問卷推播:Tauri 排程 + Web Push,定時觸發 (例:「今天朝『微積分』目標邁進了嗎? [有/沒有]」) |
| M1.5.2 | 異步輕量寫入端點:`target_alignment_status` 不開啟主程式直接寫入 |
| M1.5.3 | 微互動本地暫存與異步同步:作為深夜反思草稿的因果校準依據 |

**Deps**:M1.2 (必須在斷點才推播)
**Consumed by**:M4.4
**備註**:「打破負向信念時主動強化」的觸發 (見 `dev_logs/non_m6_features_brainstorm.md` §1.2) 2026-10-19 起由 M5.5.4 小實驗判定提供;M1.5 只負責單鍵問卷。
**Research**:`[R08: 微干預 §三.3]` `[R10: 認知負荷消解]`
**Risks**:無

---

### M1.6 WebGPU / WASM 端側模型部署 `[進階]`

**Purpose**:在瀏覽器內直接跑邊緣推論,徹底解放 IDE 底層算力。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M1.6.1 | CogentLM 引擎掛載:整合先進瀏覽器推理引擎 |
| M1.6.2 | 首字延遲優化:嚴格 ≤35.5ms |

**Deps**:M2.2
**Research**:`[R07: WebAssembly 3.0 + WebGPU §2]`
**Risks**:RISK-11 (RAM 預算)

---

## 🛡️ M2 邊緣運算與安全防禦層 (Edge Security & Inference)

### M2.1 事件防抖與排隊引擎 `[MVP]`

**Purpose**:攔截高頻系統操作,30~60 秒打包一批避免塞爆後端。

**子模組**:無 (Rust + 內嵌 queue,可選 Redis)

**Deps**:M0.2, M0.4
**Criteria**:1000 個高頻事件正確去抖為單一批次。
**Research**:無 (純工程)
**Risks**:無

---

### M2.2 Gemma 邊緣推論管線 (ai.local) `[MVP]`

**Purpose**:隱私過濾海關,將原始行為降維壓縮為「去識別化意圖標籤」。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M2.2.1 | 載入 4-bit 量化 Gemma 4 E4B 模型 (iPad M1, <3GB RAM) |
| M2.2.2 | POST 框架提示詞:將明文壓縮為 `Intent Vectors` (JSON) |
| M2.2.3 | 即時事件推論 API:消化前端傳入的焦點變化與微互動數據 |

**Deps**:M2.1
**Criteria**:推論延遲 < 500ms;Intent Vector schema 通過 JSON Schema 驗證。
**Research**:`[R07: Gemma 4 E4B §1.1]` `[R07: POST 框架 §4.3]`
**Risks**:RISK-05 (意圖向量導致圖譜空洞化), RISK-12 (側通道洩漏)

---

### M2.3 Eguard 密碼學過濾器 (基礎防禦) `[MVP]`

**Purpose**:PII 遮蔽 + Prompt Injection 防禦的第一道防線。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M2.3.1 | Regex PII 遮蔽:自動抹除 IP、Email、Token、信用卡號 |
| M2.3.2 | DRIFT 隔離框架:攔截並驗證從外部 Git Commit 傳入的字串,防範 Prompt Injection |

**Deps**:M0.4
**Criteria**:OWASP LLM Top 10 之 Prompt Injection 測試集 ≥90% 防禦率。
**Research**:`[R07: 嵌入逆向攻擊 §5.1]` `[R02: DRIFT §架構安全性]`
**Risks**:無

---

### M2.4 進階隱私防禦套件 `[進階]`

**Purpose**:進階密碼學防禦,抵禦 Zero2Text 等先進嵌入逆向攻擊。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M2.4.1 | 意圖向量轉譯器:敏感原始碼/日誌 → 連續意圖向量的語意壓縮 |
| M2.4.2 | 隱私微調與知識蒸餾模組:差分隱私技術解決模型權重耦合風險 |
| M2.4.3 | 公開資料映射傳輸器:去識別化向量安全上雲 |
| M2.4.4 | 互資訊優化雙層防禦器:抵禦 Zero2Text 等嵌入逆向攻擊 |
| M2.4.5 | 敏感句法剝離 + 抽象語意放行:剝離具體變數名稱,僅保留抽象語意 |

**Deps**:M2.2, M2.3
**Research**:`[R07: Eguard §5.2]` `[R06: 差分隱私 §7.4]`
**Risks**:無

---

### M2.5 PRISM 動態語意協作路由 `[進階]`

**Purpose**:動態評估指令敏感度,雲端僅產生「語意草圖」,邊緣做細節填補。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M2.5.1 | 指令敏感度評估器:即時評估指令隱私敏感度 |
| M2.5.2 | 雲端語意草圖生成器:非敏感部分由雲端大模型生成「語意草圖」 |
| M2.5.3 | 邊緣 L2 主動渲染填補器:邊緣模型利用本地上下文進行細節填補 |

**Deps**:M2.2, M2.4
**Research**:`[R07: PRISM §6]`
**Risks**:無

---

### M2.6 超大上下文視窗 (128K) `[進階]`

**Purpose**:不依賴本地伺服器的 128K 上下文邊緣運算。

**子模組**:無

**Deps**:M2.2
**Research**:`[R07: Gemma 4 E4B PLE §1.1]`
**Risks**:RISK-11 (RAM 預算)

---

## 🖥️ M3 前端 UI/UX 狀態與渲染層 (React Components)

### M3.1 全域狀態與佈局 (Zustand) `[MVP]`

**Purpose**:全域變數管理 + Pub/Sub 事件派發。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.1.1 | 管理 `CurrentRole`、`XP_Balance`、`Active_Expert` 等全域變數 |
| M3.1.2 | 發布-訂閱:`ROLE_SWITCHED` 事件觸發全局 UI 重繪 |

**Deps**:M0.1
**Criteria**:角色切換 → UI 100ms 內完成過渡。
**Research**:無 (前端工程)
**Risks**:無

---

### M3.2 角色儀表板 (Role-based Dashboard) `[MVP]`

**Purpose**:全域狀態切換中心與情境錨點,營造角色切換的「儀式感」。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| **M3.2.1** | **底部焦點橫向輪盤 (Visual Focus Carousel Dock)** |
| M3.2.1.1 | 橫向 Carousel:物理慣性滑動 + Snap to Center |
| M3.2.1.2 | 中央 Icon 自動放大 (Active State Scale) |
| M3.2.1.3 | 停頓完成派發 `ROLE_SWITCHED` |
| **M3.2.2** | **儀式感背景過渡引擎 (Smooth Transition Background)** |
| M3.2.2.1 | 監聽 `ROLE_SWITCHED` 即時變更主題色調 |
| M3.2.2.2 | 色溫平滑漸變 (CSS / Framer Motion / WebGL) |
| M3.2.2.3 | 介面光效遮罩 (Ambient Glow Filter) 降低對比、減少切換認知耗損 |
| **M3.2.3** | **短期記憶喚醒聚合區 (Context Header Aggregator)** |
| M3.2.3.1 | Bento Grid 三槽位:Project / Promises / Goal |
| M3.2.3.2 | 角色資料預快取 (Pre-fetching Cache),3 秒內無縫加載 |
| M3.2.3.3 | Skeleton UI 骨架屏,防止異步加載時版面跳動 |
| **M3.2.4** | **角色活躍度熱圖 (Consistency Heatmap)** |
| M3.2.4.1 | GitHub Contributions 樣式網格矩陣 |
| M3.2.4.2 | 四階色彩深淺映射演算法 |
| M3.2.4.3 | Tooltip Hover:顯示當日具體推進計數 |

**Deps**:M3.1, M6.3, M6.4
**Criteria**:角色切換到 Bento Grid 顯示完成 ≤ 3 秒。
**Research**:`[R08: 心理所有權 §一]` (儀式感切換降低認知耗損)
**Risks**:無

---

### M3.3 日報與反思模組 (Daily Report & Reflection) `[MVP]`

**Purpose**:時間軸紀錄每日任務 + 結構化反思 + 經驗值發放的守門員。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| **M3.3.1** | **雙維度時間軸與角色分組** |
| M3.3.1.1 | CSS `border-left` 垂直時間軸,可滑動切換日期 |
| M3.3.1.2 | 右側任務卡片 Grid,依生活角色嚴格群組分類 |
| **M3.3.2** | **寬容耗時卡片組件** |
| M3.3.2.1 | 狀態膠囊:「進行中」/「已完成」 |
| M3.3.2.2 | 耗時雙軌載入:優先讀取 AI 套問結果 |
| M3.3.2.3 | 兜底:若 AI 未套問,自動載入 IDE 活躍時間推算值 |
| **M3.3.3** | **草稿核准彈窗 (Draft & Approve Modal)** ⚠️ 核心心理機制 |
| M3.3.3.1 | 獨立覆蓋層,**絕不**背景全自動寫入日報 (避免適應悖論) |
| M3.3.3.2 | 吉布斯反思循環區:AI 填補「客觀描述」「初步分析」 |
| M3.3.3.3 | **強制留白欄位**:使用者必填「主觀感受」「未來行動」 |
| M3.3.3.4 | **嚴格驗證器**:未答「學到了什麼?」或「對齊初始目標?」→ 不發 XP |

**Deps**:M3.1, M4.4, M6.4
**Criteria**:草稿未填強制欄位時 XP API **必須拒絕發放**。
**Research**:`[R08: 微摩擦力 §四.2]` `[R08: IKEA 效應 §六.1]` `[R08: 吉布斯循環 §六.2]` `[R10: MindScape]`
**Risks**:RISK-01 (XP 提前發放)

---

### M3.4 沉浸式多智能體幫手模組 (Multi-Agent AI Helper) `[MVP]`

**Purpose**:核心輸入介面,雙軌制 (工具 AI + 擬真人設專家) 的對話與配對。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| **M3.4.1** | **雙軌側邊欄與視圖** |
| M3.4.1.1 | 首位固定「工具型 AI」(無人設、純客觀、高效除錯) |
| M3.4.1.2 | 其餘為「擬真人設專家」清單 |
| M3.4.1.3 | 右側並列「使用者虛擬頭像」「專家職稱」「專家名稱」 |
| **M3.4.2** | **動態專家配對控制器** |
| M3.4.2.1 | 「配對」按鈕 + 狀態輸入彈窗,**禁止**直接從清單挑選 |
| M3.4.2.2 | 「新增配對」:輸入當下狀態擴充新專家 |
| M3.4.2.3 | 「重新配對」:檢討上個專家配置,為同職位指派風格不同的新專家 |
| **M3.4.3** | **強化的多模態輸入區** |
| M3.4.3.1 | `[+]` 按鈕:上傳 PDF / 圖片 |
| M3.4.3.2 | `[🔗]` 按鈕:貼上網址作為對話脈絡 |
| M3.4.3.3 | 麥克風:語音意識流 → 轉錄 → 送出 |
| **M3.4.4** | **隱形自動化與進展效應 UI** |
| M3.4.4.1 | 自動渲染隱形提示 (例:「Project 偵測為『初始目標設定』創立」) |
| M3.4.4.2 | 背景創建專案時強制賦予非零初始進度條 (Endowed Progress Effect) |

**Deps**:M3.1, M4.1, M4.6
**Criteria**:對話下方正確顯示後端 System Event 隱形提示。
**Research**:`[R03 §1]` `[R05 §治療同盟]` `[R09 §6.1 MAS]`
**Risks**:RISK-11 (語音 + RAM)

---

### M3.5 視覺化成就展示模組 (基礎) `[MVP]`

**Purpose**:成就與徽章的 Master-Detail 展示。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.5.1 | Master-Detail 佈局:左側 CSS Grid 徽章槽位,右側動態渲染解鎖條件與描述 |
| M3.5.2 | 已解鎖背景與徽章的網格展示庫 |

**Deps**:M3.1, M6.5
**註**:抽卡互動 (Gacha) 屬進階 → M3.11;技能樹屬進階 → M3.10。
**Research**:無 (UI 設計)
**Risks**:無

---

### M3.6 脈絡內自動化設定彈窗 (In-Context Workflow Modal) `[MVP]`

**Purpose**:不脫離對話即可設定外部資料源綁定與自動化觸發。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.6.1 | 對話框快捷喚出:`workflow` 按鈕 |
| M3.6.2 | 外部資料源綁定 UI:GitHub Repo、本機 Obsidian、瀏覽器日誌端點 |
| M3.6.3 | 觸發條件設定表單:事件 (Commit)、時間週期、關鍵字 |

**Deps**:M3.4, M1.4
**Research**:`[R10: 代理工作流狀態機]`
**Risks**:無

---

### M3.7 社群與社會情懷模組 (Community UI) `[進階]`

**Purpose**:同儕驗證 + 公開承諾 + 社交情境隔離。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.7.1 | Bento Grid 儀表板佈局 |
| M3.7.2 | 社交隔離子社群切換器 (右側垂直 Carousel) |
| M3.7.3 | 社交壓力切換控制器 (陌生人 / 朋友圈) |
| M3.7.4 | 社群共識靜態展示區 (Goal / Vision / Codex) |
| M3.7.5 | 成就與貼文動態牆 |
| M3.7.6 | 定期挑戰展板 (Weekly / Monthly) |
| M3.7.7 | 承諾與驗證閉環控制區 (Tasks → Commitments → Validation) |
| M3.7.8 | XP 質押對賭介面 |

**Deps**:M4.13, M6.6, M6.5, M2.3, M4.8
**MVP 策略**:以 stub 卡片佔位即可。
**Research**:`[R09: 社會情懷 §4.1]` `[R01: α-DPO Dropout 危機]` `[R07: 嵌入逆向攻擊 §5]` `[R08: 草稿與核准]`
**Risks**:RISK-07 (ZPD + 質押複合挫敗)、RISK-09 (社群壓力 + 焦慮)、RISK-12 (社群貼文側通道洩漏)、RISK-18 (AI 挑戰生成器側通道)
**SPEC**:`docs/modules/M3_7_community_ui_SPEC.md` v2.0 (前後端全鏈路接線)

---

### M3.8 週期性回顧 Wrapped 彈窗 `[進階]`

**Purpose**:每週/月自動結算,以故事性敘事卡片呈現成長。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.8.1 | 每週/每月自動結算 → 故事性敘事卡片 |
| M3.8.2 | Wrapped 彈出視窗 + 多巴胺視覺特效 |

**Research**:`[R10: 敘事化福祉 §Narrating Fitness]`
**Risks**:RISK-10 (低 mood_score 時的 Gaslighting 感)

---

### M3.9 防疲勞非同步通知儀表板 `[進階]`

**Purpose**:低急迫性草稿靜默歸檔,防範警報疲勞。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.9.1 | 靜默歸檔通知中心 (防警報疲勞 Alert Fatigue) |
| M3.9.2 | 延遲恢復低干擾提示:僅在 M1.2 斷點訊號時溫和浮現 |
| M3.9.3 | 每日批次審閱檢視表 |

**Deps**:M1.2
**Research**:`[R08: 警報疲勞 §三.1]`
**Risks**:RISK-04 (通知三層分類)

---

### M3.10 技能樹與知識網狀圖 `[進階]`

**Purpose**:可動態點亮的節點拓樸圖,將個人成長目標具象化。

**Deps**:無 (2026-10-19 起不再依賴 M5,且**不顯示冰山節點**:把心理層畫成可點亮的遊戲節點等於將「自我」遊戲化,見 `M5_ICEBERG_REDESIGN.md` §4.1)
**Research**:`[R04: 拓樸演化 §GraphRAG]`
**Risks**:無

---

### M3.11 遊戲化抽卡組件與視覺合成工坊 (Gamification Gacha UI & Visual Studio) `[已實作]`

**Purpose**:變動比例增強的盲盒抽卡、隱藏成就與 AI 視覺排版融合工坊。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.11.1 | 變動比例盲盒抽卡介面 (100 XP 抽背景/物件，支援官方精選與自創混合池，60 分鐘上限 5 次滑動視窗防沉迷冷卻，L1 即時開獎) |
| M3.11.2 | 程序化任務「🎲 抽挑戰」按鈕 (基於 ZPD 動態難度，嚴格禁止 XP 質押與損失) |
| M3.11.3 | 隱藏成就**絕對無 UI 狀態**控制器 (解鎖前完全不產生 DOM 節點，零洩漏防 FOMO) |
| M3.11.4 | 隱藏成就無預警驚喜彈窗 (WebSocket/SSE 即時監聽與 FIFO 佇列展示) |
| M3.11.5 | 焦慮推播門禁 (偵測焦慮/迴避/抑鬱狀態主動封鎖推播) 與 AI 視覺合成工坊 (背景/透明物件生圖、畫布排版拖曳、非破壞性光影 AI 融合、自訂桌面主題套用) |

**Deps**:M3.5, M4.11, M4.12, M6.5
**Implementation**: `apps/desktop/src/components/m3_11_gacha/`, `specs/001-m3-11-gacha-ui/`
**Research**:`[R01: α-DPO Dropout 危機 §α-DPO]`, `[R09: 病態使用風險 Replika 案例 §3.3]`, `[R08: IKEA 效應 §VI.1]`
**Risks**:RISK-04 (即時慶祝不經 Defer), RISK-07 (ZPD 任務零質押), RISK-09 (焦慮門禁封鎖推播)
**SPEC**:`docs/modules/M3_11_gacha_ui_SPEC.md`

---

### M3.12 冰山之鏡 (Iceberg Mirror — 透明與控制) `[進階]`

**Purpose**:讓使用者在主動打開時看見系統目前對自己的理解,並能確認、修正、封存話題、暫停或刪除。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.12.1 | 首次同意流程 (寫入 `user_consents`, consent_type = `m5_iceberg`) |
| M3.12.2 | 假設列表 (無術語語言 + 三段信心) 與推理路徑「這個猜測是怎麼來的」(最強 1–2 條祖先路徑 + 競爭假設) |
| M3.12.3 | 回饋操作:對 / 不太對 / 完全不是 / 這個話題先不要碰 |
| M3.12.4 | 控制:暫停 N 天、碰撞劑量上限 (預設 2,可開到 3)、刪除全部 |

**Deps**:M5.1, M5.4, M3.1
**Research**:`[R08: §五 意圖脫鉤與作者身分五大設計模式]` `[R04: 心理幻覺 §心理幻覺的定義與生成機制]`
**Risks**:RISK-21, RISK-23
**SPEC**:`docs/modules/M3_12_iceberg_mirror_SPEC.md`

---

### M3.13 小實驗卡 (Micro-Experiment Card) `[進階]`

**Purpose**:在儀表板呈現系統提議的小實驗,讓使用者自主接受、婉拒或換一個,並顯示觀察結果。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.13.1 | 提議卡 (接受 / 不要 / 換一個) |
| M3.13.2 | 觀察中狀態與到期 |
| M3.13.3 | 結果呈現 (只陳述觀察到的事實,反思交給使用者) |

**Deps**:M5.5, M3.2
**Research**:`[R23: 行為實驗 §實驗設計]` `[R09: SDT §第四章]` `[R25: 生成效應 §實驗結果]`
**Risks**:RISK-22, RISK-01
**SPEC**:`docs/modules/M3_13_micro_experiment_card_SPEC.md`

---

## 🧠 M4 多智能體邏輯與業務層 (FastAPI + LangGraph)

### M4.1 Agent 路由與協作管線 (LangGraph 結構層) `[MVP]`

**Purpose**:LangGraph 純結構層,提供信心分層路由、容器與安全規劃,不含 Persona 內容。路由規則依 role_id 完全隔離,並透過 M4.1.5 每日自適應更新。

**子模組**:

| 編號 | 職責 | 執行時序 |
| ---- | ---- | -------- |
| M4.1.1 | **信心分層 Router**:三層決策引擎 (Rule → LLM 背景驗證 → LLM 主導),候選池由 M4.3 白名單限定 | 即時,每次對話 |
| M4.1.2 | Persona Agent 容器:純結構接點,Prompt 內容由 M4.2 注入 | 即時 |
| M4.1.3 | Observer / Drafting Agent 容器:背景非同步協調,具體萃取邏輯在 M4.6 | 即時並行 |
| M4.1.4 | DRIFT 安全規劃器:防範外部訊號挾持 Agent 系統提示詞 | 即時,M4.1.1 之前 |
| **M4.1.5** | **自適應規則更新器**:每日批次從 `daily_reflections` 任務標題 + `routing_samples` 負向信號抽取關鍵字,更新 `role_router_rules` 候選池;達門檻後自動晉升為 active 規則 | 每日深夜排程 |

**Deps**:M2.2, M2.3, M4.3, M6.1 (`role_router_rules`, `routing_samples`)
**Criteria**:

- 路由準確率 ≥85% 於人工標註測試集
- confidence ≥ 0.85 時 LLM 補判觸發率 = 0%
- M4.1.5 每日執行後候選規則數量不為負成長

**Research**:`[R09: MAS §6.1]` `[R02: DRIFT §架構安全性]` `[R03: LangGraph §1]` `[R10: §代理工作流狀態機]`
**Risks**:RISK-06 (跨角色規則洩漏), RISK-13 (訓練信號含明文), RISK-14 (LLM 補判上雲)

---

### M4.2 擬真人設與心理狀態機 (Persona Prompt 工程層) `[MVP]`

**Purpose**:將 Persona Agent 從靜態提示詞容器升級為具備固定個性、副語言、阻抗消解的擬真治療同盟。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.2.1 | 系統提示詞工程:固定人設 + 過往經歷敘事 + 副語言線索 (「嗯...」「讓我想想」) |
| M4.2.2 | 阻抗消解控制器 (Echo Mode):偵測防衛語氣 → 動態調降 Agency → 切換至共情傾聽 |
| M4.2.3 | 社會承諾與同理心制約:透過人設引發適度責任心,降低逃避機率 |
| M4.2.4 | 副語言瑕疵渲染:填充詞、自我修正、演算法弱點主動暴露,跨越恐怖谷 |

**Deps**:M4.1
**Criteria**:防衛性語氣輸入 → sentiment 由「指令型」自動切換為「共情型」。
**Research**:`[R03: Echo Mode §3.2]` `[R03: ARPM §2]` `[R05: 跨越恐怖谷]` `[R05: 合成心理病理學]` `[R09: SDT §4.1]` `[R09: BDI §6.2]`
**Risks**:RISK-02 (Echo+ARPM), RISK-03 (焦慮鏡像), RISK-06 (跨角色洩漏), RISK-08 (BDI 矛盾)

**完整 SPEC 範例**:見 `docs/modules/M4_2_persona_state_machine_SPEC.md`

---

### M4.3 全域情境隔離狀態機 (Role Isolation) `[MVP]`

**Purpose**:依 Role_ID 隔離資料流、DB 連線、Persona 配置,確保角色間零資料交叉。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.3.1 | 資料流沙盒中介軟體:依 `Role_ID` 路由 API 請求 |
| M4.3.2 | 資料庫連線動態切換器:強制讀寫對應角色隔離沙盒 |
| M4.3.3 | 動態 Persona 注入:依角色更換 LangGraph 啟用之專家配置 |
| M4.3.4 | 系統提示詞快取重置:確保 AI 回應語氣完全隔離 |

**Deps**:M4.1, M6.3
**Criteria**:A 角色資料**絕不**出現在 B 角色查詢結果。
**Research**:`[R03: 人設崩塌 §2]`
**Risks**:RISK-06 (隱性狀態跨角色洩漏)

---

### M4.4 自然套問與草稿生成器 `[MVP]`

**Purpose**:在對話中自然套問耗時資訊 + 深夜排程自動拼裝反思草稿。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.4.1 | 對話套問控制器:在 Persona Prompt 注入自然套問 (例:「這份作業大概花了你多久?」) |
| M4.4.2 | NER + Regex 解析器:從聊天回覆抽取時間跨度 → 寫入任務暫存槽 |
| M4.4.3 | 異步客觀草稿排程器:深夜 Cron → 拉取 `raw_tracking_logs` → 拼裝吉布斯描述 → 更新 `daily_reflections` |

**Deps**:M4.1, M4.2, M6.1, M6.4
**Criteria**:每日 02:00 自動產出前一日完整草稿。
**Research**:`[R10: 代理工作流 §狀態機]` `[R10: MindScape §反思鷹架]` `[R08: 意圖脫鉤 §五]`
**Risks**:RISK-01 (草稿 + XP 結算交互)

---

### M4.5 零摩擦 XP 自動結算引擎 `[MVP]`

**Purpose**:從數位足跡自動結算 XP,但**必須等核准**才發放 Earned XP。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.5.1 | 數位足跡自動結算腳本:`raw_tracking_logs` → XP 派發 → 更新日報 |
| M4.5.2 | 殭屍草稿淘汰 Cron:自動刪除長期未審草稿,防倦怠 |

**Deps**:M4.4, M6.4, M6.5
**Research**:`[R08: IKEA 效應 §六.1]` (Earned XP 必須等 is_reviewed)
**Risks**:RISK-01 (XP 提前發放 — **最重要的風險之一**)

---

### M4.6 Observer 背景萃取 Agent `[MVP]`

**Purpose**:平行監聽對話 → 萃取「意圖」「專案」→ Function Calling 寫入 DB → 觸發前端 System Event。

**子模組**:無 (單一 LangGraph 節點)

**Deps**:M4.1, M6.2
**Criteria**:對話含「我想做 X 專案」→ 5 秒內 `projects` 表出現對應紀錄。
**Research**:`[R02: 動態狀態解碼 §HMM]` `[R10: 結構化 §代理工作流]`
**Risks**:RISK-08 (belief/desire 矛盾), RISK-12 (推論結果上雲)

---

### M4.7 Markdown 同步至 Obsidian Agent `[進階]`

> **已移出 MVP (2026-06-10 拍板)**:MVP 閉環不依賴 Obsidian,移至 Phase 6 (見 `docs/IMPLEMENTATION_GAP_REPORT.md` GAP-A1、`docs/06_implementation_phases.md`)。原標籤 `[MVP]`。
>
> **2026-10-19 D-3**:M4.7a Vault Governance Reader (唯讀) 升為下一階段主軸,排在 M5 之前;M4.7b / M4.7c 不擋 M5 (見 `docs/MVP_CLOSURE_REPORT.md` §7.5)。

**Purpose**:Session 結束 → 歸納重點 → 寫入指定 Obsidian Vault。

**子模組**:無

**Deps**:M4.6
**Research**:無 (工具整合)
**Risks**:無

---

### M4.8 隱性狀態推論管線 `[進階]`

**Purpose**:從代碼提交、對話語氣、IDE 活動中非監督式推斷「焦慮/逃避/心流」。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.8.1 | 特徵矩陣萃取:DistilBERT 情感 + 源碼變更熵 + 時間動力學 |
| M4.8.2 | 隱性狀態解碼:孤立森林 + HMM/HSMM + Viterbi → 常態/焦慮/逃避 |
| M4.8.3 | 認知分析:POMDP + 多模態 BKT → 認知負荷透視 + ZPD 邊界動態縮放 |
| M4.8.4 | 心理指標降維轉譯:冰冷日誌 → 「焦慮」「逃避」等心理標籤 (應對姿態部分 2026-10-19 移交 M5.2.1) |
| M4.8.5 | REMT YAML 上下文工程:DRIFT 保護下將推論結果注入 Persona 決策樹 |

**Deps**:M2.2, M4.1, M4.2 (2026-10-19 移除對 M5.1 的依賴;M5.4 / M5.5 改為讀取 `role_implicit_states`)
**Research**:`[R02: 非監督式管線 §全章]` `[R01: POMDP+BKT §動態追蹤]` `[R06: 應對姿態 §4.2]`
**Risks**:RISK-03 (焦慮鏡像), RISK-06 (跨角色洩漏), RISK-09 (Gacha 推播門禁)

---

### M4.9 ARPM 異質時序記憶治理 `[進階]`

**Purpose**:雙時序重排序 + 證據稽核,防漫長對話中的「人設崩塌」。

**子模組**:無 (核心為排序演算法)

**Deps**:M4.1 (2026-10-19 起併入原 M5.3 Graph 層 ARPM 職責)
**Research**:`[R03: ARPM §2]`
**Risks**:RISK-02 (與 Echo Mode 的衝突)

---

### ~~M4.10 NSVIF 神經符號驗證 + D-ALP~~ `[退役]`

> 2026-10-19 併入新 **M5.3 符號驗證器**,以下為歷史紀錄。

**Purpose**:論述加權溯因邏輯,確保心理剖繪有客觀事實支撐,防範心理幻覺。

**子模組**:無

**Deps**:M5.2
**Research**:`[R04: 神經符號驗證 §D-ALP]` `[R04: 反溯因驗證]`
**Risks**:RISK-05 (意圖向量精度)

---

### M4.11 動態 ZPD 任務池生成器 `[進階]`

**Purpose**:從歷史對話分析興趣/痛點,在 ZPD 邊界內生成客製化隨機挑戰。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.11.1 | 歷史脈絡興趣分析器:Observer 持續分析 → 擷取「興趣延伸點」「期待改善點」 |
| M4.11.2 | 多模態 BKT 認知負荷推斷器 |
| M4.11.3 | ZONE 貝氏任務池生成器:動態 ZPD 邊界內的客製化隨機挑戰 |

**Deps**:M4.6, M4.8
**Research**:`[R01: ZONE 框架 §理論基礎]` `[R01: DDA+PCG §建構性基元]`
**Risks**:RISK-07 (ZPD + XP 質押複合挫敗)

---

### M4.12 隱藏成就驗證引擎 (Hidden Achievement Verification Engine) `[進階]` `[已實作]`

**Purpose**:背景無感驗證使用者自主探索、元認知重構、生活恢復與跨領域融通，透過心流微斷點觸發無預警驚喜解鎖，嚴格隔離未解鎖成就以杜絕 FOMO。

**SPEC**:[docs/modules/M4_12_hidden_achievement_SPEC.md](./modules/M4_12_hidden_achievement_SPEC.md)

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.12.1 | 主動探索特徵捕捉網:快慢雙軌混合架構 (快軌正則 <100ms + 慢軌本地 Gemma 語意深度分析與超時佇列) |
| M4.12.2 | 心流感知微斷點推播與 WebSocket 廣播:整合 M1.2 門禁與開機單上限 (Single Cap) 補發 |
| M4.12.3 | 零洩漏狀態隔離:SQL 層與 API 序列化層強制過濾未達成隱藏成就 (M3.11.3 鐵律) |
| M4.12.4 | 四大核心成長原型與 AI 個性化金句合成 (好奇探險家、心靈煉金術士、微光漫遊者、通識織網者) |
| M4.12.5 | ACID 交易寫入、XP 發放稽核與 60 秒滑動視窗防刷 (整合 M6.5 與 M0.4) |

**Deps**:M1.2, M2.2, M3.11, M6.5, M0.4
**Criteria**:快軌特徵掃描 <100ms;未解鎖隱藏成就 0% 洩漏至 API/DOM;心流深層工作時零通知干擾;成就終身限解鎖 1 次並具備 ACID 交易保證。
**Research**:`[R01: 動態邊界]` `[R08: Defer-to-Breakpoint §二]`
**Risks**:RISK-04 (心流感知微斷點門禁)

---

### M4.13 損失規避與同儕驗證引擎 `[進階]`

**Purpose**:XP 質押對賭 + 社會情懷強制制約 + 跨社群權限隔離。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.13.1 | 損失規避 XP 質押扣管邏輯 (與系統對賭,結算經 M6.5 ACID) |
| M4.13.2 | 社會情懷強制制約器:「沒有退路」的同儕壓力 + 同儕驗證閉環 (混合:點贊/可選證據) |
| M4.13.3 | 跨社群權限隔離中介軟體 (讀書會 / 陌生人 / 朋友圈,含成員上限 2~8 守門) |
| M4.13.4 | AI 週期挑戰生成器:僅讀 L3 聚合統計生成草稿,管理員審核後才 active |

**Deps**:M3.7, M6.5, M6.6, M2.3
**Research**:`[R01: α-DPO Dropout §Dropout 危機]` `[R09: 病態使用 §3.3]` `[R07: 嵌入逆向攻擊 §5]`
**Risks**:RISK-07 (ZPD + 質押複合挫敗)、RISK-09 (社群壓力 + 焦慮)、RISK-18 (AI 挑戰生成器側通道)
**SPEC**:`docs/modules/M3_7_community_ui_SPEC.md` v2.0 §7.4/§10.4

---

## 🧊 M5 薩提爾冰山理解與轉化層 (Iceberg Understanding & Transformation) `[進階]`

> **2026-10-19 重編** (使用者拍板,見 `docs/M5_ICEBERG_REDESIGN.md`)。原「雲端 Neo4j / DGNN / Hawkes」設計退役,**圖模型保留**:冰山以本地 SQLite 邊表儲存、networkx 做記憶體圖分析;全章資料皆為 L1,只存在本地。
> 動工前提:`docs/MVP_CLOSURE_REPORT.md` 存在 (Q4)。本章全數移除時,MVP 必須照常運作。
> 資料流:證據 (M5.2) → 假設 (M5.1) ⇄ 驗證 (M5.3) → 階段追蹤 (M5.4) → 介入規劃 (M5.5) → 指令編譯 (M5.6) → 呈現通道 (M4.2 / M1.2 / M3.3 / M3.12 / M3.13)。

### M5.1 冰山假設庫 (Iceberg Hypothesis Store) `[進階]`

**Purpose**:以本地 SQLite 保存八層冰山假設、層間因果邊、證據與主題,並執行信心更新與衰減。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M5.1.1 | `m5_1_iceberg_hypotheses` / `_links` / `_evidence` / `_prompts` 與 `m5_settings` 綱要與存取層 |
| M5.1.2 | log-odds 信心更新 + 每日衰減 + 層信心上限 |
| M5.1.3 | 狀態機:candidate → working → established → softening → transformed / refuted / user_rejected |
| M5.1.4 | 全量刪除與停用 (使用者控制) |
| M5.1.5 | `IcebergGraph` 圖存取介面:角色子圖載入 (networkx)、祖先路徑、後代;上層模組唯一的圖入口 |

**Deps**:M6.1 (本地 SQLite + Alembic local)
**Criteria**:無上層鏈的 yearning/self 無法建立;self 無 user_stated 永不 established;全量刪除後 MVP 測試照常通過。
**Research**:`[R20: Satir Model §個人冰山]` `[R04: 冰山 §冰山層次節點類型與結構化屬性定義]` `[R04: 心理幻覺 §心理幻覺的定義與生成機制]`
**Risks**:RISK-05 (已於架構上消除), RISK-23
**SPEC**:`docs/modules/M5_1_iceberg_hypothesis_store_SPEC.md`

---

### M5.2 證據萃取器與反應分類器 (Evidence Extractor & Reaction Classifier) `[進階]`

**Purpose**:把既有本地資料轉為冰山證據,並把使用者對介入的反應轉為證據。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M5.2.1 | 規則語言標記 (即時):五種應對姿態、歸因句型、期待句型、感受詞 (吸收原 M4.8.4) |
| M5.2.2 | 本地 Gemma 每日合成:新假設候選、層間連結、強制競爭假設、主題形成 |
| M5.2.3 | 反應分類器:7 種 reaction → 證據 (含 RISK-21 規則) |
| M5.2.4 | 雲端反思讀取器:經 M6.4 API 讀取 `user_feeling` / `user_learned` / `mood_score` 轉本地證據 |

**Deps**:M5.1, M2.2 (本地 Gemma), M6.1 (`chat_transcripts` / `raw_tracking_logs`), M6.4, M1.4, M4.2 (reactance 分數)
**Research**:`[R06: 應對姿態 §4.2]` `[R06: 數位表型 §2.1]` `[R04: 反溯因 §反溯因推理的對抗性驗證]` `[R16: MI §Change Talk]`
**Risks**:RISK-21, RISK-19
**SPEC**:`docs/modules/M5_2_evidence_extractor_SPEC.md`

---

### M5.3 符號驗證器 (Symbolic Verifier, NSVIF-lite) `[進階]`

**Purpose**:以確定性規則檢查每條假設的證據門檻、不跳層、競爭假設與來源可解析性,不合格者拒絕或降級。

**子模組**:無

**Deps**:M5.1, M0.4 (`raw_tracking_logs`), M6.4 API
**Research**:`[R04: D-ALP §神經符號約束滿足與 D-ALP 框架]` `[R04: 反溯因 §反溯因推理的對抗性驗證]`
**Risks**:RISK-05, RISK-21
**SPEC**:`docs/modules/M5_3_symbolic_verifier_SPEC.md`
**備註**:合併原 M5.2 NSVIF 與原 M4.10。

---

### M5.4 轉化歷程追蹤 (Change Process Tracker) `[進階]`

**Purpose**:為每個主題維護薩提爾變化階段,計算變化指標與每位專家的同盟分數。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M5.4.1 | `m5_4_themes` 階段狀態機 (現狀 / 外來元素 / 混亂 / 整合 / 練習 / 新現狀) |
| M5.4.2 | 變化指標:一致性指數、姿態分布、觀點語言轉移、實驗完成率 |
| M5.4.3 | `m5_4_alliance` 同盟分數 (取代靜態 `trust_level` 作為閘門) |
| M5.4.4 | 核心渴望分析 (圖分析):找出同時驅動 ≥2 個主題的渴望,寫入 `m5_4_core_yearnings`,供 M5.5 排序 mode 5 |

**Deps**:M5.1, M5.2, M6.4 API, M6.3 (`role_implicit_states`)
**Research**:`[R20: Satir Model §變化歷程]` `[R17: WAI §Triad Dimensions]` `[R16: MI §Change Talk]`
**Risks**:RISK-20
**SPEC**:`docs/modules/M5_4_change_process_tracker_SPEC.md`

---

### M5.5 介入規劃器 (Move Planner) `[進階]`

**Purpose**:依守門規則與評分,為每一輪 / 每個通道選出至多一個 move (12 種作用方式之一)。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M5.5.1 | Move catalog (12 mode × 每 mode ≥2 條目) |
| M5.5.2 | 守門:全域硬閘、碰撞類閘、碰撞後承接、主動通道斷點閘 |
| M5.5.3 | 評分選擇 (info_gain × readiness + phase_fit − fatigue) |
| M5.5.4 | 小實驗生命週期 (`m5_5_experiments`) 與遙測判定式 (吸收原 M1.5 負向信念觸發) |
| M5.5.5 | `presentation_policy()` 呈現政策旗標 |

**Deps**:M5.1, M5.4, M1.2 (斷點), M4.2 (echo_mode 結果), M1.4 / M0.4 (實驗判定)
**Research**:`[R20: Satir Model §變化歷程]` `[R16: MI §OARS]` `[R21: 矯正性情緒經驗 §核心概念]` `[R22: 外化 §外化對話]` `[R23: 行為實驗 §實驗設計]` `[R24: 改變階段 §階段定義]` `[R25: 生成效應 §實驗結果]` `[R26: 示範學習 §觀察學習]` `[R08: §二 任務斷點打斷管理]` `[R09: 病態使用 §3.3]`
**Risks**:RISK-20, RISK-22, RISK-23, RISK-04, RISK-09
**SPEC**:`docs/modules/M5_5_move_planner_SPEC.md`

---

### M5.6 指令編譯器與洩漏閘 (Directive Compiler & Leak Gate) `[進階]`

**Purpose**:把選中的 move 編譯為不含任何假設內容的專家行為指令,並在離開本層前通過洩漏閘。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M5.6.1 | `IcebergDirective` 編譯與 `[這一輪的陪伴方式]` 區塊 |
| M5.6.2 | 洩漏閘 (術語 / 假設 n-gram / 使用者狀態描述 / 跨角色 quote) |
| M5.6.3 | M4.2 LangGraph `iceberg_move` 節點與 BDI / MI 對接 |

**Deps**:M5.5, M4.2, M2.3 (`eguard.mask_pii`)
**Research**:`[R07: POST §4.3]` `[R03: Echo Mode §3.2]` `[R16: MI §OARS]`
**Risks**:RISK-19, RISK-03, RISK-06, RISK-08
**SPEC**:`docs/modules/M5_6_directive_compiler_SPEC.md`

---

### ~~原 M5.3 ARPM 異質時序記憶治理 (Graph 層)~~ 退役

職責併入 M4.9。原 M5.1 Cypher Writer、原 M5.2 NSVIF 由上方新 M5.1 / M5.3 取代。

---

## 🗄️ M6 資料庫綱要與 ACID 交易層

### M6.1 本地 SQLite 實體 `[MVP]`

**Purpose**:絕對不上雲的私有資料庫。

**Schema**:

- `raw_tracking_logs` (id TEXT UUID PK, timestamp DATETIME, source TEXT, raw_text TEXT)
- `chat_transcripts` (id TEXT UUID PK, thread_id TEXT, role TEXT, content TEXT, timestamp DATETIME)
- `edge_event_buffer` (id TEXT UUID PK, timestamp DATETIME, intent_tag TEXT, is_synced BOOLEAN default False)

**Deps**:M0.3
**Research**:無
**Risks**:無

---

### M6.2 雲端 PostgreSQL 核心實體 `[MVP]`

**Purpose**:跨裝置同步的應用層資料庫。

**Schema**:

- `users` (id UUID PK, username VARCHAR, current_xp INTEGER, level INTEGER, rpg_class VARCHAR, avatar_url VARCHAR)
- `ai_experts` (id UUID PK, user_id UUID FK, expert_name VARCHAR, personality_prompt TEXT, trust_level INTEGER)
- `expert_homepages` (expert_id UUID PK FK, background_image_url VARCHAR, unlocked_features JSONB)
- `expert_projects` (id UUID PK, expert_id UUID FK, title VARCHAR, status VARCHAR, progress_percentage INTEGER)
- `zpd_tasks` (id UUID PK, user_id UUID FK, task_text TEXT, difficulty VARCHAR, xp_reward INTEGER, asset_url VARCHAR, status VARCHAR)

**Deps**:M0.3
**Research**:無
**Risks**:無

---

### M6.3 角色與情境鏈結資料表 `[MVP]`

**Purpose**:角色定義 + 角色到專案/承諾/目標的一對多鏈結。

**Schema**:

- `roles` (id UUID PK, name VARCHAR, theme_color_palette JSONB, created_at TIMESTAMP)
- `role_context_aggregates`:一對多綁定 `role_id` → `expert_projects(id)`、`promises(id)`、`goals(id)`

**Deps**:M6.2
**Criteria**:支援 M3.2.3 的 3 秒短期記憶喚醒查詢。
**Research**:無
**Risks**:RISK-06 (角色隔離依賴此表的 role_id 正確性)

---

### M6.4 日報與反思核心實體 `[MVP]`

**Purpose**:daily_reflections 表,含 AI 草稿 + 使用者必填欄位 + 審核旗標。

**Schema**:

- `daily_reflections`:
  - `ai_description` TEXT (客觀描述)
  - `ai_analysis` TEXT (初步分析)
  - `user_feeling` TEXT **NOT NULL** (主觀感受)
  - `user_action_plan` TEXT **NOT NULL** (未來行動)
  - `is_draft` BOOLEAN (預設 True)
  - `is_reviewed` BOOLEAN (布林旗標)

**Deps**:M6.2
**Criteria**:NOT NULL 約束確實阻擋未填寫之 XP 發放。
**Research**:`[R08: IKEA 效應 §六.1]` (NOT NULL 是微摩擦力的 DB 層守門員)
**Risks**:RISK-01 (XP 提前發放)

---

### M6.5 遊戲化交易引擎 (基礎) `[MVP]`

**Purpose**:ACID 抽卡守門員,防 Race Condition。

**Schema**:

- `items_dictionary` (id, name, rarity, image_url, category)
- `user_collections` (user_id, item_id, acquired_at)
- Row-level Locks 包裝「扣除 XP → 隨機權重 → 寫入」

**Deps**:M6.2
**Criteria**:1000 並發抽卡請求下,無重複徽章發放。
**Research**:無 (ACID 工程)
**Risks**:無

---

### M6.6 社群實體與損失規避擴充 `[進階]`

**Purpose**:社群實體、成員關係、貼文、驗證、質押、週期挑戰的資料表。

**Schema**:

- `communities` (id, name, type, theme, origin, member_cap[2~8], created_by, created_at)
- `community_members` (community_id, user_id, role[admin\|member], joined_at)
- `social_posts` (id, community_id, user_id, kind, content, revealed_metrics, visibility, likes_count, created_at)
- `validations` (id, post_id, validator_id, evidence_url?, validated_at)
- `stakes` (id, user_id, community_id, task_id, xp_amount, deadline, status, hold_txn_id, created_at)
- `challenges` (id, community_id, title, description, period, source[ai_reviewed\|member_rotation\|admin], status, is_draft, created_by, starts_at, ends_at)

**Deps**:M6.2, M6.5
**Research**:無 (資料層,邏輯研究引用見 M4.13)
**Risks**:RISK-12 (社群貼文側通道)、RISK-18 (AI 挑戰生成器側通道)
**SPEC**:`docs/modules/M3_7_community_ui_SPEC.md` v2.0 §7.3

---

## 🎨 M7 資源與素材生成管線 (Asset Generation)

### M7.1 動態生圖系統整合 `[進階]`

**Purpose**:多來源生圖 API 整合,MVP 先用靜態素材庫。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M7.1.1 | 多來源生圖 API 抽象層:統一介接 Pollinations.ai / NanoBanana / Midjourney |
| M7.1.2 | 動態 Prompt 轉換器:依任務 Context 即時生成隱藏成就徽章/立體背景圖,雲端快取 |

**Deps**:M0.3, M3.5
**Research**:無 (工具整合)
**Risks**:無

---

## 快速統計

| 層級 | MVP 模組數 | 進階模組數 | 子模組總數 |
| ---- | ---------- | ---------- | ---------- |
| M0 基礎 | 4 | 0 | 7 |
| M1 感知 | 4 | 2 | 14 |
| M2 邊緣 | 3 | 3 | 13 |
| M3 UI | 6 | 7 | 38 |
| M4 邏輯 | 6 | 6 | 31 |
| M5 冰山 | 0 | 6 | 0 |
| M6 資料庫 | 5 | 1 | 0 |
| M7 素材 | 0 | 1 | 2 |
| **合計** | **28** | **26** | **105** |

> 2026-10-19 更新 (MVP_CLOSURE_REPORT W5):依本檔各 `### Mx.y` 標題標籤重新計數,與 `06_implementation_phases.md` 一致 —— M4.7 移出 MVP (MVP 29 → 28,M4 進階含 M4.7);M3 進階含新增的 M3.12 / M3.13;M5 依重新設計為 M5.1–M5.6。「子模組總數」欄未重算 (M3 / M5 今日新增內容待使用者審閱後再統計)。

## 如何使用此文件

```bash
# 找特定模組的完整描述
grep -A 50 "^### M4.2 " docs/04_module_registry.md

# 找所有觸及 RISK-03 的模組
grep "RISK-03" docs/04_module_registry.md

# 找所有引用 R08 的模組
grep "R08" docs/04_module_registry.md

# 找所有 MVP 模組
grep -E "### M.+ \`\[MVP\]\`" docs/04_module_registry.md

# 找某模組的所有子模組
grep -A 30 "^### M3.2 " docs/04_module_registry.md | grep "^| M3.2"
```
