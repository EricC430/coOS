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
| M1.1.3 | 焦點視窗活躍時間記錄器:背景持續記錄頁面焦點變化 (如閱讀技術文件 30 分鐘) |
| M1.1.4 | 隱私硬體禁用約束:系統層強制屏除攝影機/麥克風/定位等實體追蹤 |

**Deps**:M0.2, M0.4, M6.1
**Criteria**:30 分鐘活躍時段正確分桶記錄;任何 PII 不會原文落盤。
**Research**:`[R02: 計算心理語言學 §1]` `[R06: 數位表型 §2.1]`
**Risks**:無

---

### M1.2 斷點偵測引擎 (Defer-to-Breakpoint Engine) `[MVP]`

**Purpose**:精準偵測使用者的「任務斷點」,在低認知負荷時才推送通知,防範破壞性中斷。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M1.2.1 | 多模態斷點偵測:游標停頓、App Switching、語音停頓、IDE 焦點離開 |
| M1.2.2 | 深度工作防擾鎖定器:高認知負荷時強制攔截系統音效與通知 |
| M1.2.3 | 斷點事件派發器:向 Tauri 廣播 `BREAKPOINT_DETECTED` 事件 (極低視覺干擾) |

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
| M1.3.2 | 瀏覽器擴充 (Chrome MV3):頁面焦點變化、閱讀停留時間 |

**Deps**:M1.1
**Criteria**:正確上報任一檔案 commit-to-commit 的編輯量。
**Research**:`[R02: 源碼變更熵 §1.1]` `[R02: 時間動力學 §1.2]`
**Risks**:無

---

### M1.4 外部自動化工作流接收器 (FastAPI) `[MVP]`

**Purpose**:接收 GitHub Webhook 等外部事件並轉為結構化日誌。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M1.4.1 | OAuth 2.0 授權流程:連接 GitHub 取得 Access Token |
| M1.4.2 | Webhook Endpoints:解析 GitHub Commit Push Payload |

**Deps**:M0.3
**Criteria**:commit 後 5 秒內出現在 `raw_tracking_logs`。
**Research**:`[R06: 版本控制紀錄 §2.1]`
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

**Deps**:M4.13, M6.6
**MVP 策略**:以 stub 卡片佔位即可。
**Research**:`[R09: 社會情懷 §4.1]`
**Risks**:RISK-12 (社群貼文側通道洩漏)

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

**Deps**:M5.1
**Research**:`[R04: 拓樸演化 §GraphRAG]`
**Risks**:無

---

### M3.11 遊戲化抽卡組件 (Gamification Gacha UI) `[進階]`

**Purpose**:變動比例增強的盲盒抽卡與隱藏成就。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M3.11.1 | 變動比例盲盒抽卡介面 (XP 抽背景/徽章) |
| M3.11.2 | 程序化任務「🎲 抽挑戰」按鈕 |
| M3.11.3 | 隱藏成就**絕對無 UI 狀態**控制器 (解鎖前完全隱藏,防 FOMO) |
| M3.11.4 | 隱藏成就無預警驚喜彈窗 |

**Deps**:M3.5, M4.11, M4.12, M6.5
**Research**:無 (產品設計)
**Risks**:RISK-04 (即時慶祝), RISK-09 (焦慮 + Gacha 上癮)

---

## 🧠 M4 多智能體邏輯與業務層 (FastAPI + LangGraph)

### M4.1 Agent 路由與協作管線 (LangGraph 結構層) `[MVP]`

**Purpose**:LangGraph 純結構層,提供路由、容器與安全規劃,不含 Persona 內容。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.1.1 | Router Agent:對話精準路由至特定學科/心理專家 |
| M4.1.2 | Persona Agent 容器:純結構接點,Prompt 內容由 M4.2 注入 |
| M4.1.3 | Observer / Drafting Agent 容器:背景非同步協調,具體萃取邏輯在 M4.6 |
| M4.1.4 | DRIFT 安全規劃器:防範外部訊號挾持 Agent 系統提示詞 |

**Deps**:M2.2, M2.3
**Criteria**:路由準確率 ≥85% 於人工標註測試集。
**Research**:`[R09: MAS §6.1]` `[R02: DRIFT §架構安全性]` `[R03: LangGraph §1]`
**Risks**:無

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
**Criteria**:每日 03:00 自動產出前一日完整草稿。
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

### M4.7 Markdown 同步至 Obsidian Agent `[MVP]`

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
| M4.8.4 | 心理指標降維轉譯:冰冷日誌 → 「焦慮」「逃避」等心理標籤 |
| M4.8.5 | REMT YAML 上下文工程:DRIFT 保護下將推論結果注入 Persona 決策樹 |

