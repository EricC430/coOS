# M5.4 — 轉化歷程追蹤 (Change Process Tracker)

**標籤**:`[進階]`
**版本**:`1.0` / `draft`
**最後更新**:2026-10-19
**設計來源**:`docs/M5_ICEBERG_REDESIGN.md` §6、§4.2 (`m5_4_themes`、`m5_4_alliance`)
**動工前提**:`docs/MVP_CLOSURE_REPORT.md` 存在

## 1. Purpose (目的)

為每個冰山主題維護「現在走到改變的哪一步」(薩提爾變化階段),並產出規劃器需要的三個背景量:變化指標、每位專家的同盟分數,以及以圖分析找出的核心渴望。這是 12 種作用方式中的「3 變化追蹤」。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R20 | §變化歷程 | 六階段狀態機:status_quo → foreign_element → chaos → integration → practice → new_status_quo |
| R20 | §應對姿態 | 一致性指數以 congruent 姿態占比計算 |
| R16 | §Change Talk | foreign_element / chaos → integration 的轉移訊號 |
| R17 | §Triad Dimensions | 同盟分數的 bond / task 代理值 |
| R24 | §階段定義 | readiness:尚無 change talk = 懵懂期,不進入 practice |
| R06 | §6.1 雙層記憶網路 | 指標分為短期 (7 日滑動) 與長期 (週分布) 兩層 |
| R04 | §冰山層次節點類型與結構化屬性定義 | 圖模型:節點 = 假設、邊 = 淺 → 深 driven_by;核心渴望以路徑強度計算 |
| R21 | §核心概念 | 核心渴望的用途:在關係中直接滿足一個共同渴望,同時鬆動多個主題 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M5.1 | 主題下的假設與狀態 | `{theme_id, hypotheses:[HypothesisRef...]}` |
| M5.2 | `ChangeTalkEvent`、reaction、姿態證據 | `{theme_id, strength:0.8}` |
| M5.5 | `m5_5_moves_log`、`m5_5_experiments` | `{mode:2, dosage:1, delivered_at}` |
| M6.4 API | `mood_score` 時序 | `[6, 5, 3]` |
| M6.3 `role_implicit_states` | 未過期的 label | `{label:"avoidance", expires_at}` (無資料 = unknown) |
| M6.1 `chat_transcripts` | 每位專家的對話天數與使用者自陳比例 | — |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `m5_4_themes` | `satir_phase`、`congruence_index`、`collision_cooldown_until` | `{phase:"integration"}` |
| `m5_4_alliance` | `score` | `{persona_id, role_id, score:0.64}` |
| M5.5 | `ThemeState` | 見 §7.2 |
| M5.1 | 狀態轉移請求 | `new_status_quo` → perception 改 `softening` |
| `m5_4_core_yearnings` | `CoreYearning` | `{role_id, hypothesis_id:"h_31", reach:3, core_score:0.42, is_core:true}` |
| M3.8 / 論文評估 | `ChangeMetrics` (只含數值) | `{congruence_7d:0.31, stance_dist:{...}}` |
| M0.4 | `LogEvent` | `{event:"m5_4.phase", theme_id, from, to, trigger}` |

## 4. Dependencies

### 上游 (我依賴誰)

- **M5.1**、**M5.2**、**M5.5**:主題、證據、介入紀錄
- **M6.4 API**、**M6.3**、**M6.1**:mood、隱性狀態、對話
- **M5.1 `IcebergGraph`**:角色子圖 (networkx `DiGraph`);新增 Python 依賴 `networkx` (實作時 `uv add networkx`)

### 下游 (誰依賴我)

- **M5.5**:用階段決定可用 mode,用同盟分數閘碰撞劑量,用核心渴望排序 mode 5
- **M3.12**:顯示「最近的變化」與核心渴望標示
- **M3.8** (若實作):鞏固敘事的數據來源

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-20 | 脆弱期碰撞 | 偵測到混亂訊號即轉 chaos;chaos 期間 M5.5 只允許 4/5/12 |
| RISK-10 | 虛假樂觀 | 指標只輸出絕對值與方向,不輸出「提升 x%」的相對值給敘事層 |
| RISK-06 / RISK-23 | 跨角色 | 主題、指標、同盟分數、核心渴望皆以 role 為單位;cross_role 渴望的 reach 只計目前角色的主題 |

## 6. Acceptance Criteria (驗收標準)

