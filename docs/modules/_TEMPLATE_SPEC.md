# SPEC 模板 (Module SPEC Template)

> 複製此檔為 `Mx_y_NAME_SPEC.md` 並填入內容。所有 MVP 模組都必須具備此 9 個區塊。

---

# Mx.y — 模組名稱

**標籤**:`[MVP]` 或 `[進階]`
**版本**:`1.0` / `draft`
**最後更新**:YYYY-MM-DD

## 1. Purpose (目的)

一句話說明此模組存在的唯一理由。如果可以拆成兩個目的,就應該拆成兩個模組。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R0x | §y.z | 此模組如何體現該研究 |
| R0x | §y.z | 同上 |

來自 `docs/03_research_index.md`,**禁止**在這裡引用整篇論文而不指章節。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M_AAA 的事件 X | `{...}` | `{...}` |
| HTTP `/api/...` | Pydantic Model | ... |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M_BBB 訂閱的事件 | `{...}` | `{...}` |
| 寫入資料表 `m6_x_yyy` | SQL 欄位 | ... |

## 4. Dependencies

### 上游 (我依賴誰)

- M_AAA: 為什麼
- M_BBB: 為什麼

### 下游 (誰依賴我)

- M_CCC: 為什麼
- M_DDD: 為什麼

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-xx | 一句話描述 | 對應 `05_integration_risk_audit.md` |

若觸發新風險,**先**追加至 `05_integration_risk_audit.md`,再回此填表。

## 6. Acceptance Criteria (驗收標準)

實作完成的定義。**先寫測試,後寫程式碼**。

```python
def test_xxx():
    """驗收條件 1"""
    ...

def test_yyy():
    """驗收條件 2"""
    ...
```

## 7. Implementation Notes

### 6.1 演算法選擇

具體說明用什麼演算法、為什麼選它、論文章節在哪。

### 6.2 資料結構

具體 schema、Pydantic models、TypeScript interfaces。

### 6.3 異常處理

- 例外 1 → 處理方式
- 例外 2 → 處理方式

## 8. Anti-patterns (反模式)

明確列出**不可以做的事**,即使它看起來像快捷方式。

- ❌ 不要 X (理由 + 引用 RISK-xx)
- ❌ 不要 Y (理由)

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [ ] 問題 1
- [ ] 問題 2

---

## SPEC 撰寫 Checklist

實作前自我檢查:

- [ ] §1 Purpose 是單一職責,不能拆解
- [ ] §2 至少 1 個 `Rxx` 引用 (若無,代表此模組可能不需要存在,或屬基礎設施)
- [ ] §3 Schema 用 Pydantic / TypeScript / JSON Schema,不可只寫散文
- [ ] §4 依賴是真實模組編號,不是「某個 service」
- [ ] §5 至少 grep 過 `05_integration_risk_audit.md`,即使結果為空
- [ ] §6 測試先於程式碼
- [ ] §8 至少 3 條反模式
- [ ] §9 至少 1 個開放問題 (沒有 → 表示思考不足,重來)
