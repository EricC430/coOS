# M5 薩提爾冰山層 — 重新檢視與整合設計 (v2.0)

> **狀態**:已拍板 (§13,2026-10-19);實作待 MVP 結案報告
> **日期**:2026-10-19
> **取代**:`04_module_registry.md` 中 M5.1 / M5.2 / M5.3、M4.8.4、M4.10 的現行定義;`03_research_index.md` R04 對雲端 Neo4j / DGNN / Hawkes 的落地要求 (已拍板 Q2;**圖模型保留,改為本地儲存**,見 §4.6)
> **前置閱讀**:`03_research_index.md` R04、R06;`05_integration_risk_audit.md` RISK-03/05/06/08/10;`DESIGN_PHILOSOPHY_AUDIT.md` §5.4 / Q1

---

## 0. 一句話

**coOS 替「自己挖不下去的人」在背景形成冰山假設,並把假設轉化為專家的陪伴方式、適時的碰撞、可驗證的小實驗與變化的鞏固 —— 使用者感受到的是「被懂」與「自己發現」,而不是一份心理診斷。**

---

## 1. 為什麼要重做 (現況檢視結論)

| # | 問題 | 證據 |
| - | ---- | ---- |
| 1 | **名實落差**:冰山是產品定位第一句,程式碼 0 行 | `services/` 無 `m5_*`;`DESIGN_PHILOSOPHY_AUDIT.md` 判斷二 |
| 2 | **職責散落 8 處且重複** | NSVIF 同時存在於 M4.10 與 M5.2;ARPM 同時存在於 M4.9 與 M5.3;應對姿態轉譯在 M4.8.4,節點寫入在 M5.1,視覺化在 M3.10,敘事在 M3.8,負向信念在 M1.5 |
| 3 | **已有一半冰山在跑,但沒有共用骨架** | 感受層:`m6_4` 的 `user_feeling` / `mood_score`、`state_inversion.py`;觀點/期待層:`bdi.py` 的 belief/desire (目前來源是臨時拼湊);應對姿態:`reactance.py` / `echo_mode.py` 處理的「防衛」 |
| 4 | **原設計只有「寫入圖譜」,沒有「怎麼用」** | M5.1 的 Purpose 止於「寫入 Neo4j」;推論如何回到使用者身上只散見於 dev log |
| 5 | **隱私衝突** | 冰山假設由 L1 對話逐字稿推得,本身就是 L1 等級敏感資料,原架構卻放在雲端 Neo4j |
| 6 | **對 N=1 過度工程** | DGNN + Hawkes + Neo4j 需要大量節點才有統計意義;單一使用者一年也不會有足夠資料 |

---

## 2. 意圖、目標、非目標、反目標

### 2.1 意圖 (使用者原話整理)

服務對象是**無法自行深層探索的人**。系統推論冰山,然後透過**隱微的影響、與使用者的碰撞、以及追蹤變化**讓使用者產生改變。重點不只是推論,而是**以高品質的方式呈現到終端使用者**。

### 2.2 目標

