# coOS 文件索引 (Documentation Index)

> 此檔案是 `docs/` 目錄的地圖。Claude Code 任何時候迷路了,先回到這裡。
> 本索引只列「現在有效」的文件;數量類資訊 (幾篇研究、幾條風險) 一律用下方 grep 現查,不寫死。

## 文件分層

```
CLAUDE.md                        ★ 憲章:不可違反的規則 + 任務分級路由 (session 自動載入)
docs/
├── 00_README.md                 ← 你正在讀的這個檔案
├── DEV_WORKFLOW.md              ★ 開發流程唯一權威 (分級 T0~T3、P1~P7、DoD、commit 規範)
├── DEV_PROCESS_AUDIT.md         ← 為什麼採用現行流程 (舊流程問題稽核)
├── 01_product_vision.md         ← 產品願景與六大支柱
├── 02_architecture.md           ← 系統架構 (四層、邊緣-雲端協同)
├── 03_research_index.md         ★ 研究論文索引 (Rxx),引用源頭
├── 04_module_registry.md        ★ 模組登記冊 (標籤、子模組、依賴、研究、風險)
├── 05_integration_risk_audit.md ★ 整合風險稽核 (RISK-xx)
├── 06_implementation_phases.md  ★ 路線圖:下一步做什麼的唯一權威
├── M5_ICEBERG_REDESIGN.md       ← M5 冰山層重新設計 (已拍板)
├── MVP_CLOSURE_REPORT.md        ← MVP 結案判定 (GO / NO-GO),進階模組的守門依據
├── SPEC_DEVIATION_REPORT.md     ← 既存偏離待辦 (行為與 SPEC 不一致)
├── IMPLEMENTATION_GAP_REPORT.md ← 既存缺口待辦 (未實作 / 沒接上 / stub)
├── modules/
│   ├── _TEMPLATE_SPEC.md        ← 新模組 SPEC 必須照此模板
│   └── Mx_y_<name>_SPEC.md      ← 每個模組一份,描述「現況已核准行為」
├── changes/                     ★ 進行中的變更提案 (proposal + spec delta + tasks)
│   ├── README.md                ← 進行中 change 索引
│   ├── _templates/
│   └── archive/                 ← 已合併進 SPEC 的 change
├── CLOSURE_REPORT_PHASE_*.md    ← 各 Phase 結案快照 (歷史,非路線圖)
├── REFINEMENT/ · LEGACY/        ← 歷史文件,不作為實作依據
├── brand/ · BRAND_GUIDE.md      ← 品牌素材
└── dev_logs/                    ← 開發紀錄 (歷史)
```

## 三類讀者三種讀法

### 🤖 給 Claude Code

1. `CLAUDE.md` (自動載入) → 依「改完之後 SPEC 還對嗎?」分級
2. `docs/DEV_WORKFLOW.md` 對應 Track 的段落
3. 定向讀取,不整份讀:

   ```bash
   grep -n -A 40 "^### M4.2 " docs/04_module_registry.md   # 模組條目
   grep -n -A 35 "^## R03 " docs/03_research_index.md      # 研究章節
   grep -n "M4\.2" docs/05_integration_risk_audit.md       # 相關風險
   ls docs/modules/ | grep M4_2                             # SPEC
   ls docs/changes/                                         # 進行中的 change
   ```

### 👤 給人類開發者

第一次接手請依序讀:

1. `01_product_vision.md` (5 分鐘) — 理解這是個什麼產品
2. `02_architecture.md` (15 分鐘) — 理解技術骨架
3. `DEV_WORKFLOW.md` §0~§2 (10 分鐘) — 理解怎麼提出與完成一個改動
4. `06_implementation_phases.md` (5 分鐘) — 理解下一步做什麼
5. `03_research_index.md` (略讀) — 理解每個架構決策背後的學術依據
6. `05_integration_risk_audit.md` (20 分鐘) — 避免踩到已知地雷

### 📋 給審稿者 / 投資人

1. `01_product_vision.md`
2. `02_architecture.md` §1~§2
3. `05_integration_risk_audit.md` (證明此團隊知道風險在哪)

## 現況數量 (現查)

```bash
grep -c "^## R[0-9]" docs/03_research_index.md        # 研究篇數
grep -c "^## RISK-" docs/05_integration_risk_audit.md  # 風險條數
ls docs/modules/*_SPEC.md | grep -vc TEMPLATE          # SPEC 份數
```

## 文件狀態約定

- SPEC 標頭 `狀態`:`draft` (可自由改) → `approved` (改行為須走 `docs/changes/`) → `implemented` → `deprecated`
- 新增 / 移除文件必須同步更新本索引

## 引用標記符號規範

| 符號 | 意義 | 範例 |
| ---- | ---- | ---- |
| `Mx.y` | 模組編號 | `M4.2` = 擬真人設與心理狀態機 |
| `Rxx` | 研究論文編號 | `R03` = 勸導式科技與動態人設一致性 |
| `Rxx §y.z` | 論文章節定位 | `R08 §四.2` = 微摩擦力章節 |
| `RISK-xx` | 整合風險編號 | `RISK-03` = 隱性狀態推論 + Persona 注入 → 焦慮鏡像 |
| `REQ-Mx.y-NN` | SPEC 需求編號 | `REQ-M4.4-03` |
| `<change-id>` | 變更提案 | `m4-4-per-context-probe-limit` |
| `DEVIATION-xx` / `GAP-xx` | 既存偏離 / 缺口 | `DEVIATION-01` |

## 文件間 cross-reference 規則

- 模組 SPEC **必須**在 `## 2. References` 列出引用的 `Rxx §章節`
- 風險稽核項**必須**列出觸發此風險的模組組合
- change 的 `proposal.md` **必須**列出受影響 SPEC 與觸發的 `RISK-xx`
