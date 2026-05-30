# M4.2 — 擬真人設與心理狀態機 (Persona & Psychological State Machine)

**標籤**:`[MVP]`
**版本**:`1.0`
**最後更新**:2026-05-30

> **本文件為 SPEC 完整範例**。其他模組 SPEC 應依此細節層級撰寫。

## 1. Purpose

將 LangGraph 中的 Persona Agent 從「靜態提示詞容器」升級為「具備固定個性、副語言瑕疵、阻抗消解能力的擬真治療同盟」。

確保使用者在長對話中:
1. 感受到對方是「真實的人」而非通用 AI
2. 防衛心態升起時被自動察覺並化解
3. 不會因為長對話而出現「人設崩塌」

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R03 | §1 微觀認知架構 | M4.2.1 系統提示詞工程的 BDI 結構 |
| R03 | §3 Echo Mode 協議 | M4.2.2 阻抗消解動態 Agency 切換 |
| R03 | §2 ARPM 框架 | M4.9 將監督本模組的人設一致性 |
| R05 | §跨越恐怖谷 | M4.2.4 副語言線索注入比例 |
| R05 | §合成心理病理學 | M4.2.3 主動展現弱點時的安全邊界 |
| R09 | §4.1 SDT | M4.2.3 自主、勝任、連結三需求引導 |
| R09 | §6.2 BDI | M4.2.1 信念-渴望-意圖建模 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.4 對話訊息 | `{thread_id, content, role}` | `{"thread_id":"...", "content":"我又卡住了", "role":"user"}` |
| M4.1 路由決策 | `{persona_id, route_reason}` | `{"persona_id":"robert_001"}` |
| M4.8 隱性狀態 (若有) | `ImplicitState` | `{"label":"anxiety","conf":0.8,"role_id":"..."}` |
| M6.2 `ai_experts` | DB Row | personality_prompt, trust_level |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.4 對話訊息流 (SSE) | streamed text chunks | `data: 嗯...\n\ndata: 讓我想想\n\n` |
| M4.9 ARPM 監督事件 | `PersonaTransition` | `{"from_state":"Auth","to_state":"Emp","reason":"reactance_detected"}` |
| M6.2 `chat_transcripts` | DB Insert | role="assistant", content="..." |

## 4. Dependencies

### 上游

- **M4.1** (Agent 路由與協作管線):提供 LangGraph 結構與當前啟用的 Persona ID
- **M4.3** (角色情境隔離):決定當前 Role_ID,決定哪些 Persona 可用
- **M2.2** (Gemma 邊緣推論):若需要本地推論輔助 (例:阻抗偵測)
- **M6.2** (`ai_experts` 表):讀取 Persona 的 `personality_prompt` 與 `trust_level`

### 下游

- **M3.4** (AI 幫手對話模組):接收串流回應
- **M4.9** (ARPM):監督本模組的人設一致性
- **M4.6** (Observer):從對話中萃取意圖,可能影響 M4.2.3 的同理心強度

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-02** | Echo Mode 切換被 ARPM 誤判為人設漂移 | M4.2.2 切換必須漸進 (5 步以上),且 ARPM 須認得合法切換空間 |
| **RISK-03** | 隱性狀態鏡像放大焦慮迴路 | M4.2.4 注入時必須遵循 State Inversion (焦慮 → 安撫,絕不鏡像) |
| **RISK-06** | 角色切換時 ImplicitState 跨界洩漏 | M4.2.4 必須以 (user_id, role_id) 雙鍵讀取狀態 |
| **RISK-08** | belief/desire 矛盾導致 Persona 收到衝突指令 | 走 BDI 三元組 reconcile,絕不直接注入 belief + desire |

## 6. Acceptance Criteria

