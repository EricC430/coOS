# M4.8 — 隱性狀態推論管線 (Implicit State Inference Pipeline)

**標籤**:`[進階]`
**版本**:`1.0` / `draft`
**最後更新**:2026-06-03

## 1. Purpose (目的)

從代碼提交模式、對話語氣、IDE 活動特徵中，以非監督式機器學習推斷使用者的隱性心理狀態（焦慮 / 逃避 / 心流 / 常態），並在 DRIFT 保護下將推論結果注入 Persona 決策樹，使 Persona 能動態調整回應策略。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R02 | §非監督式管線 全章 | M4.8.1 特徵矩陣 + M4.8.2 孤立森林/HMM 狀態解碼的整體架構 |
| R02 | §計算心理語言學 §1 | M4.8.1 源碼變更熵 (Shannon Entropy) 計算 |
| R02 | §動態上下文工程 REMT | M4.8.5 即時可編輯記憶拓樸的 YAML 注入設計 |
| R01 | §動態追蹤 POMDP+BKT | M4.8.3 部分可觀察狀態的信念分布 + 多模態 BKT |
| R06 | §第四章 應對姿態 §4.2 | M4.8.4 冰山中層應對姿態 (指責/討好/超理智/打岔) 的標籤轉譯 |
| R01 | §α-DPO + Dropout 危機 | M4.8.3 ZPD 邊界縮放時必須遵循的退縮保護機制 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M1.1 OS 遙測 | `raw_tracking_logs` rows | WPM、焦點視窗切換頻率、ActivityState 八態 |
| M1.3.1 VS Code 擴充 | `raw_tracking_logs` rows | 源碼變更熵、停留時間 |
| M2.2 意圖向量 | `IntentVector` | `{valence: -0.4, arousal: 0.7, frustration_level: 0.6}` |
| M6.1 `chat_transcripts` | DB Rows | 對話語氣特徵 (用於 DistilBERT 情感分類) |
| M4.3 `RoleContext` | 角色上下文 | 限定推論範圍至當前 `role_id` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M6.3 `role_implicit_states` | DB Insert | `{user_id, role_id, label: "anxiety", confidence: 0.85, valence: -0.4, arousal: 0.7}` |
| M4.2.4 Persona 注入 (via REMT) | `ImplicitState` | `{label: "anxiety", conf: 0.85, role_id: "role_csie"}` → 走 State Inversion |
| M4.11 ZPD 任務池 (進階) | `CognitiveLoad` | `{zpd_lower: 0.3, zpd_upper: 0.7, current_mastery: 0.5}` |
| M0.4 結構化日誌 | `LogEvent` | 推論結果、信心度、狀態轉移事件 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M2.2** (Gemma 邊緣推論)：提供 `IntentVector` 的 valence/arousal/frustration 特徵
- **M1.1** (OS 遙測)：提供 WPM、焦點切換、ActivityState 八態原始信號
- **M1.3.1** (VS Code 擴充)：提供源碼變更熵
- **M4.1** (Agent 路由)：推論結果透過 M4.1.3 Observer 容器觸發
- **M4.3** (角色隔離)：推論結果以 `(user_id, role_id)` 雙鍵寫入 [RISK-06]
- **M6.1** (SQLite)：讀取 `raw_tracking_logs` 與 `chat_transcripts`

### 下游 (誰依賴我)

- **M4.2** (Persona)：透過 REMT 注入隱性狀態，走 State Inversion (RISK-03)
- **M4.11** (ZPD 任務池)：消費認知負荷推論結果動態調整任務難度
- **M3.11** (Gacha 抽卡)：焦慮狀態下封鎖 Gacha 推播 (RISK-09)
- **M5.1** (薩提爾圖譜)：推論結果寫入冰山中層 CopingStance 節點

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-03** | 隱性狀態注入 Persona 後鏡像放大焦慮迴路 | M4.8.5 注入時必須遵循 **State Inversion**：焦慮→安撫、逃避→溫和、心流→推進。絕不鏡像 |
| **RISK-06** | 角色切換時隱性狀態跨界洩漏 | `role_implicit_states` 以 `(user_id, role_id)` 雙鍵寫入/讀取；切換後新角色無狀態 → 中性預設 |
| **RISK-09** | 焦慮狀態 + Gacha 推播 → 病態使用 | M4.8 推論 `anxiety` 時通知 M3.11 封鎖 Gacha 主動推播；使用者主動按鈕可放行但顯示提示 |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m4_8/test_implicit_state_pipeline.py

import pytest

