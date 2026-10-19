# M5.5 — 介入規劃器 (Move Planner)

**標籤**:`[進階]`
**版本**:`1.0` / `draft`
**最後更新**:2026-10-19
**設計來源**:`docs/M5_ICEBERG_REDESIGN.md` §5、§7、§8.3
**動工前提**:`docs/MVP_CLOSURE_REPORT.md` 存在

## 1. Purpose (目的)

決定「這一輪、這個通道,系統要對使用者做哪一件事 (或刻意什麼都不做)」:從 move catalog 中經守門與評分選出**至多一個** move,並管理小實驗的生命週期與遊戲化呈現政策。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R20 | §變化歷程 | 各 mode 的適用階段;mode 2 = 外來元素;混亂期只承接 |
| R20 | §應對姿態 | mode 4:姿態曾是生存資源,先肯定再轉化 |
| R06 | §4.2 壓力下的應對姿態 | mode 1 依姿態調整節奏的四種策略 |
| R16 | §OARS / §Change Talk / §Rolling with Resistance | 各 move 的 MI 技術對應;阻抗時降級 |
| R17 | §Triad Dimensions | 劑量 ≥2 的同盟分數門檻 |
| R05 | §治療同盟建構 / §合成心理病理學 | mode 5、mode 6 |
| R21 | §核心概念 | mode 5 矯正性情緒經驗;核心渴望加分 (一次滿足、多處鬆動) |
| R22 | §外化對話 | mode 8 |
| R23 | §實驗設計 | mode 9 |
| R24 | §階段定義 | readiness 與 mode 12 |
| R25 | §實驗結果 | mode 7、mode 10 讓使用者自己說 |
| R26 | §觀察學習 | mode 6 |
| R08 | §二 任務斷點打斷管理 | 主動通道只在斷點 |
| R09 | §3.3 病態使用 | mode 11 呈現政策 |
| R10 | §敘事化福祉 | mode 10 鞏固敘事 (經 RISK-10) |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.2 (每輪) | `PlanRequest` | `{channel:"chat", user_id, role_id, persona_id, thread_id, echo_mode_triggered:false}` |
| M1.2 斷點事件 | `PlanRequest` | `{channel:"breakpoint", ...}` |
| M3.3 開啟反思表單 | `PlanRequest` | `{channel:"reflection", reflection_id}` |
| M5.1 | `HypothesisRef` 列表 | — |
| M5.4 | `ThemeState`、同盟分數、`CoreYearning` | `{hypothesis_id:"h_31", reach:3, core_score:0.42, is_core:true}` |
| M5.2 | `CrisisFlag` | — |
| `user_consents` / `m5_settings` | 同意、停用、暫停、劑量上限 | — |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M5.6 | `PlannedMove` | `{move_id:"COLLIDE_CURIOUS", mode:2, dosage:1, hypothesis_ids:["h_7"], channel:"chat"}` |
| `m5_5_moves_log` | 送出紀錄 | — |
| `m5_5_experiments` | 實驗提議與狀態 | — |
| M3.13 | `ExperimentCard` | 見 M3.13 SPEC |
| M4.5 / M3.5 / M4.13 / M3.11 | `PresentationPolicy` | `{soften_loss_framing:true, ...}` |
| M0.4 | `LogEvent` | `{event:"m5_5.gate", gate:"low_mood", channel}` |

## 4. Dependencies

### 上游 (我依賴誰)

- **M5.1**、**M5.4**:假設與主題狀態
- **M5.2**:危機旗標
- **M1.2**:斷點事件、深度工作狀態
- **M4.2**:echo_mode 本輪是否觸發
- **M0.4 / M1.4**:實驗判定的遙測與 Git 事件

### 下游 (誰依賴我)

