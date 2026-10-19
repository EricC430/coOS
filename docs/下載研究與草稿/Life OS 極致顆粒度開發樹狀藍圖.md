# **Life OS 極致顆粒度開發樹狀藍圖 (v3.0)**

## **📦 \[M0\] 系統基礎與通訊核心 (Infrastructure & IPC)**

* **\[M0.1\] Monorepo 專案結構初始化**：配置 Tauri (Rust)、前端 (React/Vue/Vite) 與後端 (Python/FastAPI) 工作區。  
* **\[M0.2\] Tauri IPC 與 Sidecar 行程管理**  
  * `M0.2.1`：實作 Rust `Command` 攔截器，管理 FastAPI 背景行程的啟動/關閉，處理 Port 衝突。  
  * `M0.2.2`：建立 Tauri 與前端的 WebSocket/SSE 本地通道，實現 0 毫秒延遲對話推播。  
* **\[M0.3\] 環境變數與遷移引擎**：`.env` 統一管理 Gemini 3.5 Pro, Leonardo.ai 等 API Keys；配置 Alembic/Prisma 進行資料庫遷移。

## **👁️ \[M1\] 前端感知與輸入層 (Ambient Sensors)**

* **\[M1.1\] OS 級別遙測守護行程 (Rust Native)**  
  * `M1.1.1`：實作 UIAutomation API 橋接，抓取 Word/Notion 標題與純文字。  
  * `M1.1.2`：實作全域鍵鼠防抖監聽器 (計算 WPM，去識別化)。  
  * **`M1.1.3` 延遲至斷點打斷管理監聽器 (Defer-to-Breakpoint Idle Monitor)**  
    * `M1.1.3.1`：實作核心 OS 視窗切換（App Switching）事件攔截器，精確捕捉使用者的軟體切換行為。  
    * `M1.1.3.2`：實作滑鼠與鍵盤靜止狀態計時器，偵測在特定 IDE 或瀏覽器視窗中的焦點停留時間與操作中斷點。  
    * `M1.1.3.3`：實作任務斷點決策判斷器，當判定使用者處於非深度工作心流的自然斷點時，才向 Tauri 發送極低視覺干擾的草稿提示，防範紀錄疲勞。  
* **\[M1.2\] IDE/Web 擴充掛載**  
  * `M1.2.1`：VS Code AST 攔截器，計算「源碼變更熵」與停留時間，透過 Local Socket 傳回 Tauri。  
* **\[M1.3\] 外部自動化工作流接收器 (FastAPI)**  
  * `M1.3.1`：實作 OAuth 2.0 授權流程，連接 GitHub 取得 Access Token。  
  * `M1.3.2`：實作 Webhook Endpoints，解析 GitHub Commit Push Payload。  
* **\[M1.4\] 經驗取樣微 nudges 觸發器 (Micro-Nudges Engine) `[進階]`**  
  * **`M1.4.1` 全域微型問卷推播組件 (Ambient Push Notification Scheduler)**  
    * `M1.4.1.1`：配置 Web Push / Tauri 全域背景通知排程器，定時觸發超低干擾的微互動介面。  
    * `M1.4.1.2`：實作極短單鍵問卷 UI（範例：*「今天朝『微積分』目標邁進了嗎？\[有/沒有\]」*），將繁重紀錄拆解為微型點擊。  
  * **`M1.4.2` 異步輕量狀態寫入端點 (Micro-Nudge Ingestion API)**  
    * `M1.4.2.1`：實作單鍵響應資料接收端點，允許使用者不開啟主程式直接傳入 `target_alignment_status`。  
    * `M1.4.2.2`：實作微互動數據本地暫存與異步同步邏輯，作為深夜反思草稿的因果校準依據。  
* **\[M1.5\] 情境感知與環境捕捉擴充套件 (Ambient Tracking Extensions) `[進階]`**  
  * **`M1.5.1` 焦點追蹤記錄器**：實作無侵入式 IDE 與瀏覽器擴充套件，於背景持續記錄視窗活躍時間與頁面焦點變化（如閱讀特定技術文件 30 分鐘）。  
  * **`M1.5.2` 隱私硬體禁用約束**：系統底層嚴格限制追蹤範圍於軟體互動，現階段徹底屏除實體攝影機或定位的硬體追蹤技術。  
  * **`M1.5.3` 零輸入行為導出器**：將被動收集的活躍數據封裝為標準 API，提供給 AI 幫手主動發起對話、產生重點總結，或作為 Daily Report 的耗時運算來源。  
