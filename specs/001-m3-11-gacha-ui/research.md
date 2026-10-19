# Research & Technical Decisions: M3.11 Gamification Gacha UI

## Decision 1: L1 即時通道（Immediate Celebration vs. Deferred Notification）

- **Decision**: 抽卡結果一律採用 L1 即時慶祝通道，直接觸發開獎 Toast 與動畫，嚴格禁止進入 M3.9 的工作斷點延遲中心。
- **Rationale**: 依據 `[R01: α-DPO Dropout 危機]` 與 `RISK-04`，變動比例增強（Variable Ratio Reinforcement）的核心心理機制在於操作動作（點擊抽卡）與反饋（開獎）之間的強因果時序。若強制延遲 30 分鐘至斷點才提示，使用者已切換心智模型，導致因果連結斷裂，激勵效果歸零。
- **Alternatives Considered**: 曾考慮統一納入 M3.9 批次通知隊列，但因嚴重損害即時反饋感而予以否決。

---

## Decision 2: 防成癮滑動視窗冷卻機制（Sliding Window Rate Limiting）

- **Decision**: 實作 `useDrawRateLimit` Hook，採用 60 分鐘滑動時間視窗限制抽卡上限為 5 次。當到達上限時按鈕立即進入冷卻禁用狀態，並給予柔性心智重整提示。
- **Rationale**: 依據 `[R09: 病態使用風險 §3.3 Replika 案例]` 與 `RISK-09`，盲盒抽卡在個人成長工具中極易引發賭博式重複抽取行為。固定時間重置（如每小時整點重置）可能讓使用者在 59 分與 01 分連續進行 10 抽；滑動時間視窗能維持嚴格的間隔保障。
- **Alternatives Considered**: 每日抽卡上限（限制過於僵硬，缺乏工作日與週末的彈性調度）；純後端限制（前端缺乏即時狀態提示，導致使用者在按鈕點擊後才收到 429 錯誤，體驗挫折）。

---

## Decision 3: 隱藏成就「絕對無 UI 狀態」（Zero-Leaked Hidden State）

- **Decision**: `AchievementGrid` 組件在渲染時，對所有 `item.hidden === true && !item.unlocked_at` 的項目進行底層過濾，DOM 中完全不保留任何標籤、空節點或「未解鎖問號佔位符」。
- **Rationale**: 依據 `CLAUDE.md` 第二條與 M3.11 SPEC 鐵律，若顯示「？」格位或「尚有 3 個隱藏成就」計數，將立即引發錯失恐懼症（FOMO），使用者會花費心力去猜測或逆向工程觸發條件，背離「無預警驚喜」的初衷。
- **Alternatives Considered**: 顯示灰色未命名的問號格位（傳統遊戲常見，但在心理健康/生產力系統中會製造不必要的探索焦慮）。

---

## Decision 4: 焦慮隱性狀態門禁（Anxiety-Gated Promotions）

- **Decision**: 主動推播組件 `GachaPromotion` 接收 M4.8 的隱性狀態，若狀態為 `anxiety`、`avoidance` 或 `depression`，組件直接返回 `null`。
- **Rationale**: 依據 `[R03 §4.2 反向安撫]` 與 `[R09 §3.3]`，當使用者處於高壓、焦慮或逃避狀態時，主動推播遊戲化抽卡無異於引誘使用者進行逃避性補償消費，加重心理負擔。此門禁確保「主動推播永遠不在脆弱時刻發生」。
- **Alternatives Considered**: 推播時加上提醒標語（無法消除多巴胺誘惑，效果微弱，故徹底不渲染）。

---

## Decision 5: 雙軌混合 AI 融合架構與免費公共服務 (Dual-Track Free Img2Img)

- **Decision**: 背景與物體資產分立管理。在背景之上即時排版物件作為視覺底稿，點擊「放置」時呼叫免金鑰免費服務（如 Pollinations.ai / Hugging Face 公開免金鑰端點）執行 Image-to-Image 圖生圖，融合背景與物件之光影透視；若網路失敗或連線超時（> 10 秒），100% 自動無縫降級保留 2D 畫布疊加成果。
- **Rationale**: 依據零設定原則與弱網韌性，免去使用者申請付費 API Key 門檻；雙軌降級保證離線環境下功能永不崩潰。
- **Alternatives Considered**: 僅採用傳統 2D Canvas 貼圖（缺乏光影融合真實感）；強制依賴付費 OpenAI / Midjourney API（增加使用者經濟負擔，違反開箱即用原則）。

---

## Decision 6: 非破壞性圖層管理模式 (Non-Destructive Staging)

- **Decision**: 點擊「放置」並完成 AI 圖生圖融合後，成果圖作為預覽與主題匯出展示，畫布底層各物件圖層（坐標/大小/角度）完整保留，使用者可隨時返回微調二次融合。
- **Rationale**: 遵循 IKEA 效應 [R08: §VI.1]，保護使用者投入排版的心智成果，避免單次合成破壞原始圖層導致無法微調。
- **Alternatives Considered**: 破壞性壓平合併為單一圖片（編輯彈性降為零，使用者若想更動一個物件必須重頭開始）。

---

## Decision 7: 複合混合獎池機制 (Curated & Hybrid Gacha Pool)

- **Decision**: 抽獎池預設由系統官方精選資產組成；使用者自訂生成作品預設直接入庫，並提供「投入抽獎池」（`in_gacha_pool: true`）開關；介面支援切換「官方精選池」與「自創混合池」。
- **Rationale**: 兼顧系統官方的美術品質與稀有度階層（Common ~ Legendary），同時賦予自創資產被二次抽取的成就感與驚喜感。
- **Alternatives Considered**: 自創作品強制全部入池（可能稀釋官方美術風格一致性）；完全不允許自創作品入池（喪失個人化擴展樂趣）。

---

## Decision 8: 現代自然語言完整句式 Prompt 增強範本 (FLUX/SDXL Style)

- **Decision**: 系統嚴禁堆疊碎片化標籤（如 `8k, masterpiece, award winning`），而是將使用者輸入動態重構為結構完整、細節具體的自然語言句式（包含主體細節、環境光影、空間景深透視；物件去背採用純淨單色無雜物陳列之句式描繪）。
- **Rationale**: 現代前沿開源擴散與生成模型（FLUX.1、SDXL、SD3）採用 T5/CLIP 文字編碼器，對完整自然語言連續語句的空間關聯與光影氛圍理解度遠優於舊式逗號標籤堆疊。
- **Alternatives Considered**: 傳統標籤詞庫堆疊法（已不符合現代圖像生成模型的架構最佳實踐）。

---

## Decision 9: 本地自訂主題庫與一鍵桌面背景套用 (Local Theme Scene Registry)

- **Decision**: 畫布編輯完成之場景持久儲存於本地 `CustomThemeScene`，支援管理多套自訂佈置場景，並可一鍵套用為 coOS 桌面主背景，同時提供單次 PNG/WebP 檔案下載匯出。
- **Rationale**: 將使用者的視覺合成創作直接轉化為 coOS 日常工作時的桌面沉浸氛圍，深化系統個人化與心理擁有感。
- **Alternatives Considered**: 僅提供圖片下載至本機（系統內部無法享受自製佈置的沉浸感）；強制同步至雲端伺服器（增加網路負擔與伺服器儲存成本）。

