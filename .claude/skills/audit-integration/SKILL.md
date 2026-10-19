---
name: audit-integration
description: Use this skill BEFORE implementing any task that touches 2 or more modules (e.g. M4.5 + M3.3.3, M2.2 + M5.1, M4.2 + M4.8). This skill walks through docs/05_integration_risk_audit.md to detect "modules that work alone but break when combined" risks. Trigger this skill at the START of multi-module tasks, before writing code.
---

# Skill: Audit Integration

## When to invoke

通常由 skill `propose-change` 在 P2 呼叫 (見 `docs/DEV_WORKFLOW.md` §3)。**Always** run it before code is written for any task that meets any of these criteria:

- Task touches 2+ modules across different layers (M0~M7)
- Task adds a new dependency edge between modules
- Task modifies a Persona, a state machine, or a data flow
- Task involves real-time notifications, XP grants, or privacy boundaries

**Do not** invoke this skill for:

- Pure bugfix within a single module
- Documentation-only changes
- Test additions that don't change implementation

## The four-step audit protocol

### Step 1: Enumerate touched modules

List every module the task will modify or read from. Be precise:

```
Task: 實作 M4.5 XP 自動結算
Touched modules:
  - M4.5 (主目標)
  - M3.3.3 (讀 is_reviewed 旗標)
  - M6.4 (讀 daily_reflections)
  - M6.5 (寫入 user XP via ACID)
  - M4.6 (Observer 產的事件作為 XP 觸發源)
```

### Step 2: Grep the risk audit file

For each module in the list, grep `docs/05_integration_risk_audit.md`:

```bash
grep -E "(M4\.5|M3\.3\.3|M6\.4|M6\.5|M4\.6)" docs/05_integration_risk_audit.md
```

Note every `RISK-xx` that mentions any of these modules.

### Step 3: For each triggered risk, confirm

For every `RISK-xx` found, walk through its four parts:

1. **觸發組合**:does my task actually combine these modules in the risky way?
2. **失效機制**:what concretely goes wrong?
3. **緩解策略**:is the prescribed mitigation already implemented in my plan? If not, add it before writing code.
4. **驗收測試**:is there a `@pytest.mark.integration_risk("RISK-xx")` test? If not, write it first.

### Step 4: Write the audit summary into the proposal

由 skill `propose-change` 呼叫時,把結果寫進 `docs/changes/<change-id>/proposal.md` 的「整合風險」段。
**不要另外問使用者 y/n**——稽核結果隨提案一起在 G1 拍板 (DEV_WORKFLOW §3 P2),避免同一個任務問好幾次。

```
## 整合風險 (audit-integration 結果)

- **觸及模組**:M4.5, M3.3.3, M6.4, M6.5, M4.6
- **觸發的 RISK**:
  - RISK-01 (Earned XP vs Ambient XP 分流) — 緩解:本 change 實作 → 測試 test_xp_blocked_without_approval (待新增)
  - RISK-04 (Defer-to-Breakpoint vs 即時慶祝) — 緩解:已實作 → 測試 test_xp_grant_is_immediate (已存在)
- **未觸發但相關**:RISK-14 (本 change 不改 lifetime/current XP 同步)
- **新發現的風險**:無
```

每個「待新增」的測試,都要在 `tasks.md` 一致性分析表裡有對應任務。
在 change 流程之外單獨被呼叫時 (例如使用者只想知道風險),把同樣格式直接輸出給使用者即可。

## Finding risks by module — grep 為準

風險條目會持續新增,下方速查表**只是提示,可能過時**。每次以 grep 現查為準:

```bash
grep -n "^## RISK-\|^\*\*觸發組合" docs/05_integration_risk_audit.md   # 全部風險 + 觸發組合
grep -n "M4\.5\|M3\.3\.3" docs/05_integration_risk_audit.md            # 某些模組相關的 RISK 行號
grep -n -A 12 "^## 5. Known Risks" docs/modules/M4_5_*_SPEC.md         # SPEC 自己登記的風險
```

grep 到行號後只讀那幾段 RISK 全文,不要整份讀入。

| 模組 (提示) | 可能觸發的 RISK |
| ---- | --------------- |
| M1.2 (斷點) | RISK-04 |
| M2.2 (Gemma) | RISK-05, RISK-12 |
| M3.3.3 (草稿) | RISK-01 |
| M3.7 (社群) | RISK-12 |
| M3.8 (Wrapped) | RISK-10 |
| M3.11 (Gacha) | RISK-04, RISK-09 |
| M4.2 (Persona) | RISK-02, RISK-03, RISK-06, RISK-08 |
| M4.3 (角色隔離) | RISK-06 |
| M4.5 (XP 結算) | RISK-01 |
| M4.6 (Observer) | RISK-08, RISK-12 |
| M4.8 (隱性狀態) | RISK-03, RISK-06, RISK-09 |
| M4.9 (ARPM) | RISK-02 |
| M4.11 (ZPD 任務池) | RISK-07 |
| M4.13 (XP 質押) | RISK-07 |
| M5.1 (冰山假設庫) | RISK-05, RISK-12, RISK-19, RISK-21, RISK-23 |
| M5.2 (證據萃取) | RISK-05, RISK-06, RISK-19, RISK-21 |
| M5.3 (符號驗證) | RISK-05, RISK-21, RISK-23 |
| M5.4 (轉化歷程) | RISK-06, RISK-10, RISK-20 |
| M5.5 (介入規劃) | RISK-01, RISK-04, RISK-09, RISK-20, RISK-22, RISK-23 |
| M5.6 (指令編譯) | RISK-02, RISK-03, RISK-06, RISK-08, RISK-19, RISK-23 |
| M3.12 (冰山之鏡) | RISK-12, RISK-19, RISK-21, RISK-23 |
| M3.13 (小實驗卡) | RISK-01, RISK-04, RISK-12, RISK-22 |
| M0.5 (合成使用者模擬器) | RISK-24, RISK-25 |
| Voice input | RISK-11 |

## When risks are missing from the document

If your task touches modules but no RISK-xx covers the combination:

**Option A** — The combination is genuinely safe:
- Document this conclusion: 「本任務組合 (M4.X + M3.Y) 經審查無已知整合風險」
- Add a one-line note to `05_integration_risk_audit.md` under "已審查無風險的組合"

**Option B** — You discovered a new risk:
- Stop coding. Open `docs/05_integration_risk_audit.md`.
- Add a new `RISK-xx` entry following the four-part schema.
- Update the SPEC.md of each affected module's `Known Risks` table.
- Then proceed.

## When the user asks you to skip the audit

Do not silently skip. Respond:

> 「整合風險稽核是專案級不變式 (CLAUDE.md 憲章 第三條)。若您確認此次跳過,請說明理由,我會記錄為 'audit-skipped' 並在 git commit 中標記。」

如果使用者堅持跳過且給出理由,在 commit message 加 `[audit-skipped: <理由>]`,並 echo 給使用者一個警告。