* **\[M1.6\] 延遲至斷點打斷管理引擎 (Defer-to-Breakpoint Engine) `[MVP]`**  
  * **`M1.6.1` 多模態斷點偵測模型**：實作背景監聽腳本，精準擷取游標停頓、視窗切換（App Switching）或語音停頓的時機作為使用者的「任務斷點」。  
  * **`M1.6.2` 深度工作防擾鎖定器**：當系統判定使用者處於高認知負荷階段時，強制攔截系統音效與通知，絕對不在深度工作時立即推播反思草稿或洞察。

## **🛡️ \[M2\] 邊緣運算與安全防禦層 (Edge Security & Inference)**

* **\[M2.1\] 事件防抖與排隊引擎 (Rust/Redis)**：實作 30\~60 秒時間窗 (Time Window) 事件聚合器。  
* **\[M2.2\] Gemma 邊緣推論管線 (ai.local)**  
  * `M2.2.1`：載入 4-bit 量化 Gemma 4 E4B 模型。  
  * `M2.2.2`：實作 POST 框架提示詞，將明文壓縮為 `Intent Vectors` (JSON 格式)。  
    * `M2.2.2.1` **意圖向量轉譯器**：將擷取到之敏感原始程式碼與日誌，進行語意壓縮並轉換為連續的意圖向量 (Intent Vectors)。  
    * `M2.2.2.2` **隱私微調與知識蒸餾模組**：導入知識蒸餾與差分隱私微調技術，徹底解決模型權重耦合與隱私數據上雲的風險問題。  
    * `M2.2.2.3` **公開資料映射傳輸器**：透過公開資料映射機制，將去識別化後的意圖向量安全傳輸給雲端大模型進行後續處理。  
  * `M2.2.3` **超大上下文視窗管理**：確保在完全不依賴本地伺服器的情況下，穩定執行高達 128K 上下文的邊緣運算。  
  * `M2.2.4` **即時事件推論管線**：負責即時消化並推論前端傳入之龐大螢幕焦點變化與微互動事件數據。  
* **\[M2.3\] Eguard 密碼學過濾器**  
  * `M2.3.1`：Regex PII 遮蔽模組 (自動抹除 IP, Email, Token)。  
  * `M2.3.2`：DRIFT 隔離框架：攔截並驗證從外部 Git Commit 傳入的字串，防範 Prompt Injection。  
  * `M2.3.3` **互資訊優化防禦器**：導入基於「文字互資訊優化」的雙層防禦機制，以抵禦 Zero2Text 等先進嵌入逆向攻擊。  
  * `M2.3.4` **敏感句法剝離引擎**：強制掃描並剝離意圖向量中的具體變數名稱與敏感業務句法。  
  * `M2.3.5` **抽象語意放行器**：經過攔截與剝離後，僅保留供大模型推理所需的抽象語意鑑別度傳送上雲。  
* **\[M2.4\] PRISM 動態語意協作路由 (Dynamic Semantic Routing) `[進階]`**  
  * `M2.4.1` **指令敏感度評估器**：實作動態路由中介軟體，即時評估每一條使用者指令與系統數據的隱私敏感度。  
  * `M2.4.2` **雲端語意草圖生成器**：將非敏感部分交由雲端 GPT-5.5 或 Gemini 3.5 運算，僅令其負責生成高階的「語意草圖 (Semantic Sketch)」。  
  * `M2.4.3` **邊緣 L2 主動渲染填補器**：接收雲端草圖後，交由邊緣端側模型利用本地的原始上下文進行細節渲染與填補，達成 L2 級別的狀態型主動協作。  
* **\[M2.5\] WebAssembly 3.0 與 WebGPU 推論引擎部署 `[進階(選擇Local LLM部署在PC)]`**  
  * `M2.5.1` **CogentLM 引擎掛載**：整合 CogentLM 等先進瀏覽器推理引擎，徹底解放 IDE 與瀏覽器的底層硬體算力。  
  * `M2.5.2` **超低延遲優化器**：透過底層優化，將端側首字延遲嚴格壓制於 35.5ms 以內以達成極致流暢的人機互動。

## **🖥️ \[M3\] 前端 UI/UX 狀態與渲染層 (React/Vue Components)**

* **\[M3.1\] 全域狀態與佈局 (Zustand/Pinia)**  
  * `M3.1.1`：管理 `CurrentRole`, `XP_Balance`, `Active_Expert` 等全域變數。  
  * `M3.1.2`：實作發布-訂閱模式 (Pub/Sub)，當 Role 切換時觸發全局 UI 重繪。  
