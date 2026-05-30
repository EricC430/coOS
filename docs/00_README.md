# Life OS 文件索引 (Documentation Index)

> 此檔案是 `docs/` 目錄的地圖。Claude Code 任何時候迷路了,先回到這裡。

## 文件分層

```
docs/
├── 00_README.md              ← 你正在讀的這個檔案
├── 01_product_vision.md      ← 產品願景與六大支柱
├── 02_architecture.md        ← 系統架構 (四層、邊緣-雲端協同)
├── 03_research_index.md      ★ 10 篇研究論文索引,引用源頭
├── 04_module_research_matrix.md  ★ 模組 ↔ 研究映射矩陣
├── 05_integration_risk_audit.md  ★ 整合風險稽核 (12 條已知陷阱)
├── 06_implementation_phases.md   ← Phase 1~5 MVP 建構順序
└── modules/
    ├── _TEMPLATE_SPEC.md     ← 新模組 SPEC 必須照此模板
    ├── M0_infrastructure_SPEC.md
    ├── M1_sensors_SPEC.md
    ├── M2_edge_inference_SPEC.md
    ├── M3_ui_SPEC.md
    ├── M4_agents_SPEC.md     ← 已完整撰寫,作為示範
    ├── M5_graphrag_SPEC.md
    ├── M6_database_SPEC.md
    └── M7_assets_SPEC.md
```

## 三類讀者三種讀法

### 🤖 給 Claude Code (AI 助手)

實作任一模組的順序固定為:

1. 讀 `CLAUDE.md` (專案根目錄,session 啟動會自動讀)
2. 讀 `docs/04_module_research_matrix.md` 找到該模組對應的研究編號
3. 讀 `docs/03_research_index.md` 中該研究的細節
4. 讀 `docs/05_integration_risk_audit.md` 中與此模組相關的所有警告 (用 grep 模組編號)
5. 讀 `docs/modules/Mx_y_SPEC.md`
6. 開始實作,並在 commit message 引用 `[Rxx: ...]`

### 👤 給人類開發者

第一次接手請依序讀:

1. `01_product_vision.md` (5 分鐘) — 理解這是個什麼產品
2. `02_architecture.md` (15 分鐘) — 理解技術骨架
3. `06_implementation_phases.md` (5 分鐘) — 理解你應該先做什麼
4. `03_research_index.md` (45 分鐘,略讀) — 理解每個架構決策背後的學術依據
5. `05_integration_risk_audit.md` (20 分鐘) — 避免踩到 12 個已知地雷

### 📋 給審稿者 / 投資人

只需讀:

1. `01_product_vision.md`
2. `02_architecture.md` §1~§2
3. `05_integration_risk_audit.md` (證明此團隊知道風險在哪)

## 文件版本約定

- 上方標 `version: 1.0` 的是已定案,變更需走 PR
- 上方標 `version: draft` 的是討論中,可隨意改
- 任何文件變更必須同步更新此索引若新增/移除檔案

## 引用標記符號規範

| 符號 | 意義 | 範例 |
| ---- | ---- | ---- |
| `Mx.y` | 模組編號 | `M4.2` = 擬真人設與心理狀態機 |
| `Rxx` | 研究論文編號 | `R03` = 勸導式科技與動態人設一致性 |
| `Rxx §y.z` | 論文章節定位 | `R08 §四.2` = 微摩擦力章節 |
| `RISK-xx` | 整合風險編號 | `RISK-03` = Echo Mode + ARPM 衝突 |

## 文件間 cross-reference 規則

- 模組 SPEC **必須**在頂部 `## References` 區塊列出引用的 `Rxx`
- 風險稽核項**必須**列出觸發此風險的模組組合
- 任何新建文件必須更新本索引
