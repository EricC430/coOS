# Persona 擬真化升級提案 (Persona Realism & Psychological Mechanism Upgrade)

**日期**：2026-06-10
**狀態**：提案（待拍板後依 implement-module 流程施工）
**目標**：將 M4.2 專家人設從「LLM 生成的一段 personality_prompt」升級為「**有結構化人格、有情節記憶、有心理介入技術、有一致性監督**的擬真專家」。

## 引用聲明

- 內部研究依 `[Rxx §章節]` 格式（R01–R10，見 `docs/03_research_index.md`）。
- 標記 `[EXT-n]` 者為**外部文獻/開源技術，尚未納入 03_research_index.md**。本提案任一 EXT 項目若採納為架構依據，必須先由使用者拍板將其正式登錄進研究索引（新增 R11+ 編號），方可寫入程式碼註解。

### 外部文獻清單

| 標記 | 文獻 / 技術 | 本提案取用的核心概念 |
|------|-------------|---------------------|
| [EXT-1] | Park et al., *Generative Agents: Interactive Simulacra of Human Behavior*, UIST 2023 | Memory Stream（情節記憶流）、檢索分數 = 新近性 × 重要性 × 相關性、Reflection（定期將觀察昇華為高階洞察） |
| [EXT-2] | Shao et al., *Character-LLM: A Trainable Agent for Role-Playing*, EMNLP 2023 | Experience Upload（以「形成性經歷」定義角色）、Protective Experiences（知識邊界——角色該不知道的事就承認不知道） |
| [EXT-3] | Jiang et al., *PersonaLLM*（Big Five 條件化生成研究） | OCEAN 五因子可被 LLM 穩定表達且可被外部評測辨識 → 人格用結構化特質向量而非散文描述 |
| [EXT-4] | Wang et al., *RoleLLM / RoleBench*, 2023 | 角色扮演一致性的可量化評測（role profile + 評測集） |
| [EXT-5] | Packer et al., *MemGPT*, 2023；開源後繼 **Letta**；替代品 **Mem0**、LangGraph Store | 分層記憶（core memory blocks / archival）、OS 式記憶換頁 |
| [EXT-6] | Miller & Rollnick, *Motivational Interviewing*（動機式晤談，臨床心理經典） | OARS 技術組（開放式提問 / 肯定 / 反映式傾聽 / 摘要）、變化語句 (change talk) 辨識、與阻抗「不對抗、滾動順應」 |
| [EXT-7] | Horvath & Greenberg, *Working Alliance Inventory* (WAI), 1989 | 治療同盟三成分（目標共識/任務共識/情感連結）作為 persona 品質指標——與 [R05 §EHARS] 互補 |
| [EXT-8] | Sharma et al., *Towards Understanding Sycophancy in Language Models*, 2023 | 諂媚行為的成因與緩解 → 反諂媚守則，呼應 [R03 §4 諂媚效應] |
| [EXT-9] | **sqlite-vec**（開源 SQLite 向量擴充） | 本地向量檢索——情節記憶 embedding 留在 L1，符合隱私三層 |

---

## 1. 現況診斷（為什麼現在的專家「不夠像人」）

| 症狀 | 根因 | 對應 |
|------|------|------|
| 專家記不住上次說過的事，只靠 16 條原始逐字稿 | 無情節記憶層；[記憶區塊] 因 GAP-B3 永遠為空 | §3 |
| 人設只是一段 300 字散文，多次生成品質不穩 | 無結構化人格 schema、無生成校驗（GAP-C5） | §2 |
| 回應永遠單一大氣泡、語氣機械 | message_splitter 未接（GAP-B2）；副語言只有開頭填充詞 | §5 |
| 「心理機制」只剩 Echo Mode 的 agency 數字 | 阻抗消解後**沒有對應的介入技術**——降低 agency 之後說什麼？無框架 | §4 |
| 長對話人設漂移無人監督 | M4.9 ARPM 排在進階，目前零監督 | §6 |
| 專家對任何領域都侃侃而談 | 無知識邊界 → 反而暴露「它是 AI」 | §2.3 |

---

## 2. PersonaCard v2 — 結構化人格

### 2.1 Schema（`ai_experts` 表擴充，新增 JSON 欄位 `persona_card`）

```jsonc
{
  "identity":   { "name": "...", "birth_year": 1988, "education": [...], "career": [...] },
  "big_five":   { "O": 0.8, "C": 0.7, "E": 0.4, "A": 0.6, "N": 0.3 },          // [EXT-3]
  "core_values": ["扎實基本功勝過花招", "先動手再完美"],
  "speech_profile": {
    "fillers": ["欸我跟你說", "嗯…這樣講好了"],       // 個人化副語言 [R05 §跨越恐怖谷]
    "quirks":  ["愛用做菜比喻", "句尾偶爾冒台語"],
    "taboos":  ["條列式", "客服腔"]
  },
  "formative_episodes": [                                  // [EXT-2] Experience Upload
    { "age": 24, "event": "第一份工作三個月被資遣", "lesson": "履歷不等於能力", "tellable": true }
  ],
  "knowledge_boundary": {                                  // [EXT-2] Protective Experiences
    "expert_in": ["求職策略", "履歷"],
    "casual_in": ["前端技術"],
    "ignorant_of": ["醫療", "法律細節"],   // 超出 → 承認不知道並轉介同角色其他專家
    "refer_via": "ai_registry"             // 依 M4.2 SPEC §9 決議：同角色可互相提及
  },
  "stances": [                                             // 反諂媚素材 [EXT-8][R03 §4]
    { "topic": "海投履歷", "position": "反對", "strength": 0.8 }
  ]
}
```