* **\[M3.2\] 角色儀表板模組 (Role-based Dashboard) `[MVP]`**  
  * **`M3.2.1` 底部焦點橫向輪盤組件 (Visual Focus Carousel Dock)**  
    * `M3.2.1.1`：實作橫向 Carousel 容器，提供物理慣性滑動手勢與滑動對齊（Snap to Center）互動邏輯。  
    * `M3.2.1.2`：建置選取狀態放大器（Active State Scale），自動將處於中央正核心的角色 Icon 按比例放大呈現。  
    * `M3.2.1.3`：實作全域狀態發布器，當 Carousel 停頓完成時向系統派發全域 `ROLE_SWITCHED` 事件。  
  * **`M3.2.2` 儀式感背景過渡引擎 (Smooth Transition Context Background)**  
    * `M3.2.2.1`：監聽 `ROLE_SWITCHED` 事件，根據角色設定檔即時變更系統主題色調（Theme Color Palette）。  
    * `M3.2.2.2`：實作色溫平滑過渡動畫（CSS/Framer Motion WebGL），提供背景色溫的線性漸變以營造狀態轉換的物理儀式感。  
    * `M3.2.2.3`：建立介面光效遮罩（Ambient Glow Filter），在色溫切換時同步降低視覺對比度以減少大腦上下文切換的認知耗損。  
  * **`M3.2.3` 短期記憶喚醒聚合區 (Context Header Aggregator)**  
    * `M3.2.3.1`：於畫面頂部配置 Bento Grid 情境標籤列，隔離封裝專案（Project）、承諾（Promises）與目標（Goal）三大顯示槽位。  
    * `M3.2.3.2`：配置角色資料預快取（Pre-fetching Cache）機制，確保切換角色時能在 3 秒內無縫加載新情境資料。  
    * `M3.2.3.3`：實作 Skeleton UI 骨架屏組件，防止資料異步加載時的版面跳動，在 3 秒內瞬間喚醒使用者的短期記憶。  
  * **`M3.2.4` 角色活躍度紀錄熱圖 (Consistency Consistency Heatmap)**  
    * `M3.2.4.1`：於儀表板正中央置入網格矩陣組件，外觀與互動行為嚴格比照 GitHub Contributions 網格熱圖。  
    * `M3.2.4.2`：實作網格顏色深淺映射演算法（Color Density Mapper），將該特定角色下的每日活躍度量化為四種色彩階調。  
    * `M3.2.4.3`：實作熱圖網格提示窗（Tooltip Hover），懸停時顯示該角色當日具體的行為推進計數以維持不打破鏈條的心理韌性。  
* **\[M3.3\] 日報與反思模組 (Daily Report & Reflection) `[MVP]`**  
  * **`M3.3.1` 雙維度時間軸與角色分組組件 (Dual-Dimension Calendar Feed)**  
    * **`M3.3.1.1`：使用 CSS `border-left` 繪製左側垂直時間軸導覽線，滑動可跳轉切換查看不同日期的歷史紀錄。**  
    * **`M3.3.1.2`：實作右側卡片式任務清單（Task Cards Grid），卡片內容必須嚴格依據生活身分「角色」進行視覺群組分類（Contextual Grouping）以幫助大腦降噪。**  
  * **`M3.3.2` 狀態與寬容耗時卡片組件 (Tolerance Task Card)**  
    * **`M3.3.2.1`：實作卡片狀態膠囊按鈕，動態標示並渲染任務狀態為「進行中」或「已完成」。**  
    * **`M3.3.2.2`：實作多管道耗時數據動態載入器，卡片「花了～時間」優先讀取並預填 AI 在對話中自然套問得出的計時欄位。**  
    * **`M3.3.2.3`：實作底層 Workflow 監聽數據補全器，若 AI 未套問出耗時，自動加載被動監聽（如 IDE 活躍時間）自動推算的預設時間，免除手動填寫的麻煩。**  
  * **`M3.3.3` 認知摩擦力草稿核准彈窗 (Draft & Approve Metacognition Modal)**  
    * **`M3.3.3.1`：實作獨立的草稿與核准（Draft & Approve）覆蓋層，系統絕不在背景全自動直接寫入日報，以保留使用者的心理所有權並避免引發「適應悖論」。**  
    * **`M3.3.3.2`：建置吉布斯反思循環（Gibbs Reflective Cycle）結構化區域，由 AI 自動填補並展示「客觀描述」與「初步分析」的文字內容。**  
    * **`M3.3.3.3`：實作系統二（System 2）認知摩擦力強制留白欄位，溫和引導並強制使用者微調填補「主觀感受」與「未來行動計畫」。**  
    * **`M3.3.3.4`：實作反思表單嚴格驗證器（Scaffold Form Validator），強制使用者必須回答一句 *「學到了什麼？」* 或 *「是否對齊初始目標（reviewed? click）」* 否則不發放 XP，將打卡深化為認知吸收，觸發 IKEA 效應。**  
