# M5.1 — 冰山假設庫 (Iceberg Hypothesis Store)

**標籤**:`[進階]`
**版本**:`1.0` / `draft`
**最後更新**:2026-10-19
**設計來源**:`docs/M5_ICEBERG_REDESIGN.md` §4.1–§4.4
**動工前提**:`docs/MVP_CLOSURE_REPORT.md` 存在 (拍板 Q4)

## 1. Purpose (目的)

以本地 SQLite 保存使用者的冰山圖 (八層假設為節點、層間因果為邊) 與證據、主題歸屬,作為**唯一**可以改變假設信心與狀態的地方,並提供上層模組唯一的圖存取介面 `IcebergGraph`。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R20 | §個人冰山 | 八層 enum 的原典定義 (含「感受的感受」) |
| R04 | §冰山層次節點類型與結構化屬性定義 | `attrs` 欄位:stance_type / need_type / target / valence / arousal |
| R04 | §心理幻覺的定義與生成機制 | 層信心上限 (對抗「信心錯位」)、不跳層 (對抗「過度推論」) |
| R04 | §神經符號約束滿足與 D-ALP 框架 | 證據 weight:nucleus 1.0 / satellite 0.4 / elaboration 0 |
| R07 | §POST §4.3 | `content` 為 L1,永不上雲 |
| R04 | §跨層次因果邊緣的提取與多模態溯源 | 圖模型保留:邊一律為「淺 → 深」driven_by,manifests_as 為查詢時反向視圖 (拍板 Q2 只拿掉雲端 Neo4j,不拿掉圖) |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M5.2 證據萃取 | `EvidenceIn` | `{hypothesis_ref, source_table:"chat_transcripts", source_id:"ct_91", polarity:"supports", weight:1.0}` |
| M5.2 Gemma 合成 | `HypothesisProposal` | `{layer:"perception", content:"求助等於無能", rival_group_id:"rg_3", parent_ids:[...]}` |
| M5.3 驗證結果 | `VerificationResult` | `{hypothesis_id, verdict:"reject", reason:"layer_skip"}` |
| M3.12 使用者回饋 | `UserFeedback` | `{hypothesis_id, action:"not_at_all"}` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M5.4 / M5.5 讀取 | `Hypothesis` | 見 §7.2 |
| M5.6 (只讀 id 與 layer,不讀 content 給雲端) | `HypothesisRef` | `{id, layer, status, confidence}` |
| M3.12 冰山之鏡 | `MirrorItem` | 見 M3.12 SPEC |
| M0.4 `raw_tracking_logs` | `LogEvent` | `{event:"m5_1.status_change", hypothesis_id, from:"working", to:"established"}` (**不含 content**) |

## 4. Dependencies

### 上游 (我依賴誰)

- **M6.1** (本地 SQLite + `alembic_local`):表的實體位置與遷移
- **M5.3** (符號驗證器):所有新假設與升級必須先過驗證

### 下游 (誰依賴我)

- **M5.2**:寫入證據、提出假設
- **M5.4**:讀主題與假設狀態
- **M5.5**:讀可用假設選 move
- **M5.6**:讀 id / layer (不讀 content 上雲)
- **M3.12**:呈現與回饋;經 `IcebergGraph.ancestor_paths()` 取推理路徑
- **M5.4**:經 `IcebergGraph.load_subgraph()` 做核心渴望分析
- **M4.2 `bdi_reconciler`**:讀 perception / expectation `working+` 作為 belief / desire 來源

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-05 | 證據無法回到原文 → 無法驗證 | 已於架構上消除;`source_id` 必須可解析 (M5.3 檢查) |
| RISK-19 | 假設 content 上雲 | 本模組不提供任何把 content 傳到網路的介面;雲端相關模組只能拿 `HypothesisRef` |
| RISK-21 | 不可證偽 | 本模組的 `apply_evidence` 拒絕任何 `reject_reactive → supports` 的組合 (防禦性檢查,主規則在 M5.2) |
| RISK-23 | 深層跨角色 | `role_scope = 'cross_role'` 只能由 `promote_cross_role()` 設定,且必須通過 ≥2 角色獨立鏈檢查 |
| RISK-12 | 社群側通道 | `m5_*` 表不得被 `m6_6_*` 任何程式碼讀取 (import-lint 測試) |

