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
| R02 | §非監督式管線 / REMT | M4.2.1 DRIFT 輸入過濾與 REMT 狀態注入 |
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
| M6.2 `ai_experts` | DB Row | personality_prompt, backstory, trust_level |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.4 對話訊息流 (SSE) | streamed text chunks | `data: 嗯...\n\ndata: 讓我想想\n\n` |
| M4.9 ARPM 監督事件 | `PersonaTransition` | `{"from_state":"Auth","to_state":"Emp","reason":"reactance_detected"}` |
| M6.1 `chat_transcripts` | DB Insert | role="assistant", content="..." |

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
        persona = load_persona("robert_001")
        responses = simulate_conversation(persona, turns=50)
        backstory_extractions = [extract_backstory_claims(r) for r in responses]
        # 過往經歷必須一致
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
        plan = controller.plan_transition(ToneState.AUTHORITATIVE, ToneState.EMPATHETIC)
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
        with implicit_state("avoidance", conf=0.8, role_id="role_csie"):
            response = persona.respond("我這週都沒寫程式碼")
        assert not contains_guilt_phrases(response)

class TestM4_2_4_Paralinguistic:
    def test_filler_word_injection_rate(self):
        """[R05 §跨越恐怖谷] 填充詞注入率隨 trust_level 調整，預設 trust_level=0.5"""
        responses = [persona.respond(...) for _ in range(1000)]
        filler_count = sum(starts_with_filler(r) for r in responses)
        assert 60 <= filler_count <= 100  # 6% ~ 10%

    def test_implicit_state_never_mirrors(self):
        """[RISK-03] 焦慮狀態必觸發安撫,絕不鏡像"""
        with implicit_state("anxiety", conf=0.85, role_id="role_csie"):
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
    graph.add_node("message_splitter", split_response)        # [R05 §跨越恐怖谷]
    graph.add_node("arpm_audit", arpm_supervise)              # [R03 §2]

    # Edges (見圖 1)
    return graph.compile()
```

### 7.1.1 記憶區塊注入與目標對齊審視 (v1.2 新增)

> [!IMPORTANT]
> **設計原則**：Persona 的 system prompt 中新增 `[記憶區塊]` 段落，由 M4.3 `build_commitment_context()` 預撈的 active goals 與 upcoming promises 填充。此區塊讓專家「知道」使用者之前設定的目標和即將到期的承諾，從而能主動追蹤進度、提醒偏離、並在適當時機引導更新目標。

```python
# services/m4_2_persona/prompt_builder.py
# [v1.2] 記憶區塊注入