* **\[M3.4\] 沉浸式多智能體幫手模組 (Multi-Agent AI Helper) `[MVP]`**  
  * **`M3.4.1` 雙軌側邊欄與視圖組件 (Dual-Track Sidebar & Avatar List)**  
    * **`M3.4.1.1`：實作側邊欄首位固定為無人設、純客觀且專注於高效查閱除錯的「工具型 AI」介面。**  
    * **`M3.4.1.2`：實作側邊欄其餘欄位為「擬真人設專家」列表，以提供沉浸式陪伴。**  
    * **`M3.4.1.3`：實作側邊欄列表右側統一並列顯示「使用者虛擬頭像圖示」、「專家職稱」與「專家名稱」的多列排版。**  
  * **`M3.4.2` 動態專家配對控制器 (Dynamic Matching & Re-matching System)**  
    * **`M3.4.2.1`：實作「配對」按鈕與狀態輸入彈窗，禁止使用者直接從清單挑選專家，改由系統依據輸入狀態分派。**  
    * **`M3.4.2.2`：實作「新增配對」功能，支援透過輸入當下狀態來擴充並獲取合適的新專家。**  
    * **`M3.4.2.3`：實作「重新配對」功能，當互動感到不適配時可檢討上個專家人設配置，並為同個職位指派風格不同的新專家。**  
  * **`M3.4.3` 強化的上下文多模態輸入區 (Enhanced Context Input Bar)**  
    * **`M3.4.3.1`：實作對話框左側 `[+]` 按鈕，支援快速上傳單一 PDF 或圖片文件以動態加入 Context。**  
    * **`M3.4.3.2`：實作對話框左側 `[🔗]` 按鈕，支援貼上特定網址作為對話脈絡。**  
    * **`M3.4.3.3`：實作麥克風圖示按鈕，支援隨性傾訴的語音意識流輸入並轉錄為文字送出。**  
  * **`M3.4.4` 隱形自動化與進展效應 UI (Invisible Automation & Endowed Progress)**  
    * **`M3.4.4.1`：監聽後端系統事件，於對話流下方自動渲染隱形提示（例如：「*Project 偵測為『初始目標設定』創立*」）。**  
    * **`M3.4.4.2`：當背景創建專案時，視覺上強制賦予非零的初始進度條，利用賦予進展效應（Endowed Progress Effect）提昇使用者的完成動機。**  
* **\[M3.5\] 收藏與抽卡經濟模組 (Collection)**  
  * `M3.5.1 Master-Detail 佈局`：左側 CSS Grid 徽章槽位 (Slots)，右側動態渲染解鎖條件與描述。  
  * `M3.5.2 Gacha 觸發器`：實作抽卡按鈕，綁定 XP 扣除 API，整合 Framer Motion/Lottie 實作開箱與粒子特效。
* **\[M3.6\] 社群與社會情懷模組 (Community UI) `[進階]`**
  * **`M3.6.1` Bento Grid 儀表板佈局組件**：實作 Bento Grid 區塊化網格佈局，將社群共識、動態牆、挑戰與驗證區塊模組化呈現。  
  * **`M3.6.2` 社交隔離子社群切換器**：於右側實作一條垂直線串聯多個圓形按鈕的垂直輪盤卷軸（Carousel）導覽列。  
  * **`M3.6.3` 社交壓力切換控制器**：支援點擊切換如完全陌生人、朋友圈等不同社交壓力屬性的子社群，精準控制資訊邊界。  
  * **`M3.6.4` 社群共識靜態展示區**：實作包含 Goal、Vision、Codex 等標籤的靜態區塊，展示當前社群的核心精神與行為規範以確保共同的認知底線。  
  * **`M3.6.5` 成就與貼文動態牆**：實作內部為條列式的動態卡片清單，即時展示同儕互相驗證的成就與鼓勵貼文。  
  * **`M3.6.6` 定期挑戰展板**：配置一個帶有 Weekly/Monthly community Challenges 標題的大型空白視圖區塊，用於展示近期的共同任務。  
  * **`M3.6.7` 承諾與驗證閉環控制區**：實作視覺化的狀態轉移拖曳或點擊介面，強制任務需經過 Tasks \-\> Commitments \-\> Validation 的嚴格流程。  
  * **`M3.6.8` XP 質押對賭介面**：於 Commitments 階段引入 XP 質押輸入框介面，讓使用者設定對賭協議的抵押數量。  
* **\[M3.7\] 週期性回顧與敘事彈窗 (Wrapped Insights Card) `[進階]`**  
  * **`M3.7.1` 數據故事化視覺生成組件 (Wrapped Insight Animator)**  
    * `M3.7.1.1`：實作每週／每月自動化數據結算腳本，將全域活躍數據轉化為結構化的故事性敘事卡片。  
    * `M3.7.1.2`：實作 Wrapped 彈出視窗組件，於週期首次登入時動態播放多巴胺視覺特效（例如 *「這週你的動力指數提升了 20%」* ），主動推送知覺成就感。  
