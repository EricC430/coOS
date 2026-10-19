# SPEC 模板 (Module SPEC Template)

> 複製此檔為 `Mx_y_NAME_SPEC.md` 並填入內容。所有模組都必須具備以下 9 個區塊 (編號固定,方便 grep)。
> SPEC 只描述**已核准的現況行為**;要改行為請走 `docs/changes/` (見 `docs/DEV_WORKFLOW.md`)。

---

# Mx.y — 模組名稱

**標籤**:`[MVP]` | `[進階]`
**狀態**:`draft` | `approved` | `implemented` | `deprecated`   <!-- 只能填其中一個 -->
**版本**:`MAJOR.MINOR.PATCH`   <!-- 行為變更 → MINOR;契約破壞 → MAJOR;文字修正 → PATCH -->
**最後更新**:YYYY-MM-DD
**最後變更**:`<change-id>` (首版填 `initial`)

## 1. Purpose (目的)

一句話說明此模組存在的唯一理由。如果可以拆成兩個目的,就應該拆成兩個模組。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| Rxx | §y.z | 此模組如何體現該研究 |

來自 `docs/03_research_index.md`,**禁止**引用整篇論文而不指章節。純工程模組寫「無 (純工程)」。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| Mx.y 的事件 X | `{...}` | `{...}` |
| HTTP `/api/mx_y/...` | Pydantic Model | ... |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| Mx.y 訂閱的事件 | `{...}` | `{...}` |
| 寫入資料表 `mx_y_yyy` | SQL 欄位 | ... |

## 4. Dependencies

### 上游 (我依賴誰)

- Mx.y:為什麼

### 下游 (誰依賴我)

- Mx.y:為什麼

`[MVP]` 模組不可硬依賴 `[進階]` 模組 (CLAUDE.md 憲章)。

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 | 測試 |
| -------- | ---- | -------- | ---- |
| RISK-xx | 一句話描述 | 對應 `05_integration_risk_audit.md` | `test_...` |

若觸發新風險,**先**追加至 `05_integration_risk_audit.md`,再回此填表。

## 6. Requirements & Acceptance (需求與驗收)

每條需求有穩定編號,用 SHALL / MUST 敘述**可觀察的行為** (不綁實作),每條至少一個情境;**一個情境 = 一個測試**。

### REQ-Mx.y-01:<需求名稱>

系統 SHALL <行為>。

依據:`[Rxx: 關鍵字 §章節]` 風險:`RISK-xx`

#### Scenario:<情境名稱>

- **GIVEN** <前置狀態>
- **WHEN** <觸發>
- **THEN** <可斷言的結果>

測試:`testing/mx_y/test_<name>.py::test_<scenario>` (前端:`apps/desktop/tests/mx_y/<Name>.test.tsx`)

### REQ-Mx.y-02:…

## 7. Implementation Notes

### 7.1 演算法選擇

具體說明用什麼演算法、為什麼選它、論文章節在哪。

### 7.2 資料結構

具體 schema、Pydantic models、TypeScript interfaces。

### 7.3 異常處理

- 例外 1 → 處理方式 (必須寫 log;跨模組失敗寫 `raw_tracking_logs`;禁止靜默吞掉)

## 8. Anti-patterns (反模式)

明確列出**不可以做的事**,即使它看起來像捷徑。

- ❌ 不要 X (理由 + 引用 RISK-xx 或 Rxx)

## 9. Open Questions / 拍板紀錄

- `draft` 狀態:列出 `[NEEDS DECISION]` 問題,每個附建議。
- 轉為 `approved` 前:所有問題必須已拍板,改寫為「拍板:… (YYYY-MM-DD)」。
- 沒有問題時寫「無」— 不需要為了填表而製造問題。

## 變更紀錄

| 日期 | 版本 | change-id | 摘要 |
| ---- | ---- | --------- | ---- |
| YYYY-MM-DD | 1.0.0 | initial | 首版 |

---

## SPEC 撰寫 Checklist (轉 `approved` 前自我檢查)

- [ ] §1 Purpose 是單一職責,不能再拆
- [ ] §2 研究引用皆有章節;或明確寫「無 (純工程)」
- [ ] §3 Schema 用 Pydantic / TypeScript / JSON Schema,不可只寫散文
- [ ] §4 依賴是真實模組編號;MVP 無硬依賴進階模組
- [ ] §5 已 grep `05_integration_risk_audit.md`,即使結果為空也註明
- [ ] §6 每條需求有 `REQ-` 編號與至少一個 WHEN/THEN 情境,情境可直接寫成測試
- [ ] §8 至少 3 條反模式
- [ ] §9 沒有未拍板的 `[NEEDS DECISION]`
