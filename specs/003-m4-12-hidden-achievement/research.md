# Research & Architecture Decisions: M4.12 隱藏成就驗證引擎

**Branch**: `003-m4-12-hidden-achievement` | **Date**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

本文件彙整 M4.12 隱藏成就驗證引擎在 Phase 0 階段之架構選型、心理學約束對齊與技術決策。

---

## Decision 1: 快慢雙軌混合特徵捕捉架構 (Dual-Track Epistemic Trap)

### Decision
採用「快軌正則/向量預篩（Fast Path）」與「慢軌本機 LLM 深層評估（Slow Path）」混合架構：
- **Fast Path（快軌）**：每次使用者送出訊息後，於背景非同步執行本地正則表達式、關鍵字模式（Keyword Traps）與輕量向量嵌入相似度計算（<100ms），即時捕捉明確的高階技術探究或跨領域概念。
- **Slow Path（慢軌）**：於會話結束（Session Idle > 5 分鐘）或 M6.4 每日反思提交時觸發，呼叫本機 Gemma (M2.2) 執行深層語意與心理狀態解析，萃取薩提爾冰山元認知轉化、心態重構與深層頓悟。

### Rationale
- **引用依據**: `[R01: 動態邊界 §動態追蹤]`, `[R01: 變動比例增強]`, `[R08: 微摩擦力 §四.2]`。
- 單純依賴即時 LLM 推論會造成本機端高耗電與計算阻塞，無法支撐每則對話的流暢響應；單純依賴批次掃描則會失去使用者在對話中當下提出深刻問題時「即刻觸發驚喜」的心理強化效果。快慢雙軌能在資源耗費與即時回饋感之間取得完美平衡。

### Alternatives Considered
1. **純即時全量 LLM 推論**：每次對話回應均調用 Gemma。揚棄原因：在筆電等終端裝置上會造成風扇狂轉、推論排隊延遲（1~3 秒），嚴重拖慢對話體驗。
2. **純跨日批次結算**：僅在每日跨日結算時掃描昨日對話。揚棄原因：使用者昨天的頓悟到今天才彈窗，早已遺忘當下語境，失去「無預警驚喜」的心流共鳴。

---

## Decision 2: 資料庫層級的「絕對無 UI 狀態」零洩漏隔離 (Zero-Leaked State)

### Decision
在後端資料庫查詢層與 API 序列化層實作嚴格隔離：
- 所有成就查詢端點（如 `GET /api/achievements`）在 SQL 層執行強制過濾：
  ```sql
  SELECT * FROM achievements
  WHERE is_hidden = 0
     OR (is_hidden = 1 AND id IN (SELECT achievement_id FROM user_achievements WHERE user_id = :uid));
  ```
- 任何統計進度條、成就總數計數、技能樹節點，分母一律排除未解鎖的隱藏成就。

### Rationale
- **引用依據**: `[CLAUDE.md 第二條]`, `[M3.11 SPEC §7.3]`, `[R09: 病態使用與 FOMO 防護]`, `[Deci & Ryan: 自我決定論 (SDT)]`。
- 若前端收到未解鎖的隱藏成就（即便標記 `hidden: true` 或灰底「？」），開發者透過 DevTools 或封包攔截即可預先獲取成就 ID、名稱或觸發提示，導致使用者轉移焦點至「刷成就」，破壞內在動機並引發嚴重的錯失恐懼症（FOMO）。從 SQL 層阻斷可保證傳輸層 0% 資料洩漏。

### Alternatives Considered
1. **前端過濾與虛擬佔位**：回傳完整成就清單，前端以問號卡片或 `v-if="!item.hidden || item.unlocked"` 隱藏。揚棄原因：違反 M3.11.3 鐵律，且網路傳輸 JSON 仍會洩漏資料，極易被逆向工程。
2. **成就總數包含隱藏成就**：例如顯示「成就進度 15/25（含 10 個隱藏）」。揚棄原因：使用者看見「缺了 10 個」會產生焦慮與完形崩潰感，違背無負擔探索初衷。

---

## Decision 3: 心流感知微斷點排隊推播 (Flow-Gated Micro-Breakpoint Dispatch)

### Decision
隱藏成就達成後，系統先行於背景以 M6.5 ACID 交易完成落庫與 XP 核發；但解鎖廣播事件暫存於本地記憶體佇列，待 M1.2 斷點偵測模組發布自然微斷點（如使用者送出下一則對話、任務階段交接、或視窗暫歇停頓 > 3 秒）時，才透過 WebSocket 廣播至前端彈出 `SurpriseModal`。