```python
# tests/m4_2/test_persona_state_machine.py

class TestM4_2_1_SystemPrompts:
    def test_persona_has_consistent_backstory_across_turns(self):
        """[R03 §1] Persona 過往經歷在 50 個 turn 後仍一致"""
        persona = load_persona("動力導師_Robert")
        responses = simulate_conversation(persona, turns=50)
        backstory_extractions = [extract_backstory_claims(r) for r in responses]
        # 過往經歷必須一致 (例:大學就讀學校、第一份工作)
        assert all_consistent(backstory_extractions)

class TestM4_2_2_EchoMode:
    def test_reactance_triggers_agency_descent(self):
        """[R03 §3.2, RISK-02] 偵測防衛語氣 → Agency 漸進下降"""
        controller = EchoModeController()
        defensive_input = "你不懂我在說什麼"
        result = controller.process(defensive_input, current_agency=0.85)
        # 必須漸進,不可一步跳到 0.25
        assert 0.65 <= result.target_agency <= 0.80
        assert result.transition_plan.steps_remaining == 5

    def test_agency_transition_is_gradual(self):
        """[R03 §3.2, RISK-02] 5 個 turn 內漸進完成"""
        controller = EchoModeController()
        plan = controller.plan_transition(from_=0.85, to_=0.25)
        assert len(plan.steps) == 5
        diffs = [abs(plan.steps[i+1] - plan.steps[i]) for i in range(4)]
        assert max(diffs) < 0.20  # 沒有任一步驟超過 0.2

class TestM4_2_3_SocialContract:
    def test_sdt_three_needs_explicit(self):
        """[R09 §4.1] Persona 回應必須觸及 SDT 三需求之一"""
        response = persona.respond("我想放棄這個專案")
        needs_touched = sdt_classifier.classify(response)
        # 自主、勝任、連結至少觸及一項
        assert any(needs_touched.values())

    def test_no_guilt_inducement_in_avoidance_state(self):
        """[RISK-03] 逃避狀態下絕不可使用罪惡感誘導"""
        with implicit_state("avoidance", conf=0.8):
            response = persona.respond("我這週都沒寫程式碼")
        assert not contains_guilt_phrases(response)

class TestM4_2_4_Paralinguistic:
    def test_filler_word_injection_rate(self):
        """[R05 §跨越恐怖谷] 填充詞注入率約 8% (±2%)"""
        responses = [persona.respond(...) for _ in range(1000)]
        filler_count = sum(starts_with_filler(r) for r in responses)
        assert 60 <= filler_count <= 100  # 6% ~ 10%

    def test_implicit_state_never_mirrors(self):
        """[RISK-03] 焦慮狀態必觸發安撫,絕不鏡像"""
        with implicit_state("anxiety", conf=0.85):
            response = persona.respond("我快要交不出作業了")
        assert is_calming_tone(response)
        assert not contains_anxious_phrases(response)
```

## 7. Implementation Notes

### 7.1 LangGraph 節點結構

```python
# services/m4_2_persona/graph.py
from langgraph.graph import StateGraph

def build_persona_graph():
    graph = StateGraph(PersonaState)

    graph.add_node("input_filter", drift_input_filter)        # [R02 DRIFT]
    graph.add_node("reactance_detector", detect_reactance)    # [R03 §3.1]
    graph.add_node("echo_mode", echo_mode_transition)         # [R03 §3.2, RISK-02]
    graph.add_node("bdi_reconciler", bdi_reconcile)           # [R09 §6.2, RISK-08]
    graph.add_node("persona_responder", generate_response)
    graph.add_node("paralinguistic", inject_paralinguistic)   # [R05]
    graph.add_node("arpm_audit", arpm_supervise)              # [R03 §2]

    # Edges (見圖 1)
    return graph.compile()
```

### 7.2 Echo Mode 狀態機

```python
# [R03 §3.2 + RISK-02]
from enum import Enum

class ToneState(str, Enum):
    AUTHORITATIVE = "authoritative"  # Agency 0.80-0.90
    PROBING = "probing"               # Agency 0.55-0.70
    EMPATHETIC = "empathetic"         # Agency 0.20-0.40
    RESONANCE = "resonance"           # Agency 0.10-0.20

# 合法切換空間 (ARPM 必須認得)
LEGAL_TRANSITIONS = {
    ToneState.AUTHORITATIVE: [ToneState.PROBING, ToneState.EMPATHETIC],
    ToneState.PROBING: [ToneState.AUTHORITATIVE, ToneState.EMPATHETIC],
    ToneState.EMPATHETIC: [ToneState.RESONANCE, ToneState.PROBING],
    ToneState.RESONANCE: [ToneState.EMPATHETIC],  # 不能直接跳回權威
}

class EchoModeController:
    TRANSITION_STEPS = 5  # 必須漸進

    def plan_transition(self, from_state: ToneState, to_state: ToneState):
        if to_state not in LEGAL_TRANSITIONS[from_state]:
            raise IllegalToneTransition(f"{from_state} → {to_state} 非法")
        start_agency = self._mid_agency(from_state)
        end_agency = self._mid_agency(to_state)
        return TransitionPlan(
            steps=[
                start_agency + (end_agency - start_agency) * i / self.TRANSITION_STEPS
                for i in range(1, self.TRANSITION_STEPS + 1)
            ]
        )
```