- **M5.6**:編譯 move
- **M3.13**:實驗卡
- **M4.5 / M3.5 / M4.13 / M3.11**:讀 `presentation_policy()` (無 M5 時回傳全 false)

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-20 | 脆弱期碰撞 | §7.2 第 2 層閘 + 碰撞後 2 輪承接 |
| RISK-22 | 遊戲化強化冰山 | §7.6 `presentation_policy` |
| RISK-23 | 深層跨角色 | cross_role 假設在無本角色支撐時只允許 mode 1/5/6 |
| RISK-04 | 斷點 vs 即時 | breakpoint 通道只回應 M1.2 斷點事件 |
| RISK-09 | 焦慮 + Gacha | `block_stake_offers` 同時擋 Gacha 主動推播 |
| RISK-01 | 草稿核准 | reflection 通道只出題目,不出答案、不給 XP |

## 6. Acceptance Criteria (驗收標準)

```python
def test_at_most_one_move_per_turn():
    assert isinstance(plan(req(channel="chat")), (PlannedMove, type(None)))

def test_no_consent_only_hold():
    revoke_consent("m5_iceberg")
    assert plan(req()).mode == 12

def test_crisis_disables_everything_for_72h():
    raise_crisis_flag()
    assert plan(req()).mode == 12
    advance(hours=71); assert plan(req()).mode == 12

@pytest.mark.integration_risk("RISK-20")
def test_collision_blocked_low_mood(): ...
@pytest.mark.integration_risk("RISK-20")
def test_collision_blocked_in_chaos_phase(): ...
@pytest.mark.integration_risk("RISK-20")
def test_two_holding_turns_after_collision(): ...

def test_echo_mode_turn_limits_modes():
    assert plan(req(echo_mode_triggered=True)).mode in {1, 4, 5, 12}

def test_dosage_2_requires_alliance():
    set_alliance(0.5); seed_established_theme()
    assert (plan(req()).dosage or 0) < 2
    set_alliance(0.7)
    assert (plan(req()).dosage or 0) <= 2                    # 預設上限 2 (拍板 Q6)

def test_dosage_3_requires_user_setting_and_prior_resonance():
    set_alliance(0.9); set_max_dosage(2)
    assert (plan(req()).dosage or 0) <= 2

def test_collision_cooldown_per_theme_and_weekly_cap():
    log_move(mode=2, theme="t1")
    assert plan(req(), force_theme="t1").mode != 2
    log_move(mode=2, theme="t2"); log_move(mode=2, theme="t3", days_ago=3)
    assert plan(req()).mode not in {2, 7, 8}                   # 本週已 2 次

def test_breakpoint_channel_requires_breakpoint_event():
    assert plan(req(channel="breakpoint", breakpoint_event=None)) is None

def test_mode_6_only_for_persona_with_iceberg_story():
    assert plan(req(persona_has_iceberg_story=False)).mode != 6

@pytest.mark.integration_risk("RISK-23")
def test_cross_role_hypothesis_limited_to_relational_modes(): ...

def test_experiment_signal_must_be_local_source():
    with pytest.raises(ValueError):
        SuccessSignal(source="m6_6_social_posts", action="post", within_days=7)

def test_experiment_observed_from_telemetry():
    e = accept_experiment(signal={"source": "raw_tracking_logs", "action": "github_pr_opened", "within_days": 7})
    insert_log(action="github_pr_opened")
    run_experiment_check()
    assert get_experiment(e.id).status == "observed"

def test_mode5_prefers_core_yearning():
    seed_yearning(id="y_core", need="recognition", core_score=0.6, is_core=True, confidence=0.5)
    seed_yearning(id="y_other", need="acceptance", is_core=False, confidence=0.7)
    m = plan(req(force_mode=5))
    assert m.hypothesis_ids == ["y_core"] and m.move_id == "MEET_RECOGNIZE"

def test_core_bonus_lifts_mode5_over_equal_candidates():
    seed_yearning(id="y_core", is_core=True, core_score=0.8)
    a = score_of(plan_candidates(req()), move_id="MEET_ACCEPT")
    unset_core("y_core")
    b = score_of(plan_candidates(req()), move_id="MEET_ACCEPT")
    assert a - b == pytest.approx(0.4)

def test_core_bonus_does_not_bypass_global_gate():
    seed_yearning(id="y_core", is_core=True, core_score=1.0)
    revoke_consent("m5_iceberg")
    assert plan(req()).mode == 12

@pytest.mark.integration_risk("RISK-22")
def test_policy_blocks_stake_for_worth_theme(): ...

def test_policy_all_false_without_m5():
    disable_m5_module()
    assert presentation_policy(USER) == PresentationPolicy()
```