### 2.2 Persona Compiler（取代現行 `_ai_generate_expert` 單次生成）

兩段式管線，修復 GAP-C5：

1. **生成**：依使用者描述產出 PersonaCard v2 JSON（雲端 tier3，一次性成本）。
2. **批判校驗 (critic pass)**：以 rubric 檢查——具體性（有年代/機構/事件）、無 `_FORBIDDEN_PHRASES`、big_five 與 speech_profile 互洽（如 E=0.2 卻滿口驚嘆號 → 退回重生成）、stances 至少 2 條。不過關最多重試 2 次，仍不過則降級為人工模板。
3. **入庫**：`personality_prompt` 改為由 PersonaCard **編譯產生**（單一真相來源是結構化卡片，不是散文）。

## 3. 情節記憶層 (Persona Episodic Memory) — [EXT-1][EXT-5]

> **隱私鐵則**：記憶全部落在本地 SQLite（L1），embedding 以 [EXT-9] sqlite-vec 本地計算與檢索。**雲端只收到檢索後注入 prompt 的少量文字**，與現行對話通道相同等級（受 DEVIATION-09 拍板結果約束），絕不整庫上雲。RISK-06：所有記憶以 `(role_id, persona_id)` 雙鍵隔離。

新表 `m4_2_persona_memories`：

| 欄位 | 說明 |
|------|------|
| `id, role_id, persona_id` | 雙鍵隔離 |
| `kind` | `observation`（對話事實）/ `reflection`（夜間昇華）/ `commitment`（使用者承諾，與 M4.6 promises 互通） |
| `content` | 一句話記憶（先過 Eguard mask_pii — RISK-12） |
| `importance` | 1–10，寫入時由 Gemma 邊緣評分（tier1，省雲端配額） |
| `embedding` | sqlite-vec，本地 |
| `created_at, last_accessed` | 新近性計算用 |

**檢索**（每次回應前，取 top-5 注入 [記憶區塊] v2）：

```
score = α·recency(decay 0.995/hr) + β·importance + γ·cosine(query, embedding)   # [EXT-1]
```

**夜間 Reflection job**：掛在與 M4.4.3 草稿排程同一個 cron 槽（02:00 草稿、02:30 reflection、03:00 rule miner，錯開 DB 鎖）。把當日 observations 摘要成 1–3 條 reflection（Gemma 邊緣優先）。[EXT-1] 的核心發現：沒有 reflection，agent 只會復述瑣事；有 reflection 才會「他最近為了期末考壓力很大」這種人味洞察。

**[記憶區塊] v2 組成**（修復 GAP-B3 後擴充）：
`核心目標(M4.3) + 即將到期承諾(M4.6) + top-5 情節記憶(本層) + 上次對話結尾摘要`，總預算 ≤ 350 tokens。

## 4. 心理介入層：MI 技術選擇器 — [EXT-6] × [R03 §3] × [R09 §4.1]

Echo Mode 目前只輸出「agency 數值」；本層補上「**降到這個 agency 之後，具體用哪種說話技術**」。

| 輸入狀態 | ToneState / Agency [R03 §3.2] | MI 技術 [EXT-6] | 行為指令範例 |
|----------|------------------------------|-----------------|--------------|
| 阻抗高（reactance > 0.7） | EMPATHETIC 0.2–0.4 | **反映式傾聽**＋滾動順應，禁止建議 | 「聽起來你覺得這些方法都試過了，很悶。」 |
| 焦慮（implicit_state=anxiety） | EMPATHETIC | **肯定 (Affirmation)** + 任務切小 | State Inversion 不鏡像 [RISK-03] |
| 逃避（avoidance） | PROBING 0.55–0.7 | **開放式提問**誘發 change talk，禁罪惡感誘導 [RISK-03] | 「如果這件事做完了，最先變輕鬆的會是什麼？」 |
| 心流/穩定 | AUTHORITATIVE 0.8+ | **摘要 + 結構化建議** | 正常專家模式 |
| 使用者自己說出改變意圖 | 任意 | **摘要回放 change talk** | 「你剛剛自己說了想先把演算法補起來——這句很關鍵。」 |

實作：`m4_2_persona/mi_selector.py`，輸入 `(reactance_score, implicit_state, tone_state)` → 輸出 2–3 行「本回合行為指令」拼入 system prompt。**SDT 檢查** [R09 §4.1]：回應後以規則層快檢是否觸及自主/勝任/連結之一（M4.2 SPEC 驗收 `test_sdt_three_needs_explicit` 終於有實作對象）。

