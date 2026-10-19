# Design:<change-id>

> **何時需要本檔**:跨 2+ 模組、schema 變更、新外部依賴 (套件 / 雲端服務)、研究推導的演算法、或存在 2 個以上可行方案。
> 其他情況刪除本檔,不要寫空殼。

## Context

現況與限制 (引用 SPEC 章節、既有程式碼位置 `path:line`)。

## Goals / Non-Goals

- Goals:
- Non-Goals:

## 方案比較

| 方案 | 做法 | 優點 | 缺點 | 風險 |
| ---- | ---- | ---- | ---- | ---- |
| A (建議) | | | | |
| B | | | | |

**決定**:A,因為……

## 資料流與介面

```
Mx.y ──(Pydantic Model / 事件名)──▶ Mx.z ──▶ 資料表 mx_y_...
```

- Pydantic / TypeScript 介面定義
- 新增的 `raw_tracking_logs` 事件名稱與欄位 (不含 L1 明文)

## 隱私分層

| 資料 | 層級 (L1/L2/L3) | 儲存 | 是否可能上雲 |
| ---- | --------------- | ---- | ------------ |

## Migration / 回滾

- Alembic revision (local / cloud 分開)
- 回滾步驟

## 未決問題

- (應在 G1 前清空,或移入 proposal 拍板項)
