# M5.2 — 證據萃取器與反應分類器 (Evidence Extractor & Reaction Classifier)

**標籤**:`[進階]`
**版本**:`1.0` / `draft`
**最後更新**:2026-10-19
**設計來源**:`docs/M5_ICEBERG_REDESIGN.md` §4.5
**動工前提**:`docs/MVP_CLOSURE_REPORT.md` 存在

## 1. Purpose (目的)

把 coOS 已經在收集的本地資料 (對話、遙測、Git、反思) 與使用者對介入的反應,轉換成 M5.1 可以消化的冰山證據 —— 本模組只產生證據與假設**提案**,不決定信心。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R06 | §4.2 壓力下的應對姿態 | 五種姿態的語言特徵詞表 (M5.2.1) |
| R06 | §2.1 版本控制紀錄作為認知狀態感測器 | 敷衍 commit message 作為打岔姿態的 behavior 證據 |
| R06 | §4.1 冰山模型的層次解構 | 歸因句型 → perception;祈使/應該句型 → expectation;後設情緒詞 → meta_feeling |
| R04 | §反溯因推理的對抗性驗證 | Gemma 合成必須同時提出競爭假設 |
| R04 | §神經符號約束滿足與 D-ALP 框架 | nucleus / satellite 權重判定 |
| R16 | §Change Talk | 變化語句偵測 (供 M5.4 階段轉移) |
| R16 | §Rolling with Resistance | 反應分類:阻抗下的否認不等於反證 |
| R07 | §POST §4.3 | 萃取全程本地,只用 ai.local Gemma |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M6.1 `chat_transcripts` | DB rows (使用者訊息) | `{id:"ct_91", role_id, content:"問了就代表我不行啦"}` |
| M0.4 `raw_tracking_logs` | DB rows | `{id, action:"ide_focus", payload:{duration_s: 10800}}` |
| M1.4 Git 事件 | `raw_tracking_logs` (source=m1_4) | `{commit_msg:"ok"}` |
| `ReflectionSource` (正式 = M6.4 API 雲端讀;M0.5 模擬 = 合成庫本地鏡像表) | `DailyReflectionResponse` 子集 | `{id, user_feeling, user_learned, mood_score}` |
| M4.2 `reactance_detector` | `{score, source}` | `{score:0.72, source:"rule"}` |
| M5.5 `m5_5_moves_log` | 待分類的 move | `{id, hypothesis_ids, delivered_at, thread_id}` |
| M4.6 goals / promises | `ObserverResult` | 作為 expectation 證據 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M5.1 | `EvidenceIn` | `{source_table:"chat_transcripts", source_id:"ct_91", polarity:"supports", weight:1.0}` |
| M5.1 (經 M5.3) | `HypothesisProposal` | `{layer:"perception", content:"求助等於無能", parent_ids:[...], rival:{content:"偏好獨立思考"}}` |
| M5.4 | `ChangeTalkEvent` | `{theme_id, source_id, strength:0.8}` |
| `m5_5_moves_log.reaction` | `Reaction` enum | `"reject_calm"` |
| M4.2 / M5.5 | `CrisisFlag` | `{flag:true, source_id}` (見 §7.4) |

## 4. Dependencies

### 上游 (我依賴誰)

- **M5.1**:寫入目標
- **M5.3**:假設提案必須先過驗證
- **M2.2**:本地 Gemma (`gemma-4-e4b-it-4bit` @ ai.local);不可用時降級
- **M6.1**:`chat_transcripts`、`raw_tracking_logs`
- **M6.4**:反思 API (雲端 → 本地讀)
- **M1.2**:每日批次在閒置時段觸發
- **M4.2**:reactance 分數

### 下游 (誰依賴我)

