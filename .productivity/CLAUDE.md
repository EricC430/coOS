# Memory

> **範圍：coOS 專案，minimal 版。** 生活/學業的完整身分本體在 Obsidian Vault 的 `Governance/`，不在這裡複製。
> 這份檔案不會被 Claude Code 自動載入（只有 repo 根目錄的 `CLAUDE.md` 會）——見 `.productivity/README.md`。

## Me

Eric（陳廷翰）。中央大學資工系大三下。coOS 專案的唯一開發者，用 Claude Code 實作。

- 兩年前開始建 Obsidian「Personal Life OS」，coOS 是它的高階介面
- 論文/期末專題以 coOS 為主題，已經過一輪同儕審查（`reports/coOS_審查報告.md`）

## Projects

| 名稱 | 是什麼 |
| --- | --- |
| **coOS** | 多智能體 AI + 遊戲化 + 薩提爾冰山 + 邊緣雲端協同的個人目標管理系統。Tauri + React 前端、FastAPI + LangGraph 後端 |
| **Vault** / **底層** | `C:\Users\chent\Documents\Obsidian\Eric's Obsidian Vault`。coOS 的 Layer 0（System of Record），**不是要被取代的舊系統** |
| **Phase 1（底層接通）** | 當前階段。讓 coOS 讀懂 Vault 的「我是誰」，讓已核准的反思落回 Vault，且 Vault 仍可獨立手動編輯 |

## Terms

| 術語 | 意思 |
| --- | --- |
| `Mx.y` | coOS 模組編號。M0 基礎 / M1 感知 / M2 邊緣 / M3 UI / M4 邏輯 / M5 圖譜 / M6 DB / M7 素材 |
| `Rxx` | 研究論文編號（R01–R19），見 `docs/03_research_index.md`。引用格式 `[R08 §四.2]` |
| `RISK-xx` | 整合風險編號，見 `docs/05_integration_risk_audit.md` |
| `GAP-xx` / `DEVIATION-xx` | 實作缺口 / SPEC 偏離編號 |
| **L1 / L2 / L3** | 隱私三層。L1 明文（絕不上雲）/ L2 意圖向量 / L3 業務狀態 |
| **L0–L3 驗收階梯** | 與隱私層**同名但無關**。接通 / 契約 / 保真 / 體感，見 `PHASE1_SCOPE_AND_ACCEPTANCE.md` §3 |
| **底層 / 高階介面** | Vault = 底層 (Substrate)；coOS = 高階介面 (Interface & Runtime) |
| **微摩擦力** | `[R08 §四.2]`。刻意保留的填寫負擔，是 feature 不是 bug |
| **草稿與核准** | `[R08 §五]`。AI 生草稿、人核准；未核准不發 XP、不寫 Vault |
| **黃金樣本** | `testing/golden/`。使用者手寫的理想輸出，AI 不得生成或修改 |
| **ai.local** | iPad M1 上的 Gemma 4 E4B 邊緣推論服務 |
| **Eguard / DRIFT** | PII 遮蔽 / Prompt Injection 防禦（M2.3） |

## Preferences

- 回應**簡潔直接**，去掉不必要的解釋與贅字
- 中文為主，技術名詞保留英文
- 引用必須可溯源：`[Rxx §章節]`，禁止「根據相關研究」
- 實作前先讀 `docs/` 對應文件（見 repo 根目錄 `CLAUDE.md` 鐵則）
- 測試失敗只看 `tail -20`，不要把整段 stack trace 讀進 context
- Windows 環境，`.ini` / `pyproject.toml` 必須純 ASCII（cp950 locale）
- 個人原則寫在 Vault `Governance/Principles/`，其中最相關的是**最小可行迭代法則**：完成比完美重要，拒絕教學地獄

## Phase 1 鐵則（本階段專用）

1. 黃金樣本由使用者手寫，AI 不得新增或修改。實作與樣本不符時，預設是實作錯。
2. L2 保真驗收由使用者判定。AI 可產生 diff 報告，但不得在任何文件寫「L2 通過」。
3. 任何寫入 Vault 的行為必須經 `_System/.coos_inbox/` 契約。禁止 Python 直接改 `.md`，禁止呼叫 Templater API。
4. Closure Report 不得以「N passed / 0 failed」作為主要成果陳述。
