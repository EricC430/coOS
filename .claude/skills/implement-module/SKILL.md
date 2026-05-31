---
name: implement-module
description: Use this skill whenever the user asks to implement a coOS module identified by a Mx.y code (e.g. "實作 M4.2", "build the M3.3.3 reflection modal"). This skill enforces the read-before-code protocol: read research → check risks → read SPEC → write tests → write code. Trigger this for any module implementation task.
---

# Skill: Implement Module

## When to invoke

Trigger this skill when the user request contains any of:

- 「實作 Mx.y」「實作 [模組名稱]」
- 「build M4.5」「implement the persona controller」
- 「開始做 [功能名稱]」(若該功能對應某個 Mx.y)

If the task is bugfix in an existing module (not new implementation), use only Step 6-7 of this protocol.

## The seven-step implementation protocol

This is **mandatory order**. Do not skip steps.

### Step 1: Read the module's SPEC

```
view docs/modules/Mx_y_NAME_SPEC.md
```

If no SPEC exists, **stop**. Either:
- Ask the user to write a SPEC first using `docs/modules/_TEMPLATE_SPEC.md`
- Or offer to draft a SPEC by reading the research papers and risk audit

Do **not** start coding without a SPEC.

### Step 2: Read the research citations

From the SPEC's `## References` section, identify all `Rxx` papers. You can also cross-reference `docs/04_module_registry.md` for the module's full list of research and risk tags:

```
grep -A 50 "^### Mx.y" docs/04_module_registry.md
grep -A 30 "^## Rxx" docs/03_research_index.md
```

If the SPEC cites a paper but you don't understand the technique, **stop** and ask the user. Don't fake comprehension.

### Step 3: Invoke audit-integration skill

If this task touches 2+ modules (almost all module implementations do), invoke:

```
.claude/skills/audit-integration/SKILL.md
```

Walk through its four-step protocol. Output the audit summary to the user.

### Step 4: Write tests first

From SPEC's `## Acceptance Criteria` section, translate every criterion to a concrete test file:

- Python: `tests/m{x}_{y}/test_<name>.py`
- TypeScript: `apps/web/src/components/m{x}_{y}/<name>.test.tsx`

Tests must:

- Reference the research: `# [R03 §3.2] Echo Mode 漸進切換測試`
- Reference the risks: `@pytest.mark.integration_risk("RISK-02")`
- Initially fail (red phase of TDD)

Run the tests to confirm they fail for the right reasons:

```bash
pytest tests/m4_2/ -v
# Expected: tests fail with "module not implemented"
```

### Step 5: Implement

Now write the actual code. File naming follows CLAUDE.md §程式碼規範:

- `services/m4_2_persona/graph.py`
- `apps/web/src/components/m3_2_dashboard/RoleCarousel.tsx`
- `services/m4_2_persona/echo_mode.py`

Each file's header must include:

```python
"""
M4.2 — 擬真人設與心理狀態機

實作 SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
研究依據: [R03 §3, R05 §跨越恐怖谷, R09 §6.2]
緩解風險: RISK-02, RISK-03, RISK-06, RISK-08
"""
```

Each non-trivial function must cite which research it implements:

```python
def plan_transition(self, from_state, to_state):
    """
    [R03: Echo Mode §3.2] 5 步漸進切換

    Args/Returns/Raises 標準 docstring 略
    """
    ...
```

### Step 6: Iterate until tests pass

```bash
pytest tests/m4_2/ -v
# Iterate until: all pass

pnpm test --filter m3_2  # 前端模組
```

If a test still fails after 3 iterations, **stop and report**. Common reasons:

- SPEC 不夠精準 → 回 Step 1 與使用者澄清
- 測試本身寫錯了 → 修測試而非妥協實作
- 違反了 RISK 緩解 → 回 Step 3 重新規劃

### Step 7: Commit with full citation

```bash
git add ...
git commit -m "feat(M4.2): Echo Mode 阻抗消解控制器

實作 ToneState 狀態機與漸進 Agency 切換 (5 步)。

研究依據:
- [R03: Echo Mode §3.2] 漸進切換原則
- [R03: ARPM §2] 切換須通過 ARPM 監督
- [R05: 跨越恐怖谷] 副語言瑕疵注入

整合風險緩解:
- RISK-02: Echo Mode + ARPM 衝突 → ARPMValidator 認得合法切換空間
- RISK-03: 焦慮鏡像 → STATE_RESPONSE_MAP 強制反轉

測試: tests/m4_2/test_echo_mode.py (12 個案例皆通過)
"
```

## Skill composition examples

### 範例 1: 純粹的單模組實作

User: 「實作 M0.4 結構化日誌」

Protocol:
1. ✅ Read SPEC M0.4
2. ✅ No research citations (M0.4 是基礎設施)
3. ⏭️ Skip audit-integration (單模組,不過為了安全還是 grep 一下)
4. ✅ Write tests
5. ✅ Implement
6. ✅ Iterate
7. ✅ Commit (commit message 不需 research,但需註明 SPEC)

### 範例 2: 跨層整合實作

User: 「實作 M4.5 XP 自動結算」

Protocol:
1. ✅ Read SPEC M4.5
2. ✅ Read R08 §六 (IKEA 效應) from research index
3. ✅ **invoke audit-integration skill** — 發現 RISK-01
4. ✅ Write tests including `test_xp_blocked_without_approval`
5. ✅ Implement XP 守門員邏輯
6. ✅ Iterate
7. ✅ Commit with [R08 §六.1, RISK-01 緩解]

### 範例 3: 涉及多研究 + 多風險的複雜模組

User: 「實作 M4.2 完整模組 (含 Echo Mode 與副語言瑕疵)」

Protocol:
1. ✅ Read SPEC M4.2 (這是最詳細的範例 SPEC,長度約 250 行)
2. ✅ Read R03, R05, R09 對應章節
3. ✅ **invoke audit-integration** — 發現 RISK-02, RISK-03, RISK-06, RISK-08 共 4 個
4. ✅ Write tests for ALL acceptance criteria (約 8-12 個案例)
5. ✅ Implement LangGraph node by node (input_filter → reactance_detector → echo_mode → ...)
6. ✅ Iterate (預估需要 3-5 個迭代)
7. ✅ Commit with full citations and all 4 RISK references

## Anti-patterns

❌ **不要**在沒讀 SPEC 的情況下寫程式碼,即使你「覺得知道」這模組要做什麼
❌ **不要**跳過寫測試直接 implement
❌ **不要**為了讓測試過而調鬆 acceptance criteria,該是修實作而不是修測試
❌ **不要**在發現新的整合風險時自己默默繞過,要在 `05_integration_risk_audit.md` 追加 RISK-xx
❌ **不要**讓 commit message 缺少研究引用 (若該模組有 research basis)
❌ **不要**一次實作超過一個模組。每個 commit 對應一個模組或一個 sub-module

## When the user requests scope creep

If during implementation the user adds new requirements:

- 「順便也做 M4.X 吧」→ 拒絕,要求另開 task
- 「這個欄位改名好了」→ 若不在 SPEC,要求先更新 SPEC
- 「測試太嚴格了,放寬一點」→ 拒絕,SPEC 是合約

回應範本:

> 「此變更超出 M4.2 SPEC 範圍。建議:
> 1. 先完成當前 SPEC 定義的範圍
> 2. 將新需求記入 docs/modules/M4_2_*_SPEC.md §9 Open Questions
> 3. 完成後另開一個 task 處理
>
> 是否同意此流程?」
