# docs/changes — 變更提案

> 流程說明見 `docs/DEV_WORKFLOW.md` §3。本目錄只放 **T2 Change / T3 New Module**;T0、T1 不開資料夾。

## 結構

```
docs/changes/
├── README.md                      ← 本檔 (含進行中 change 索引)
├── _templates/                    ← 新 change 從這裡複製
│   ├── proposal.md
│   ├── design.md                  (條件必要)
│   ├── tasks.md
│   └── specs/SPEC_NAME.delta.md
├── <change-id>/                   ← 進行中
│   ├── proposal.md
│   ├── design.md
│   ├── tasks.md
│   └── specs/M4_4_natural_elicitation_draft_SPEC.delta.md
└── archive/
    └── 2026-10-19-<change-id>/    ← 已合併進 docs/modules/ 的 change
```

## 規則

1. **現況規格**在 `docs/modules/`,**將要改的**在這裡。change 未歸檔前,不要直接改 `docs/modules/` 的既有需求 (T3 新建的 `draft` SPEC 除外)。
2. change-id:動詞開頭 kebab-case,含模組號,例 `m4-4-per-context-probe-limit`、`add-m4-7a-vault-reader`。
3. 一個 change 只解決一件事;可以跨多個 SPEC,但必須是同一個理由。
4. `proposal.md` 狀態流轉:`proposed → approved → implementing → done → archived`。

## 進行中的 change

| change-id | 模組 | 狀態 | 分支 |
| --------- | ---- | ---- | ---- |
| add-m0-5-gemini-free-tier-guard | M0.5 | implementing | (未建;目前在 feat/m4-2-episodic-memory-m4-6-topic-anchors 工作區,未提交) |