```python
def test_collision_moves_theme_to_foreign_element():
    t = seed_theme(phase="status_quo")
    log_move(theme=t, mode=2, dosage=1)
    tracker.tick()
    assert get_theme(t.id).satir_phase == "foreign_element"

def test_two_chaos_signals_within_72h_enter_chaos():
    t = seed_theme(phase="foreign_element", entered=hours_ago(10))
    record_reaction(t, "reject_reactive"); record_mood_drop(2)
    tracker.tick()
    assert get_theme(t.id).satir_phase == "chaos"

def test_single_chaos_signal_is_not_enough():
    t = seed_theme(phase="foreign_element")
    record_mood_drop(2)
    tracker.tick()
    assert get_theme(t.id).satir_phase == "foreign_element"

def test_change_talk_moves_to_integration():
    t = seed_theme(phase="foreign_element")
    emit_change_talk(t, strength=0.8)
    tracker.tick()
    assert get_theme(t.id).satir_phase == "integration"

def test_chaos_without_change_talk_returns_to_status_quo_with_cooldown():
    t = seed_theme(phase="chaos", entered=days_ago(8), chaos_signals_cleared=True)
    tracker.tick()
    th = get_theme(t.id)
    assert th.satir_phase == "status_quo"
    assert th.collision_cooldown_until >= now() + days(13)

def test_new_status_quo_requires_two_observed_experiments_and_congruence_gain():
    t = seed_theme(phase="practice", congruence_at_entry=0.20)
    observe_experiments(t, n=2); set_congruence(t, 0.30)
    tracker.tick()
    assert get_theme(t.id).satir_phase == "practice"           # +0.10 不足 0.15
    set_congruence(t, 0.36); tracker.tick()
    assert get_theme(t.id).satir_phase == "new_status_quo"

def test_alliance_starts_low_and_grows():
    assert alliance(persona="p1", role="r1") < 0.6
    simulate_days_of_chat(persona="p1", days=12, disclosure_rate=0.3, resonate_share=0.7)
    assert alliance(persona="p1", role="r1") >= 0.6

def test_missing_implicit_state_is_unknown_not_neutral():
    clear_role_implicit_states()
    assert tracker.theme_state(t.id).implicit_state == "unknown"

def test_core_yearning_requires_two_themes():
    y = seed_yearning(role="r1")
    connect_theme(y, theme="help_seeking", strength=0.8)
    graph_job.run(role="r1")
    assert core(y).is_core is False                       # reach = 1
    connect_theme(y, theme="perfectionism", strength=0.7)
    graph_job.run(role="r1")
    assert core(y).reach == 2 and core(y).is_core is True

def test_core_score_uses_strongest_path_per_theme():
    y = seed_yearning(role="r1")
    connect_theme(y, theme="t1", strength=0.9); connect_theme(y, theme="t1", strength=0.2)
    connect_theme(y, theme="t2", strength=0.3)
    graph_job.run(role="r1")
    assert core(y).core_score == pytest.approx(0.9 + 0.3, rel=1e-6)

def test_core_yearning_ignores_candidate_nodes_and_other_roles():
    y = seed_yearning(role="r1", cross_role=True)
    connect_theme(y, theme="t1", strength=0.8)
    connect_theme(y, theme="t2", strength=0.8, via_status="candidate")
    connect_theme(y, theme="t3", strength=0.8, role="r2")
    graph_job.run(role="r1")
    assert core(y, role="r1").reach == 1

def test_graph_job_writes_only_ids_and_numbers():
    graph_job.run(role="r1")
    for row in fetch_all("m5_4_core_yearnings"):
        assert set(row.keys()) == {"role_id", "hypothesis_id", "reach", "core_score", "is_core", "computed_at"}

def test_metrics_never_include_content():
    m = tracker.metrics(theme_id=t.id)
    assert all(isinstance(v, (int, float, dict)) for v in m.model_dump().values())
```

## 7. Implementation Notes

### 7.1 階段轉移

完整轉移表見設計稿 §6.1。實作為純函式 `next_phase(theme, signals) -> (phase, trigger)`,由每小時 tick 與「move 送出 / reaction 分類完成」事件觸發。

**混亂訊號** (72 小時窗內任 2 項):`reject_reactive`、mood_score 較進入 foreign_element 前下降 ≥2、`role_implicit_states` 出現 avoidance / anxiety、該主題 behavior 證據頻率較前 7 日增加 ≥50%。

**混亂消退**:上述訊號連續 3 天皆無。

### 7.2 資料結構

```python
class SatirPhase(StrEnum):
    STATUS_QUO = "status_quo"; FOREIGN_ELEMENT = "foreign_element"; CHAOS = "chaos"
    INTEGRATION = "integration"; PRACTICE = "practice"; NEW_STATUS_QUO = "new_status_quo"

class ThemeState(BaseModel):
    theme_id: str
    role_scope: str
    phase: SatirPhase
    phase_entered_at: datetime
    readiness: Literal["precontemplation", "contemplation", "preparation", "action", "maintenance"]
    congruence_7d: float | None
    collision_cooldown_until: datetime | None
    is_sensitive: bool
    implicit_state: str                    # "unknown" when M4.8 has no data
    latest_mood_48h: int | None

class ChangeMetrics(BaseModel):
    theme_id: str
    congruence_7d: float | None
    stance_distribution_week: dict[str, float]   # 五種姿態占比
    attribution_shift: float | None              # 可控 / 情境性歸因占比的變化
    experiments_observed: int
    reaction_distribution: dict[str, int]
```