- G1 系統能從既有本地資料形成**有證據、有信心值、可被推翻**的七層冰山假設。
- G2 假設透過 12 種作用方式 (§5) 回到使用者身上,且每一次作用都經過時機、劑量、安全的守門。
- G3 使用者在專家對話中**看不到任何術語或診斷**,只感受到陪伴方式的改變。
- G4 使用者的每一個反應都回流成證據,讓假設自我修正 (假設 → 介入 → 反應 → 更新)。
- G5 變化可被量化 (一致性指數、姿態分布、實驗完成),可作為期末論文的 N=1 證據。
- G6 MVP 在本層全數移除時仍可獨立運作 (CLAUDE.md 不要做的事 #7)。

### 2.3 非目標

- 不是心理治療、不做臨床診斷、不輸出任何疾病或人格標籤。
- 不處理創傷、原生家庭等議題的**主動探索**(使用者自己提起時,只承接、不深挖)。
- 不做跨使用者模型、不做圖神經網路訓練。

### 2.4 反目標 (技術上能動,但算失敗)

- ❌ 專家說出「你的渴望是被接納」「你又在超理智了」這類宣讀式句子。
- ❌ 使用者否認時,系統把否認一律當成「防衛 = 證實假設」(不可證偽的陷阱)。
- ❌ 在使用者低落、焦慮、深度工作時碰撞。
- ❌ 冰山假設的文字出現在任何雲端請求、社群貼文、日誌明文中。
- ❌ 遊戲化在結構上強化使用者的冰山問題 (例:對「價值 = 表現」的人推 XP 質押)。

---

## 3. 架構總覽

```
 ┌───────────────────── 本地 (L1,永不上雲) ─────────────────────┐
 │                                                               │
 │  既有證據源                                                    │
 │  chat 逐字稿 · m6_4 反思 (feeling/mood/learned) · M1 遙測       │
 │  M1.4 Git · M4.6 goals/promises · reactance 分數 · MI change talk│
 │          │                                                    │
 │          ▼                                                    │
 │  M5.2 證據萃取器 ──► M5.1 冰山假設庫 ◄── M5.3 符號驗證器        │
 │  (規則標記 + 本地 Gemma)   (SQLite)      (證據門檻/反溯因/衰減)  │
 │                              │                                │
 │                              ▼                                │
 │                  M5.4 轉化歷程追蹤 (變化階段 · 變化指標 · 圖分析) │
 │                              │                                │
 │                              ▼                                │
 │                  M5.5 介入規劃器 (12 種作用方式 · 守門 · 劑量)    │
 │                              │                                │
 │                              ▼                                │
 │                  M5.6 指令編譯器 + 洩漏閘                        │
 │                  (假設文字 ✕ → 專家行為指令 ✓)                    │
 └──────────────────────────────┼────────────────────────────────┘
                                ▼  只有「行為指令」離開本層
   呈現通道:M4.2 專家對話 · M1.2 斷點主動訊息 · M3.3 反思提問
            M3.13 小實驗卡 · M3.8 Wrapped · M4.5/M3.5 呈現政策 · M3.12 冰山之鏡
                                │
                                ▼
                 使用者反應 ──► M5.2 反應分類 ──► 回到 M5.1 (證據)
```

**核心設計原則**:

1. **假設留在本地,只有「怎麼陪伴」離開** —— 延伸 `bdi.py` (belief/desire → intention) 與 `state_inversion.py` (狀態 → 語氣) 已經驗證過的模式:推論永遠先被翻譯成行為指令,才交給雲端 LLM。
2. **越深的層,證據門檻越高、信心上限越低** (§4.3)。
3. **每次作用都是一次實驗**:介入是用來區分競爭假設的,使用者反應就是實驗結果。
4. **一輪只做一件事**:每一則專家回覆最多攜帶一個 move。

---

## 4. 資料與推論層

### 4.1 模組重編 (取代現行 M5 章)

| 新編號 | 名稱 | 取代 / 吸收 | 類型 |
| ------ | ---- | ----------- | ---- |
| M5.1 | 冰山假設庫 (Hypothesis Store) | 原 M5.1 Cypher Writer | `[進階]` |
| M5.2 | 證據萃取器 + 反應分類器 | 吸收 M4.8.4 應對姿態轉譯 | `[進階]` |
| M5.3 | 符號驗證器 (NSVIF-lite + 反溯因) | 合併原 M5.2 與 M4.10 | `[進階]` |
| M5.4 | 轉化歷程追蹤 | 新增 | `[進階]` |
| M5.5 | 介入規劃器 (Move Planner) | 新增;吸收 M1.5 負向信念部分 | `[進階]` |
| M5.6 | 指令編譯器 + 洩漏閘 | 新增 | `[進階]` |
| M3.12 | 冰山之鏡 (透明與控制) | 新增 UI | `[進階]` |
| M3.13 | 小實驗卡 | 新增 UI | `[進階]` |
| ~~M5.3 ARPM Graph~~ | 退役,職責併入 M4.9 | — | — |
| ~~M4.10~~ | 退役,併入新 M5.3 | — | — |

M3.10 技能樹**不顯示冰山節點** (我的判斷:把心理層畫成可點亮的遊戲節點,等於把「自我」遊戲化,違反 §5 作用方式 11)。M3.10 改為只呈現技能,不再硬依賴 M5。

### 4.2 本地 SQLite 綱要 (全部 L1)

```sql
-- M5.1 冰山假設
CREATE TABLE m5_1_iceberg_hypotheses (
  id              TEXT PRIMARY KEY,
  user_id         TEXT NOT NULL,
  role_scope      TEXT NOT NULL,        -- 'role:<uuid>' | 'cross_role' (見 §10 RISK-23)
  theme_id        TEXT REFERENCES m5_4_themes(id),
  layer           TEXT NOT NULL CHECK (layer IN (
                    'behavior','coping_stance','feeling','meta_feeling',
                    'perception','expectation','yearning','self')),
  content         TEXT NOT NULL,        -- 自然語言假設 (L1,永不上雲)
  attrs           TEXT,                 -- JSON: stance_type / need_type / target(self|other|from_other) / valence / arousal
  confidence      REAL NOT NULL DEFAULT 0.3,
  status          TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
                    'candidate','working','established',
                    'softening','transformed','refuted','user_rejected')),
  origin          TEXT NOT NULL CHECK (origin IN (
                    'rule_marker','local_synthesis','user_stated','user_corrected')),
  rival_group_id  TEXT,                 -- 同組為互相競爭的解釋 (反溯因)
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  last_evidence_at TEXT,
  last_tested_at  TEXT                  -- 最後一次被 move 測試
);

CREATE TABLE m5_1_iceberg_links (       -- 冰山圖的邊 (圖模型保留,存在本地;見 §4.6)
  from_id   TEXT NOT NULL REFERENCES m5_1_iceberg_hypotheses(id),   -- 較淺層
  to_id     TEXT NOT NULL REFERENCES m5_1_iceberg_hypotheses(id),   -- 較深層
  relation  TEXT NOT NULL DEFAULT 'driven_by' CHECK (relation = 'driven_by'),
            -- 一律只存「淺 → 深」的 driven_by;manifests_as 是查詢時的反向視圖,不另存,避免兩份邊不一致
  confidence REAL NOT NULL,
  PRIMARY KEY (from_id, to_id, relation)
);

CREATE TABLE m5_1_iceberg_evidence (
  id            TEXT PRIMARY KEY,
  hypothesis_id TEXT NOT NULL REFERENCES m5_1_iceberg_hypotheses(id),
  source_table  TEXT NOT NULL,          -- 'raw_tracking_logs' | 'chat_transcripts' | 'daily_reflections' | 'm5_5_moves_log' | 'm5_5_experiments' | 'm5_1_iceberg_prompts'
  source_id     TEXT NOT NULL,          -- [RISK-05] 必須指回本地原始紀錄
  polarity      TEXT NOT NULL CHECK (polarity IN ('supports','contradicts','inconclusive')),
  weight        REAL NOT NULL,          -- [R04: D-ALP §神經符號約束滿足] nucleus=1.0 / satellite=0.4 / elaboration=0
  observed_at   TEXT NOT NULL,
  extractor_version TEXT NOT NULL
);

-- M5.4 主題 (一串跨層假設 = 一個主題,例:「求助」)
CREATE TABLE m5_4_themes (
  id                 TEXT PRIMARY KEY,
  user_id            TEXT NOT NULL,
  role_scope         TEXT NOT NULL,
  label              TEXT NOT NULL,     -- 內部標籤 (L1)
  satir_phase        TEXT NOT NULL DEFAULT 'status_quo' CHECK (satir_phase IN (
                       'status_quo','foreign_element','chaos',
                       'integration','practice','new_status_quo')),
  phase_entered_at   TEXT NOT NULL,
  congruence_index   REAL,              -- 0~1,見 §6.2
  collision_cooldown_until TEXT,
  is_sensitive       INTEGER NOT NULL DEFAULT 0,  -- 創傷/原生家庭 → 只承接不碰撞
  external_name      TEXT,                        -- mode 8:使用者同意的模式名字
  tags               TEXT                         -- JSON:固定詞彙 (worth_contingent / fear_of_failure / help_seeking / perfectionism / conflict_avoidance / control)
);

-- M5.5 介入紀錄
CREATE TABLE m5_5_moves_log (
  id            TEXT PRIMARY KEY,
  theme_id      TEXT,
  hypothesis_ids TEXT NOT NULL,         -- JSON array (只存 id)
  mode          INTEGER NOT NULL,       -- 1~12,見 §5
  move_id       TEXT NOT NULL,          -- move catalog 條目
  dosage        INTEGER,                -- 碰撞劑量 1~3
  channel       TEXT NOT NULL,          -- 'chat' | 'breakpoint' | 'reflection' | 'experiment' | 'wrapped' | 'policy'
  persona_id    TEXT,
  delivered_at  TEXT NOT NULL,
  reaction      TEXT CHECK (reaction IN (
                  'resonate','elaborate','neutral','deflect',
                  'reject_calm','reject_reactive','no_response')),
  reaction_at   TEXT
);

CREATE TABLE m5_5_experiments (
  id             TEXT PRIMARY KEY,
  theme_id       TEXT NOT NULL,
  proposal_text  TEXT NOT NULL,         -- 給使用者看的文字 (不含術語)
  success_signal TEXT NOT NULL,         -- JSON:遙測/Git 判定式,例 {"source":"m1_4","event":"pr_opened","within_days":7}
  status         TEXT NOT NULL CHECK (status IN (
                   'proposed','accepted','declined','in_progress','observed','not_observed','expired')),
  result_note    TEXT,
  created_at     TEXT NOT NULL,
  closed_at      TEXT
);

-- M3.3 反思中的冰山提問 (獨立表,不改 MVP 的 daily_reflections)
CREATE TABLE m5_1_iceberg_prompts (
  id            TEXT PRIMARY KEY,
  reflection_id TEXT NOT NULL,
  move_log_id   TEXT NOT NULL REFERENCES m5_5_moves_log(id),
  question      TEXT NOT NULL,
  answer        TEXT,                   -- 使用者自行填寫;絕不自動填
  answered_at   TEXT
);

-- 使用者控制 (同意本身沿用既有 user_consents 表,consent_type = 'm5_iceberg';未同意或 revoked → 整層停用)
CREATE TABLE m5_settings (
  user_id            TEXT PRIMARY KEY,
  engine_enabled     INTEGER NOT NULL DEFAULT 1,
  max_collision_dosage INTEGER NOT NULL DEFAULT 2,
  paused_until       TEXT
);

-- M5.4 同盟分數 (取代 ai_experts.trust_level:後者建立後從不更新,不能當閘門)
CREATE TABLE m5_4_alliance (
  persona_id   TEXT NOT NULL,
  role_id      TEXT NOT NULL,
  score        REAL NOT NULL DEFAULT 0,   -- 0~1,每日批次重算
  updated_at   TEXT NOT NULL,
  PRIMARY KEY (persona_id, role_id)
);

-- M5.4 核心渴望 (圖分析結果,只存數值與 id;見 §6.3)
CREATE TABLE m5_4_core_yearnings (
  role_id       TEXT NOT NULL,
  hypothesis_id TEXT NOT NULL REFERENCES m5_1_iceberg_hypotheses(id),
  reach         INTEGER NOT NULL,       -- 能抵達此渴望的主題數
  core_score    REAL NOT NULL,
  is_core       INTEGER NOT NULL,       -- reach ≥2 且 core_score ≥0.25
  computed_at   TEXT NOT NULL,
  PRIMARY KEY (role_id, hypothesis_id)
);
```

**同盟分數** [R17: WAI §Triad Dimensions] 以三項可觀測代理值等權平均:近 14 天與此專家有對話的天數 / 14 (bond);使用者在對話中自陳感受的訊息占比,以 0.3 為滿分 (bond);過去 move 中 resonate + elaborate 的占比,無 move 時為 0.5 (task)。

**跨庫說明**:`daily_reflections` 在雲端 PostgreSQL (M6.4)。M5.2 每日批次經 M6.4 既有 API 讀取當日反思,只把 `user_feeling` / `user_learned` / `mood_score` 轉成本地證據;`source_id` 存反思 id,M5.3 驗證時經 M6.4 API 解析 (雲端→本地讀,不反向)。冰山提問的答案只存本地 `m5_1_iceberg_prompts`,不寫回雲端。

### 4.3 證據階梯 (每層的推論權限)

[R04: 心理幻覺 §心理幻覺的定義與生成機制] 指出三種成因:過度推論、信心錯位、錯誤前提。以下門檻逐條對應:

| 層 | 可由誰形成 | 最低證據 (升至 `working`) | 升至 `established` | 信心上限 (無使用者確認時) | 衰減半衰期 |
| -- | ---------- | ------------------------- | ------------------ | ------------------------- | ---------- |
| behavior | 遙測/Git/日誌直接觀察 | 1 筆本地事實 | 3 筆、跨 ≥2 天 | 0.95 | 7 天 |
| coping_stance | 語言標記規則 + 本地 Gemma | 3 段情節 | 6 段、跨 ≥3 天、≥2 種情境 | 0.85 | 21 天 |
| feeling | **使用者自陳優先**;推論只能補位 | 1 筆自陳 或 2 筆推論 | 自陳 ≥2 | 0.8 | 3 天 |
| meta_feeling | 使用者語句 | 2 筆 nucleus 語句 | 3 筆 | 0.7 | 14 天 |
| perception | 使用者語句 (歸因、因果連詞) | 2 筆 nucleus 語句 | 4 筆、跨 ≥2 週 | 0.8 | 60 天 |
| expectation | 使用者語句 + goals/promises | 2 筆 | 4 筆 | 0.8 | 60 天 |
| yearning | **只能由上層鏈推得** | 需 ≥2 個 `working` 上層假設以 `driven_by` 連結 | 需 ≥2 個 `established` 上層 + 1 次 move 獲 `resonate` | 0.75 | 180 天 |
| self | 只作「工作假設」 | 同 yearning | **不可經推論升至 established**;只有 `user_stated` | 0.6 | 365 天 |

**不跳層規則** [R04: D-ALP §神經符號約束滿足]:yearning/self 假設若沒有完整的上層鏈 (behavior → stance 或 feeling → perception 或 expectation),M5.3 直接拒絕。

### 4.4 信心更新

對數勝算 (log-odds) 累加,刻意保持簡單、可測試、可解釋:

```
logit(c_new) = logit(c_old) + Σ_e  sign(e.polarity) · e.weight · k_layer
k_layer: behavior 1.0 · stance 0.8 · feeling 0.8 · perception 0.6 · expectation 0.6 · yearning 0.4 · self 0.3
inconclusive 證據 sign = 0 (只更新 last_evidence_at)
每日批次套用衰減:c ← 0.5 + (c − 0.5) · 2^(−Δt / half_life)
最後夾在 [0.02, 層上限]
```

狀態轉移:`c < 0.15` 或反溯因挫敗分數 > 0.5 → `refuted`;使用者在冰山之鏡按「不是這樣」→ `user_rejected` (之後不得以相同 content 重新生成,30 天內同 rival_group 不得再次升級)。

### 4.5 M5.2 證據萃取

**兩段式,全部本地**:

1. **規則標記 (每則訊息即時,零成本)** —— [R06: 應對姿態 §4.2] 的語言特徵:
   - 討好:道歉頻率、自我貶抑詞 (「我太笨」「都是我的錯」)
   - 指責:絕對詞 (「總是」「從不」)、外歸因 + 攻擊性情緒詞
   - 超理智:術語密度、被動語態、情緒詞缺席率 (在高壓情境下)
   - 打岔:話題跳轉、敷衍回覆 (「ok」「隨便」),以及 Git 中敷衍 commit message [R06: 數位表型 §2.1]
   - 一致:第一人稱情緒 + 需求的清楚表述
   - 觀點:歸因句型 (「因為我…所以…」「一定是…」)
   - 期待:「應該」「必須」「希望他」句型
   輸出:`(layer, attrs, source_id, weight)` 候選證據,**不產生自然語言假設**。
   例外:behavior 與 coping_stance 層可由規則直接建立假設 (content 用模板生成,例「卡關超過 2 小時未求助」),因為這兩層屬於可觀測事實。
2. **本地 Gemma 合成 (每日批次,走 M1.2 閒置時段)** —— 讀取當日新證據 + 現有 `working` 假設,產出:新假設候選、上層鏈 links、**每個 perception/expectation/yearning 假設至少 1 個競爭假設** [R04: 反溯因 §反溯因推理的對抗性驗證]。Gemma 不可用時本步跳過 (只有規則層運作,系統不壞)。

**主題 (theme) 的形成**:當一個 perception 或 expectation 假設首次升到 `working`,即建立一個主題,並把以 links 連到它的上下層假設都歸入該主題。一個假設只屬於一個主題;Gemma 合成時若判斷兩個主題的 perception 為同一信念,合併為一個 (保留較早的 id)。behavior / stance / feeling 在尚未連到任何 perception 前不屬於任何主題,只供 mode 1/4/5 使用。

**反應分類器** (同屬 M5.2):在 move 送出後,讀使用者下一則訊息 (或 48 小時無回應) 分類為 7 種 reaction,結合當輪 reactance 分數:

| 反應 | 對被測假設的證據 |
| ---- | ---------------- |
| resonate (「對…其實我就是這樣」) | supports, weight 1.0 |
| elaborate (主動多講) | supports, 0.6 |
| neutral / no_response | inconclusive |
| deflect (轉移話題) | inconclusive (同時為 distracting 姿態的 behavior 證據) |
| reject_calm (平靜地說不是) | contradicts, 0.8 |
| reject_reactive (帶防衛地否認,reactance 高) | **inconclusive** —— 但同一假設累計 3 次 → 改記 contradicts 0.5 (RISK-21:防止「否認 = 證實」的不可證偽陷阱) |

### 4.6 圖模型與本地儲存

拍板 Q2 拿掉的是**雲端 Neo4j** (隱私:冰山屬 L1) 與 **DGNN / Hawkes** (N=1 資料量不足以訓練或估計),**不是圖模型本身**。冰山在資料上仍是一張有向圖:

| 圖的元素 | 存放 |
| -------- | ---- |
| 節點 | `m5_1_iceberg_hypotheses` (八層) |
| 邊 | `m5_1_iceberg_links` (淺 → 深 `driven_by`,帶 confidence) |
| 子圖 | 以 `(user_id, role_scope)` 切分;`cross_role` 節點出現在每個有支撐的角色子圖中 |

**兩種存取方式,各司其職**:

1. **SQLite 遞迴 CTE** —— 確定性的結構檢查 (M5.3 不跳層、祖先鏈),每次寫入時即時執行。
2. **記憶體圖分析 (networkx)** —— 每日批次 (M1.2 閒置時段) 與冰山之鏡開啟時,由 M5.1 依角色子圖載入成 `networkx.DiGraph` 計算,結果只寫回數值與 id,不另存圖副本。用途:
   - **核心渴望分析** (§6.3) → M5.5 mode 5 排序
   - **推理路徑** (§9) → 冰山之鏡「這個猜測是怎麼來的」

所有圖存取都經過 M5.1 的 `IcebergGraph` 介面 (`load_subgraph` / `ancestor_paths` / `descendants`),上層模組不直接寫 SQL 或碰 networkx。日後若出現以下任一情況,再評估改用**本地嵌入式**圖資料庫 (不回雲端):節點數 > 約 5,000、需要 > 7 跳的查詢、或開始做 Obsidian Vault 的跨實體圖整合。屆時只需替換 `IcebergGraph` 的實作。注意:常被推薦的嵌入式選項 Kùzu 原專案已於 2025-10 封存,改由 RyuGraph 等分支維護,長期依賴前需評估。

---

## 5. 12 種作用方式 (Move Catalog)

以薩提爾變化歷程 (現狀 → 外來元素 → 混亂 → 整合 → 練習 → 新現狀) [R20: Satir Model §變化歷程] 為骨架。每種方式在 move catalog 中有多個條目,每條目定義:前置條件、通道、指令模板、禁止事項、成功訊號。

| # | 作用方式 | 適用階段 | 最低假設狀態 | 主要通道 | 研究依據 |
| - | -------- | -------- | ------------ | -------- | -------- |
| 1 | 隱微影響 | 全程 | working | chat | [R03: Echo Mode §3.2] [R16: MI §OARS] |
| 2 | 碰撞 (外來元素) | status_quo → foreign_element | working (劑量 1) / established (劑量 2–3) | chat, breakpoint, reflection | [R20: Satir Model §變化歷程] [R16: MI §Change Talk] |
| 3 | 變化追蹤 | 全程 (背景) | — | 無 (內部) | [R06: 雙層記憶網路 §6.1] |
| 4 | 肯定姿態的正向用意 | status_quo, foreign_element | working (coping_stance) | chat | [R16: MI §Rolling with Resistance] [R20: Satir Model §應對姿態] |
| 5 | 在關係中滿足渴望 | 全程,chaos 優先 | working (yearning) | chat | [R05: 治療同盟 §治療同盟建構] [R17: WAI §Triad Dimensions] [R21: 矯正性情緒經驗 §核心概念] |
| 6 | 示範 (專家的一致與脆弱) | status_quo, integration | working | chat | [R05: 主動展現弱點 §合成心理病理學] [R26: 示範學習 §觀察學習] |
| 7 | 使用者自己的話回聲 | foreign_element, integration | 需有 nucleus 語句證據 | chat, reflection | [R16: MI §Change Talk] [R11: Reflection §3.2] [R25: 生成效應 §實驗結果] |
| 8 | 外化命名 | foreign_element, integration | established | chat | [R22: 外化 §外化對話] |
| 9 | 小實驗 + 證據回饋 | practice | established (perception) | experiment card, chat | [R23: 行為實驗 §實驗設計] [R09: SDT §第四章] |
| 10 | 鞏固 | new_status_quo | softening / transformed | chat, wrapped | [R10: 敘事化福祉 §敘事化福祉] (RISK-10 守門) |
| 11 | 結構性不強化 | 全程 (政策) | established | policy | [R09: 病態使用 §3.3] [R08: §五 意圖脫鉤] |
| 12 | 策略性留白 | chaos、低準備度 | — | 無 (不介入) | [R08: §二 任務斷點打斷管理] [R24: 改變階段 §階段定義] |

### 5.1 每種方式的具體行為 (以「求助 = 無能」主題為例)

假設鏈 (內部,使用者看不到):
`behavior: 卡關 3 小時不問人` → `coping_stance: 超理智` → `feeling: 挫折、羞愧` → `perception: 求助等於無能` → `expectation(self): 應該自己解決` → `yearning: 被肯定、被接納`;
rival:`perception: 偏好獨立思考的學習風格` (非防衛)。

| # | 專家實際說的話 / 系統實際做的事 | 禁止 |
| - | ------------------------------ | ---- |
| 1 | 使用者卡關時,專家先問「卡在哪一段?我可以陪你看」,而不是丟解法;主動分享「我以前也常卡很久才問人」 | 說出任何層名、診斷語 |
| 2 劑量1 | 「我有點好奇 —— 你剛說想今天做完,但好像一直自己扛著?」(好奇並置,問句) | 肯定句陳述心理 |
| 2 劑量2 | 「你上週說『問了就代表我不行』,今天你又卡了三小時。這兩件事你覺得有關嗎?」(用使用者原話並置) | 「你又來了」、帶評價的形容詞 |
| 2 劑量3 | 「我注意到一個模式,想跟你確認看看對不對…」(命名模式,需使用者在設定中允許劑量 3) | 未經允許使用 |
| 4 | 「一個人撐住這麼久,其實需要很大的力氣。這個習慣大概也幫你度過不少難關。」 | 把姿態說成缺點 |
| 5 | 使用者完成一件事時,肯定的是**努力與思考過程**而非結果;使用者坦露時,先接住再回應 | 以結果為條件的肯定 |
| 6 | 專家講自己的故事:「我實習時也覺得問人很丟臉,後來發現大家其實很樂意」(來源:persona card 新增 `iceberg_story` 欄位) | 編造與 persona card 矛盾的經歷 (ARPM 會擋) |
| 7 | 「你上個月說過『卡住的時候其實是怕被看到不會』—— 今天也是那種感覺嗎?」 | 竄改使用者原話;引用跨角色的原話 |
| 8 | 「我們幫它取個名字?像是那個『要先準備好才敢開口』的聲音?」→ 之後雙方用這個名字溝通 | 系統單方面命名後強加 |
| 9 | 小實驗卡:「這週試一次:卡超過 30 分鐘就發一則問題給同學。」接受後,M1.4 偵測到 issue/PR 留言 → 專家:「你問了,而且對方 20 分鐘就回了。感覺怎樣?」 | 強制接受;用 XP 獎勵綁定 (見 §8) |
| 10 | 「三週前你說問人代表不行,這週你問了三次。你覺得自己有什麼不一樣嗎?」(讓使用者自己說出變化) | 系統替使用者宣告「你成長了」 |
| 11 | 對此使用者:XP 呈現強調「投入」而非「排名」;不推薦 M4.13 XP 質押;連續中斷不出現損失文案 | 改動 XP 數值 (只改呈現) |
| 12 | 使用者低落或剛被碰撞後出現 reject_reactive → 接下來 2 輪只做 4/5,不提主題 | — |

---

## 6. M5.4 轉化歷程追蹤

### 6.1 階段轉移 (每個主題各自一條)

| 從 → 到 | 觸發訊號 |
| ------- | -------- |
| status_quo → foreign_element | 送出劑量 ≥1 的碰撞、回聲或外化 move |
| foreign_element → chaos | 72 小時內出現任 2 項:reject_reactive、mood_score 下降 ≥2、M4.8 avoidance/anxiety、該主題相關行為增加 |
| foreign_element → integration | reaction = resonate/elaborate,或使用者自發說出 change talk [R16: MI §Change Talk] |
| chaos → integration | 混亂訊號消退 ≥3 天,且出現 change talk |
| chaos → status_quo | 7 天無 change talk 且混亂訊號消退 (回到原狀,冷卻 14 天) |
| integration → practice | 使用者接受一個小實驗 |
| practice → new_status_quo | 2 個實驗 `observed`,且一致性指數較進入 foreign_element 前上升 ≥0.15 |
| new_status_quo | 對應 perception 假設改為 `softening`;30 天維持 → `transformed` |

### 6.2 變化指標

- **一致性指數** (congruence_index):該主題相關情境中,被標為 congruent 姿態的語句占比 (7 日滑動)。
- **姿態分布**:五種姿態的週分布。
- **觀點語言轉移**:歸因句型從「穩定、內在、不可控」轉向「可控、情境性」的比例。
- **實驗完成率**、**碰撞反應分布**。

全部只存數值,供 M5.5 決策、M3.8 敘事、論文評估使用。

### 6.3 核心渴望分析 (圖分析)

**問題**:同一個渴望 (例:被肯定) 可能同時驅動好幾個主題 (求助、完美主義、怕衝突)。若只看單一主題,系統會在三個主題上各自碰撞三次;但如果在關係中直接滿足那個共同的渴望 (mode 5),一次就能同時鬆動三個主題 [R21: 矯正性情緒經驗 §核心概念]。

**定義** (每個角色子圖各自計算;只計 `working+` 節點與邊):

```
path_strength(p) = Π 節點 confidence × Π 邊 confidence     (沿 behavior → … → yearning 的一條路徑)
reach(Y)         = 能經由 driven_by 路徑抵達 Y 的不同主題數
core_score(Y)    = Σ_主題 t  max_{p: t 中的節點 → Y} path_strength(p)
Y 為核心渴望  ⇔  reach(Y) ≥ 2  且  core_score(Y) ≥ 0.25
```

- 路徑列舉以 `networkx.all_simple_paths(cutoff=7)` 實作;N=1 規模下 (每角色數百節點) 每日批次 < 1 秒。
- 跨角色:reach 只計**目前角色**內的主題,不累加其他角色 (RISK-23 保守做法)。
- 輸出寫入 `m5_4_core_yearnings (role_id, hypothesis_id, reach, core_score, computed_at)`,只有數值與 id。

**使用**:M5.5 為 mode 5 (`MEET_ACCEPT` / `MEET_RECOGNIZE`) 加上核心加分,並在選擇「要滿足哪個渴望」時優先挑核心渴望 (§7.2)。冰山之鏡在核心渴望旁標示「在好幾件事背後都看到它」。

---

## 7. M5.5 介入規劃器

### 7.1 守門順序 (確定性規則,全部可單元測試)

```
1. 全域硬閘 (任一失敗 → 只允許 mode 12)
   - user_consents 無有效 'm5_iceberg' 同意 / engine_enabled = 0 / paused
   - 危機訊號 (自傷、自殺相關語句) → 整層停用 + 專家切換支持模式並提供求助資源 (1925 安心專線)。
     我的判斷:危機偵測是安全功能,應放在 M4.2 管線中、**不依賴 M5 同意與否**都執行;M5 只讀它的旗標
   - M1.2 深度工作中 (主動通道)
2. 碰撞類閘 (mode 2/7/8;失敗 → 降級為 1/4/5/6)
   - 48 小時內最新 mood_score ≤ 3 (無紀錄 → 此條不判)
   - role_implicit_states 中未過期的 label = anxiety (M4.8 尚未實作 / 無資料 → 視為 unknown,此條不判,改靠 mood 與 reactance)
   - 主題 satir_phase = chaos
   - 當輪 reactance 觸發 Echo Mode
   - collision_cooldown_until 未到 (每主題 72h;全域每週 ≤2 次)
   - theme.is_sensitive = 1
   - m5_4_alliance.score < 0.6 (劑量 ≥2 時) [R17: WAI §Triad Dimensions]
3. 碰撞後保護:任何碰撞之後的 2 輪,強制 mode 4 或 5
4. 主動通道 (breakpoint) 只在 M1.2 發出斷點事件時送出 [R08: §二]
```

### 7.2 選擇

通過守門的候選 move 依下式排序,取第一名 (一輪只取一個):

```
score = info_gain × readiness + phase_fit − fatigue + core_bonus
info_gain  : 此 move 能區分同 rival_group 假設的程度 (成功訊號在兩個假設下預測不同 → 高)
readiness  : 主題階段與 mode 的適配表 (§5 表格「適用階段」)
fatigue    : 同 mode 近 7 日使用次數 × 0.2
core_bonus : 只用於 mode 5;目標渴望為核心渴望時 = 0.5 × min(core_score, 1),否則 0 (§6.3)
```

mode 5 的目標渴望選擇:同時有多個 `working+` yearning 時,取 `core_score` 最高者;都不是核心渴望時,取與當前對話主題相連且信心最高者。

不做強化學習;權重先寫死,等 N=1 數據回來再調 (留給 builder 的常數)。

### 7.3 多專家

move 指派給 `role_scope` 對應角色中**目前對話的專家**;主動通道則依 M1.2 `StaggeredDispatcher` 既有的優先序。mode 6 只指派給 persona card 有 `iceberg_story` 的專家。

---

## 8. M5.6 指令編譯器與呈現通道

### 8.1 指令編譯 (假設 → 行為)

輸出結構延用 `mi_selector.MIDirective` 的形狀,新增欄位,注入 `prompt_builder.build_system_prompt` 的新區塊 `[這一輪的陪伴方式]` (≤ 120 tokens):

```python
@dataclass
class IcebergDirective:
    move_id: str
    mode: int
    instruction: str           # 例:「使用者提到卡關時,先肯定他已經投入的努力,再用好奇的問句問他是否想找人一起看。」
    quote: str | None          # mode 7 才有:使用者同角色內的原話 (已經 Eguard mask_pii)
    forbidden_actions: list[str]
```

**洩漏閘 (RISK-19)**:編譯結果在離開本層前必須通過:

- 不含層名與術語:冰山、應對姿態、討好、指責、超理智、打岔、渴望、自我價值、yearning、coping…
- 不含使用者狀態描述 (沿用 RISK-03 測試的做法)
- `quote` 必須來自同一 `role_scope`,且經 `eguard.mask_pii()`
- 失敗 → 丟棄 move,改為 mode 12,寫 `raw_tracking_logs`

### 8.2 與現有 M4.2 管線整合

```
drift_filter → bdi_reconciler → reactance_detector → echo_mode
            → [新] iceberg_move  → persona_responder → paralinguistic → message_splitter → arpm_audit
```

- `iceberg_move` 節點:讀 M5.5 已排好的 move (本地 SQLite 查詢,<10ms);若 echo_mode 本輪觸發 → 只接受 mode 1/4/5/12。
- `bdi_reconciler` 的 `bdi_belief` / `bdi_desire` 改由 M5.1 的 perception / expectation `working` 以上假設提供 (目前來源是臨時拼湊);仍必須經 reconcile [RISK-08]。
- MI 選擇器的技術選擇優先採用 move 指定的技術 (例:mode 7 → `CHANGE_TALK_REPLAY`;mode 4 → `AFFIRMATION`)。
- `arpm_audit` 之後非同步觸發反應分類 (透過 `_dispatch_observer_bg` 既有路徑)。

### 8.3 其他通道

| 通道 | 行為 | 守門 |
| ---- | ---- | ---- |
| M1.2 斷點主動訊息 | mode 2/7/9 的追問與實驗回饋 | 只在斷點;每日 ≤1 則冰山類主動訊息 |
| M3.3 反思提問 | Gibbs 表單下方可選的「今天想多問你一個問題」,題目來自 move (問句) | **可跳過**、**不自動填** [R08: §六.1 IKEA 效應];不給額外 XP (避免外在動機污染自我揭露) |
| M3.13 小實驗卡 | 儀表板卡片:提議文字、接受 / 不要 / 換一個;接受後顯示觀察中;結果出來後由專家在斷點聊 | 不可強制;不綁 XP;7 天到期 |
| M3.8 Wrapped | mode 10 鞏固敘事 | [RISK-10] 低落週不慶祝;M3.8 未實作前改由專家對話承擔 |
| M4.5 / M3.5 呈現政策 | `presentation_policy(user)` 回傳旗標 `soften_loss_framing` / `emphasize_effort` / `hide_rank_comparison` / `block_stake_offers` | 只改呈現,不改 XP 數值與 ACID 流程;無此層時全部預設 false (MVP 不受影響) |
| M3.12 冰山之鏡 | 見 §9 | — |

---

## 9. M3.12 冰山之鏡 (透明與控制)

設定頁中的一個獨立頁面 (使用者主動打開才看得到,系統不推)。

- **呈現語言**:不用術語,改用溫和的假設語氣,例「我們猜:你遇到困難時,常習慣自己扛 —— 也許是因為擔心問了會被覺得不夠好」。每條附信心 (三段:「還在猜」「有點把握」「比較確定」)。
- **「這個猜測是怎麼來的」(推理路徑)**:以圖分析取最強的 1–2 條祖先路徑 (§4.6),由淺到深呈現,例「卡關時常一個人撐很久 → 壓力大時先把感覺放一邊 → 覺得有點丟臉 → 心裡也許覺得『問了就代表我不夠好』」。路徑上每一步都可點開看證據 (日期 + 來源類型 + 本地原文)。若同 rival_group 還有存活的競爭假設,附一行「也可能是:…」(我的判斷:把「系統也不確定」攤開,是對心理幻覺最誠實的呈現)。
- **操作**:「對,就是這樣」(→ user_stated 證據)、「不太對」(→ contradicts 0.8)、「完全不是」(→ user_rejected)、「這個話題先不要碰」(→ is_sensitive)、暫停整個功能 N 天、刪除全部冰山資料。
- **同意流程**:首次啟用時說明「coOS 會在背景形成對你的理解,並據此調整專家陪伴你的方式;這些理解只存在你的電腦,你隨時可以查看、修正、刪除。」未同意 → 整層停用。

> 這是「隱微」與「操弄」的分界:**作用方式是隱微的,但存在本身不是祕密**。具體分界由使用者拍板 (§13 Q1)。

---

## 10. 整合風險稽核

### 10.1 已觸發的既有風險

| RISK | 本設計的處理 | 驗收測試 |
| ---- | ------------ | -------- |
| RISK-03 焦慮鏡像 | 指令編譯沿用 State Inversion;碰撞類在 anxiety 時被閘掉 | `test_collision_blocked_when_anxiety` |
| RISK-04 斷點 vs 即時 | 主動通道只在 M1.2 斷點 | `test_breakpoint_channel_requires_breakpoint_event` |
| RISK-05 壓縮 vs 驗證 | **根本消除**:冰山全在本地,證據 `source_id` 直接指回本地原文;不再有雲端圖譜 | `test_evidence_source_id_resolves_locally` |
| RISK-06 跨角色 | 證據與淺層假設綁 role;深層 cross_role 規則見 RISK-23 | `test_quote_never_crosses_role` |
| RISK-08 BDI 矛盾 | belief/desire 改由 M5.1 供給,仍強制 reconcile | 沿用 `test_contradictory_bdi_resolution` |
| RISK-09 Gacha + 焦慮 | `presentation_policy` 對特定主題加 `block_stake_offers` | `test_policy_blocks_stake_for_worth_theme` |
| RISK-10 Wrapped 虛假樂觀 | mode 10 經 RISK-10 模板 | 沿用 |
| RISK-12 社群側通道 | 冰山資料不得被任何社群模組讀取 (DB 層禁止 m6_6 讀 m5_*) | `test_community_cannot_read_m5_tables` |
| RISK-01 草稿核准 | 反思提問不自動填、不給 XP | `test_iceberg_prompt_never_autofilled` |

### 10.2 新增風險 (待寫入 `05_integration_risk_audit.md`)

- **RISK-19 指令洩漏**:`M5.6 + M4.2 + 雲端 LLM` —— 假設文字經指令流入雲端 prompt。緩解:§8.1 洩漏閘。測試:`test_directive_contains_no_iceberg_terms`、`test_directive_never_contains_hypothesis_content`。
- **RISK-20 脆弱期碰撞**:`M5.5 + M4.8 + M6.4 mood_score` —— 低落/混亂期的碰撞造成二次傷害。緩解:§7.1 第 2 步。測試:`test_collision_blocked_low_mood`、`test_collision_blocked_in_chaos_phase`。
- **RISK-21 不可證偽**:`M5.2 反應分類 + M4.2 reactance` —— 否認被一律當作防衛而強化假設。緩解:§4.5 reject_reactive 規則。測試:`test_three_reactive_rejections_count_as_contradiction`。
- **RISK-22 遊戲化強化冰山**:`M5 + M4.5/M4.13/M3.11` —— 損失規避機制強化「價值 = 表現」。緩解:`presentation_policy`。測試同 RISK-09 列。
- **RISK-23 深層假設跨角色**:`M5.1 + M4.3` —— yearning/self 天生跨角色,與角色隔離衝突。我的建議:淺層與證據一律綁 role;yearning/self 只有在 ≥2 個角色各自有獨立支撐鏈時才可標 `cross_role`;跨角色使用時只能影響 mode 1/5/6 (陪伴方式),**不可**引用另一角色的任何事件或原話。須使用者拍板 (§13 Q3)。

### 10.3 觀測性

每次 move 選擇、閘門拒絕、送出、反應分類、假設狀態轉移,都寫 `raw_tracking_logs` (M0.4),payload 只含 id、mode、gate 名稱、數值,**不含 content**。

---

## 11. 研究引用

### 11.1 既有可引用 (`03_research_index.md`)

R03 Echo Mode §3.2;R04 §冰山層次節點類型與結構化屬性定義、§心理幻覺的定義與生成機制、§神經符號約束滿足與 D-ALP 框架、§反溯因推理的對抗性驗證;R05 §治療同盟建構、§合成心理病理學;R06 §2.1 版本控制紀錄、§4.1 冰山層次、§4.2 應對姿態、§6.1 雙層記憶網路;R08 §二、§五、§六.1;R09 §第四章 SDT、§3.3 病態使用;R10 敘事化福祉;R11 §3.2;R16 §OARS / §Change Talk / §Rolling with Resistance;R17 §Triad Dimensions;R18 §Mitigation Strategies。

### 11.2 新補登 (2026-10-19 已寫入研究索引)

| 編號 | 文獻 | 支撐 |
| -------- | ---- | ---- |
| R20 | Satir, Banmen, Gerber & Gomori (1991). *The Satir Model: Family Therapy and Beyond.* | 冰山原典、五種姿態、變化歷程 (外來元素/混亂/整合) |
| R21 | Alexander & French (1946). *Psychoanalytic Therapy* — 矯正性情緒經驗 | mode 5 |
| R22 | White & Epston (1990). *Narrative Means to Therapeutic Ends* — 外化 | mode 8 |
| R23 | Bennett-Levy et al. (2004). *Oxford Guide to Behavioural Experiments in Cognitive Therapy* | mode 9 |
| R24 | Prochaska & DiClemente (1983). 改變階段模型 | mode 12、readiness |
| R25 | Slamecka & Graf (1978). 生成效應 (Generation effect) | mode 7 |
| R26 | Bandura (1977). *Social Learning Theory* — 示範學習 | mode 6 |

R04 的**圖模型保留** (本地 SQLite 邊表 + 記憶體圖分析,§4.6);雲端 Neo4j、DGNN、Hawkes 不再落地 (研究約束鬆綁,§13 Q2)。D-ALP 降級為「nucleus / satellite 證據權重」,反溯因保留為「強制競爭假設 + 挫敗分數」。

---

## 12. 分階段交付

| 階段 | 內容 | 使用者可見 | 為何這個順序 |
| ---- | ---- | ---------- | ------------ |
| P0 | 文件:更新 registry、research index、risk audit;處理 MVP 守門 (§13 Q4) | 無 | 憲章要求 |
| P1 | M5.1 + M5.2 (規則層 + Gemma 批次) + M5.3 + M3.12 冰山之鏡 (唯讀 + 修正) + 同意流程 | 只有冰山之鏡 | **先看準,再動手**:使用者先用冰山之鏡檢查推論準不準,修正本身也是證據 |
| P2 | M5.5 + M5.6 + M4.2 整合;只開 mode 1/4/5/6/12 + mode 11 | 專家陪伴方式改變 | 低風險方式先上,累積同盟分數 (m5_4_alliance) |
| P3 | mode 2/7/8 + 反應分類 + M5.4 階段追蹤 + M3.3 反思提問 | 碰撞出現 | 需要 P2 累積的信任與 P1 驗證過的精度 |
| P4 | mode 9 (M3.13 實驗卡 + 遙測判定) + mode 10 + 變化指標儀表 (論文用) | 實驗卡、鞏固 | 需要前面階段的主題進入 practice |

每階段的完成條件 = 該階段相關的 §10 測試全部通過 + 既有測試 0 failed。

### 12.1 驗收標準 (摘要,各模組 SPEC 再展開)

- [ ] 任何雲端請求的 payload 中搜不到 `m5_1_iceberg_hypotheses.content` 的任何片段 (property test)
- [ ] yearning/self 假設無上層鏈時無法建立
- [ ] self 層無 `user_stated` 證據時 status 永不為 established
- [ ] 一輪專家回覆最多一個 move
- [ ] mood ≤3 / anxiety / chaos / 深度工作 / 未同意 → 零碰撞
- [ ] 碰撞後 2 輪必為 mode 4/5
- [ ] 3 次 reject_reactive 計為 contradicts
- [ ] 冰山之鏡「完全不是」後,同 content 不再生成
- [ ] 刪除全部冰山資料後,M4.2 對話與 MVP 流程照常 (移除測試)
- [ ] 每個 move 都在 `raw_tracking_logs` 留下不含 content 的紀錄

---

## 13. 拍板紀錄 (2026-10-19,使用者:六題全部照建議)

| # | 問題 | 決定 |
| - | ---- | ---- |
| Q1 | 透明的分界 | ✅ 冰山之鏡 + 首次同意 (§9):作用方式隱微,存在本身不是祕密;使用者隨時可查看、修正、刪除、暫停 |
| Q2 | Neo4j / DGNN / Hawkes | ✅ 雲端 Neo4j、DGNN、Hawkes 放棄;**圖模型保留**,以本地 SQLite 邊表儲存、networkx 做圖分析 (§4.6,2026-10-19 補充);R04 的 D-ALP 降級為證據權重,反溯因保留為競爭假設 + 挫敗分數 |
| Q3 | 深層假設跨角色 (RISK-23) | ✅ 有條件跨角色 (§10.2):≥2 個角色各有獨立支撐鏈才可標 `cross_role`,且只影響 mode 1/5/6,不引用他角色事件或原話 |
| Q4 | MVP 守門 | ✅ 先補 `docs/MVP_CLOSURE_REPORT.md`,通過後本層才可動工;SPEC 撰寫不受此限 |
| Q5 | 補登 R20–R26 | ✅ 已寫入 `03_research_index.md` |
| Q6 | 碰撞最大劑量預設 | ✅ 預設 2,使用者可在冰山之鏡設定開到 3 |

各模組 SPEC:`docs/modules/M5_1_*` ~ `M5_6_*`、`M3_12_*`、`M3_13_*`。

---

## 14. 留給 builder 的決定

- 規則標記的詞表、閾值、Gemma prompt 措辭 (§4.5)
- log-odds 權重、衰減半衰期、info_gain 的計算細節 (先寫死,可調)
- move catalog 的條目數與指令模板措辭 (每 mode 至少 2 條)
- 冰山之鏡與實驗卡的視覺設計 (遵循 `docs/BRAND_GUIDE.md`)
- 危機詞表與求助資源文案 (需人工審)
- 核心渴望門檻 (reach ≥2、core_score ≥0.25) 與推理路徑顯示條數的實測調整
