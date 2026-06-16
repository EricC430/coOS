# 整合風險稽核 (Integration Risk Audit)

> 本文件記錄「**單獨運作正確,但合併後效果變差或互相衝突**」的模組組合。
>
> Claude Code 任務涉及 2 個以上模組時,**必須先 grep 本文件**確認是否觸發風險。
>
> 每條風險都有:`觸發組合 → 失效機制 → 緩解策略 → 驗收測試`。

---

## RISK-01:草稿與核准 + XP 自動結算 → IKEA 效應失效

**觸發組合**:`M3.3.3 (Draft & Approve) + M4.5 (XP 自動結算)`

**失效機制**:

M4.5 設計為「使用者只需正常做事,系統自動發 XP」(零摩擦)。M3.3.3 設計為「強制使用者核准草稿才能拿 XP」(刻意摩擦)。兩者並存時,若 M4.5 從 `raw_tracking_logs` 直接結算,會在 M3.3.3 還沒核准前就把 XP 入帳,導致使用者點開草稿時看到 XP 已發 → 失去 IKEA 效應 → 草稿變成可選 → 心理所有權喪失。

**研究衝突點**:R08 §六.1 (IKEA 效應) vs (產品架構 §2.4 零摩擦)

**緩解策略**:

明確 XP 分流為兩類:

| XP 類別 | 觸發 | 模組 |
| ------- | ---- | ---- |
| **Earned XP** (主流) | 必須 `is_reviewed = true` | M4.5 ← M3.3.3 |
| **Ambient XP** (微量) | 純粹的存在獎勵 (如連續登入) | M4.5 直接,額度極小 (≤5% 每日總 XP) |

M4.5 守門員邏輯:

```python
# [R08 §六.1] Earned XP 必須等核准
if reflection.is_draft:
    return XPGrantDenied("draft_not_approved")
if reflection.is_reviewed and reflection.user_feeling and reflection.user_action_plan:
    grant_xp(reflection.calculate_earned_xp())
```

**驗收測試**:

```python
def test_xp_blocked_without_approval():
    """RISK-01: 草稿狀態下 XP 必不發放"""
    log = create_raw_tracking_log(activity_minutes=120)
    draft = generate_draft_from(log)
    assert draft.is_draft is True
    xp_before = user.current_xp
    run_xp_settlement_cron()
    assert user.current_xp == xp_before  # 應毫無變化
```

---

## RISK-02:Echo Mode + ARPM → 認定 Persona 漂移而還原

**觸發組合**:`M4.2.2 (Echo Mode) + M4.9 (ARPM)`

**失效機制**:

Echo Mode 設計為動態切換 Agency (0.85 → 0.25),用於阻抗消解。ARPM 設計為偵測「人設崩塌」並強制還原。當 Echo Mode 將 Persona 從「權威」切到「共情」時,ARPM 可能誤判為人設漂移,把 Persona 強拉回原本的權威語氣 → 阻抗加劇 → 使用者更防衛。

**研究衝突點**:R03 §3.3 (Echo Mode 漸進切換) vs R03 §2 (ARPM 嚴格還原)

**緩解策略**:

ARPM 必須**讀取 Echo Mode 的當前授權狀態**,在 Echo Mode 授權的範圍內視「切換」為合法。實作上:

```python
# [R03 §3.4] ARPM 必須認識 Echo Mode 的合法狀態空間
class ARPMValidator:
    LEGAL_TRANSITIONS = {
        "Authoritative": ["Empathetic", "Probing"],  # 合法切換目標
        "Empathetic": ["Authoritative", "Resonance"],
    }

    def validate(self, prev_persona_state, current_persona_state, echo_mode_authorized: bool):
        if echo_mode_authorized:
            target_state = current_persona_state.tone_label
            if target_state in self.LEGAL_TRANSITIONS.get(prev_persona_state.tone_label, []):
                return ValidationResult.LEGAL  # 不還原
        # 否則才走原本的漂移偵測
        return self.detect_drift(prev_persona_state, current_persona_state)
```

Echo Mode 切換必須符合 R03 §3.2 的**漸進原則** (5 個 turn 完成,不可一步跳變),否則 ARPM 仍會判定漂移。

**驗收測試**:

```python
def test_echo_mode_passes_arpm():
    """RISK-02: Echo Mode 切換不應觸發 ARPM 還原"""
    persona = create_persona("動力導師_Robert", base_tone="Authoritative")
    arpm = ARPMValidator(persona)
    for turn in echo_mode_gradient(from_="Authoritative", to_="Empathetic", steps=5):
        result = arpm.validate(prev=persona.last_state, current=turn, echo_mode_authorized=True)
        assert result == ValidationResult.LEGAL
```

---

## RISK-03:隱性狀態推論 + Persona 注入 → 焦慮鏡像放大迴路

**觸發組合**:`M4.8 (隱性狀態推論) + M4.2.4 (REMT Persona 注入)`

**失效機制**:

M4.8 偵測使用者「焦慮」→ M4.2.4 將「焦慮」注入 Persona 的 Prompt context → Persona 可能因此語氣變焦慮 (鏡像) → 使用者察覺 → 焦慮升級 → M4.8 再次偵測到更高焦慮 → 鏡像更強... **正回饋迴路**,可能導致使用者 30 分鐘內崩潰退出。

**研究衝突點**:R02 §動態提示轉換 (注入推論狀態) vs R01 §α-DPO (面對挫折擴張獎勵邊界、強制安撫)

**緩解策略**:

M4.2.4 必須遵循**狀態反轉原則** (State Inversion Principle):