## 6. Acceptance Criteria (驗收標準)

```python
def test_yearning_requires_upper_chain():
    """不跳層:無 working 上層鏈的 yearning 被拒"""
    with pytest.raises(LayerSkipError):
        store.create(HypothesisProposal(layer="yearning", content="被接納", parent_ids=[]))

def test_self_never_established_without_user_stated():
    h = seed(layer="self", confidence=0.59)
    for _ in range(50):
        store.apply_evidence(h.id, supports(weight=1.0, source="chat_transcripts"))
    assert store.get(h.id).status != "established"
    assert store.get(h.id).confidence <= 0.6

def test_layer_confidence_cap():
    h = seed(layer="yearning")
    for _ in range(50):
        store.apply_evidence(h.id, supports(weight=1.0))
    assert store.get(h.id).confidence <= 0.75

def test_logodds_update_and_decay():
    h = seed(layer="behavior", confidence=0.5)
    store.apply_evidence(h.id, supports(weight=1.0))
    c1 = store.get(h.id).confidence
    assert c1 > 0.5
    store.run_decay(now=days_later(7))           # behavior 半衰期 7 天
    assert abs((store.get(h.id).confidence - 0.5) - (c1 - 0.5) / 2) < 1e-6

def test_user_rejected_blocks_regeneration():
    h = seed(layer="perception", content="求助等於無能", rival_group_id="rg1")
    store.apply_user_feedback(h.id, "not_at_all")
    assert store.get(h.id).status == "user_rejected"
    with pytest.raises(RejectedContentError):
        store.create(HypothesisProposal(layer="perception", content="求助等於無能"))

def test_purge_all_leaves_mvp_working(mvp_test_suite):
    store.purge_all(user_id=USER)
    assert count_rows("m5_1_iceberg_hypotheses") == 0
    assert mvp_test_suite.run().failed == 0

def test_status_change_logged_without_content(captured_logs):
    h = seed(layer="behavior", content="卡關超過 2 小時未求助")
    promote(h)
    assert all("卡關" not in str(e.payload) for e in captured_logs("m5_1.status_change"))

def test_links_only_store_shallow_to_deep():
    a = seed(layer="behavior"); b = seed(layer="perception")
    with pytest.raises(LinkDirectionError):
        store.add_link(from_id=b.id, to_id=a.id)          # 深 → 淺 不允許

def test_load_subgraph_is_role_scoped_and_status_filtered():
    seed(layer="behavior", role="r1", status="working", id="n1")
    seed(layer="behavior", role="r2", status="working", id="n2")
    seed(layer="behavior", role="r1", status="candidate", id="n3")
    g = graph.load_subgraph(USER, "r1", min_status="working")
    assert set(g.nodes) == {"n1"}

def test_ancestor_paths_ordered_by_strength():
    y = seed_chain(["behavior", "coping_stance", "perception"], confidences=[0.9, 0.8, 0.7])
    seed_chain(["behavior", "perception"], target=y, confidences=[0.3, 0.7])
    paths = graph.ancestor_paths(y, role_id="r1", limit=2)
    assert len(paths) == 2 and paths[0].strength >= paths[1].strength

def test_community_modules_cannot_import_m5():
    assert not imports_any("services/m6_6_community", prefix="m5_")
```

## 7. Implementation Notes

### 7.1 演算法選擇