* **\[M3.8\] 脈絡內自動化設定彈窗 (In-Context Workflow Modal) `[MVP]`**  
  * **`M3.8.1` 對話框快捷喚出按鈕**：於對話輸入框旁實作 `workflow` 按鈕，點擊後隨時喚出不脫離當下聊天脈絡的懸浮設定面板。  
  * **`M3.8.2` 外部資料源綁定介面**：實作無縫授權與綁定 UI，支援連接 GitHub Repo、本機 Obsidian 庫或瀏覽器日誌追蹤端點。  
  * **`M3.8.3` 自動化觸發條件設定表單**：提供下拉選單與輸入框，允許使用者基於事件（如 Commit）、時間週期或特定關鍵字來設定工作流的啟動條件。  
* **\[M3.9\] 防疲勞非同步通知儀表板 (Persistent Notification Dashboard) `[進階]`**  
  * **`M3.9.1` 靜默歸檔通知中心**：建立一個持續性的非同步通知面板，將所有低急迫性的系統草稿靜默收納於此，徹底防範警報疲勞（Alert Fatigue）。  
  * **`M3.9.2` 延遲恢復低干擾提示**：僅在接收到 `M1.6` 的任務斷點訊號時，才以極低視覺干擾的溫和動畫浮現核准提示，避免引發恢復延遲（Resumption Lag）。  
  * **`M3.9.3` 每日批次審閱檢視表**：提供清單式 UI，讓使用者能在每日結束前打開儀表板，一次性進行草稿的批次審閱與核准。  
* **\[M3.10\] 視覺化成就展示與知識拓樸模組 (Collection & Knowledge UI) `[MVP]`**  
  * `M3.10.1` **視覺化成就展示櫃組件**：實作具備網格佈局的收藏庫介面，負責集中展示已解鎖的系統背景與專屬徽章。  
  * `M3.10.2` **技能樹與知識網狀圖渲染器**：實作可動態點亮的節點拓樸圖組件，將個人的成長目標具象化以滿足完形心理學偏好。  
* **\[M3.11\] 遊戲化成癮引擎與盲盒抽卡組件 (Gamification Gacha UI) `[進階]`**  
  * `M3.11.1` **變動比例盲盒抽卡介面**：實作消耗 XP 抽取背景與徽章的互動 UI，透過變動比例增強機制最大化使用者的多巴胺分泌。  
  * `M3.11.2` **程序化任務「🎲 抽挑戰」按鈕**：於 Collection 介面實作專屬抽取按鈕，綁定未知探索盲盒的資料請求與翻牌特效。  
  * `M3.11.3` **絕對無 UI 隱藏成就狀態控制器**：實作隱藏成就進度條的完全隱藏邏輯，確保在解鎖前處於絕對的「無 UI」狀態以防範 FOMO 焦慮。  
  * `M3.11.4` **動態隱藏成就驚喜彈窗**：實作無預警的華麗解鎖彈出畫面，提供意外驚喜感並強化主動性與好奇心的正向回饋。

## **🧠 \[M4\] 多智能體邏輯與業務層 (FastAPI \+ LangGraph)**

* **\[M4.1\] Agent 協作與記憶狀態機 (LangGraph & ARPM) `[MVP/進階核心]`**   
  * **`M4.1.1` 路由與協作管線 (Routing & Collaboration)**  
    * `M4.1.1.1`：實作 Router Agent，負責精準路由對話發言至特定的學科或心理專家。  
    * `M4.1.1.2`：實作 Persona Agents，使其嚴格受控於 Echo Mode 中介軟體以進行動態的心理狀態切換。  
      * `M4.1.1.2.1 系統提示詞工程`：注入固定人設與副語言線索 (如「嗯...」、「讓我想想」)。  
      * `M4.1.1.2.2 阻抗消解控制器`：偵測防衛語氣，動態調降 Agency 切換至共情模式。  
    * `M4.1.1.3`：部署 Observer/Drafting Agent，負責在背景非同步提煉對話意圖、萃取任務池並生成反思草稿。  
  * **`M4.1.2` 異質時序記憶治理 (ARPM Integration)**  
    * `M4.1.2.1`：將 Persona Agents 綁定 ARPM 框架，進行雙時序重排序與證據稽核，徹底防止漫長對話中的「人設崩塌」。  
  * **`M4.1.3` 神經符號驗證與反溯因推理 (NSVIF & D-ALP)**  
    * `M4.1.3.1`：實作論述加權溯因邏輯 (D-ALP)，確保每一條心理剖繪皆具備嚴格的客觀事實支撐與邏輯健全性，防範大模型產生「心理幻覺」。  
  * **`M4.1.4` 動態規則隔離框架 (DRIFT Security)**  
    * `M4.1.4.1`：實作安全規劃器與注入隔離器，確保從代碼或日誌萃取的行為特徵絕對無法挾持 Agent 的系統提示詞（防範 Prompt Injection）。  
