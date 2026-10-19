# M5.3 — 符號驗證器 (Symbolic Verifier, NSVIF-lite)

**標籤**:`[進階]`
**版本**:`1.0` / `draft`
**最後更新**:2026-10-19
**設計來源**:`docs/M5_ICEBERG_REDESIGN.md` §4.3、§4.4
**取代**:原 M5.2 NSVIF 幻覺防禦引擎、原 M4.10 NSVIF + D-ALP
**動工前提**:`docs/MVP_CLOSURE_REPORT.md` 存在

## 1. Purpose (目的)

以確定性、可單元測試的規則,判斷一條冰山假設 (新建或升級) 是否有足夠且結構健全的證據;不合格者拒絕、維持原狀或標為 refuted。本模組**不呼叫任何 LLM**。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R04 | §心理幻覺的定義與生成機制 | 三種成因 → V2 證據門檻 (過度推論)、層信心上限 (信心錯位)、V1 來源可解析 (錯誤前提) |
| R04 | §神經符號約束滿足與 D-ALP 框架 | V3 不跳層:推理鏈跳過必要因果環節即拒絕;證據權重 nucleus/satellite |
| R04 | §反溯因推理的對抗性驗證 | V4 競爭假設 + 挫敗分數 > 0.5 即視為幻覺 |
| R20 | §個人冰山 | 層深度順序的原典依據 |

> **偏離紀錄** (拍板 Q2):R04 的 NSVIF 原為「LLM 推理 + 符號求解器」雙軌;本模組只保留符號軌,神經軌的語意判斷已在 M5.2 的本地 Gemma 合成中完成。D-ALP 的 RST 樹解析降級為 M5.2 的 nucleus / satellite 規則判定。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M5.1 `create()` | `HypothesisProposal` | `{layer:"yearning", content:"被肯定", parent_ids:["h_12","h_19"]}` |
| M5.1 升級請求 | `PromotionRequest` | `{hypothesis_id, to:"established"}` |
| M5.1 每日批次 | `RivalGroupCheck` | `{rival_group_id}` |
| M5.1 `promote_cross_role()` | `CrossRoleRequest` | `{hypothesis_id}` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M5.1 | `VerificationResult` | `{verdict:"reject", checks_failed:["V3_layer_skip"], defeat_score:null}` |
| M0.4 `raw_tracking_logs` | `LogEvent` | `{event:"m5_3.verify", hypothesis_id, verdict, checks_failed}` (不含 content) |

## 4. Dependencies

### 上游 (我依賴誰)

- **M5.1**:讀假設、links、證據
- **M0.4 / M6.1**:解析 `raw_tracking_logs`、`chat_transcripts` 的 `source_id`
- **M6.4 API**:解析 `daily_reflections` 的 `source_id` —— 經 M5.2 §7.5 的 `ReflectionSource` 注入 (正式 = M6.4 API;M0.5 模擬 = 合成庫本地鏡像)

### 下游 (誰依賴我)

- **M5.1**:所有建立 / 升級 / 跨角色標記都經過本模組

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-05 | 證據找不到原文 | V1:任一證據無法解析即不計入;計入後不足門檻則拒絕 |
| RISK-21 | 不可證偽 | V4:沒有競爭假設的深層假設不可升級;挫敗分數讓反證有實際效力 |
| RISK-23 | 深層跨角色 | V7:≥2 角色各有獨立完整上層鏈 |

## 6. Acceptance Criteria (驗收標準)

```python
def test_v1_unresolvable_evidence_not_counted():
    h = seed(layer="perception", evidence=[ev(source_id="ct_missing"), ev(source_id="ct_1")])
    r = verify_promotion(h, to="working")
    assert r.verdict == "reject" and "V2_evidence_floor" in r.checks_failed

def test_v2_stance_needs_three_episodes():
    h = seed(layer="coping_stance", evidence=[ev(day=1), ev(day=1)])
    assert verify_promotion(h, to="working").verdict == "reject"
    add_evidence(h, ev(day=2))
    assert verify_promotion(h, to="working").verdict == "accept"

def test_v3_yearning_without_two_working_parents_rejected():
    p1 = seed(layer="perception", status="working")
    r = verify_new(proposal(layer="yearning", parent_ids=[p1.id]))
    assert "V3_layer_skip" in r.checks_failed

def test_v3_parent_must_have_shallow_ancestor():
    p1 = seed(layer="perception", status="working", ancestors=[])
    p2 = seed(layer="expectation", status="working", ancestors=[seed(layer="behavior", status="working")])
    r = verify_new(proposal(layer="yearning", parent_ids=[p1.id, p2.id]))
    assert "V3_layer_skip" in r.checks_failed

def test_v4_deep_hypothesis_without_rival_cannot_promote():
    h = seed(layer="perception", status="candidate", rival_group_id=None, enough_evidence=True)
    assert "V4_no_rival" in verify_promotion(h, to="working").checks_failed

def test_v4_defeat_score_above_half_refutes():
    h, rival = seed_rival_pair(h_support=1.0, rival_support=2.0)
    r = verify_rival_group(h.rival_group_id)
    assert r.refuted == [h.id]

def test_v5_diagnostic_terms_rejected():
    assert "V5_forbidden_term" in verify_new(proposal(layer="perception", content="使用者有憂鬱症傾向")).checks_failed

def test_v6_user_rejected_content_blocked():
    reject_by_user("求助等於無能")
    assert "V6_user_rejected" in verify_new(proposal(layer="perception", content="求助就等於無能")).checks_failed

def test_v7_cross_role_needs_two_independent_chains(): ...   # RISK-23 測試

def test_verifier_makes_no_network_calls(network_spy):
    verify_new(proposal(layer="behavior", content="卡關 3 小時"))
    assert network_spy.hosts() == set()
```