```python
# [R01 §α-DPO + R02 §REMT] 注入時必須反轉,不可鏡像
STATE_RESPONSE_MAP = {
    "anxiety": {
        "persona_tone": "calm",
        "response_pace": "slow",
        "scaffolding_level": "high",     # 提供更多支持
        "challenge_level": "low",         # 降低挑戰
    },
    "avoidance": {
        "persona_tone": "gentle",
        "response_pace": "patient",
        "scaffolding_level": "ultra-high",
        "challenge_level": "lowest",
        "guilt_inducement": False,       # 絕對不能用罪惡感
    },
    "flow": {
        "persona_tone": "energetic",
        "response_pace": "matched",
        "scaffolding_level": "low",
        "challenge_level": "stretch",     # 推進挑戰
    },
}

def inject_persona_context(implicit_state: str) -> PersonaContext:
    # [RISK-03] 絕對禁止 mirror 模式
    response_config = STATE_RESPONSE_MAP[implicit_state]
    return PersonaContext(**response_config)
```

**強制守門員**:DRIFT 層 (M4.1.4) 必須驗證注入的 Persona Context **不包含**使用者當前狀態的鏡像描述。

**驗收測試**:

```python
def test_anxiety_state_triggers_calm_persona():
    """RISK-03: 焦慮狀態必須觸發安撫,絕不鏡像"""
    state = ImplicitState(label="anxiety", confidence=0.85)
    context = inject_persona_context(state.label)
    assert context.persona_tone == "calm"
    assert "anxious" not in context.system_prompt.lower()
    assert "焦慮" not in context.system_prompt
```

---

## RISK-04:Defer-to-Breakpoint + 即時 XP 慶祝 → 動機脫節

**觸發組合**:`M1.2 (斷點偵測) + M3.x (XP 即時回饋動畫)`

**失效機制**:

M1.2 設計為延遲所有通知至「任務斷點」才推送。但 Gacha 抽卡、徽章解鎖等遊戲化獎勵需要**即時回饋**才有多巴胺效應。若兩者一刀切應用 Defer-to-Breakpoint,使用者抽完卡 30 分鐘後才看到結果 → 失去因果連結 → 變動比例增強失效。

**研究衝突點**:R08 §二 (Defer-to-Breakpoint) vs (產品架構 §2.5 變動比例增強)

**緩解策略**:

通知三層分類,各自走獨立通道:

| 類別 | 範例 | 是否 Defer | 通道 |
| ---- | ---- | ---------- | ---- |
| **L1 即時慶祝** | Gacha 結果、徽章解鎖 | ❌ **不 Defer** (使用者主動觸發後就應立刻看到) | Toast (1.5s) + 視覺特效 |
| **L2 系統洞察** | 反思草稿、行為觀察 | ✅ **必 Defer** | 通知儀表板 (M3.9) |
| **L3 安全警示** | CARE 安全資源、隱私警告 | ❌ **不 Defer** | Modal,強制中斷 |

判定原則:**使用者主動發起的動作** → L1 即時;**系統主動推送的內容** → L2 deferred;**安全相關** → L3 強制。

**驗收測試**:

```python
def test_gacha_result_immediate():
    """RISK-04: 使用者觸發的 Gacha 必須即時顯示"""
    response = client.post("/api/m3_11/draw_card")
    assert response.headers["X-Defer-Strategy"] == "immediate"
    assert "BREAKPOINT_REQUIRED" not in response.json()["delivery"]

def test_observer_insight_deferred():
    """RISK-04: 系統主動產出的洞察必須 Defer"""
    insight = observer_agent.emit_insight(...)
    assert insight.delivery_strategy == "defer_to_breakpoint"
```

---

## RISK-05:語意壓縮 + GraphRAG → 因果邊精度崩潰

**觸發組合**:`M2.2 (Gemma 邊緣壓縮) + M5.1 (薩提爾冰山圖譜) + M5.2 (NSVIF)`

**失效機制**:

M2.2 將原始程式碼壓縮為意圖向量 (壓縮率約 50-100x)。M5.1 用意圖向量在 Neo4j 建立節點與邊。但意圖向量丟失了具體變數名稱、具體錯誤、具體挫折時刻 → M5.1 建立的 `(Behavior)-[REFLECTS]->(CopingStance)` 邊可能基於誤解 → M5.2 NSVIF 嘗試反溯因驗證時找不到對應 raw_log (因為只有意圖向量) → 無法驗證 → 大量邊被丟棄 → 圖譜空洞化。

**研究衝突點**:R07 §4 (壓縮為意圖向量) vs R04 §反溯因驗證 (需對照具體事實)

**緩解策略**:

NSVIF 反溯因驗證**必須走本地 raw_log 路徑**,而**不是**從雲端意圖向量回推:

```python
# [R04 §反溯因 + R07 §POST] NSVIF 必須使用本地 SQLite 的 raw_text
class NSVIFValidator:
    async def validate_edge(self, edge: GraphEdge):
        # 雲端 Neo4j 只儲存 edge metadata 與 source_log_id
        source_log_id = edge.metadata["source_log_id"]

        # 對照本地 raw_text (絕不出本機)
        raw_log = await local_sqlite.get_raw_log(source_log_id)
        if not raw_log:
            return ValidationResult.REJECTED  # 沒有原始證據 → 丟棄邊

        # 在本地用較小的模型做反溯因
        evidence_supports = await local_abductive_check(edge, raw_log.raw_text)
        return ValidationResult.ACCEPTED if evidence_supports else ValidationResult.REJECTED
```

這意味 M5.1 寫入 Neo4j 邊時,**必須記錄 `source_log_id`**,讓後續驗證可以回本地找原文。

**驗收測試**:

```python
def test_nsvif_uses_local_raw_text():
    """RISK-05: 反溯因驗證必須走本地路徑,不可只看雲端意圖向量"""
    edge = create_satir_edge(source_log_id="log_abc123")
    with patch("local_sqlite.get_raw_log") as mock_local:
        with patch("neo4j.fetch_intent_vector") as mock_cloud:
            nsvif_validator.validate_edge(edge)
            mock_local.assert_called_with("log_abc123")
            mock_cloud.assert_not_called()  # 雲端意圖向量不應被讀
```