* **\[M4.2\] 非監督式隱性狀態推論管線 (Implicit State Inference) `[進階核心]`**  
  * **`M4.2.1` 特徵矩陣與情感萃取器 (Feature & Emotion Extraction)**  
    * **`M4.2.1.1`：部署 DistilBERT 模型提取語言情感，並結合演算法計算源碼變更熵與時間延遲的特徵矩陣。**  
  * **`M4.2.2` 隱性狀態解碼引擎 (HMM & Viterbi Decoder)**  
    * **`M4.2.2.1`：結合孤立森林與隱馬爾可夫模型 (HMM/HSMM)，利用 Viterbi 解碼演算法，從特徵中即時推斷使用者處於常態、焦慮或逃避狀態。**  
  * **`M4.2.3` 認知分析與 ZPD 動態縮放 (POMDP & BKT)**  
    * **`M4.2.3.1`：引入 POMDP 與多模態 BKT 演算法賦予系統決策能力，分析任務耗時與挫折語氣，即時透視認知負荷並動態縮放 ZPD 邊界。**  
  * **`M4.2.4` 記憶拓樸即時注入器 (REMT Context Engineering)**  
    * **`M4.2.4.1`：透過 REMT 與 YAML 上下文工程，在 DRIFT 框架保護下，將推論結果安全且動態地注入 Persona Agent 的決策樹中。**  
* **\[M4.3\] 背景自動化 Agents**  
  * `M4.3.1 Observer / Extractor Agent`：平行監聽對話，自動萃取「意圖 (Intention)」與「專案 (Project)」，呼叫 Function Calling 寫入資料庫並觸發前端 System Event。  
  * `M4.3.2 總結 Agent`：Session 結束後自動歸納重點，同步產出 Markdown 透過腳本寫入 Obsidian。  
* **\[M4.4\] 程序化生成與排程 (PCG & Cron)**  
  * `M4.4.1 ZONE 貝氏計算與 BKT`：分析認知負荷，動態縮放 ZPD 邊界生成盲盒任務池。  
* **\[M4.5\] 全域情境與隔離狀態機 (Context Isolation State Machine) `[MVP]`**  
  * **`M4.5.1` 資料流沙盒路由守護 (Data Flow Isolation Middleware)**  
    * `M4.5.1.1`：實作後端中介軟體，攔截非特定角色的 API 請求並自動附加當前切換的 `Role_ID` 請求頭。  
    * `M4.5.1.2`：實作資料庫連線動態變更器（Dynamic Connection Switcher），強制將後續的寫入與查詢導向特定角色隔離的資料沙盒。  
  * **`M4.5.2` AI 領域專家提示詞動態切換引擎 (Dynamic Persona Injector)**  
    * `M4.5.2.1`：根據目前的 `Role_ID`，動態更換 LangGraph 大腦中當前啟用之微積分助教、家庭諮商師等專家配置。  
    * `M4.5.2.2`：重置系統全局上下文快取（System Prompt Context Cache），確保 AI 的回應語氣、專業背景隨身分切換完全隔離。  
* **\[M4.6\] 自然套問與反思草稿生成器 (Natural Query & Draft Synthesizer) `[MVP]`**  
  * **`M4.6.1` AI 專門專家對話套問控制器 (Conversational Probe Controller)**  
    * `M4.6.1.1`：在各領域 Persona Agent 的 Prompt 中注入自然套問指令（例如當任務結束時問：*「這份作業大概花了你多久時間？」*）。  
    * `M4.6.1.2`：配置正則與命名實體識別（NER）解析器，自動從使用者的聊天對話回覆中抽取時間跨度，並寫入任務暫存槽。  
  * **`M4.6.2` 異步客觀行為草稿生成器 (Asynchronous Gibbs Draft Engine)**  
    * `M4.6.2.1`：實作深夜後台排程器，自動拉取本地 SQLite 的 `raw_tracking_logs` 行為日誌明文。  
    * `M4.6.2.2`：調用 Gemini API 將客觀數據與代碼提交歷史拼裝為符合吉布斯循環的「客觀描述草稿」，並更新至 `daily_reflections` 表中。  
