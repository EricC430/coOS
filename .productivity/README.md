# .productivity/

Productivity plugin 的安裝目錄。**這是 coOS 專案專屬的，不是系統層級的。**

## 是系統性的還是個別專案的？

**個別專案的。** 這個 plugin 沒有全域註冊表——它只認「當前工作目錄」底下的 `TASKS.md`、`CLAUDE.md`、`memory/`。你在哪個資料夾啟動，它就管哪個資料夾。

所以現在的狀態是：

| 範圍 | 用什麼管 |
| --- | --- |
| **coOS 專案的工作項** | 這個目錄（`coOS/.productivity/`） |
| **生活、學業、健康、人脈** | Obsidian Vault（`Executive/Projects`、`Routines`、Daily note 的 Time Blocking）——**唯一真相，不搬過來** |

這個切分是刻意的，和 `docs/DESIGN_PHILOSOPHY_AUDIT.md` §3 的分層架構一致：Vault 是底層，任何平行的任務清單都會製造第二個真相來源。

### 之後想改成系統層級？

把 `TASKS.md` / `CLAUDE.md` / `memory/` 放到家目錄（例如 `C:\Users\chent\.productivity\`），並在那裡啟動。但除非你打算讓 Vault 退居二線，否則不建議——那會直接違反分層原則。

## 檔案

| 檔案 | 用途 |
| --- | --- |
| `TASKS.md` | Phase 1 工作項（僅此範圍） |
| `CLAUDE.md` | 工作記憶（minimal 版） |
| `memory/glossary.md` | 術語解碼表 |
| `memory/projects/coos.md` | coOS 現況、技術棧、已知痛點 |
| `memory/context/vault_substrate.md` | 底層契約（XP 規格、寫入路徑、Quick Capture 契約） |
| `dashboard.html` | 視覺化看板 |

## 兩個要注意的地方

**1. 這裡的 `CLAUDE.md` 不會被 Claude Code 自動載入。**
只有 repo 根目錄的 `CLAUDE.md`（專案憲章）會自動讀。這份是給 productivity plugin 用的工作記憶，兩者刻意分開——憲章是鐵則，工作記憶是脈絡。

若希望每次 session 都帶到，在根目錄 `CLAUDE.md` 末尾加一行即可：

```markdown
> 工作記憶與當前階段任務見 `.productivity/CLAUDE.md` 與 `.productivity/TASKS.md`。
```

（我沒有自動加——`CLAUDE.md` 是受管文件。）

**2. `/productivity:update` 預設找當前工作目錄的 `TASKS.md`。**
從 coOS 根目錄執行會找不到。執行時指明 `.productivity/`，或直接說「更新 `.productivity/TASKS.md`」。

## Dashboard 用法

用 Chrome 或 Edge 開啟 `dashboard.html`（需要 File System Access API，Firefox 與 Safari 不支援）：

1. 點 **Select TASKS.md** → 選 `coOS/.productivity/TASKS.md`
2. 記憶頁籤要求選資料夾 → 選 `coOS/.productivity/`

它會自動存檔並監看外部變更，你我改同一個檔都會同步。