---

## RISK-06:動態 Persona 注入 + 角色情境隔離 → 跨角色資料洩漏

**觸發組合**:`M4.2.4 (REMT Persona 注入) + M4.3 (角色情境隔離)`

**失效機制**:

M4.3 規定:角色 A (CSIE) 的資料庫資料絕不洩漏到角色 B (FAMILY)。M4.2.4 動態注入「使用者當前狀態」到 Persona context。若使用者在 CSIE 角色被偵測為「焦慮」,然後切換到 FAMILY,M4.2.4 可能仍把焦慮狀態注入 FAMILY 的 Persona → 角色狀態跨越了沙盒邊界 → 違反 M4.3 隔離。

**研究衝突點**:R02 §REMT (狀態動態注入) vs (架構文件 §角色沙盒)

**緩解策略**:

ImplicitState 必須**綁定 Role_ID**,且 M4.2.4 注入時必須以**當前角色**為 key:

```python
# [M4.3 + R02 §REMT] Implicit State 必須是 (user_id, role_id) 雙鍵
class ImplicitState:
    user_id: UUID
    role_id: UUID  # ← 強制綁定
    label: str
    confidence: float
    inferred_at: datetime

# 注入時必須匹配當前角色
async def inject_persona_context(user_id: UUID, current_role_id: UUID):
    state = await fetch_implicit_state(user_id=user_id, role_id=current_role_id)
    # 找不到 → 用該角色的中性預設,不繼承其他角色的狀態
    if not state:
        return PersonaContext.neutral_default()
    return inject(state)
```

優先順序:**M4.3 (隔離)** > **M4.2.4 (動態注入)**。角色切換後若無新角色的狀態資料,寧可用中性預設,不要跨界繼承。

**驗收測試**:

```python
def test_role_switch_clears_implicit_state_injection():
    """RISK-06: 切換角色後不可繼承上一個角色的隱性狀態"""
    user.switch_role("CSIE")
    inject_implicit_state(user, role="CSIE", label="anxiety")
    user.switch_role("FAMILY")
    context = build_persona_context(user)
    assert "anxiety" not in context.injected_state_labels
```

---

## RISK-07:ZPD 任務池 + 損失規避 XP 質押 → 複合挫敗

**觸發組合**:`M4.11 (ZPD 任務池) + M4.13 (XP 質押)`

**失效機制**:

M4.11 設計 ZPD 任務的失敗機率約 30-50% (這是 ZPD 的定義,挑戰應該夠難)。M4.13 設計 XP 質押的「沒有退路」懲罰機制。若使用者對一個 ZPD 任務做了 XP 質押,然後正常地 (約 40% 機率) 失敗 → 扣 XP → 加上 ZPD 失敗本身的挫敗 → 複合打擊 → R01 §Dropout 危機 → 棄用。

**研究衝突點**:R01 §ZONE 框架 (ZPD 挑戰應夠難) vs R01 §α-DPO (失敗時應退縮、重建自信)

**緩解策略**:

**XP 質押僅開放給 high-confidence 區的任務** (使用者主觀預估成功率 ≥ 70%):

```python
# [R01 §REJECT + α-DPO] 質押任務必須先通過信心過濾
def can_stake_on_task(task: Task, user_estimated_success: float) -> bool:
    if user_estimated_success < 0.70:
        return False  # 拒絕質押
    if task.zpd_zone == "edge":  # 邊緣 ZPD 不可質押
        return False
    return True
```

**ZPD 探索任務** (失敗機率 30-50% 的) 應走**非質押的盲盒抽卡**機制 (M3.11),失敗只損失抽卡成本,不損失累積資產。

**驗收測試**:

```python
def test_edge_zpd_blocks_staking():
    """RISK-07: 邊緣 ZPD 任務不可質押"""
    task = generate_zpd_task(zone="edge", success_prob=0.4)
    with pytest.raises(StakingForbidden):
        stake_xp(task=task, amount=100)
```

---

## RISK-08:Observer 推論 + ToM 信念追蹤 → 矛盾 Persona 輸入

**觸發組合**:`M4.6 (Observer Agent) + R05 ToM 信念追蹤 (隱含於 M4.2)`

**失效機制**:

M4.6 Observer 從對話表面推論「使用者想做 X」。R05 ToM 從更深層的信念追蹤「使用者相信自己有能力 Y」。兩者可能矛盾:
- Observer: 「使用者想完成 OpenStack 部署」
- ToM: 「使用者相信自己不會雲端架構」

若兩者都同時注入 Persona,Persona 收到「使用者想做但相信做不到」→ 容易給出**矛盾建議** (鼓勵 + 質疑同時出現),引發認知失調。

**研究衝突點**:R02 §動態狀態 (表面推論) vs R05 §信念追蹤 (深層信念)

**緩解策略**:

引入**信念-意圖優先序**:

```python
# [R05: 第三章 + R09: BDI 框架] 統一以 BDI 三元組整合
@dataclass
class BDIState:
    belief: str       # ToM 推論的信念 (深層)
    desire: str       # Observer 推論的意圖 (表面)
    intention: str    # 整合後的可行意圖 (供 Persona 使用)

def reconcile(belief: str, desire: str) -> str:
    """[R09 §BDI] 信念與渴望矛盾時,intention 必須先承認信念,再橋接渴望"""
    if contradicts(belief, desire):
        # 例:"我想做 OpenStack" + "我不懂雲端" → "從 K8s 基礎開始累積"
        return bridge(belief, desire)
    return desire
```

**永遠不要直接把 (belief, desire) 兩個獨立欄位丟給 Persona**。先 reconcile 成 intention。

**驗收測試**:

```python
def test_contradictory_bdi_resolution():
    """RISK-08: 矛盾的 belief/desire 應產出橋接型 intention"""
    bdi = reconcile(
        belief="不懂雲端架構",
        desire="完成 OpenStack 部署"
    )
    assert "從...開始" in bdi or "逐步" in bdi or "先" in bdi
```

---

## RISK-09:Gacha + 焦慮狀態 → 上癮輔助焦慮

**觸發組合**:`M3.11 (Gacha 抽卡) + M4.8 (焦慮狀態偵測)`

**失效機制**:

變動比例增強是強烈的多巴胺刺激。當使用者處於焦慮狀態,焦慮 + 賭博式增強 = **病態使用風險** (見 R09 §3.3 Replika 案例)。若 Gacha 在焦慮狀態下推播,可能加劇焦慮型上癮。

**研究衝突點**:(產品架構 §2.5) vs R09 §3.3 (病態使用)

**緩解策略**:

Gacha **必須讀 M4.8 的隱性狀態**並做封鎖:

```python
# [R09 §3.3] Gacha 推播門禁
async def can_promote_gacha(user_id: UUID) -> Tuple[bool, str]:
    state = await m4_8.get_current_implicit_state(user_id)
    if state.label in ("anxiety", "avoidance", "depression"):
        return False, "user_state_blocks_gacha"
    if state.confidence < 0.6:
        return True, "low_confidence_allow"
    # 連續抽卡計數
    recent_draws = await count_recent_draws(user_id, window_hours=1)
    if recent_draws >= 5:
        return False, "compulsive_behavior_pattern"
    return True, "ok"
```

**主動的抽卡按鈕** (使用者按下) 可以放行但顯示提示;**被動推播的抽卡邀請** (系統主動) 在焦慮狀態下絕對不送。

**驗收測試**:

```python
def test_gacha_blocked_in_anxiety():
    """RISK-09: 焦慮狀態下系統不主動推 Gacha"""
    set_implicit_state(user, "anxiety", confidence=0.8)
    promotions = await get_active_promotions(user)
    assert not any(p.type == "gacha_invite" for p in promotions)
```

---

## RISK-10:Wrapped Insights + 低 mood_score → Gaslighting 感

**觸發組合**:`M3.8 (Wrapped 彈窗) + daily_reports.mood_score 低`

**失效機制**:

Wrapped 模式以慶祝口吻呈現「本週動力指數提升 20%」。但若使用者本週 mood_score 平均為 2/10 (低落),20% 的相對提升仍在低點。把這呈現為「成就」會讓使用者覺得系統不理解自己 → 信任崩潰 → 棄用。

**研究衝突點**:R10 §敘事化福祉 (Wrapped 樂觀敘事) vs R05 §諂媚效應 (避免不真實的正向)

**緩解策略**:

Wrapped 模板必須**先讀絕對水平**,再決定敘事框架:

```python
# [R05 §諂媚效應] Wrapped 不能虛假樂觀
def generate_wrapped_narrative(metrics: WeeklyMetrics) -> str:
    if metrics.mood_score_avg < 4:
        # 低落週:不慶祝,以陪伴口吻
        return f"這週你撐過來了。雖然心情平均 {metrics.mood_score_avg:.1f},但你還是完成了 {metrics.tasks_done} 項任務。"
    if metrics.mood_score_avg >= 7:
        # 高昂週:可慶祝
        return f"動力滿格的一週!動力指數提升 {metrics.motivation_delta:.0%},繼續保持。"
    # 中性週:平實呈現
    return f"這週你完成了 {metrics.tasks_done} 項任務,動力穩定。"
```

絕對禁止把相對提升 (20%) 抽離絕對水平 (2/10) 單獨呈現。

**驗收測試**:

```python
def test_low_mood_wrapped_no_celebration():
    """RISK-10: 低落週 Wrapped 不可使用慶祝詞彙"""
    metrics = WeeklyMetrics(mood_score_avg=2.5, motivation_delta=0.20)
    narrative = generate_wrapped_narrative(metrics)
    forbidden = ["恭喜", "提升", "突破", "滿格", "棒"]
    for word in forbidden:
        assert word not in narrative
```

---

## RISK-11:語音輸入 + 本地優先 → RAM 爆炸

**觸發組合**:`M3.4.3.3 (語音意識流) + 系統架構 (本地優先)`

**失效機制**:

筆電 16GB RAM 已被 Tauri (~500MB) + FastAPI sidecar (~800MB) + 前端 (~600MB) + SQLite + 瀏覽器佔走大半。若語音輸入跑 Whisper-large (1.5GB) 本地推論,RAM 不足 → swap → 對話卡頓 → R05 治療同盟受損。

若走雲端 Whisper API,使用者意識流 (含敏感想法) 直接上雲 → 違反 L1 明文不上雲。

**研究衝突點**:R07 §1.1 (端側 RAM 限制) vs (系統架構 §1 隱私) vs R10 §語音輸入

**緩解策略**:

採用**三級降級策略**:

```python
# [R07 §1.1] RAM 預算門檻
class VoiceTranscriptionRouter:
    async def transcribe(self, audio_bytes: bytes) -> str:
        ram_available = psutil.virtual_memory().available
        if ram_available > 3 * 1024**3:  # > 3GB
            return await self.local_whisper_base(audio_bytes)  # 39M params
        if ram_available > 1.5 * 1024**3:  # > 1.5GB
            return await self.local_whisper_tiny(audio_bytes)  # 8M params,降精度
        # RAM 太緊
        if user.privacy_consent_voice_cloud:
            return await self.cloud_whisper_with_consent(audio_bytes)
        return await self.queue_for_later(audio_bytes)  # 排隊到斷點再處理
```

任何上雲必須**先取得明確同意**,且記錄在 `user_consents` 表。

**驗收測試**:

```python
def test_voice_never_cloud_without_consent():
    """RISK-11: 沒有明確同意絕不走雲端轉錄"""
    user.privacy_consent_voice_cloud = False
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.available = 500 * 1024**2  # 極低 RAM
        result = voice_router.transcribe(audio_bytes)
        assert isinstance(result, QueuedForLater)
```

---

## RISK-12:Social Posts 公開 + 邊緣推論結果 → 隱私側通道洩漏

**觸發組合**:`M3.7 (社群動態牆) + M4.6 Observer + M2.2 邊緣推論`

**失效機制**:

社群動態牆會自動推播「Boyu 達成了 ... 成就」。若這條成就是 Observer Agent 從邊緣意圖向量推論出來的 (例如:「持續解 RL 題目 30 天」),雖然意圖向量不上雲,但**推論結果**作為貼文上雲了 → 從貼文可以反推回原始行為模式 → **側通道洩漏 (Side-channel Leak)**。

**研究衝突點**:R07 §5 (隱私防禦) vs (產品架構 §2.6 社群)

**緩解策略**:

**社群貼文絕對需要使用者手動核准**,且必須提示「將公開的具體內容」:

```python
# [R07 §5 + R08 §草稿與核准] 社群貼文走嚴格的核准流程
async def propose_social_post(achievement: Achievement):
    # 系統不直接發布,只生成草稿
    post_draft = SocialPostDraft(
        content=achievement.public_description,
        revealed_metrics=achievement.metrics_to_show,  # 透明列出
        privacy_warning="此貼文將公開以下資訊: ..."  # 強制顯示
    )
    return post_draft  # 等使用者按下 publish 才寫入
```

並且,**Observer Agent 推論出的成就**(自動產生) 預設為**僅自己可見** (`visibility="private"`),除非使用者主動切換為公開。

**驗收測試**:

```python
def test_observer_inferred_achievements_default_private():
    """RISK-12: Observer 自動發現的成就預設不公開"""
    achievement = observer_agent.detect_achievement(...)
    assert achievement.default_visibility == "private"
    post_draft = propose_social_post(achievement)
    assert post_draft.requires_explicit_publish is True
```

---

## 用法總結

每次 Claude Code 任務涉及 ≥2 個模組,執行流程:

```bash
# 1. 找出觸發了哪些風險
grep -E "(M4\.2|M4\.3|M4\.8)" docs/05_integration_risk_audit.md

# 2. 對每條觸發的 RISK-xx 確認:
#    - 緩解策略是否在程式碼中體現
#    - 驗收測試是否已寫並通過

# 3. Commit message 引用
git commit -m "feat(M4.8+M4.2.4): 隱性狀態注入 Persona [R02 §REMT, RISK-03 緩解]"
```

## RISK-13:每日反思 Segment 刪除 → 反思無法完成

**觸發組合**:`M6.4 (Segment 子表化) + M6.5 (ACID 交易) + 資料清理 / 使用者刪除`

**失效機制**:

M6.4 Refinement 將 `daily_reflections` 分解為父表 + 多個 `daily_reflection_segments` 子表。父表 `is_completed` 標記為「至少一個 segment 被核准」。若:
1. 使用者核准了 Segment A
2. 父表標記為 `is_completed = true`，XP 已結算
3. 後續 Segment A 被使用者或系統刪除（如清理重複）

則父表失去「完成」的根據，卻已發放 XP → XP 記錄與狀態不一致。

**研究衝突點**:R08 §六.1 (IKEA 效應 XP 發放原子性) vs 使用者修正權

**緩解策略**:

採用**軟刪除 + 狀態鎖定**:

```sql
-- 修改 daily_reflection_segments
ALTER TABLE daily_reflection_segments 
ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE,
ADD COLUMN deleted_at TIMESTAMPTZ;

-- 刪除時標記為軟刪除，但不真正移除
UPDATE daily_reflection_segments 
SET is_active = FALSE, deleted_at = NOW() 
WHERE id = :segment_id;

-- 查詢時過濾活躍 segment
SELECT * FROM daily_reflection_segments 
WHERE reflection_id = :id AND is_active = TRUE;

-- 若已結算 segment 被軟刪除，audit log 記錄
INSERT INTO audit_log(table_name, operation, segment_id, old_is_active, new_is_active)
VALUES('daily_reflection_segments', 'soft_delete', :segment_id, TRUE, FALSE);

-- M6.5 settle 時，檢查結算 segment 是否被刪除
-- 若被刪除後欲完全撤銷，需人工審核（不允許自動回滾 XP）
```

**驗收測試**:

```python
def test_segment_soft_delete_prevents_unwind():
    """RISK-13: 已結算 segment 軟刪除後無法撤銷 XP"""
    segment = create_segment(reflection_id=..., user_feeling="...", ...)
    settle_segment_xp(segment.id, user.id, 50)
    assert user.current_xp == 50
    
    # 軟刪除 segment
    soft_delete_segment(segment.id)
    segment_after = get_segment(segment.id)
    assert segment_after.is_active is False
    
    # XP 不能自動回滾，保持 50
    assert user.current_xp == 50
    
    # Audit log 記錄刪除事實
    audit = get_audit_log(segment_id=segment.id)
    assert audit.operation == "soft_delete"
```

---

## RISK-14:Lifetime XP 與 Current XP 同步失敗 → 等級倒退或幻覺升級

**觸發組合**:`M6.2 (users 表 lifetime_xp 欄位) + M6.5 (ACID 交易) + 並發操作`

**失效機制**:

M6 Refinement 新增 `users.lifetime_xp` 作為生涯累計總值，以防止消費 XP（Gacha、質押）導致等級倒退。同時保留 `users.current_xp` 作為可用餘額。

若 M6.5 在 settle 時**僅更新 current_xp 而忘記更新 lifetime_xp**，或兩次更新之間發生 crash，則:
- current_xp += 50, lifetime_xp 未變 → 等級計算錯誤 → 幻覺升級或倒退
- 消費時：current_xp -= 30, lifetime_xp 也 -= 30（錯誤）→ 等級失真