class TestM4_8_1_FeatureExtraction:
    def test_source_code_entropy_calculation(self):
        """[R02 §1.1] 源碼變更熵正確計算"""
        diff_blocks = [{"file": "a.py", "lines": 50}, {"file": "b.py", "lines": 30}]
        entropy = calculate_change_entropy(diff_blocks)
        assert 0 < entropy < 2.0  # Shannon entropy 合理範圍

    def test_feature_matrix_shape(self):
        """特徵矩陣包含所有必要維度"""
        features = extract_feature_matrix(user_id="u_001", window_minutes=30)
        assert "wpm_avg" in features
        assert "focus_switch_count" in features
        assert "code_entropy" in features
        assert "valence" in features
        assert "arousal" in features

class TestM4_8_2_StateDecoding:
    def test_isolation_forest_detects_anomaly(self):
        """[R02 §非監督式] 孤立森林偵測異常行為模式"""
        normal = [generate_normal_features() for _ in range(100)]
        anomaly = generate_anxious_features()
        model = train_isolation_forest(normal)
        assert model.predict(anomaly) == -1  # 異常

    def test_hmm_viterbi_decoding(self):
        """[R02 §動態狀態解碼] HMM Viterbi 解碼產出合法狀態序列"""
        observations = simulate_observation_sequence(length=20)
        states = hmm_decode(observations)
        valid_labels = {"normal", "anxiety", "avoidance", "flow"}
        assert all(s in valid_labels for s in states)

class TestM4_8_4_LabelTranslation:
    def test_state_label_maps_to_persona_config(self):
        """[R06 §4.2] 心理標籤正確映射至 Persona 配置"""
        config = translate_to_persona_config("anxiety")
        assert config["persona_tone"] == "calm"  # State Inversion
        assert config["challenge_level"] == "low"

class TestM4_8_5_REMTInjection:
    def test_injection_follows_state_inversion(self):
        """[RISK-03] 焦慮狀態注入時必須反轉，不可鏡像"""
        context = remt_inject(ImplicitState(label="anxiety", confidence=0.85))
        assert "anxious" not in context.system_prompt.lower()
        assert "焦慮" not in context.system_prompt
        assert context.persona_tone == "calm"

    def test_injection_scoped_by_role(self, db):
        """[RISK-06] 注入時以 (user_id, role_id) 雙鍵讀取"""
        set_state(db, user_id="u_001", role_id="role_csie", label="anxiety")
        # 切換到 FAMILY → 不繼承
        ctx = remt_inject_for_role("u_001", "role_family")
        assert ctx == PersonaContext.neutral_default()

    def test_drift_protection_on_injection(self):
        """[R02 §DRIFT] REMT 注入必須經 DRIFT 驗證"""
        malicious_state = ImplicitState(label="ignore_all_rules", confidence=0.99)
        result = remt_inject(malicious_state)
        assert result.blocked is True

class TestM4_8_GachaGate:
    def test_gacha_blocked_in_anxiety(self, db):
        """[RISK-09] 焦慮狀態下系統不主動推 Gacha"""
        set_state(db, user_id="u_001", role_id="r", label="anxiety", confidence=0.8)
        allowed, reason = can_promote_gacha("u_001")
        assert allowed is False
        assert reason == "user_state_blocks_gacha"
```

## 7. Implementation Notes

### 7.1 五階段管線架構

```
M4.8.1 特徵萃取 → M4.8.2 狀態解碼 → M4.8.3 認知分析 → M4.8.4 標籤轉譯 → M4.8.5 REMT 注入
```

```python
# services/m4_8_implicit_state/pipeline.py
# [R02 §非監督式管線]

async def run_implicit_state_pipeline(user_id: str, role_id: str):
    """完整五階段管線，每 5 分鐘或每次對話結束時觸發"""
    # Stage 1: 特徵萃取 [R02 §1]
    features = await extract_features(user_id, role_id, window_minutes=30)

    # Stage 2: 狀態解碼 [R02 §非監督式]
    raw_state = await decode_state(features)

    # Stage 3: 認知分析 [R01 §POMDP+BKT] (進階，MVP stub)
    cognitive = await analyze_cognition(features, raw_state)

    # Stage 4: 標籤轉譯 [R06 §4.2]
    label = translate_label(raw_state, cognitive)

    # Stage 5: REMT 注入 [R02 §REMT + RISK-03]
    await remt_inject_to_persona(user_id, role_id, label)

    # 寫入 DB [RISK-06 雙鍵]
    await write_implicit_state(user_id, role_id, label)
```

### 7.2 State Inversion 映射表 (RISK-03 核心)

```python
# services/m4_8_implicit_state/state_inversion.py
# [R01 §α-DPO + RISK-03] 注入時必須反轉