- **M5.1 / M5.4 / M5.5**
- **M0.5** (測試基礎設施):以 `LocalMirrorReflectionSource` 注入,在合成庫上驅動本模組並評估精確率 / 召回率 (M0.5 SPEC §9.1 Q7)

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-21 | 防衛性否認被當成證實 | §7.3 反應 → 證據表;reject_reactive 永不為 supports;第 3 次起計 contradicts 0.5 |
| RISK-19 | 萃取時把 L1 內容送雲端 | 只允許呼叫 ai.local;禁止 import `_call_gemini*` (lint 測試) |
| RISK-06 | 證據跨角色 | 每筆證據繼承來源 `role_id`;合成批次以 role 為單位執行 |
| RISK-05 | 證據無法回溯 | 每筆證據必帶 `source_table + source_id` |
| RISK-24 | 合成反思被當成真實資料讀入 | `LocalMirrorReflectionSource` 只接受帶 `application_id` 哨兵的合成庫;正式預設來源固定為 M6.4 API (§7.5) |

## 6. Acceptance Criteria (驗收標準)

```python
@pytest.mark.parametrize("text,stance", [
    ("對不起,我真的太笨了,連這個都不會", "placating"),
    ("這工具總是壞,從來沒好用過", "blaming"),
    ("就時間複雜度而言,此方案的漸進行為是被證明最優的", "super_reasonable"),
    ("ok 隨便啦 先這樣", "irrelevant"),
    ("我有點挫折,我需要有人幫我看一下", "congruent"),
])
def test_rule_markers_detect_stances(text, stance):
    ev = rule_markers(msg(text))
    assert any(e.attrs.get("stance_type") == stance for e in ev)

def test_rule_markers_never_create_deep_layers():
    ev = rule_markers(msg("我覺得問人就是代表我不行,我應該自己搞定"))
    assert all(e.layer in {"behavior", "coping_stance", "feeling", "meta_feeling",
                           "perception", "expectation"} for e in ev)
    assert not any(isinstance(x, HypothesisProposal) and x.layer in {"yearning", "self"} for x in ev)

def test_synthesis_always_proposes_rival():
    out = synthesize(day_evidence(fixture="help_seeking"), gemma=FakeGemma())
    for p in out.proposals:
        if p.layer in {"perception", "expectation", "yearning"}:
            assert p.rival is not None

def test_synthesis_skips_when_gemma_down():
    out = synthesize(day_evidence(), gemma=UnavailableGemma())
    assert out.proposals == [] and out.skipped_reason == "gemma_unavailable"

def test_extractor_never_calls_cloud(network_spy):
    synthesize(day_evidence(), gemma=LocalGemma())
    assert network_spy.hosts() <= {"ai.local", "127.0.0.1"}

@pytest.mark.integration_risk("RISK-21")
def test_reactive_rejection_never_supports(): ...   # 見 05_integration_risk_audit.md RISK-21

def test_no_response_after_48h_is_inconclusive():
    m = deliver_move(at=now() - hours(49))
    assert classify_pending(now())[m.id] == "no_response"

def test_evidence_inherits_role():
    ev = rule_markers(msg("對不起都是我的錯", role_id="role_family"))
    assert all(e.role_id == "role_family" for e in ev)

def test_crisis_flag_raised_regardless_of_consent():
    revoke_consent("m5_iceberg")
    assert crisis_check(msg("我不想活了")).flag is True

def test_reflection_source_injectable(syn_db):
    """§7.5:注入本地鏡像來源時,不呼叫 M6.4 API,且同樣只讀已核准的反思"""
    src = LocalMirrorReflectionSource(syn_db)
    seed_reflection(syn_db, is_reviewed=True,  user_feeling="有點挫折")
    seed_reflection(syn_db, is_reviewed=False, user_feeling="草稿")
    out = read_reflection_evidence(day=today(), source=src, m6_4_client=ExplodingClient())
    assert [e.attrs.get("text") for e in out] == ["有點挫折"]

def test_default_reflection_source_is_m6_4_api():
    assert isinstance(default_reflection_source(Settings(_env_file=None)), M64ApiReflectionSource)
```

## 7. Implementation Notes

### 7.1 M5.2.1 規則語言標記 (即時)

每則使用者訊息寫入 `chat_transcripts` 後,經 `_dispatch_observer_bg` 既有路徑非同步執行。純 Python,目標 < 5ms。