* **\[M4.7\] 擬真專家與心理學狀態機引擎 (Persona & Psychological State Machine) `[MVP]`**  
  * **`M4.7.1` 擬真社會承諾與同理心制約器 (Social Contract & Guilt Engine)**  
    * **`M4.7.1.1`：於專家 Prompt 中設定連貫的過往經歷、真人語氣與主動分享經驗的特質，將其塑造為真實的「人」。**  
    * **`M4.7.1.2`：透過擬真人設建立情感羈絆，引發使用者「不想辜負對方關心」的適度罪惡感與責任心，藉此大幅降低逃避機率。**  
  * **`M4.7.2` 副語言線索與瑕疵渲染器 (Paralinguistic Cues Injector)**  
    * **`M4.7.2.1`：在 AI 回覆管線中刻意注入填充詞（如「嗯...」、「讓我想想」）與自我修正的語言瑕疵。**  
    * **`M4.7.2.2`：設定演算法弱點暴露機制，使 AI 主動展現自身限制以跨越恐怖谷效應，建立真實的治療同盟。**  
  * **`M4.7.3` Echo Mode 阻抗消解控制器 (Reactance Mitigation Controller)**  
    * **`M4.7.3.1`：實作心理阻抗偵測防禦模組，即時分析對話以判斷使用者是否對權威指導產生防衛心態。**  
    * **`M4.7.3.2`：當偵測到阻抗時觸發狀態機切換，主動調降 AI 專家的能動性（Agency），從權威指導平滑切換至共情傾聽（Resonance）以化解認知防衛。**  
* **\[M4.8\] 背景洞察與 ZPD 盲盒任務池生成器 (Observer & ZPD Generator) `[進階]`**  
  * **`M4.8.1` 動態邊界任務池萃取引擎 (Dynamic ZPD Task Extraction)**  
    * **`M4.8.1.1`：部署 Observer Agent 持續非同步分析使用者的歷史對話紀錄。**  
    * **`M4.8.1.2`：自動捕捉對話中的延伸興趣或挫折痛點，於背景自動生成客製化的隨機挑戰，確保任務落在使用者的「近側發展區（ZPD）」。**  
* **\[M4.9\] 隱性行為模式量化管線 (Implicit Behavior Quantification) `[進階]`**  
  * **`M4.9.1` 行為特徵矩陣萃取器：部署背景分析任務，持續從 GitHub 提交歷史與 IDE 活躍度中萃取出結構化的數位足跡特徵。**  
  * **`M4.9.2` 源碼與時序動力學運算子：實作機器學習演算法，將萃取出的底層數據量化計算為「源碼變更熵 (Source-code Change Entropy)」與「時間動力學 (Temporal Dynamics)」。**  
  * **`M4.9.3` 心理指標降維轉譯器：將計算出的冰冷日誌參數精準轉譯，映射為深層的「焦慮」或「逃避」等心理指標狀態標籤。**  
* **\[M4.10\] 零摩擦被動監聽與自動化獎勵器 (Zero-Friction Automation Engine) `[MVP]`**  
  * **`M4.10.1` 數位足跡自動結算排程：實作後台 XP 自動派發腳本，讓使用者只需正常進行日常任務，系統即會在背後自動將進度轉化為經驗值並更新日報。**  
  * **`M4.10.2` 殭屍草稿自動淘汰機制：實作資料庫清理排程（Cron Job），自動判斷並刪除長期被忽視的無效反思草稿，極大化降低長期維護的倦怠感。**  
* **\[M4.11\] 動態邊界任務池與 ZPD 盲盒管線 (Dynamic ZPD Gacha Pipeline) `[進階]`**  
  * **`M4.11.1` 歷史脈絡興趣分析器：部署 Observer Agent 持續分析歷史對話，精準擷取使用者的「興趣延伸點」與「期待改善點」。**  
  * **`M4.11.2` 多模態 BKT 認知負荷推斷器：實作多模態貝氏知識追蹤（BKT）演算法，即時透視並精準評估使用者的當下認知負荷與挫折耐受度。**  
  * **`M4.11.3` ZONE 貝氏任務池生成器：透過 ZONE 貝氏計算框架動態生成落在「近側發展區 (ZPD)」的客製化隨機挑戰，確保任務既不無聊也不致崩潰。**  
* **\[M4.12\] 隱藏成就與高階概念驗證引擎 (Hidden Achievement Validator) `[進階]`**  
  * **`M4.12.1` 主動探索特徵捕捉網：實作背景對話驗證邏輯，專門監聽使用者是否主動探索並理解了未曾觸及的高階知識概念。**  
  * **`M4.12.2` 無預警解鎖訊號發射器：當 Observer Agent 確認概念通過對話驗證後，立即向前端發送隱藏成就解鎖的 WebSocket 廣播訊號。**  