**Deps**:M2.2, M4.1, M4.2, M5.1
**Research**:`[R02: 非監督式管線 §全章]` `[R01: POMDP+BKT §動態追蹤]` `[R06: 應對姿態 §4.2]`
**Risks**:RISK-03 (焦慮鏡像), RISK-06 (跨角色洩漏), RISK-09 (Gacha 推播門禁)

---

### M4.9 ARPM 異質時序記憶治理 `[進階]`

**Purpose**:雙時序重排序 + 證據稽核,防漫長對話中的「人設崩塌」。

**子模組**:無 (核心為排序演算法)

**Deps**:M4.1, M5.3
**Research**:`[R03: ARPM §2]`
**Risks**:RISK-02 (與 Echo Mode 的衝突)

---

### M4.10 NSVIF 神經符號驗證 + D-ALP `[進階]`

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

### M4.12 隱藏成就驗證引擎 `[進階]`

**Purpose**:背景對話驗證使用者是否主動探索高階概念,觸發無預警解鎖。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.12.1 | 主動探索特徵捕捉網:背景對話驗證,監聽是否主動探索高階概念 |
| M4.12.2 | 無預警 WebSocket 解鎖廣播 |

**Deps**:M4.6, M3.11
**Research**:`[R01: 動態邊界]`
**Risks**:無

---

### M4.13 損失規避與同儕驗證引擎 `[進階]`

**Purpose**:XP 質押對賭 + 社會情懷強制制約 + 跨社群權限隔離。

**子模組**:

| 編號 | 職責 |
| ---- | ---- |
| M4.13.1 | 損失規避 XP 質押扣管邏輯 |
| M4.13.2 | 社會情懷強制制約器:「沒有退路」的同儕壓力 |
| M4.13.3 | 跨社群權限隔離中介軟體 (讀書會 / 陌生人 / 朋友圈) |

**Deps**:M3.7, M6.5, M6.6
**Research**:`[R01: α-DPO Dropout §Dropout 危機]` `[R09: 病態使用 §3.3]`
**Risks**:RISK-07 (ZPD + 質押複合挫敗)

---

## 🕸️ M5 深層認知圖譜層 (GraphRAG Pipeline) `[進階]`

> 全章皆屬 [進階],GraphRAG 屬對話深度增強,非 MVP 必要。

### M5.1 薩提爾圖譜寫入器 (Cypher Generator) `[進階]`

**Purpose**:Gemini 將日誌轉化為 Behavior / Feeling / Yearning 節點寫入 Neo4j。

**子模組**:無

**Deps**:M4.6, M6
**Criteria**:節點與邊 schema 通過 Cypher validator;能還原原始日誌語意。
**Research**:`[R04: 冰山本體論化 §冰山七大節點]` `[R06: 應對姿態 §4.1]`
**Risks**:RISK-05 (意圖向量精度)

---

### M5.2 NSVIF 幻覺防禦引擎 `[進階]`

**Purpose**:反溯因驗證器,對照 `raw_tracking_logs` 進行因果檢驗,丟棄不合邏輯邊緣。

**子模組**:無

**Deps**:M5.1, M0.4
**Research**:`[R04: 反溯因驗證 §神經符號約束]`
**Risks**:RISK-05 (必須走本地 raw_log 路徑)

---

### M5.3 ARPM 異質時序記憶治理 (Graph 層) `[進階]`

**Purpose**:雙時態檢索器,BM25 + 時序權重,分離靜態人設與動態經驗。

**子模組**:無

**Deps**:M5.1, M4.9
**Research**:`[R03: ARPM §2]` `[R04: 霍克斯過程 §時序激發]`
**Risks**:無

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

**Purpose**:社群貼文、驗證、質押的資料表。

**Schema**:

- `social_posts` (id, user_id, content, likes_count, created_at)
- `validations` (id, post_id, validator_id, validated_at)
- `stakes` (id, user_id, xp_amount, deadline, status)

**Deps**:M6.2, M6.5
**Research**:無
**Risks**:RISK-12 (社群貼文側通道)

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
| M3 UI | 6 | 5 | 38 |
| M4 邏輯 | 7 | 6 | 30 |
| M5 圖譜 | 0 | 3 | 0 |
| M6 資料庫 | 5 | 1 | 0 |
| M7 素材 | 0 | 1 | 2 |
| **合計** | **29** | **21** | **104** |

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
