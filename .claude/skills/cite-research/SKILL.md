---
name: cite-research
description: Use this skill when writing any code, comment, commit message, or design document that claims an architectural choice is "based on research" or "from a paper". This skill enforces the [Rxx §section] citation format and prevents vague or fabricated citations. Trigger this skill BEFORE writing the code, not after.
---

# Skill: Cite Research

## When to invoke

Trigger this skill whenever you are about to:

- Write a code comment that says "根據研究" / "based on the paper" / "為了避免 XYZ effect"
- Write a commit message that justifies a design decision
- Add a design rationale in a SPEC.md or pull request description
- Implement an algorithm whose origin is a research paper

If you are **not** writing code derived from research (e.g. pure CRUD, UI boilerplate, build tooling), **do not** invoke this skill.

## The three-step protocol

### Step 1: Identify the claim

What exactly are you about to claim? Reduce to a single sentence:

- 「我要實作 Agency 從 0.85 漸進降到 0.25」
- 「我要在 reflection form 強制留白主觀感受欄位」
- 「我要把焦慮狀態轉換為安撫語氣而非鏡像」

### Step 2: Find the source

Open `docs/03_research_index.md` and find the paper that supports the claim. The mapping table at the top of each entry tells you which modules consume each research.

If you cannot find a supporting paper:

- **STOP**. Do not invent a citation.
- Either change the claim to remove the research justification, or
- Mark the decision as "來自產品架構文件" with a TODO for the reviewer.

### Step 3: Format the citation

Use exactly this format:

```
[Rxx: 短關鍵字 §章節]
```

- `Rxx` = paper number (R01-R10), uppercase R
- `短關鍵字` = the key concept from the paper, in Chinese or English as it appears in the index
- `§章節` = the specific section in the paper

**Good examples**:

```python
# [R03: Echo Mode §3.2] Agency 漸進切換 5 步,絕不一步跳變
# [R08: 微摩擦力 §四.2] 強制 user_feeling 欄位非空
# [R07: POST §4.3] 原始程式碼絕不上雲,僅傳意圖向量
```

**Bad examples** (do not use):

```python
# 根據相關研究...                              ← 模糊
# 為了避免人設崩塌                              ← 沒引用
# 根據 R03                                     ← 沒章節
# [R11: ...]                                   ← R11 不存在
# Based on the paper                           ← 哪篇?
```

## Common citation combos

When implementing certain modules, you typically need multiple citations:

| 模組類型 | 標準引用組合 |
| -------- | ------------ |
| Persona 對話設計 | `[R03 §1, R05 §治療同盟, R09 §6.2 BDI]` |
| 隱私壓縮上雲 | `[R07 §POST, R07 §Eguard, R06 §7.4]` |
| 草稿與核准 | `[R08 §四, R08 §六, R10 §MindScape]` |
| 狀態推論 | `[R02 §HMM, R01 §POMDP+BKT, R06 §第四章]` |
| 圖譜建模 | `[R04 §冰山, R04 §NSVIF, R03 §ARPM]` |

## Self-check before commit

Before `git commit`, check:

- [ ] 每個架構決策都有 `[Rxx §y.z]` 或明確標記為「非學術依據」
- [ ] 沒有 `R11` 以上的編號 (目前只有 R01-R10)
- [ ] 沒有 `[R03]` 這種沒章節的引用
- [ ] 沒有「根據相關研究」「研究表明」「論文指出」這種無編號表達

Commit message 範本:

```
feat(M4.2): Echo Mode 阻抗消解控制器

實作 ToneState 狀態機與漸進 Agency 切換。

依據:
- [R03: Echo Mode §3.2] 5 步漸進切換
- [R03: ARPM §2] 切換必須通過 ARPM 監督
- 緩解 RISK-02 (Echo Mode + ARPM 衝突)
```

## When to push back on the user

If the user asks you to implement something that:

- claims research basis but you can't find it in `03_research_index.md`
- contradicts an existing research citation in another module
- removes a citation that was previously required

You must **stop and ask**:

> 「這個變更會移除/違反 `[Rxx §y.z]` 的引用。可否確認這是有意為之?如果是,要在哪裡記錄這個偏離?」

Do not silently comply. Citation hygiene is a project-level invariant.
