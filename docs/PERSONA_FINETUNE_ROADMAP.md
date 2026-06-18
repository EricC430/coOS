# coOS Persona Fine-Tuning Roadmap

> **Phase 6+ 研究項目 — 本文件僅供規劃，不在 MVP 範圍內實作。**

---

## 背景

MVP（Phase 1–5）採「Prompt 策略層」控制人設品質：

- `persona_card` JSON 結構化定義人設 (identity, big_five, speech_profile, stances, …)
- `compile_to_prompt()` 將 persona_card 編譯成 BDI 結構英文 system prompt
- `output_rules` 注入回覆節奏骨架 (短句、一次一問、共情優先)
- `message_splitter` 依語意切割成多個氣泡，模擬真人打字節奏

Prompt 策略層的天花板：LLM 底座（Gemini Flash / Gemma 4B）本身的說話節奏、慣用語模式仍
會「滲透」出來。真正要讓專家「說話聽起來像那個人」，需要**回覆策略微調**。

---

## 四層架構（對應 PERSONA_UPGRADE_PERPLEXITY.md）

| 層 | 名稱 | MVP 狀態 | Phase 6 目標 |
|----|------|----------|-------------|
| L1 | 人設層 | `persona_card` 已實作 | 加入動態記憶更新（互動後調整 big_five） |
| L2 | 記憶層 | `chat_transcripts` 已存 | 接 Mem0 / LangGraph checkpointer，長期記憶摘要 |
| L3 | 回覆策略層 | `output_rules` Prompt 控制 | LoRA SFT 強化短句 / 分段 / 問句時機 |
| L4 | 微調層 | 無 | LoRA 適配器，插拔式，不改動底座 |

---

## LoRA 微調方案（Phase 6+）

### 參考工作

- **WhatsApp-Llama** (Meta, 2024)：從 WhatsApp 對話訓練短句分段風格
- **LoveChatAI** (2023)：角色扮演 + 情緒安撫對話對，SFT + DPO 二階段
- **[R03 §3.2 Echo Mode]**：防衛語氣偵測 → Agency 漸降；微調資料需包含此類情境
- **[R05 §治療同盟]**：先共情、再回答、最後一個小追問的三段式骨架

### 資料格式

訓練資料使用「分段訊息序列」而非單一長回覆：

```jsonl
{
  "messages": [
    {"role": "system", "content": "<compiled_persona_prompt>"},
    {"role": "user", "content": "我好焦慮，明天要交作業"},
    {"role": "assistant", "content": "聽起來壓力很大。"},
    {"role": "assistant", "content": "你現在進行到哪裡了？"},
  ],
  "persona_id": "严峰_v1",
  "style_tags": ["short_sentence", "empathy_first", "single_question"]
}
```

**關鍵設計**：
- 每個 `assistant` turn 可以是多條訊息（模擬氣泡分割）
- `style_tags` 用於 DPO 正負樣本標記
- `persona_id` 讓同一底座學多個人設（LoRA Mixture）

### 隱私保護（CLAUDE.md L1 約束）

1. 訓練資料必須來自**合成對話**或**使用者知情同意匯出**（不得直接使用 `chat_transcripts` L1 明文）
2. 合成資料生成流程：`persona_card → Gemini Pro 生成對話草稿 → 人工審核 → Eguard.mask_pii → 存訓練集`
3. 訓練在本地或 Google TPU 私有環境執行，訓練資料不上雲端公開服務

### 訓練流程

```
Stage 1: SFT（監督式微調）
  底座: Gemma 4B（本地）或 Gemini Flash（雲端 API 微調，若 GA）
  資料: 合成短句對話 ~5K–20K turns
  目標: 學會短句分段、問句獨立 bubble、情緒安撫優先

Stage 2: DPO（直接偏好優化）
  正樣本: 通過人工評估的回覆（共情、短句、自然）
  負樣本: MVP 期間收集的「太長/催促/問多個問題」case
  目標: 拉大好回覆 vs 壞回覆的 log-prob 差距
```

### 推理整合（coOS 架構）

```
Gemma 4B (本地, MLX 量化)
  ↳ 載入 LoRA 適配器 (persona_lora_v1.safetensors)
  ↳ M4.2 graph.py 的 _call_gemma() 改走本地端點
  ↳ 保持 output_rules Prompt 策略層作為 guardrail

Gemini Flash (雲端, 無 LoRA)
  ↳ fallback when 本地不可用
  ↳ 仍走 compile_to_prompt + output_rules 控制
```

---

## 驗收指標（Phase 6 進入標準）

| 指標 | 目標值 | 量測方式 |
|------|--------|---------|
| 平均氣泡長度 | ≤ 25 字 | 自動統計 |
| 多問題合泡率 | ≤ 5% | 正則偵測 |
| 共情回覆率（焦慮輸入） | ≥ 80% | LLM-as-Judge |
| 催促語氣誤觸 | 0 | 關鍵詞過濾 |
| 人設一致性（10 輪後） | ≥ 85% cosine sim | persona embedding |

---

## 里程碑

| 時間 | 里程碑 |
|------|--------|
| Phase 5 結束 | MVP_CLOSURE_REPORT.md 產出，收集真實對話 case |
| Phase 6 Q1 | 合成資料集 v1 完成（5K turns，3 個 persona） |
| Phase 6 Q2 | SFT 模型 v1 本地可推理，A/B 測試 vs Prompt 策略層 |
| Phase 6 Q3 | DPO 模型 v1，人工盲測 ≥ 70% 偏好 |
| Phase 6 Q4 | LoRA Mixture（多 persona 同底座），正式上線 |

---

## 開放問題

1. **Gemma 4B vs Gemini Flash 微調**：Gemma 本地微調隱私更佳，但 Gemini API 微調成本更低。
   → 建議先 Gemini API 驗證效果，隱私可接受時再移植 Gemma。

2. **多 persona LoRA Mixture**：是否一個 LoRA per persona，或共用底座加 persona token？
   → 先 per-persona LoRA（簡單），待 persona 數 > 10 時考慮 token conditioning。

3. **訓練資料版權**：合成對話若用 Gemini Pro 生成，需確認 Google AI Studio 使用條款。

4. **評估人力**：DPO 負樣本標記需人工審核，需估算標記成本（建議至少 500 pair）。