**研究衝突點**:R08 §六.1 (XP 發放原子性) vs 稿費用平衡（lifetime 單向增長）

**緩解策略**:

在 M6.5 所有 XP 異動時，**同時更新 current_xp 與 lifetime_xp**:

```python
# services/m6_5_acid_gatekeeper/gatekeeper.py

async def settle_segment_xp(self, segment_id, user_id, amount):
    """[RISK-14] 同時更新 current_xp (可用餘額) 與 lifetime_xp (生涯累計)"""
    async with self._session.begin():
        user = await self._session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user.scalar_one()
        
        # [RISK-14] 同一交易中同時更新兩個欄位
        user.current_xp += amount       # 可用餘額增加
        user.lifetime_xp += amount      # 生涯累計增加（唯增不減）
        
        # 記帳
        ledger = XPLedger(...)
        self._session.add(ledger)
        # 交易結束時同步提交，無中間狀態
        
        return TransactionResult(True)

async def deduct_xp_for_gacha(self, user_id, cost_xp):
    """[RISK-14] Gacha 扣費：current_xp -= cost，lifetime_xp 保持不變"""
    async with self._session.begin():
        user = await self._session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user.scalar_one()
        
        # [RISK-14] 扣費時只減 current_xp，lifetime_xp 唯增不減
        if user.current_xp < cost_xp:
            return TransactionResult(False, "GATEKEEPER_004", "insufficient_xp")
        
        user.current_xp -= cost_xp      # 餘額減少
        # lifetime_xp 保持不變（記錄生涯最高成就）
        
        return TransactionResult(True, ...)
```

**驗收測試**:

```python
def test_lifetime_xp_never_decreases():
    """RISK-14: 消費 XP 時 lifetime_xp 不減少"""
    user.current_xp = 100
    user.lifetime_xp = 100
    
    deduct_xp_for_gacha(user.id, cost_xp=30)
    
    assert user.current_xp == 70   # 可用餘額減少
    assert user.lifetime_xp == 100 # 生涯累計不變

def test_earned_xp_updates_both_columns():
    """RISK-14: 獲得 XP 時同時更新 current 與 lifetime"""
    settle_segment_xp(segment.id, user.id, amount=50)
    
    assert user.current_xp == 50   # 可用餘額增加
    assert user.lifetime_xp == 50  # 生涯累計增加
    
    # 消費再獲得：lifetime 應持續增長
    deduct_xp_for_gacha(user.id, 30)
    assert user.current_xp == 20
    assert user.lifetime_xp == 50  # 仍是生涯總值
    
    settle_segment_xp(segment2.id, user.id, amount=60)
    assert user.current_xp == 80   # 20 + 60
    assert user.lifetime_xp == 110 # 50 + 60
```

---

## RISK-15：Opt-in 內文摘要 → 草稿引用 → 雲端側通道洩漏

**觸發組合**：`M1.1 (content_summary, Opt-in) + M4.4 (深夜草稿) + M6.2 (雲端同步)`

**失效機制**：

M1.1 v1.1 新增 Opt-in 內文採集模式,由 M2.2 Local LLM 產出 `content_summary`（如「正在編輯畢業論文第五章結論」）。此摘要存於本地 SQLite (L1)。但若 M4.4 深夜草稿生成器在拼裝 `daily_reflections.ai_description` 時引用了 `content_summary` 原文,而 `ai_description` 後續經 M6.2 同步至雲端 PostgreSQL (L3) → **側通道洩漏**：從雲端可反推使用者正在做什麼具體工作。

**研究衝突點**：R07 §3 (IDE 脈絡擷取供 AI 分析) vs 架構文件 §3 (T1 明文絕不上雲)

**緩解策略**：

```python
# [R07 §3 + 架構文件 §3] content_summary 嚴格鎖定 L1
class DraftGenerator:
    async def build_ai_description(self, segments: list[Segment]) -> str:
        for seg in segments:
            # 草稿可用的欄位:app_bucket, duration_minutes, wpm_avg
            # 草稿不可用的欄位:content_raw, content_summary, window_title
            if seg.content_summary:
                # 若需引用,必須先經 Eguard 過濾為泛化描述
                sanitized = await eguard.generalize(seg.content_summary)
                # "編輯畢業論文第五章結論" → "進行文件編輯工作"
            else:
                sanitized = seg.app_bucket  # "writing"
```

**三層防禦**：
1. `content_raw` 與 `content_summary` 在 `raw_tracking_logs` 中標記為 `privacy_tier = "T1_OPTIN"`
2. M4.4 草稿生成器在引用 `content_summary` 時,必須經 M2.3 Eguard 泛化為無具體細節的描述
3. M6.2 雲端同步管線設置 hard block:payload 含 `content_raw` 或 `content_summary` 欄位 → 拒絕同步

**驗收測試**：

```python
def test_content_summary_never_in_cloud_sync():
    """RISK-15: content_summary 絕不進入雲端同步"""
    log = create_raw_tracking_log(
        payload={"content_summary": "編輯畢業論文第五章", "app_bucket": "writing"}
    )
    sync_payload = cloud_sync.prepare_payload(log)
    assert "content_summary" not in sync_payload
    assert "content_raw" not in sync_payload

def test_draft_generalizes_content_summary():
    """RISK-15: 草稿引用 content_summary 時必須泛化"""
    segment = create_segment(content_summary="編輯畢業論文第五章結論")
    draft = draft_generator.build_ai_description([segment])
    assert "畢業論文" not in draft
    assert "第五章" not in draft
```

---

## RISK-16：動態 Persona 生成 + 首次注入無歷史 → 人設不穩定

**觸發組合**：`M4.1 (LLM 新建 Persona)` + `M4.2 (Persona 注入)` + `M4.9 (ARPM 人設一致性監督)`