- **信心更新**:log-odds 累加 (`M5_ICEBERG_REDESIGN.md` §4.4)。不用貝氏網路或 GNN:N=1 資料量不足以估計結構,而 log-odds 可逐筆解釋「為什麼信心是這個值」,冰山之鏡需要這個可解釋性。
- **衰減**:向 0.5 指數回歸,半衰期依層 (§4.3 表)。以每日批次執行 (M1.2 閒置時段觸發),不即時。
- **層係數 `k_layer`**:behavior 1.0 · stance 0.8 · feeling 0.8 · meta_feeling 0.7 · perception 0.6 · expectation 0.6 · yearning 0.4 · self 0.3。

### 7.2 資料結構

SQL 綱要見設計稿 §4.2 (`m5_1_iceberg_hypotheses` / `_links` / `_evidence` / `_prompts`、`m5_settings`)。遷移放 `services/alembic/versions/`,檔名前綴 `m5_1_`;**不可** `--autogenerate` 後直接 apply,須先給使用者審。

```python
# services/m5_1_iceberg_store/models.py
class Layer(StrEnum):
    BEHAVIOR = "behavior"; COPING_STANCE = "coping_stance"; FEELING = "feeling"
    META_FEELING = "meta_feeling"; PERCEPTION = "perception"; EXPECTATION = "expectation"
    YEARNING = "yearning"; SELF = "self"

LAYER_DEPTH = {Layer.BEHAVIOR: 0, Layer.COPING_STANCE: 1, Layer.FEELING: 2, Layer.META_FEELING: 2,
               Layer.PERCEPTION: 3, Layer.EXPECTATION: 4, Layer.YEARNING: 5, Layer.SELF: 6}

class Status(StrEnum):
    CANDIDATE = "candidate"; WORKING = "working"; ESTABLISHED = "established"
    SOFTENING = "softening"; TRANSFORMED = "transformed"
    REFUTED = "refuted"; USER_REJECTED = "user_rejected"

class Hypothesis(BaseModel):
    id: str
    user_id: str
    role_scope: str                      # "role:<uuid>" | "cross_role"
    theme_id: str | None
    layer: Layer
    content: str                         # L1
    attrs: dict = {}
    confidence: float = Field(ge=0.02, le=0.95)
    status: Status
    origin: Literal["rule_marker", "local_synthesis", "user_stated", "user_corrected"]
    rival_group_id: str | None
    last_evidence_at: datetime | None
    last_tested_at: datetime | None

class HypothesisRef(BaseModel):
    """唯一可以被雲端相關模組持有的形狀 —— 沒有 content。"""
    id: str
    layer: Layer
    status: Status
    confidence: float

class EvidenceIn(BaseModel):
    hypothesis_id: str
    source_table: Literal["raw_tracking_logs", "chat_transcripts", "daily_reflections",
                          "m5_5_moves_log", "m5_5_experiments", "m5_1_iceberg_prompts"]
    source_id: str
    polarity: Literal["supports", "contradicts", "inconclusive"]
    weight: float = Field(ge=0, le=1)
    observed_at: datetime
    extractor_version: str
```

**狀態轉移表** (M5.3 驗證通過後才可升級):

| 從 | 到 | 條件 |
| -- | -- | ---- |
| candidate | working | 達該層最低證據 (設計稿 §4.3) 且 c ≥ 0.4 |
| working | established | 達 established 門檻且 c ≥ 0.7 (self 層需 user_stated) |
| established | softening | M5.4 主題進入 new_status_quo |
| softening | transformed | 維持 30 天 |
| 任一 | refuted | c < 0.15 或 M5.3 挫敗分數 > 0.5 |
| 任一 | user_rejected | 冰山之鏡「完全不是」 |
| softening | established | 30 天內出現舊模式 supports ≥3 (回退) |

**公開介面**:

```python
class IcebergStore:
    def create(self, p: HypothesisProposal) -> Hypothesis: ...          # 先呼叫 M5.3.verify_new
    def apply_evidence(self, e: EvidenceIn) -> Hypothesis: ...
    def apply_user_feedback(self, hid: str, action: Literal["yes", "not_quite", "not_at_all", "dont_touch"]) -> None: ...
    def run_decay(self, now: datetime) -> int: ...
    def promote_cross_role(self, hid: str) -> bool: ...                  # RISK-23
    def refs_for_role(self, user_id: str, role_id: str, min_status: Status) -> list[HypothesisRef]: ...
    def purge_all(self, user_id: str) -> None: ...

class IcebergGraph:
    """M5.1.5 上層模組唯一的圖入口。SQLite 邊表是唯一真實來源;networkx 圖只在記憶體中、用完即丟。"""
    def load_subgraph(self, user_id: str, role_id: str, min_status: Status = Status.WORKING) -> "nx.DiGraph": ...
        # 節點屬性: layer, confidence, theme_id, status;邊屬性: confidence。cross_role 節點只在該角色有支撐時納入
    def ancestor_paths(self, hypothesis_id: str, role_id: str, min_status: Status = Status.WORKING,
                       limit: int = 2) -> list["GraphPath"]: ...   # 依路徑強度遞減;遞迴 CTE 實作,不需 networkx
    def descendants(self, hypothesis_id: str, role_id: str) -> list[str]: ...

class GraphPath(BaseModel):
    node_ids: list[str]          # 由淺到深
    strength: float              # 節點 × 邊 confidence 連乘
```

**邊的方向**:`add_link(from_id, to_id)` 要求 `LAYER_DEPTH[from] < LAYER_DEPTH[to]` (feeling 與 meta_feeling 同深度,兩者之間不建邊),否則拋 `LinkDirectionError`。日後若改用本地嵌入式圖資料庫,只替換 `IcebergGraph` 實作 (設計稿 §4.6 的評估條件)。

使用者回饋對應:`yes` → `supports` 1.0 + origin 改 `user_stated`;`not_quite` → `contradicts` 0.8;`not_at_all` → `user_rejected`;`dont_touch` → 所屬主題 `is_sensitive = 1`。

### 7.3 異常處理

- 證據的 `source_id` 解析失敗 → 拒收該證據,寫 `raw_tracking_logs` (`gate="unresolvable_source"`)
- SQLite 鎖定 → 重試 3 次 (100ms 退避),仍失敗則放棄本次更新 (證據會在下次批次重算)
- `m5_settings.engine_enabled = 0` 或無有效同意 → 所有寫入 API 直接 no-op 並回傳 `None`
- 衰減批次中斷 → 以 `last_decay_at` 冪等重跑

## 8. Anti-patterns (反模式)

- ❌ 不要在 `HypothesisRef` 以外的形狀把假設交給 M4.2 / M5.6 (RISK-19)
- ❌ 不要讓任何模組直接 `UPDATE confidence`;只能經 `apply_evidence` (否則失去可解釋性)
- ❌ 不要把假設同步到雲端 PostgreSQL / Neo4j,即使「只是備份」(L1 原則,拍板 Q2)
- ❌ 不要因為 Gemma 合成「看起來很有道理」就跳過 M5.3 (R04 §心理幻覺:連貫性會掩飾錯誤)
- ❌ 不要在 `raw_tracking_logs` 寫入 content 或 attrs 的自由文字

## 9. Open Questions

- [ ] 一位使用者的假設上限 (建議 500 筆 active,超過時最舊的 candidate 先淘汰) —— 實作時以實測資料量決定
- [ ] `purge_all` 是否也要清掉 `raw_tracking_logs` 中 M5 相關事件 (只含 id,不含內容) —— 預設不清,留作論文評估

---

## SPEC 撰寫 Checklist

- [x] §1 單一職責
- [x] §2 至少 1 個 Rxx 引用
- [x] §3 Schema 為 Pydantic
- [x] §4 依賴為真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼
- [x] §8 ≥3 條反模式
- [x] §9 ≥1 個開放問題
