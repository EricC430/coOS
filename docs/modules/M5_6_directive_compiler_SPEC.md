# M5.6 — 指令編譯器與洩漏閘 (Directive Compiler & Leak Gate)

**標籤**:`[進階]`
**版本**:`1.0` / `draft`
**最後更新**:2026-10-19
**設計來源**:`docs/M5_ICEBERG_REDESIGN.md` §8.1、§8.2
**動工前提**:`docs/MVP_CLOSURE_REPORT.md` 存在

## 1. Purpose (目的)

把 M5.5 選出的 move 翻譯成「專家這一輪該怎麼做」的行為指令,確保離開本地的只有行為、沒有任何對使用者的心理推論,並把指令接進 M4.2 的 LangGraph 管線。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R07 | §POST §4.3 | 假設 (L1) 永不上雲;只有行為指令可進雲端 prompt |
| R03 | §Echo Mode §3.2 | echo_mode 觸發時只接受溫和 mode;語氣仍由 Echo Mode 主導 |
| R16 | §OARS | move → MI 技術對應,與既有 `mi_selector` 合流 |
| R09 | §第六章 MAS + ToM + BDI | belief / desire 改由 M5.1 供給,仍須 reconcile 成 intention |
| R18 | §Mitigation Strategies | 碰撞類指令要求「溫和堅持」,使用者一否認不可立刻倒戈認錯,也不可硬推 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M5.5 | `PlannedMove` | `{move_id:"ECHO_INSIGHT", mode:7, quote_source_id:"ct_88"}` |
| M5.1 | `HypothesisRef` + (僅本地洩漏閘比對用) content | — |
| M6.1 `chat_transcripts` | quote 原文 (同角色) | `"卡住的時候其實是怕被看到不會"` |
| M2.3 | `eguard.mask_pii()` | — |
| M4.2 `PersonaState` | `current_tone`、`role_id`、`persona_id` | — |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.2 `prompt_builder.build_system_prompt` | `iceberg_directive: IcebergDirective | None` | 見 §7.2 |
| M4.2 `mi_selector` | 技術覆寫 | `MITechnique.CHANGE_TALK_REPLAY` |
| M4.2 `bdi_reconciler` | `bdi_belief` / `bdi_desire` | `"還不熟悉怎麼開口問人"` / `"把這個 bug 修好"` |
| `m5_5_moves_log` | 送出確認 | `{delivered_at, channel:"chat"}` |
| M0.4 | `LogEvent` | `{event:"m5_6.leak_gate", passed:false, reason:"term:渴望"}` |

## 4. Dependencies

### 上游 (我依賴誰)

- **M5.5**:要編譯的 move
- **M5.1**:假設 (洩漏閘比對)
- **M2.3**:PII 遮罩
- **M6.1**:quote 原文

### 下游 (誰依賴我)

- **M4.2**:新增 `iceberg_move` 節點;`prompt_builder` 新增區塊

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-19 | 假設經指令洩漏上雲 | §7.3 洩漏閘;未通過一律 HOLD |
| RISK-03 | 鏡像使用者狀態 | 指令只寫專家行為;沿用 RISK-03 狀態描述詞表檢查 |
| RISK-06 / RISK-23 | 跨角色 | quote 必須 `role_id == current_role`;cross_role 假設不產生 quote |
| RISK-08 | BDI 矛盾直接拼接 | belief / desire 仍走 `reconcile_bdi()`,本模組不直接輸出 intention |
| RISK-02 | Echo Mode + ARPM | 冰山指令不改 `current_tone` / `current_agency`,不觸發 ARPM 漂移判定 |

## 6. Acceptance Criteria (驗收標準)

```python
@pytest.mark.integration_risk("RISK-19")
def test_directive_contains_no_iceberg_terms(): ...          # 見 05_integration_risk_audit.md

@pytest.mark.integration_risk("RISK-19")
def test_cloud_payload_never_contains_hypothesis_content(capture_gemini_payload): ...

def test_leak_gate_rejects_hypothesis_ngram_overlap():
    h = seed(layer="perception", content="求助等於無能")
    d = IcebergDirective(move_id="X", mode=1, instruction="使用者認為求助等於無能,請溫和回應", forbidden_actions=[])
    assert leak_gate(d, [h]).passed is False

def test_failed_gate_degrades_to_hold():
    with force_leaky_template():
        assert compile_move(planned(mode=2)).mode == 12

def test_quote_is_pii_masked_and_same_role():
    seed_transcript(id="ct_1", role="r1", text="我跟王小明說問了就代表我不行")
    d = compile_move(planned(mode=7, quote_source_id="ct_1"), current_role="r1")
    assert "王小明" not in d.quote
    with pytest.raises(CrossRoleQuoteError):
        compile_move(planned(mode=7, quote_source_id="ct_1"), current_role="r2")

def test_directive_block_token_budget():
    for move in MOVE_CATALOG:
        assert estimate_token_count(render_block(compile_move(planned(move)))) <= 120

def test_echo_mode_turn_rejects_collision_move():
    state = persona_state(echo_mode_triggered=True)
    out = iceberg_move_node({**state, "_planned_move": planned(mode=2)})
    assert out["iceberg_directive"] is None or out["iceberg_directive"].mode in {1, 4, 5}

def test_no_m5_installed_persona_graph_unchanged():
    disable_m5_module()
    out = run_persona_graph(user_message="嗨")
    assert out["final_response"] and "iceberg_directive" not in out

def test_iceberg_does_not_change_tone_or_agency():
    before = persona_state(current_tone="authoritative", current_agency=0.85)
    after = iceberg_move_node({**before, "_planned_move": planned(mode=4)})
    assert after["current_tone"] == before["current_tone"]
    assert after["current_agency"] == before["current_agency"]
```