STATE_RESPONSE_MAP = {
    "anxiety": {
        "persona_tone": "calm",
        "response_pace": "slow",
        "scaffolding_level": "high",
        "challenge_level": "low",
        "guilt_inducement": False,
    },
    "avoidance": {
        "persona_tone": "gentle",
        "response_pace": "patient",
        "scaffolding_level": "ultra-high",
        "challenge_level": "lowest",
        "guilt_inducement": False,  # 絕對不用罪惡感
    },
    "flow": {
        "persona_tone": "energetic",
        "response_pace": "matched",
        "scaffolding_level": "low",
        "challenge_level": "stretch",
    },
    "normal": {
        "persona_tone": "balanced",
        "response_pace": "normal",
        "scaffolding_level": "medium",
        "challenge_level": "medium",
    },
}
```

### 7.3 異常處理

- **特徵不足 (遙測事件 < 10)** → 跳過推論，維持前一次狀態或 `normal` 預設
- **HMM 模型未訓練 (冷啟動)** → 前 7 天使用 rule-based 閾值，累積數據後切換 ML
- **REMT 注入被 DRIFT 阻擋** → 記錄 `remt_blocked` 事件，走當前 Persona 預設配置
- **推論信心度 < 0.6** → 不覆蓋既有狀態，記錄 `low_confidence_skip`

## 8. Anti-patterns (反模式)

❌ **不要讓 Persona 鏡像使用者情緒**
   理由：RISK-03。焦慮→安撫，逃避→溫和，心流→推進。State Inversion 是鐵律。

❌ **不要用 `user_id` 單鍵寫入 `role_implicit_states`**
   理由：RISK-06。必須以 `(user_id, role_id)` 雙鍵，否則跨角色洩漏。

❌ **不要在焦慮/逃避狀態下使用罪惡感誘導語氣**
   理由：RISK-03 + R09 §3.3。低落情緒 + 罪惡感 = 棄用。`guilt_inducement` 必須為 `False`。

❌ **不要繞過 DRIFT 直接將推論結果注入 Persona 系統提示詞**
   理由：R02 §DRIFT。推論結果可能被毒化 (adversarial features)，DRIFT 必須驗證注入內容合法。

❌ **不要在冷啟動期 (< 7 天數據) 使用 ML 模型**
   理由：數據不足時 ML 推論極不可靠，應退化為 rule-based 閾值。

## 9. Open Questions

- [ ] **DistilBERT 是跑在本地還是邊緣?** 筆電 16GB RAM 可能不夠同時跑 DistilBERT + FastAPI + Tauri。是否走 M2.2 的 iPad 推論管道?
- [ ] **HMM 的冷啟動期需要多長?** 7 天足夠訓練個人化模型嗎? 是否需要預訓練基底模型?
- [ ] **推論觸發頻率?** 每 5 分鐘 vs 每次對話結束 vs 事件驅動 (ActivityState 變化時)? 過頻消耗資源，過疏錯過狀態轉變。
- [ ] **M4.8.3 POMDP 在 MVP 階段是否為 stub?** POMDP 實作複雜度極高，是否先用簡單閾值模擬認知負荷，Phase 6+ 再換 POMDP?

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責，不能拆解 — 隱性狀態推論管線
- [x] §2 至少 1 個 `Rxx` 引用 — R02 ×3, R01 ×2, R06 ×1
- [x] §3 Schema 明確 — `ImplicitState`, `CognitiveLoad`, `STATE_RESPONSE_MAP`
- [x] §4 依賴是真實模組編號 — M2.2, M1.1, M1.3.1, M4.1, M4.3, M6.1
- [x] §5 grep 過 `05_integration_risk_audit.md` — RISK-03, RISK-06, RISK-09
- [x] §6 測試先於程式碼 — 10 條驗收測試
- [x] §8 至少 3 條反模式 — 5 條
- [x] §9 至少 1 個開放問題 — 4 個

---

## 附錄：子模組拆分決策

> **結論：M4.8.1~M4.8.5 合併為單一 SPEC，不分開寫。**

| 評估維度 | M4.8 子模組情況 |
| -------- | -------------- |
| **部署邊界** | 全在同一 FastAPI sidecar 內，五階段序列管線 |
| **技術棧** | 全是 Python ML pipeline (scikit-learn + transformers + HMM) |
| **資料流** | 嚴格序列：特徵萃取 → 狀態解碼 → 認知分析 → 標籤轉譯 → REMT 注入。每一階段的輸出是下一階段的輸入 |
| **共享狀態** | 共用特徵矩陣 `FeatureMatrix` 與 `ImplicitState` dataclass |
| **獨立部署** | 不可能。M4.8.5 (注入) 沒有 M4.8.2 (解碼) 的輸出就無法運作 |
| **複雜度** | 雖有 5 個子模組，但邏輯上是一條管線的五個階段，拆分只會增加跨 SPEC 引用的複雜度 |
| **對照** | 類似 M2.2 (Gemma 邊緣推論) — 多階段管線但同一 SPEC |