## 7. Implementation Notes

### 7.1 檢查清單 (依序執行,回報所有失敗項)

| 代號 | 檢查 | 適用 |
| ---- | ---- | ---- |
| V1 | 每筆證據的 `(source_table, source_id)` 可解析;不可解析者不計入 | 全部 |
| V2 | 有效證據達該層、該目標狀態的門檻 (設計稿 §4.3 表:筆數、跨天數、情境數、nucleus 數) | 全部 |
| V3 | 不跳層 (§7.2) | yearning、self |
| V4 | 必須屬於某 `rival_group`,且挫敗分數 ≤ 0.5 (§7.3) | perception、expectation、yearning、self |
| V5 | content 不含診斷 / 疾病 / 人格障礙名詞 (詞表需人工審) | 全部 |
| V6 | content 與任一 `user_rejected` 假設相似度 < 0.8 (字元 3-gram Jaccard) | 全部 |
| V7 | `cross_role` 需 ≥2 角色各自通過 V3 | 只在 `promote_cross_role` |
| V8 | self 層升至 established 需至少 1 筆 `origin = user_stated` 或 冰山之鏡 `yes` | self |

### 7.2 不跳層 (V3) 的具體定義

層深度:behavior 0 · coping_stance 1 · feeling / meta_feeling 2 · perception 3 · expectation 4 · yearning 5 · self 6。

- **yearning** 需要 ≥2 個 `working+` 父節點,深度 ∈ {3, 4},以 `driven_by` 連結;每個父節點都要有一條全由 `working+` 節點組成、深度遞減到 0–2 的祖先路徑。
- **self** 需要 ≥2 個 `working+` 的 yearning 或 perception 父節點,且同樣滿足祖先路徑。
- 升到 `established` 時,上述父節點須為 `established` (設計稿 §4.3),另需 1 次 move 獲 `resonate`。

以 SQLite 遞迴 CTE 實作祖先查詢,深度上限 7。

### 7.3 挫敗分數 (V4)

對同一 `rival_group` 中的假設 H 與每個對手 R:

```
S(x) = Σ supports.weight − Σ contradicts.weight      (只計 V1 可解析的證據,下限 0)
defeat(H) = max_R  S(R) / (S(H) + S(R) + ε)           ε = 0.1
defeat(H) > 0.5  →  H 標記 refuted
```

`rival_group` 中只有一個存活假設時,M5.2 下次合成必須補提對手;補不出則該假設停在 `candidate`。

### 7.4 資料結構

```python
class VerificationResult(BaseModel):
    verdict: Literal["accept", "reject", "hold"]   # hold = 證據尚不足,維持原狀
    checks_failed: list[str] = []
    defeat_score: float | None = None
    effective_evidence_count: int = 0

class RivalGroupResult(BaseModel):
    rival_group_id: str
    scores: dict[str, float]          # hypothesis_id → defeat
    refuted: list[str]
```

### 7.5 異常處理

- M6.4 API 不可達 → 該證據暫視為「未解析」,verdict 最多為 `hold` (不因網路問題 refute)
- 遞迴 CTE 出現環 (資料錯誤) → reject 並記 `raw_tracking_logs` (`gate="link_cycle"`)

## 8. Anti-patterns (反模式)

- ❌ 不要在驗證中呼叫 LLM 「再確認一次」(本模組必須確定性、可重現)
- ❌ 不要因為某條假設「看起來很重要」而放寬門檻
- ❌ 不要從雲端資料回推證據 (RISK-05 原則:證據只能從原文來)
- ❌ 不要讓 refuted 的假設在同一 rival_group 中被原封不動重提 (V6 同理適用 refuted,相似度門檻 0.9)

## 9. Open Questions

- [ ] V5 診斷詞表由誰審?建議使用者 + 一位有心理背景的同學各審一次後凍結
- [ ] 挫敗分數 0.5 門檻沿用 R04 原文;N=1 資料下是否過嚴,待 P1 實測後檢討

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