| 標記 | 判定 (起始詞表,留給 builder 擴充) | 輸出 |
| ---- | -------------------------------- | ---- |
| placating | 道歉詞 (對不起/抱歉/不好意思) ≥2 或 自我貶抑 (我太笨/都是我的錯/我不配) | coping_stance |
| blaming | 絕對詞 (總是/從不/每次都) + 外歸因主詞 + 負向情緒詞 | coping_stance |
| super_reasonable | 高壓情境 (近 2 小時同任務 ≥90 分鐘 或 reactance>0.5) 下,情緒詞缺席 + 術語密度高 | coping_stance |
| irrelevant | 與前一輪話題相似度 < 0.2 的跳轉、≤3 字敷衍回覆、Git 敷衍 commit (ok/fix/update/.) | coping_stance + behavior |
| congruent | 第一人稱情緒詞 + 需求/請求句 | coping_stance |
| feeling | 情緒詞典 (正/負向 + 激發度) | feeling |
| meta_feeling | 情緒詞 + 對情緒的評價 (「我氣自己…」「覺得自己不該難過」) | meta_feeling |
| perception | 歸因句型 (「因為我…所以…」「一定是…」「代表…」) | perception 證據 (不建假設) |
| expectation | 「應該/必須/一定要/希望他」 | expectation 證據 |
| change_talk | 「我想試試/也許可以/下次我會」 | ChangeTalkEvent |

**weight 判定** [R04: D-ALP §神經符號約束滿足與 D-ALP 框架]:直接陳述行為或強烈情緒的主句 = nucleus 1.0;背景、推測 (「好像」「可能」「似乎」) = satellite 0.4;修飾 = 0 (丟棄)。

behavior / coping_stance 可由規則直接提出假設 (content 用模板,例 `"卡關超過 {hours} 小時未求助"`);其他層只產生證據,等 M5.2.2 合成。

### 7.2 M5.2.2 本地 Gemma 每日合成

- 觸發:M1.2 回報閒置 ≥10 分鐘,且當日尚未合成;以 `(user_id, role_id)` 為單位
- 輸入 (全部本地):當日新證據 (含原文片段) + 該 role 的 `working+` 假設 + 已 `user_rejected` 的 content 清單 (避免重提)
- 輸出 JSON (以 schema 驗證,失敗重試 1 次後丟棄):

```python
class SynthesisOut(BaseModel):
    proposals: list[HypothesisProposal]   # 每個 perception/expectation/yearning 必附 rival
    links: list[LinkProposal]             # 一律「淺 → 深」driven_by (M5.1 拒收反向邊)
    theme_merges: list[tuple[str, str]]   # 兩個主題的 perception 是同一信念
    theme_tags: dict[str, list[str]]      # theme_id → 固定詞彙 (見 M5.5 SPEC §7.4),供 presentation_policy 使用
    skipped_reason: str | None = None
```

- prompt 要求:每條提案必須列出支撐的 `evidence_ids`;不得提出無 evidence_ids 的假設;不得使用診斷或疾病名詞
- 主題形成規則見設計稿 §4.5「主題 (theme) 的形成」

### 7.3 M5.2.3 反應分類器

被分類的訊息 = move 送出後**同一 thread** 的下一則使用者訊息;48 小時無訊息 → `no_response`。

| reaction | 判定 | 對被測假設的證據 |
| -------- | ---- | ---------------- |
| resonate | 同意語 + 延伸自己的經驗 | supports 1.0 |
| elaborate | 長度 > 前 5 則平均 ×1.5 且沿同一主題 | supports 0.6 |
| neutral | 其他 | inconclusive |
| deflect | 話題跳轉 (同 irrelevant 判定) | inconclusive;另寫一筆 irrelevant 姿態 behavior 證據 |
| reject_calm | 否定語 + reactance < 0.5 | contradicts 0.8 |
| reject_reactive | 否定語 + reactance ≥ 0.5 | inconclusive;同假設第 3 次起 contradicts 0.5 (RISK-21) |
| no_response | 48h 無訊息 | inconclusive |