**readiness 對應** [R24: 改變階段 §階段定義]:無 change talk → precontemplation;有 change talk 但未接受實驗 → contemplation;接受實驗 → preparation;實驗進行中 → action;new_status_quo → maintenance。

**一致性指數**:該主題相關情境 (被歸入該主題的 behavior 證據前後 2 小時內) 的使用者語句中,被 M5.2 標為 congruent 的占比,7 日滑動;樣本 < 5 句時為 `None`。

**同盟分數** [R17: WAI §Triad Dimensions]:三項等權平均 —— 近 14 天對話天數 / 14;使用者自陳感受訊息占比 / 0.3 (上限 1);過去 move 的 resonate + elaborate 占比 (無 move 時 0.5)。每日批次重算。

### 7.3 核心渴望分析 (M5.4.4,圖分析)

設計稿 §6.3。每日批次在 M1.2 閒置時段、於變化指標之後執行;冰山之鏡開啟時若結果超過 24 小時也會重算一次。

```python
# [R04 §冰山層次節點類型] 圖模型保留;[R21 §核心概念] 核心渴望 → 一次滿足、多處鬆動
import networkx as nx

def compute_core_yearnings(g: nx.DiGraph, role_id: str) -> list[CoreYearning]:
    # g 由 IcebergGraph.load_subgraph(user_id, role_id, min_status="working") 提供
    # 節點屬性: layer, confidence, theme_id;邊屬性: confidence (淺 → 深 driven_by)
    out = []
    for y in (n for n, d in g.nodes(data=True) if d["layer"] == "yearning"):
        best: dict[str, float] = {}                       # theme_id → 最強路徑
        for src in (n for n, d in g.nodes(data=True) if d["layer"] in SHALLOW and d["theme_id"]):
            for path in nx.all_simple_paths(g, src, y, cutoff=7):
                strength = math.prod(g.nodes[n]["confidence"] for n in path)                          * math.prod(g.edges[a, b]["confidence"] for a, b in zip(path, path[1:]))
                t = g.nodes[src]["theme_id"]
                best[t] = max(best.get(t, 0.0), strength)
        score = sum(best.values())
        out.append(CoreYearning(role_id=role_id, hypothesis_id=y, reach=len(best),
                                core_score=score, is_core=len(best) >= 2 and score >= 0.25))
    return out
```

`SHALLOW = {"behavior", "coping_stance", "feeling", "meta_feeling"}`。路徑數在 N=1 規模下有限;若單一渴望的路徑數 > 5,000 (異常密的圖),改為只取每個來源節點的最強路徑 (`nx.shortest_path` 於 `-log(strength)` 權重上),並記 `raw_tracking_logs` (`gate="path_explosion"`)。

```python
class CoreYearning(BaseModel):
    role_id: str
    hypothesis_id: str
    reach: int = Field(ge=0)
    core_score: float = Field(ge=0)
    is_core: bool
    computed_at: datetime
```

### 7.4 異常處理

- mood 無紀錄 → 該訊號不計 (不視為下降)
- 主題被 M5.2 合併 → 保留較早主題的階段;兩者階段不同時取**較保守** (chaos > foreign_element > status_quo > integration > practice > new_status_quo)
- 主題所有 perception / expectation 皆 refuted → 主題封存,階段凍結

## 8. Anti-patterns (反模式)

- ❌ 不要以「時間到了」推進階段 (階段只能由訊號推進;改變不能被排程)
- ❌ 不要把相對提升 (「一致性提升 50%」) 交給任何敘事層 (RISK-10)
- ❌ 不要用靜態的 `ai_experts.trust_level` 代替同盟分數 (它建立後從不更新)
- ❌ 不要跨角色累加核心渴望的 reach (RISK-23);也不要把「核心渴望」標籤或其 content 交給任何雲端模組 (RISK-19)
- ❌ 不要把 networkx 圖物件快取到磁碟或另存一份圖資料庫 (SQLite 邊表是唯一真實來源)
- ❌ 不要把混亂期當作失敗而自動「重置」主題;混亂是改變的必經階段 (R20 §變化歷程)

## 9. Open Questions

- [ ] 混亂訊號的「behavior 頻率增加 ≥50%」在低頻主題 (一週 1–2 次) 會過敏,實測後可能需要改為絕對次數門檻
- [ ] 同盟分數三項是否等權,待 P2 資料回來後檢討
- [ ] 核心渴望門檻 (reach ≥2、core_score ≥0.25) 是否合理,待 P1 有實際圖資料後與冰山之鏡的使用者回饋一起校準

---

## SPEC 撰寫 Checklist

- [x] §1 單一職責 (階段與背景量;不選 move)
- [x] §2 至少 1 個 Rxx 引用
- [x] §3 Schema 為 Pydantic
- [x] §4 依賴為真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼
- [x] §8 ≥3 條反模式
- [x] §9 ≥1 個開放問題