* **\[M4.13\] 損失規避與同儕驗證引擎 (Loss Aversion Engine) `[進階]`**  
  * **`M4.13.1` 損失規避 XP 扣管邏輯：實作硬核的質押扣除演算法，當任務未經社群驗證即宣告失敗或逾期時，系統自動扣除全額質押的 XP。**  
  * **`M4.13.2` 社會情懷強制制約器：透過「沒有退路」的 XP 質押懲罰機制，創造正向同儕壓力與「不願辜負承諾」的內部驅動力。**  
  * **`M4.13.3` 跨社群權限隔離中介軟體：依據右側垂直輪盤的切換狀態，嚴格管控並動態過濾讀書會、陌生人與朋友圈之間的貼文能見度與驗證權限。**

## **🕸️ \[M5\] 深層認知圖譜層 (GraphRAG Pipeline)**

* **\[M5.1\] 薩提爾圖譜寫入器 (Cypher Generator)**  
  * `M5.1.1`：利用 Gemini 3.5 Pro 將日誌轉化為 Behavior, Feeling, Yearning 節點。  
* **\[M5.2\] NSVIF 幻覺防禦引擎**  
  * `M5.2.1 反溯因驗證器`：對照底層 SQLite 行為日誌 (Evidence) 進行因果檢驗，丟棄不合邏輯的邊緣連線。  
* **\[M5.3\] 異質時序記憶治理 (ARPM)**  
  * `M5.3.1 雙時態檢索器`：結合 BM25 與時序權重，分離靜態人設與動態經驗，於發言前撈取 Context 注入 Prompt。

## **🗄️ \[M6\] 資料庫綱要與 ACID 交易層 (Database Schemas)**

* **\[M6.1\] 本地 SQLite 實體綱要 (SQLAlchemy/SQLx)**  
  * `raw_tracking_logs` (id, timestamp, source, raw\_text)。  
  * `chat_transcripts` (id, thread\_id, role, content, timestamp)。  
  * `edge_event_buffer` (id, timestamp, intent\_tag, is\_synced)。  
* **\[M6.2\] 雲端 PostgreSQL 實體綱要與關聯**  
  * `users` (id, current\_xp, level, rpg\_class, avatar\_url)。  
  * `ai_experts` (id, user\_id, expert\_name, personality\_prompt, trust\_level)。  
  * `expert_homepages` (expert\_id, background\_image\_url, unlocked\_features)。  
  * `expert_projects` & `daily_reports` & `zpd_tasks` & `social_posts` (完整 CRUD 實作)。  
* **\[M6.3\] 遊戲化與社群交易引擎 (Transaction DB Locks)**  
  * `M6.3.1 ACID 抽卡守門員`：以 Row-level Locks 包裝「扣除 XP \-\> 隨機權重演算法 \-\> 寫入 Items\_Dictionary / User\_Collections」，防範 Race Condition 刷徽章。  
  * `M6.3.2 損失規避合約引擎`：管理社群對賭協議，當 Validation 逾期時自動扣除質押 XP。  
* **\[M6.4\] 角色與情境鏈結資料表 (PostgreSQL / SQLite)**  
  * `M6.4.1 roles` **表**：`id (UUID)`, `name (VARCHAR)`, `theme_color_palette (JSONB - 用於平滑色溫過渡)`, `created_at`。  
  * `M6.4.2 role_context_aggregates` **表**：建立一對多關聯，將 `role_id` 強烈綁定至 `expert_projects(id)`、`promises(id)`、`goals(id)`，以支援 `M3.2.2` 的 3 秒短期記憶喚醒查詢。  
* **\[M6.5\] 日報與反思草稿核心實體表 (PostgreSQL / SQLite) `[MVP]`**  
  * **`M6.5.1` daily\_reflections 實體關係宣告**  
    * `M6.5.1.1`：宣告包含吉布斯欄位 `ai_description` (客觀描述) 與 `ai_analysis` (初步分析) 的 SQL 表綱要。  
    * `M6.5.1.2`：配置 `user_feeling` (主觀感受) 與 `user_action_plan` (未來行動) 的非空 (NOT NULL) 約束，強制推進微摩擦力反思。  
    * `M6.5.1.3`：實作 `is_draft` (預設為 True) 與 `is_reviewed` 狀態布林旗標，用以嚴格管控 XP 發放與日報正式寫入的 ACID 交易邊界。

### **🎨 \[M7\] 資源與素材生成管線 (Asset Generation Pipeline)**

* **\[M7.1\] 動態生圖系統整合管線 `[MVP/進階]`**  
  * **`M7.1.1` 多來源生圖 API 介接**  
    * `M7.1.1.1`：實作統一的生圖抽象層 API，整合 Pollinations.ai、NanoBanana API 或 Midjourney API 服務。  
  * **`M7.1.2` 上下文渲染與資產產出**  
    * `M7.1.2.1`：開發動態 Prompt 轉換器，根據當下任務的 Context Prompt 即時生成隱藏成就專屬徽章或是立體背景圖並快取至雲端。