**失效機制**：

LLM 剛生成的 Persona 只有 `personality_prompt`，沒有任何對話歷史。M4.9 ARPM 的人設一致性監督依賴**對話歷史序列**作為基準比對。新 Persona 第一次上場時 ARPM 基準為空 → 無法判斷是否漂移 → 若 LLM 在前幾個 turn 輸出的回覆風格不穩定（初始化雜訊），ARPM 抓不到任何異常 → 使用者感覺剛配對的新專家「人格飄移」→ 治療同盟建立失敗（R05 §治療同盟），使用者立刻要求重新配對或放棄。

**研究衝突點**：R03 §2 (ARPM 嚴格還原，需歷史基準) vs R05 §治療同盟建構 (第一印象決定信任基線)

**緩解策略**：

1. **種子對話注入**：新 Persona 建立時，系統自動呼叫 LLM 生成 2～3 條「種子對話（Seed Exchanges）」作為 ARPM 的初始歷史錨點，不顯示給使用者，純粹作為 ARPM 的 `persona_history` 基準：

```python
# services/m4_1_router/persona_factory.py
# [R03 §2 + RISK-16] 新 Persona 建立後立即生成種子對話

async def create_persona_with_seed(
    persona_config: dict,
    role_context: RoleContext,
) -> AIExpert:
    expert = await db.insert("ai_experts", persona_config)

    # 生成種子對話作為 ARPM 錨點（不寫入 chat_transcripts，僅作 ARPM 基準）
    seed_exchanges = await llm_generate_seed_exchanges(
        personality_prompt=persona_config["personality_prompt"],
        n_exchanges=3,
    )
    await arpm_service.set_persona_anchor(
        persona_id=expert.id,
        seed_exchanges=seed_exchanges,
    )
    return expert
```

1. **ARPM 新 Persona 寬鬆模式**：ARPM 在新 Persona 前 5 個 turn 採寬鬆模式，漂移判斷閾值提高 30%（避免把初始化雜訊誤判為崩塌）：

```python
# services/m4_9_arpm/validator.py
# [R03 §2 + RISK-16]

def get_drift_threshold(persona: AIExpert, turn_count: int) -> float:
    BASE_THRESHOLD = 0.70
    if turn_count <= 5:
        return BASE_THRESHOLD * 1.30   # 新 Persona 前 5 turn 寬鬆 30%
    return BASE_THRESHOLD
```

1. **首次配對的「破冰腳本」**：M4.2 為新 Persona 注入一段固定的「破冰系統提示」，確保前幾個 turn 語氣穩定，不依賴 LLM 的自由發揮：

```python
ICEBREAKER_SUFFIX = """
在前五次互動中，你應：
1. 先做自我介紹（姓名、背景一句話）
2. 詢問使用者當下最想討論什麼
3. 語氣保持[tone_default]，不做風格實驗
"""
```

**驗收測試**：

```python
def test_new_persona_has_arpm_anchor():
    """RISK-16: 新建 Persona 後 ARPM 必須有種子對話錨點"""
    expert = create_persona_with_seed(persona_config=mock_config, role_context=mock_ctx)
    anchor = arpm_service.get_persona_anchor(expert.id)
    assert anchor is not None
    assert len(anchor.seed_exchanges) >= 2

def test_new_persona_arpm_lenient_mode():
    """RISK-16: 新 Persona 前 5 turn ARPM 閾值提高 30%"""
    expert = create_new_persona()
    threshold_turn1 = arpm.get_drift_threshold(expert, turn_count=1)
    threshold_turn6 = arpm.get_drift_threshold(expert, turn_count=6)
    assert threshold_turn1 == pytest.approx(threshold_turn6 * 1.30, rel=0.01)

def test_new_persona_stable_first_response():
    """RISK-16: 新 Persona 第一個回覆語氣必須符合 tone_default"""
    expert = create_new_persona(tone_default="authoritative")
    first_response = persona_agent.respond("你好", expert=expert, turn=1)
    tone = classify_tone(first_response)
    # 破冰腳本確保第一 turn 不漂移
    assert tone in ("authoritative", "probing")
    assert tone != "resonance"   # 不應直接跳到最共情模式
```

---

## RISK-17：刪除唯一 Persona → Router 白名單空集合 → 靜默降級

**觸發組合**：`M3.4 (Persona 管理 UI)` + `M4.1.1 (Router 白名單)` + `M4.3 (角色沙盒)`

**失效機制**：

使用者在 Role CSIE 下只有一個 Persona（微積分助教宏軒），刪除後 `active_experts` 白名單為空。M4.1.1 Router fallback 到 `tool_ai_default`（工具型 AI），但前端沒有任何提示 → 使用者以為仍在和「微積分助教」說話，但實際上對話對象已靜默切換為無人設的工具型 AI → 治療同盟斷裂，使用者察覺後信任崩潰。

**研究衝突點**：R05 §治療同盟 (使用者需感知對話對象) vs (產品設計 工具型 AI 作為 fallback)

**緩解策略**：

前端強制 warning + 後端 SSE 廣播：

```python
# Frontend: M3.4 側邊欄刪除守門員
def can_delete_expert(role_id: str, expert_id: str) -> DeletePermission:
    active_count = count_active_experts(role_id)
    if active_count <= 1:
        return DeletePermission(
            allowed=True,   # 技術上允許，但必須顯示 warning
            requires_confirmation=True,
            warning_message=(
                "刪除後此角色將暫時只有「工具型 AI」可用，"
                "建議先配對新專家再刪除。"
            )
        )
    return DeletePermission(allowed=True, requires_confirmation=False)

# Backend: M4.3 刪除後廣播
async def on_expert_deleted(role_id: str, expert_id: str):
    remaining = count_active_experts(role_id)
    if remaining == 0:
        await broadcast_sse("EXPERT_POOL_EMPTY", {
            "role_id": role_id,
            "message": "此角色目前沒有配對的 AI 專家",
            "action_hint": "match_new_expert",
        })
```