## 7. Implementation Notes

### 7.1 Move catalog (每 mode ≥2 條目;指令措辭留給 builder 精修,但不得違反「禁止」欄)

mode 3 (變化追蹤) 由 M5.4 承擔,不是 move;mode 11 是政策,不佔回合;mode 12 是空 move (`HOLD`)。

| move_id | mode | 適用階段 | 前置 | 通道 | MI 技術 | 指令要點 (行為) | 禁止 |
| ------- | ---- | -------- | ---- | ---- | ------- | --------------- | ---- |
| `INFL_EMPHASIS` | 1 | 全 | 主題 working+ | chat | open_question | 回應時優先接住與主題相關的面向 (例:對求助主題主動提「要不要一起看」) | 提及主題本身 |
| `INFL_STANCE_PACE` | 1 | 全 | stance working+ | chat | 依姿態 | [R06 §4.2] 討好 → 少評價、多給選擇;指責 → 聚焦具體邊界與共同目標;超理智 → 先談事實再輕觸感受;打岔 → 縮小範圍、給兩個選項 | 指出姿態 |
| `COLLIDE_CURIOUS` | 2 | status_quo, foreign_element | perception/expectation working+;劑量 1 | chat, breakpoint, reflection | open_question | 以好奇問句並置使用者「想要的」與「正在做的」 | 肯定句陳述心理 |
| `COLLIDE_QUOTE` | 2 | 同上 | established;劑量 2;同盟 ≥0.6 | chat, reflection | reflective_listening | 並置使用者同角色的原話與近期行為,問兩者是否有關 | 評價性形容詞、「又」 |
| `COLLIDE_NAME` | 2 | foreign_element | established;劑量 3 (使用者開啟);曾有劑量 2 獲 resonate | chat | summary | 說出觀察到的模式並請使用者確認對不對 | 未經允許使用 |
| `VALIDATE_PURPOSE` | 4 | status_quo, foreign_element | stance working+ | chat | affirmation | 肯定該習慣背後的用意與它曾經幫過的忙 | 把姿態說成缺點 |
| `VALIDATE_EFFORT` | 4 | 全 | 任一 working+ | chat | affirmation | 先肯定使用者已經付出的努力,再談下一步 | 以結果為條件 |
| `MEET_ACCEPT` | 5 | 全,chaos 優先 | yearning working+ (need = acceptance / belonging) | chat | reflective_listening | 使用者坦露時先完整接住,不急著給建議 | 立刻給解法 |
| `MEET_RECOGNIZE` | 5 | 全,chaos 優先 | yearning working+ (need = recognition / competence) | chat | affirmation | 肯定思考過程與投入,具體指出做得好的地方 | 空泛稱讚 |
| `MODEL_STORY` | 6 | status_quo, integration | persona 有 `iceberg_story`;主題相關 | chat | — | 專家簡短分享自己相似的經驗與後來的轉變 | 與 persona card 矛盾 (ARPM 稽核) |
| `MODEL_CONGRUENT` | 6 | 全 | — | chat | — | 專家用「我感覺… 我希望…」的一致方式表達自己的感受與需求 | 情緒勒索 |
| `ECHO_INSIGHT` | 7 | foreign_element, integration | 有 nucleus 原話證據;同角色 | chat, reflection | change_talk_replay | 引用使用者過去說過的一句話,問它今天是否也適用 | 竄改原話、跨角色 |
| `ECHO_CHANGE_TALK` | 7 | integration, practice | 近 14 天有 change talk | chat, breakpoint | change_talk_replay | 回放使用者自己說過的改變意願,問想不想試試 | 替使用者承諾 |
| `EXTERN_INVITE` | 8 | foreign_element, integration | established;主題無 `external_name` | chat | open_question | 邀請使用者一起幫這個模式取個名字 | 系統單方面命名 |
| `EXTERN_USE` | 8 | integration, practice | 主題有使用者同意的 `external_name` | chat, breakpoint | reflective_listening | 用那個名字和使用者討論它今天有沒有出現 | 把名字當成使用者本人 |
| `EXP_PROPOSE` | 9 | integration, practice | perception established;readiness ≥ contemplation | experiment card, chat | structured_advice | 提議一個 7 天內可完成、可被遙測判定的小行動 | 強制、綁 XP |
| `EXP_DEBRIEF` | 9 | practice | 實驗 observed / not_observed | breakpoint, chat | open_question | 陳述觀察到的事實,問使用者感覺如何、學到什麼 | 替使用者下結論 |
| `CONSOL_ASK` | 10 | new_status_quo | 主題 softening | chat, breakpoint | open_question | 對比過去與現在的具體行為,問使用者覺得自己哪裡不一樣 | 系統宣告「你成長了」 |
| `CONSOL_NARRATIVE` | 10 | new_status_quo | M3.8 存在 | wrapped | summary | 以使用者自己的話串起變化敘事 | 相對提升數字 (RISK-10) |
| `HOLD` | 12 | 全 | — | — | — | 不攜帶任何冰山指令 | — |