規則先判,模糊時 (同時命中 ≥2 類) 交本地 Gemma 單題分類。

### 7.4 危機偵測

`crisis_check()` 是純規則 (詞表需人工審),放在本模組但**由 M4.2 管線在每則訊息呼叫,不依賴 M5 同意** (設計稿 §7.1 我的判斷)。命中 → 回傳 `CrisisFlag`;M4.2 切換支持模式並提供求助資源;M5.5 全層停用 72 小時。

### 7.5 M5.2.4 雲端反思讀取器

每日批次經 `ReflectionSource` 讀取當日已核准 (`is_reviewed = true`) 的反思;**不讀草稿**(草稿的 `ai_description` 是 AI 寫的,不是使用者的證據)。`user_feeling` → feeling 證據 weight 1.0 (自陳);`mood_score` → feeling attrs.valence;`user_learned` 送規則標記。

**可注入來源** (2026-10-19 使用者拍板,M0.5 SPEC §9.1 Q7):

```python
class ReflectionSource(Protocol):
    def reviewed_on(self, user_id: str, role_id: str, day: date) -> list[ReflectionEvidenceRow]: ...

class ReflectionEvidenceRow(BaseModel):
    id: str                       # 成為證據的 source_id (source_table = "daily_reflections")
    role_id: str
    user_feeling: str
    user_learned: str | None
    mood_score: int | None
    reviewed_at: datetime

class M64ApiReflectionSource:          # 正式預設:經 M6.4 既有 API (雲端 → 本地讀)
    ...
class LocalMirrorReflectionSource:     # 只供 M0.5:讀合成庫的本地鏡像 daily_reflections 表
    def __init__(self, db_path: Path):  # 開啟時檢查 PRAGMA application_id == SYNTHETIC_APP_ID,不符即拒絕 (RISK-24)
        ...
```

- `default_reflection_source(settings)` 一律回傳 `M64ApiReflectionSource`;`LocalMirrorReflectionSource` 只能由 M0.5 harness 明確注入,正式程式碼路徑不得建構它。
- 兩種來源都只回傳 `is_reviewed = true` 的列;「不讀草稿」的規則在來源層與萃取層各檢查一次。
- M5.3 V1 解析 `daily_reflections` 的 `source_id` 時,使用同一個注入的來源 (模擬時才找得到本地鏡像的列)。

### 7.6 異常處理

- Gemma 逾時 / 不可用 → 跳過合成,只留規則層 (系統不壞)
- JSON schema 驗證失敗 → 重試 1 次,仍失敗則丟棄並記 `raw_tracking_logs` (`gate="synthesis_schema_fail"`)
- M6.4 API 不可達 → 當日反思證據延到下次批次

## 8. Anti-patterns (反模式)

- ❌ 不要把冰山萃取交給雲端 Gemini,即使原文先經 `mask_pii` (L1 對話逐字稿不上雲)
- ❌ 不要用 AI 撰寫的 `ai_description` / `ai_analysis` 當證據 (那是系統自己的話,會形成自我強化迴圈)
- ❌ 不要讓規則層直接建立 yearning / self 假設
- ❌ 不要把 reject_reactive 當 supports (RISK-21)
- ❌ 不要為了「多一點證據」而讀其他角色的訊息 (RISK-06)

## 9. Open Questions

- [ ] E4B 4-bit 在冰山合成任務上的品質是否足夠 —— 建議 P1 階段以冰山之鏡的使用者修正率 (「不太對」+「完全不是」占比) 評估;若 > 40%,討論是否允許雲端只接收**結構化特徵** (不含原文) 做合成
- [ ] super_reasonable 的「高壓情境」判定門檻需以實測資料校準

---

## SPEC 撰寫 Checklist

- [x] §1 單一職責 (證據生產;信心決定權在 M5.1)
- [x] §2 至少 1 個 Rxx 引用
- [x] §3 Schema 為 Pydantic
- [x] §4 依賴為真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼
- [x] §8 ≥3 條反模式
- [x] §9 ≥1 個開放問題