## 7. Implementation Notes

### 7.1 LangGraph 整合

```
drift_filter → bdi_reconciler → reactance_detector → echo_mode
            → iceberg_move (新) → persona_responder → paralinguistic → message_splitter → arpm_audit
```

- `iceberg_move` 節點:若 M5 未安裝或未同意 → 直接回傳 state (no-op)。否則呼叫 `M5.5.plan(PlanRequest(channel="chat", echo_mode_triggered=...))`,再呼叫本模組 `compile_move()`,把結果放進 `state["iceberg_directive"]`。
- `bdi_reconciler` 在 `iceberg_move` **之前**,所以 belief / desire 的供給走另一條路:`M4.1` 組 `PersonaState` 時呼叫 `bdi_inputs_from_m5(user_id, role_id)`,從 M5.1 取 perception / expectation 各一條 `working+` 假設,經本模組改寫為**能力描述**而非心理描述 (例:perception「求助等於無能」→ belief「還不熟悉怎麼開口問人」),再交 `reconcile_bdi()`。改寫結果同樣過洩漏閘。
- `mi_selector`:若 directive 指定技術,覆寫 MI 選擇器的技術;reactance 高時 MI 的「禁給建議」仍優先。
- `arpm_audit` 之後:寫 `m5_5_moves_log.delivered_at`,並經 `_dispatch_observer_bg` 排入 M5.2 反應分類。

### 7.2 資料結構與提示詞區塊

```python
class IcebergDirective(BaseModel):
    move_id: str
    mode: int
    instruction: str                 # ≤ 80 字,描述專家行為
    quote: str | None = None         # 已 mask_pii,同角色
    mi_technique: MITechnique | None = None
    forbidden_actions: list[str]     # 會原樣列進 prompt

def render_block(d: IcebergDirective) -> str:
    lines = ["[這一輪的陪伴方式]", f"- {d.instruction}"]
    if d.quote:
        lines.append(f"- 對方之前說過:「{d.quote}」。可以自然地引用這句話,但只引用一次。")
    lines.append("- 用問句,不要替對方下結論;對方不同意時,溫和地接受並轉回關心對方。")
    lines += [f"- 不要:{x}" for x in d.forbidden_actions]
    return "\n".join(lines)
```

所有 move 共用的固定禁止事項:說出任何心理學術語 · 診斷或貼標籤 · 「你總是 / 你又」· 一次問超過一個問題 · 對方否認後繼續堅持同一說法 [R18: Sycophancy Mitigation §Mitigation Strategies 的反向應用:不倒戈也不硬推,轉回關心]。

`prompt_builder.build_system_prompt` 新增參數 `iceberg_directive: IcebergDirective | None = None`,區塊放在 `[記憶區塊]` 之後、MI 指令之前;為 None 時輸出與現行完全相同 (回歸測試)。

### 7.3 洩漏閘

依序檢查,任一失敗 → 丟棄 move、改 HOLD、記 `raw_tracking_logs`:

1. **術語**:`ICEBERG_TERMS` (RISK-19 列表) 與診斷詞表 (M5.3 V5 共用)
2. **假設重疊**:instruction 與任一相關假設 content 的字元 3-gram Jaccard ≥ 0.5
3. **使用者狀態描述**:沿用 RISK-03 測試的狀態詞 (焦慮、逃避、anxious…) 出現在「使用者 / 對方 + 是 / 有 / 覺得」句型中
4. **quote**:來源 `role_id` 必須等於當前角色;必須經 `mask_pii`;長度 ≤ 40 字
5. **長度**:整個區塊 ≤ 120 tokens (`estimate_token_count`)

### 7.4 異常處理

- 洩漏閘任何例外 → 視為未通過 (fail closed)
- quote 來源已被使用者刪除 → 改用不帶 quote 的同 mode 條目;無替代 → HOLD
- 編譯耗時 > 20ms → HOLD

## 8. Anti-patterns (反模式)

- ❌ 不要把假設 content 放進 prompt「讓 LLM 自己決定怎麼用」(RISK-19,也違反 CLAUDE.md 不要做的事 #2)
- ❌ 不要讓冰山指令改動 Echo Mode 的 tone / agency (RISK-02;語氣與內容是兩條獨立的線)
- ❌ 不要在 fail 時「退而求其次」送出部分指令;只有 HOLD 一種降級
- ❌ 不要直接把 belief / desire 字串交給 persona_responder (RISK-08)

## 9. Open Questions

- [ ] perception → 能力描述 belief 的改寫規則先以 move catalog 的固定對照表實作 (每個 theme tag 一組);是否需要本地 Gemma 動態改寫,待 P2 觀察專家回覆品質後決定

---

## SPEC 撰寫 Checklist

- [x] §1 單一職責 (翻譯與把關;不選 move)
- [x] §2 至少 1 個 Rxx 引用
- [x] §3 Schema 為 Pydantic
- [x] §4 依賴為真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼
- [x] §8 ≥3 條反模式
- [x] §9 ≥1 個開放問題