### 7.2 守門 (依序;任一層失敗即降級)

```
L0 全域硬閘 → 只能 HOLD
   無有效 user_consents('m5_iceberg') · engine_enabled=0 · paused · CrisisFlag 72h 內
   channel=breakpoint 且 (無斷點事件 或 深度工作中 或 今日已送 1 則冰山主動訊息)
L1 角色閘
   只考慮 role_scope = 當前 role 的假設;cross_role 假設若本 role 無支撐 → 只允許 mode 1/5/6
L2 碰撞類閘 (mode 2/7/8) → 失敗則改從 mode 1/4/5/6 選
   latest_mood_48h ≤ 3 · implicit_state = anxiety · phase = chaos · echo_mode_triggered
   collision_cooldown_until 未到 (每主題 72h) · 本週碰撞類已 2 次 · theme.is_sensitive
   劑量 ≥2 時 alliance < 0.6 · 劑量 > m5_settings.max_collision_dosage
L3 承接閘
   最近一次碰撞後的 2 個使用者回合內 → 只能 mode 4/5
L4 準備度閘
   readiness = precontemplation → 不出 mode 9;phase 不符 move 的「適用階段」→ 剔除
```

### 7.3 評分

```
score = info_gain × readiness_w + phase_fit − fatigue + core_bonus
info_gain   = |P(成功訊號 | H) − P(成功訊號 | rival)|,先以 move 條目上的靜態值近似 (0~1)
readiness_w = {precontemplation:0.3, contemplation:0.6, preparation:0.8, action:1.0, maintenance:0.7}
phase_fit   = 1 (move 主要階段) / 0.5 (次要) / 0 (不適用,已在 L4 剔除)
fatigue     = 同 mode 近 7 日次數 × 0.2
core_bonus  = mode 5 且目標渴望 is_core → 0.5 × min(core_score, 1);其他 → 0
```

**mode 5 的目標渴望選擇** (在算分之前決定,決定 `MEET_ACCEPT` 或 `MEET_RECOGNIZE` 與 `hypothesis_ids`):

1. 候選 = 目前角色中 `working+` 的 yearning (cross_role 者亦可,mode 5 屬 RISK-23 允許範圍)
2. 有核心渴望 → 取 `core_score` 最高者
3. 無核心渴望 → 取與當前對話主題相連、confidence 最高者
4. 依 `attrs.need_type` 對應條目:acceptance / belonging → `MEET_ACCEPT`;recognition / competence → `MEET_RECOGNIZE`;其他 → `MEET_ACCEPT`

核心渴望的 mode 5 **不受碰撞類閘限制** (它本來就是承接),但仍受 L0 全域硬閘與 L1 角色閘約束。

同分時偏好**較淺**的 mode (1 > 4 > 5 > 6 > 7 > 2),寧可溫和。常數先寫死於 `services/m5_5_planner/constants.py`,實測後調整。

### 7.4 資料結構