### Rationale
- **引用依據**: `[R04: 認知中斷理論 (Cognitive Interruption)]`, `[RISK-04: 推播時機干擾]`, `[M1.2 斷點偵測 SPEC]`。
- 當使用者處於高頻敲擊程式碼或深度思考（Flow）時，粗暴彈出的強烈慶祝聲光會瞬間摧毀工作記憶（Working Memory）與思維脈絡；若使用者處於焦慮狀態（M4.8），突兀彈窗甚至會加劇認知過載。延遲至微斷點呈現，既維護了「意料之外的驚喜感」，又保證了心流安全。

### Alternatives Considered
1. **達成時立即彈出全螢幕視窗**：不論當前打字狀態直接打斷。揚棄原因：在撰寫複雜演算法中途彈窗會引發使用者的強烈煩躁感（Annoyance）。
2. **歸檔至 M3.9 Defer 通知中心**：等待使用者手動點開鈴鐺通知。揚棄原因：M3.11 SPEC 鐵律明定「不要把隱藏成就驚喜彈窗路由到通知中心，驚喜彈窗的心理機制在於無預警」，事後點開完全喪失儀式感。

---

## Decision 4: 本機 Gemma 離線與推論逾時佇列 (`epistemic_evidence_queue`)

### Decision
建立本機 SQLite `epistemic_evidence_queue` 暫存表。當慢軌執行深層評估時，若偵測到本機 Gemma (M2.2) 處於未載入、模型卸載或推論超時（>3 秒），系統將佐證封包（含對話摘錄、時間戳、候選原型）原子寫入該佇列，狀態設為 `PENDING`。由本機背景守護協程在模型喚醒且系統負載低於閾值時依序出隊處理。

### Rationale
- **引用依據**: `[Constitution Principle I: 本地優先]`, `[Principle V: 進階模組獨立性]`。
- 確保桌面端在斷網、筆電拔除電源節能、或使用者關閉本機大模型時，系統仍具備韌性，絕不因為推論逾時拋出例外或遺漏使用者的元認知成長記錄。

### Alternatives Considered
1. **模型不可用時直接丟棄慢軌**：僅保留快軌正則。揚棄原因：導致需要深刻思考才能解鎖的薩提爾冰山突破（`THE_REFRAME_ALCHEMIST`）在離線時永遠無法觸發。
2. **同步阻塞等待模型喚醒**：強制等待模型載入完成。揚棄原因：可能導致反思送出介面凍結 10~30 秒，嚴重違反本地客戶端流暢性規範。

---

## Decision 5: 開機與重連之單一精選上限補發 (Single Cap Catch-Up)

### Decision
在客戶端啟動或 WebSocket 斷線重連時，後端檢查是否存在 `is_acknowledged = false` 的成就。若有多筆積壓，系統僅選取**稀有度最高（Legendary > Epic > Rare）且時間最新**的 1 筆成就發送 `SurpriseModal` 彈窗，並將該筆及剩餘積壓成就的 `is_acknowledged` 全數置為 `true`，其餘項目在成就頁標記 `is_new = true` 高亮徽章。

### Rationale
- **引用依據**: `[UX 心理學: 警報疲勞 (Alert Fatigue)]`, `[M3.11.4 彈窗排隊佇列]`。
- 避免使用者開機時遭遇連續跳出 3~5 個全螢幕彈窗的「彈窗地獄」，在維護一次最高榮耀驚喜的同時，兼顧桌面應用的清爽開機體驗。

---

## Decision 6: 宣告式核心原型與 AI 個性化金句生成 (Hybrid Archetype Engine)

### Decision
系統固定內建四大核心成長原型（Archetypes）：
1. `THE_CURIOUS_CARTOGRAPHER` (主動探究與高階概念跳躍)
2. `THE_REFRAME_ALCHEMIST` (薩提爾冰山元認知自省與失敗重構)
3. `THE_SERENDIPITY_SEEKER` (脫離螢幕的實體生活探索與注意力恢復)
4. `THE_POLYGLOT_SYNTHESIZER` (跨角色、跨領域之結構性知識整合)

四大原型具備固定的稀有度與 XP 經濟常數；而解鎖時的「個人化副稱號」與「啟發金句（flavor_text）」則由本機 Gemma 依據使用者的真實對話/反思內容動態填充並記錄於 `context_summary` 中。

### Rationale
- **引用依據**: `[Deci & Ryan: 勝任感與自主感]`, `[IKEA 效應 R08: 個人化共鳴]`。
- 固定的原型規則保證了回歸測試的確定性與遊戲化經濟系統的平衡；動態生成的金句與脈絡摘要則為使用者帶來獨一無二的被理解感與情感連結。