**反諂媚守則** [EXT-8][R03 §4]：system prompt 注入該 persona 的 `stances`，並加指令「使用者觀點與你的 stance 衝突時，先承認其合理處、再溫和堅持你的立場並給理由；不可立刻倒戈」。呼應 SPEC §9 決議「真誠且具邊界感、可表現些許無奈」。

## 5. 表現層：把已有的零件接起來（與 GAP 報告合併施工）

1. **message_splitter 入圖**（GAP-B2）：persona graph 新增 `message_splitter` 節點；API 回傳 `messages: [{content, delay_ms}]`；前端逐氣泡渲染 + 打字指示器。
2. **個人化副語言**：`inject_paralinguistic` 改從 PersonaCard `speech_profile.fillers` 取詞（取代全域共用 FILLER_WORDS），比例維持 `0.08×(1.5−trust)`，上限 15% [R05 §諂媚效應反模式]。
3. **問候語 persona 化**（GAP-C4）：配對問候改走 M4.2 graph 生成（帶 formative_episodes 其一作自我介紹素材），並落地 `chat_transcripts`。

## 6. 一致性監督：ARPM-lite — [R03 §2] + [EXT-4]

完整 ARPM (M4.9) 屬進階模組，此處先做可獨立拆除的輕量版（符合 MVP 不依賴進階原則）：

- **Claim Ledger**：每次回應後（背景、非阻塞）以 Gemma 邊緣抽取「persona 對自身的事實宣稱」（年齡/經歷/立場），寫入 `persona_claims` 表。
- **矛盾檢查**：新宣稱與既有 ledger 衝突（規則層：數字/年代不符；語意層：Gemma NLI 式判斷）→ 記 `persona_drift_detected` 事件至 `raw_tracking_logs`（M0.4），**不打斷對話**，供日後 M4.9 消費。
- **評測集**：仿 [EXT-4] RoleBench 思路，為每個 persona 由 PersonaCard 自動生成 20 題「身世拷問」題庫，CI 內離線跑一致性（取代 SPEC 中無法落地的 `simulate_conversation(turns=50)`）。

## 7. 分期施工計畫

| 期 | 內容 | 前置 |
|----|------|------|
| **P0（修復，1–2 天）** | GAP-B3 記憶區塊接線、GAP-C7 歷史方向、GAP-C4 問候落地、message_splitter 入圖 | 無 |
| **P1（PersonaCard v2，3–5 天）** | schema + compiler + critic、個人化副語言、知識邊界與 stances 注入、`_ai_generate_expert` 退役 | P0 |
| **P2（記憶層，5–8 天）** | `m4_2_persona_memories` + sqlite-vec + 檢索注入 + 夜間 reflection（與 GAP-B1 草稿 cron 同槽施工） | P0、GAP-B1 |
| **P3（心理介入 + 監督，3–5 天）** | mi_selector + SDT 快檢 + 反諂媚守則 + ARPM-lite claim ledger | P1 |

**驗收測試先行**（CLAUDE.md 鐵則 3）：每期開工前把上述行為寫成 pytest（`testing/m4_2/test_persona_card.py`、`test_persona_memory.py`、`test_mi_selector.py`、`test_claim_ledger.py`）。

## 8. 整合風險預警（對照 `05_integration_risk_audit.md`）

| 風險 | 本提案的觸碰點 | 緩解 |
|------|----------------|------|
| RISK-02 | MI 技術切換可能被 ARPM-lite 誤判為漂移 | mi_selector 輸出登記於合法切換空間（同 Echo Mode LEGAL_TRANSITIONS 處理） |
| RISK-03 | 記憶層回放使用者焦慮語句 → 變相鏡像 | reflection 寫入前過 State Inversion 詞彙過濾；MI 表格明文禁鏡像 |
| RISK-06 | 記憶/claims 跨角色洩漏 | 所有新表雙鍵 `(role_id, persona_id)` + middleware 驗證；嚴禁跨 role 檢索 |
| RISK-08 | stances + MI 指令 + BDI 同時注入 → 衝突指令 | 全部經 bdi_reconciler 之後的單一 prompt assembler 統一拼裝，定義優先序：安全 > MI > stances > 副語言 |
| RISK-12 | 記憶 content 含 PII 進 prompt 後上雲 | 寫入即 mask_pii；注入前二次檢查 `[REDACTED` |
| 配額 | 記憶評分/reflection/claims 全走 Gemma 邊緣（tier1），雲端只負責回應本身 | Rate limiter 已就位 |

## 9. 待拍板事項

1. EXT-1 ~ EXT-9 是否登錄進 `03_research_index.md`（R11+）？[可以登錄R11+]
2. DEVIATION-09（逐字稿上雲豁免條款）需先決議，否則記憶注入 prompt 的合法性懸置。[已在該文件決策]
3. P2 記憶層 schema 為新增資料表（非破壞性），但仍依憲章走 Alembic migration 審核流程。