```python
class PlanRequest(BaseModel):
    channel: Literal["chat", "breakpoint", "reflection", "experiment", "wrapped"]
    user_id: str
    role_id: str
    persona_id: str | None = None
    thread_id: str | None = None
    echo_mode_triggered: bool = False
    breakpoint_event_id: str | None = None
    reflection_id: str | None = None

class PlannedMove(BaseModel):
    move_id: str
    mode: int = Field(ge=1, le=12)
    dosage: int | None = Field(default=None, ge=1, le=3)
    hypothesis_ids: list[str]
    theme_id: str | None
    channel: str
    persona_id: str | None
    quote_source_id: str | None = None      # mode 7 / COLLIDE_QUOTE:指向 chat_transcripts.id (同角色)

class SuccessSignal(BaseModel):
    source: Literal["raw_tracking_logs"]     # 只允許本地來源 (M1.x / M1.4 事件皆寫入此表)
    action: str
    where: dict = {}
    within_days: int = Field(ge=1, le=14)
    min_count: int = 1

class PresentationPolicy(BaseModel):
    soften_loss_framing: bool = False
    emphasize_effort: bool = False
    hide_rank_comparison: bool = False
    block_stake_offers: bool = False
```

`m5_4_themes` 新增欄位 `external_name TEXT` (mode 8 使用者同意的名字) 與 `tags TEXT` (JSON,M5.2 合成時從固定詞彙表選:`worth_contingent`、`fear_of_failure`、`help_seeking`、`perfectionism`、`conflict_avoidance`、`control`)。

### 7.5 小實驗生命週期

`proposed → accepted | declined → in_progress → observed | not_observed | expired`。
- 每主題同時最多 1 個進行中實驗;全域最多 2 個
- `declined` 是有效選擇 (SDT 自主性),記為 inconclusive 證據,14 天內不再提同主題實驗
- 每小時檢查 `SuccessSignal`;`observed` → 對被測 perception 寫 contradicts 0.8 (行動結果與信念預測不符) 並排 `EXP_DEBRIEF`;`not_observed` → inconclusive,不責備
- 實驗**不綁 XP**:接受、完成都不給額外 XP

### 7.6 呈現政策

`presentation_policy(user_id)`:若存在 `established` 主題帶 `worth_contingent` 或 `fear_of_failure` tag → 四個旗標全 true;否則全 false。消費端只改文案與顯示,不改 XP 數值、不改 M6.5 交易 (RISK-22)。M5 未安裝時函式回傳預設值 —— 消費端以 `try import` 或 feature flag 呼叫,MVP 不依賴本模組 (CLAUDE.md 不要做的事 #7)。

### 7.7 異常處理

- 任一資料來源讀取失敗 → 回傳 `HOLD`,記 `raw_tracking_logs` (`gate="planner_error"`)
- 規劃耗時 > 50ms → 回傳 `HOLD` (不拖慢專家回覆)

## 8. Anti-patterns (反模式)

- ❌ 不要在一輪中攜帶兩個 move,即使兩個都很適合
- ❌ 不要用強化學習或線上學習調整選擇策略 (N=1、不可解釋、不可測試)
- ❌ 不要讓實驗與 XP、徽章、連續天數掛鉤 (外在動機會污染實驗的意義)
- ❌ 不要在 breakpoint 通道之外主動打擾使用者 (R08 §二、CLAUDE.md 不要做的事 #4)
- ❌ 不要在 chaos 期「趁勝追擊」再碰撞 (RISK-20)

## 9. Open Questions

- [ ] info_gain 的靜態近似值需要為每個 move 條目手動標定 —— 建議在 P2 實作時與使用者一起過一遍 catalog
- [ ] 每週碰撞上限 2 次是否過保守,待 P3 實測反應分布後檢討

---

## SPEC 撰寫 Checklist

- [x] §1 單一職責 (選擇;不編譯、不呈現)
- [x] §2 至少 1 個 Rxx 引用
- [x] §3 Schema 為 Pydantic
- [x] §4 依賴為真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼
- [x] §8 ≥3 條反模式
- [x] §9 ≥1 個開放問題