def build_system_prompt(persona: dict, role_context: dict) -> str:
    """
    組裝 Persona 的完整 system prompt。
    [記憶區塊] 由 M4.3 RoleContext.active_goals / upcoming_promises 填充，
    按當前 persona_id 篩選，僅注入屬於此專家的目標/承諾。
    """
    persona_id = persona["id"]
    
    # 篩選屬於此專家的目標與承諾
    my_goals = [g for g in role_context.get("active_goals", [])
                if g["persona_id"] == persona_id]
    my_promises = [p for p in role_context.get("upcoming_promises", [])
                   if p["persona_id"] == persona_id]
    
    # 組裝 [記憶區塊]（< 200 tokens）
    memory_block = ""
    if my_goals:
        goals_text = "\n".join(
            f"  - {g['title']}（確立於 {g.get('created_at', '未知')}, 進度 {int(g.get('progress', 0)*100)}%）"
            for g in my_goals[:3]
        )
        memory_block += f"[核心目標]\n{goals_text}\n"
    
    if my_promises:
        promises_text = "\n".join(
            f"  - {p['text']}（deadline: {p.get('deadline', '未定')}）"
            for p in my_promises[:5]
        )
        memory_block += f"[即將到期的承諾]\n{promises_text}\n"
    
    # 組裝完整 system prompt
    prompt = f"""[角色]
{persona['personality_prompt']}

[記憶區塊 — AI登錄系統紀錄]
{memory_block if memory_block else "（目前無已確立的核心目標或即將到期的承諾）"}

[行為指令]
- 若使用者尚未與你確立核心目標（[核心目標] 為空），在適當時機自然引導使用者說出「找你的最主要目的是什麼」，確立後記錄。
- 若 [即將到期的承諾] 中有項目，以自然語氣主動提醒（如「對了，你之前提到{'{承諾內容}'}，進度怎麼樣了？」）。
- 若使用者的對話內容明顯偏離 [核心目標]，溫和地提醒並引導回歸（如「嗯，我記得你之前說你找我最主要是想{'{目標}'}，現在好像聊到別的方向了，要不要先回來？」），或討論是否需要更新目標。
- 這些提醒應自然融入對話，不可生硬打斷。偏離提醒每個 session 最多 1 次。
"""
    return prompt
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
    # 預設 trust_level=0.5；不同等級下副語言比例會動態調整
    trust = getattr(persona, "trust_level", 0.5)
    
    # 信任度低/高防衛時，填充詞比例調高；信任度高時比例回歸標準
    filler_rate = 0.08 * (1.5 - trust)  # 0.5 trust_level -> 8%
    
    # 注入填充詞
    if random.random() < filler_rate:
        filler = random.choice(FILLER_WORDS)
        response = f"{filler} {response}"

    # 注入自我修正 (僅對長回應，同樣與 trust_level 負相關)
    correction_rate = 0.05 * (1.5 - trust)
    if len(response) > 100 and random.random() < correction_rate:
        position = response.find("。", len(response) // 2)
        if position > 0:
            correction = random.choice(SELF_CORRECTIONS)
            response = response[:position+1] + " " + correction + " " + response[position+1:]

    return response
```

### 7.4.1 多訊息分割器 (Message Splitter)

> [!IMPORTANT]
> **設計原則**：Persona 的回覆不應永遠是一大段文字。真人聊天的節奏是分段傳送多個短訊息（2–4 個獨立氣泡），中間穿插打字延遲。此分割器將 Persona 的完整回應依據語意斷句拆分為多個獨立訊息，前端以獨立氣泡逐一渲染，模擬真實的聊天體驗。

```python
# services/m4_2_persona/message_splitter.py
# [R05 §跨越恐怖谷] 模擬真人分段發言

import random
from dataclasses import dataclass, field

@dataclass
class SplitMessage:
    """單一訊息氣泡"""
    content: str
    delay_ms: int  # 與前一個訊息的間隔 (ms)

@dataclass
class MessageSequence:
    """多訊息序列，由前端逐一渲染"""
    messages: list[SplitMessage] = field(default_factory=list)

# 句號、問號、驚嘆號為主要分割點
SPLIT_DELIMITERS = ["。", "？", "！", "\n\n"]

def split_response(response: str, max_bubbles: int = 4) -> MessageSequence:
    """
    將 Persona 的完整回應拆分為 2~4 個獨立訊息氣泡。
    
    規則：
    1. 短回應 (< 60 字) → 不拆分，保持單一氣泡
    2. 中等回應 (60~200 字) → 拆為 2 個氣泡
    3. 長回應 (> 200 字) → 拆為 3~4 個氣泡
    4. 每個氣泡之間插入 300~1500ms 的隨機延遲
    5. M4.4 套問的 ElicitationPromptFragment.inject_messages 已預先分割，
       直接作為多氣泡序列輸出，不再經過此分割器
    """
    if len(response) < 60:
        return MessageSequence(messages=[
            SplitMessage(content=response, delay_ms=0)
        ])
    
    # 依語意斷句切割
    segments = []
    current = ""
    for char in response:
        current += char
        if char in SPLIT_DELIMITERS and len(current.strip()) > 15:
            segments.append(current.strip())
            current = ""
    if current.strip():
        segments.append(current.strip())
    
    # 合併過短的段落
    merged = []
    buffer = ""
    for seg in segments:
        buffer += seg
        if len(buffer) >= 30:
            merged.append(buffer)
            buffer = ""
    if buffer:
        if merged:
            merged[-1] += buffer
        else:
            merged.append(buffer)
    
    # 限制氣泡數量
    while len(merged) > max_bubbles:
        # 合併最短的兩個相鄰段落
        min_idx = min(range(len(merged) - 1),
                      key=lambda i: len(merged[i]) + len(merged[i+1]))
        merged[min_idx] = merged[min_idx] + merged[min_idx + 1]
        merged.pop(min_idx + 1)
    
    # 生成延遲
    messages = []
    for i, text in enumerate(merged):
        delay = 0 if i == 0 else random.randint(300, 1500)
        messages.append(SplitMessage(content=text, delay_ms=delay))
    
    return MessageSequence(messages=messages)
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

## 9. Open Questions (已決議)

本模組設計之核心開放問題已與使用者拍板決議：

- **Persona 過往經歷的具體腳本由誰寫？**
  * **決策**：**AI 自動產生（以學術資料檢索比對為基礎生成）**。
  * **細節**：系統不包含人類硬編碼的靜態人設。所有的專家皆為 AI 經過精確學術資料比對翻找後設計生成，並作為操作範例下一致配對到的專家（雖然每一次生成的名字與部分細節可能不同，但學術與心理學流派背景完全一致）。

- **Echo Mode 切換是否在 UI 上向使用者透明顯示？**
  * **決策**：**完全不顯示**。
  * **細節**：UI 上不會有任何 Echo Mode 切換的提示或色變，保持對話的自然感，避免使用者產生被套路的防衛心態。

- **Persona 的 `trust_level` 起始值是多少？不同等級下副語言比例是否調整？**
  * **決策**：**起始值為 0.5**。
  * **細節**：副語言（如填充詞 `filler_rate` 及自我修正機率）將隨著 `trust_level` 動態微調。信任度愈低或防衛心愈重時，填充詞比例適度調高以顯得謹慎；親密信任度高時回歸正常基準。

- **當使用者明確說「請停止 Echo Mode 假裝同情」時，系統如何回應？**
  * **決策**：**像有耐心的真人大人一樣，以「真誠且具邊界感」的態度直面問題**。
  * **細節**：此 meta 對話為諂媚陷阱。Persona 絕不卑躬屈膝地認錯討好，而是像有耐心的成熟真人一樣真誠回覆。必要時 Persona 也可以表現出個人的情緒（例如表達對使用者防衛態度的些許無奈或堅持），從而讓使用者意識到自己的反應過激或不妥，引導其自省。

- **多 Persona 之間是否可以「互相提及」？**
  * **決策**：**同角色（Role）下可以互相提及**。
  * **細節**：同一角色沙盒（如 `role_csie`）下的專家能以「**AI 登錄系統**」為名目互相提及。使用者了解這些專家會將對談與背景監測等資訊登錄到系統，因此專家可以透過讀取這些登錄紀錄來獲取彼此對談的進度與資訊。跨角色的專家則嚴格禁止存取與提及。