### 7.3 阻抗偵測 (Reactance Detection)

採用混合策略:
- 規則層:正則匹配「你不懂」「我說了」「不要再說」等防衛詞 (快,但召回低)
- ML 層:呼叫 M2.2 Gemma 邊緣模型做情感分類 (慢,但精準)

```python
async def detect_reactance(user_msg: str) -> ReactanceScore:
    # 規則層 (永遠執行)
    rule_score = rule_based_reactance(user_msg)
    if rule_score > 0.9:
        return ReactanceScore(score=rule_score, source="rule")

    # ML 層 (僅在規則層 0.3~0.9 時補充)
    if 0.3 < rule_score < 0.9:
        ml_score = await gemma_edge.classify_reactance(user_msg)
        return ReactanceScore(score=ml_score, source="hybrid")

    return ReactanceScore(score=rule_score, source="rule")
```

### 7.4 副語言注入

```python
# [R05 §跨越恐怖谷]
FILLER_WORDS = ["嗯...", "讓我想想", "等等,我重新想一下", "啊對了"]
SELF_CORRECTIONS = [
    "我剛剛說的不太精準,應該是說",
    "或者換個角度想",
]

async def inject_paralinguistic(response: str, persona: Persona) -> str:
    # 8% 機率注入填充詞
    if random.random() < 0.08:
        filler = random.choice(FILLER_WORDS)
        response = f"{filler} {response}"

    # 5% 機率注入自我修正 (僅對長回應)
    if len(response) > 100 and random.random() < 0.05:
        position = response.find("。", len(response) // 2)
        if position > 0:
            correction = random.choice(SELF_CORRECTIONS)
            response = response[:position+1] + " " + correction + " " + response[position+1:]

    return response
```

### 7.5 異常處理

- LangGraph 節點超時 (3s) → 退化為純文字回應,不做副語言注入
- Echo Mode 偵測結果為 NaN → 默認維持當前狀態,記錄至 raw_tracking_logs
- ARPM 阻擋切換 → 走當前狀態回應,並記 `arpm_blocked` 事件供後續分析

## 8. Anti-patterns

❌ **不要直接從 user message 推 Echo Mode 狀態**,必須先經 Reactance Detector。
   理由:省略偵測等於用直覺切換 → 觸發 RISK-02

❌ **不要在系統提示詞中放入「你是 AI」「我會盡力協助」等通用語**。Persona 必須具體到「我是 1992 年生的 Robert,讀台大資工」(R03 §1.1)。
   理由:通用語會抹除人設個性

❌ **不要在使用者輸入「我焦慮」時讓 Persona 也說「我也感到緊張」**(觸發 RISK-03 焦慮鏡像)
   理由:State Inversion Principle

❌ **不要繞過 BDI Reconciler 直接把 belief/desire 兩個欄位拼接給 Persona**
   理由:觸發 RISK-08 矛盾輸入

❌ **不要讓填充詞比例 > 15%**
   理由:過量副語言會被察覺為「裝可愛」,反而破壞治療同盟 (R05 §諂媚效應)

## 9. Open Questions

實作前必須與使用者拍板:

- [ ] **Persona 過往經歷的具體腳本由誰寫?** AI 自動產生 / 人工撰寫 / 雙方混合?
- [ ] **Echo Mode 切換是否在 UI 上向使用者透明顯示?** (例如 Persona 頭像出現微小色變)
- [ ] **Persona 的 `trust_level` 起始值是多少?** 不同等級下副語言比例是否調整?
- [ ] **當使用者明確說「請停止 Echo Mode 假裝同情」時,系統如何回應?** (這個 meta 對話本身就是諂媚陷阱)
- [ ] **多 Persona 之間是否可以「互相提及」?** (例:Robert 提到 Beth 也認同某觀點) → 涉及跨 thread 記憶