**驗收測試**：

```python
def test_delete_last_expert_shows_warning():
    """RISK-17: 刪除最後一個 Persona 前必須顯示 warning"""
    role = create_role_with_one_expert()
    perm = can_delete_expert(role.id, role.experts[0].id)
    assert perm.requires_confirmation is True
    assert "工具型 AI" in perm.warning_message

def test_empty_expert_pool_broadcasts_sse():
    """RISK-17: 刪除後 active_experts 為空時廣播 EXPERT_POOL_EMPTY"""
    role = create_role_with_one_expert()
    with capture_sse_events() as events:
        delete_expert(role.id, role.experts[0].id)
    assert any(e["type"] == "EXPERT_POOL_EMPTY" for e in events)

def test_tool_ai_visible_when_pool_empty():
    """RISK-17: 空池時前端側邊欄仍顯示工具型 AI，不顯示空白"""
    role = create_role_with_no_experts()
    sidebar = render_expert_sidebar(role_id=role.id)
    assert sidebar.tool_ai_entry.visible is True
    assert "暫無配對專家" in sidebar.empty_state_hint
```

---

## RISK-18：AI 週期挑戰生成器讀取社群歷史 → 聚合統計反推個人行為側通道

**觸發組合**：`M4.13.4 (AI 挑戰生成器)` + `M6.6 (社群歷史/貼文/XP 趨勢)` + `M4.6 (Observer 行為推論的間接輸入)`

**失效機制**：

M3.7.6 週期挑戰的主要生成路徑 (`source="ai_reviewed"`) 由 AI 系統性檢核社群「歷史、目標、近況」來生成挑戰草稿。若生成器的 context builder 圖方便直接撈社群成員的個別 `daily_reflections`、聊天逐字稿或 M2.2 意圖向量做摘要餵給雲端 LLM,等同把 L1/L2 私有資料包裝成「挑戰文案」上雲——比 RISK-12 的貼文側通道更隱蔽,因為使用者從未主動按下「發布」,挑戰文案卻可能精準到讓其他成員反推出某人的具體弱點或行為模式 (例如挑戰文案寫「這週我們來克服連續 3 天沒寫日報的低潮」,直接點名式洩漏)。

**研究衝突點**：R07 §第五章 嵌入逆向攻擊 (任何彙整輸出都需檢查反推風險) vs (產品設計 §AI 個人化挑戰要「夠貼近社群近況」才有激勵效果)

**緩解策略**：

**Context builder 強制只讀 L3 聚合統計,且輸出前需管理員核准 (草稿閘):**

```python
# [R07 §5 + RISK-12 同源緩解] M4.13.4 context builder 隱私邊界
@dataclass
class ChallengeContext:
    privacy_layer: Literal["L3"]          # 型別層級就鎖死只能是 L3
    completion_rate_pct: float            # 聚合完成率,非個人列表
    common_goal_tags: list[str]           # 去識別化的目標標籤頻率
    xp_trend: Literal["up", "flat", "down"]
    raw_transcripts: list = field(default_factory=list)   # 必為空
    intent_vectors: list = field(default_factory=list)    # 必為空

def build_challenge_context(community_id: UUID) -> ChallengeContext:
    stats = m6_6_repo.get_aggregate_stats(community_id)  # SQL 聚合,不取個人列
    return ChallengeContext(
        privacy_layer="L3",
        completion_rate_pct=stats.completion_rate_pct,
        common_goal_tags=stats.top_goal_tags,
        xp_trend=stats.xp_trend,
    )

async def generate_challenge(community_id: UUID) -> Challenge:
    ctx = build_challenge_context(community_id)
    assert ctx.raw_transcripts == [] and ctx.intent_vectors == []  # 雙重保險斷言
    draft_text = await cloud_llm.generate(prompt=render_prompt(ctx))
    return Challenge(
        title=draft_text.title,
        description=draft_text.description,
        source="ai_reviewed",
        is_draft=True,                # R08 草稿與核准:必須管理員看過才 active
        status="pending_review",
    )
```

**管理員審核時必須能看到「這份草稿引用了哪些聚合統計」**,以便人工判斷是否仍有間接點名風險 (例如社群只有 2 人時,「完成率 50%」其實等於指名)。**小社群 (member_cap ≤ 3) 的 AI 挑戰生成應預設更保守的措辭模板**,避免統計值在小群組中退化為個人識別。

**驗收測試**：

```python
def test_ai_challenge_context_excludes_l1_l2():
    """RISK-18: context builder 絕不附帶逐字稿或意圖向量"""
    ctx = build_challenge_context(community_id=CID)
    assert ctx.privacy_layer == "L3"
    assert ctx.raw_transcripts == []
    assert ctx.intent_vectors == []

def test_ai_challenge_always_pending_review():
    """RISK-18: AI 生成挑戰一律先進 pending_review,不可直接 active"""
    challenge = generate_challenge(community_id=CID)
    assert challenge.is_draft is True
    assert challenge.status == "pending_review"

def test_small_community_uses_conservative_template():
    """RISK-18: member_cap<=3 的小群組使用保守措辭模板,避免統計值退化為指名"""
    small_community = make_community(member_cap=3, member_count=2)
    challenge = generate_challenge(community_id=small_community.id)
    assert challenge.template_tier == "conservative"
```

---

## 新增風險的流程

當實作過程中發現新的「合併後變差」模式:

1. 在本文件追加 `RISK-15`、`RISK-16`...
2. 記錄完整四欄:觸發組合 / 失效機制 / 緩解策略 / 驗收測試
3. 更新對應模組 SPEC.md 的 `## Known Risks` 區塊
4. 寫對應的 pytest 標記為 `@pytest.mark.integration_risk("RISK-xx")`
