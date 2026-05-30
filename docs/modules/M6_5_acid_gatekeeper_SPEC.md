# M6.5 — ACID 交易守門員 (ACID Transaction Gatekeeper)

**標籤**:`[MVP]`
**版本**:`1.0` / `draft`
**最後更新**:2026-05-30

## 1. Purpose (目的)

提供 XP 發放、XP 質押、Gacha 抽卡等涉及「使用者資產異動」的操作一個原子性 (ACID) 交易層,確保在任何情境下 (crash、網路斷線、並發操作) 都不會出現 XP 憑空產生、重複發放、或扣除後未回滾的資產不一致。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §六.1 IKEA 效應 | `is_reviewed = true` 是 XP 發放的前置條件; 此模組負責原子性檢查 |
| R01 | §α-DPO Dropout | XP 質押失敗時的退款必須在同一交易中完成, 不可分步 |
| (無) | CLAUDE.md §不要做的事 第 6 條 | 「不要在缺少 `is_draft = false` 確認前就發放 XP」 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.5 XP 結算請求 | `XPSettlementRequest` | `{reflection_id: "uuid", user_id: "uuid", amount: 50}` |
| M4.13 XP 質押請求 | `StakeRequest` | `{user_id: "uuid", task_id: "uuid", amount: 100}` |
| M3.11 Gacha 抽卡請求 | `GachaDrawRequest` | `{user_id: "uuid", cost_xp: 30}` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `xp_ledger` 寫入 (M6.2) | DB INSERT | `{amount: 50, xp_type: "earned", ...}` |
| `users.current_xp` 更新 (M6.2) | DB UPDATE | `current_xp += 50` |
| `daily_reflections.xp_settled` 更新 (M6.4) | DB UPDATE | `xp_settled = true, xp_settled_at = NOW()` |
| 交易失敗回應 | `XPTransactionFailed` | `{reason: "draft_not_approved", code: "GATEKEEPER_001"}` |

## 4. Dependencies

### 上游 (我依賴誰)

- **M6.2** (PostgreSQL schemas)：操作 `users`, `xp_ledger` 表
- **M6.4** (daily_reflections)：讀取 `is_reviewed`, `xp_settled` 狀態
- **M0.3** (.env + Alembic)：依賴資料庫連線

### 下游 (誰依賴我)

- **M4.5** (XP 自動結算)：呼叫本模組的 `settle_earned_xp()` 方法
- **M4.13** (損失規避 XP 質押)：呼叫本模組的 `stake_xp()` / `refund_stake()` 方法
- **M3.11** (Gacha 抽卡)：呼叫本模組的 `deduct_xp_for_gacha()` 方法

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-01** | 草稿狀態下 XP 被提前發放 | `settle_earned_xp()` 第一步必須 SELECT FOR UPDATE 檢查 `is_reviewed = true`; 不符則 rollback |
| **RISK-07** | ZPD 邊緣任務質押後失敗 → 複合挫敗 | `stake_xp()` 必須先檢查 `task.zpd_zone != "edge"` 且 `user_estimated_success >= 0.70` |
| (無直接 RISK-xx) | 並發結算同一份反思 → 重複發放 XP | `xp_settled` 欄位 + `SELECT FOR UPDATE` 排他鎖; `xp_settled = true` 後拒絕再次結算 |
| (無直接 RISK-xx) | Gacha 扣費與開獎不在同一交易 → 扣了錢沒開到獎 | 扣費 + 開獎結果寫入必須在同一 DB transaction 中完成 |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m6_5/test_acid_gatekeeper.py

import pytest


class TestEarnedXPSettlement:
    def test_xp_blocked_for_draft(self, db, user, draft_reflection):
        """驗收條件 1: [RISK-01] 草稿反思不發放 XP"""
        result = settle_earned_xp(
            reflection_id=draft_reflection.id,
            user_id=user.id,
            amount=50,
        )
        assert result.success is False
        assert result.error_code == "GATEKEEPER_001"  # draft_not_approved
        assert user.current_xp == 0  # XP 不變

    def test_xp_granted_after_review(self, db, user, reviewed_reflection):
        """驗收條件 2: [RISK-01] 已核准反思成功發放 XP"""
        initial_xp = user.current_xp
        result = settle_earned_xp(
            reflection_id=reviewed_reflection.id,
            user_id=user.id,
            amount=50,
        )
        assert result.success is True
        assert user.current_xp == initial_xp + 50
        assert reviewed_reflection.xp_settled is True

    def test_no_double_settlement(self, db, user, reviewed_reflection):
        """驗收條件 3: 同一反思不可重複結算"""
        settle_earned_xp(reflection_id=reviewed_reflection.id, user_id=user.id, amount=50)
        result = settle_earned_xp(
            reflection_id=reviewed_reflection.id,
            user_id=user.id,
            amount=50,
        )
        assert result.success is False
        assert result.error_code == "GATEKEEPER_002"  # already_settled

    def test_concurrent_settlement_safe(self, db, user, reviewed_reflection):
        """驗收條件 4: 並發結算不會重複發放"""
        import asyncio
        results = asyncio.get_event_loop().run_until_complete(
            asyncio.gather(
                async_settle(reviewed_reflection.id, user.id, 50),
                async_settle(reviewed_reflection.id, user.id, 50),
            )
        )
        successes = [r for r in results if r.success]
        assert len(successes) == 1  # 只有一個成功


class TestXPStaking:
    def test_stake_blocked_for_edge_zpd(self, db, user, edge_task):
        """驗收條件 5: [RISK-07] 邊緣 ZPD 任務不可質押"""
        result = stake_xp(
            user_id=user.id,
            task_id=edge_task.id,
            amount=100,
        )
        assert result.success is False
        assert result.error_code == "GATEKEEPER_003"  # edge_zpd_forbidden

    def test_stake_deducts_and_ledger(self, db, user, safe_task):
        """驗收條件 6: 質押成功時 XP 扣除且記入 ledger"""
        user.current_xp = 200
        result = stake_xp(user_id=user.id, task_id=safe_task.id, amount=100)
        assert result.success is True
        assert user.current_xp == 100
        ledger_entry = get_latest_ledger(user.id)
        assert ledger_entry.amount == -100
        assert ledger_entry.xp_type == "staked"

    def test_insufficient_xp_blocks_stake(self, db, user, safe_task):
        """驗收條件 7: XP 不足時拒絕質押"""
        user.current_xp = 50
        result = stake_xp(user_id=user.id, task_id=safe_task.id, amount=100)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_004"  # insufficient_xp


class TestGachaTransaction:
    def test_gacha_atomic_deduct_and_reward(self, db, user):
        """驗收條件 8: Gacha 扣費與開獎在同一交易"""
        user.current_xp = 100
        result = deduct_xp_for_gacha(user_id=user.id, cost_xp=30)
        assert result.success is True
        assert user.current_xp == 70
        assert result.reward is not None  # 開獎結果必須在同一交易中產生

    def test_gacha_rollback_on_reward_failure(self, db, user):
        """驗收條件 9: 開獎失敗時 XP 退回"""
        user.current_xp = 100
        with mock_reward_generator_failure():
            result = deduct_xp_for_gacha(user_id=user.id, cost_xp=30)
        assert result.success is False
        assert user.current_xp == 100  # 退回
```

## 7. Implementation Notes

### 7.1 核心交易函式 — Earned XP 結算

```python
# services/m6_5_acid_gatekeeper/transactions.py

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


class XPGatekeeper:
    """
    [RISK-01, CLAUDE.md §6] ACID 交易守門員。
    所有 XP 異動必須走此類, 禁止直接操作 DB。
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def settle_earned_xp(
        self, reflection_id: str, user_id: str, amount: int
    ) -> TransactionResult:
        """
        [RISK-01] Earned XP 結算。
        原子性: SELECT FOR UPDATE → 檢查 → UPDATE → INSERT ledger → COMMIT
        """
        async with self._session.begin():
            # Step 1: 鎖定反思記錄
            reflection = await self._session.execute(
                select(DailyReflection)
                .where(DailyReflection.id == reflection_id)
                .with_for_update()  # 排他鎖
            )
            reflection = reflection.scalar_one_or_none()
            if not reflection:
                return TransactionResult(False, "GATEKEEPER_000", "reflection_not_found")

            # Step 2: [RISK-01] 守門檢查
            if reflection.is_draft or not reflection.is_reviewed:
                return TransactionResult(False, "GATEKEEPER_001", "draft_not_approved")
            if reflection.xp_settled:
                return TransactionResult(False, "GATEKEEPER_002", "already_settled")
            if not reflection.user_feeling or not reflection.user_action_plan:
                return TransactionResult(False, "GATEKEEPER_001", "missing_user_input")

            # Step 3: 更新使用者 XP
            await self._session.execute(
                update(User)
                .where(User.id == user_id)
                .values(current_xp=User.current_xp + amount)
            )

            # Step 4: 寫入 ledger
            ledger_entry = XPLedger(
                user_id=user_id,
                role_id=reflection.role_id,
                amount=amount,
                xp_type="earned",
                reason=f"daily_reflection_approved_{reflection.reflection_date}",
                source_module="M4.5",
                reflection_id=reflection_id,
            )
            self._session.add(ledger_entry)

            # Step 5: 標記已結算
            reflection.xp_settled = True
            reflection.xp_settled_at = datetime.now(timezone.utc)
            reflection.earned_xp = amount

            # COMMIT (由 async with self._session.begin() 管理)
            return TransactionResult(True)
```

### 7.2 XP 質押交易

```python
    async def stake_xp(
        self, user_id: str, task_id: str, amount: int
    ) -> TransactionResult:
        """[RISK-07] XP 質押, 須先通過 ZPD 與餘額檢查"""
        async with self._session.begin():
            # Step 1: [RISK-07] ZPD 檢查
            task = await self._get_task(task_id)
            if task.zpd_zone == "edge":
                return TransactionResult(False, "GATEKEEPER_003", "edge_zpd_forbidden")

            # Step 2: 鎖定使用者, 檢查餘額
            user = await self._session.execute(
                select(User).where(User.id == user_id).with_for_update()
            )
            user = user.scalar_one()
            if user.current_xp < amount:
                return TransactionResult(False, "GATEKEEPER_004", "insufficient_xp")

            # Step 3: 扣除 + 記帳
            user.current_xp -= amount
            self._session.add(XPLedger(
                user_id=user_id,
                amount=-amount,
                xp_type="staked",
                reason=f"task_stake_{task_id}",
                source_module="M4.13",
            ))

            return TransactionResult(True, staked_amount=amount)
```

### 7.3 Gacha 抽卡交易

```python
    async def deduct_xp_for_gacha(
        self, user_id: str, cost_xp: int
    ) -> TransactionResult:
        """Gacha 扣費 + 開獎必須在同一交易"""
        async with self._session.begin():
            # Step 1: 鎖定使用者, 檢查餘額
            user = await self._session.execute(
                select(User).where(User.id == user_id).with_for_update()
            )
            user = user.scalar_one()
            if user.current_xp < cost_xp:
                return TransactionResult(False, "GATEKEEPER_004", "insufficient_xp")

            # Step 2: 扣費
            user.current_xp -= cost_xp

            # Step 3: 開獎 (在同一交易中)
            try:
                reward = generate_gacha_reward(user_id)
            except GachaRewardGenerationError:
                # 開獎失敗 → 自動 rollback (async with begin() 管理)
                raise  # 觸發 rollback

            # Step 4: 記帳 + 記錄獎勵
            self._session.add(XPLedger(
                user_id=user_id,
                amount=-cost_xp,
                xp_type="gacha",
                reason=f"gacha_draw_{reward.id}",
                source_module="M3.11",
            ))

            return TransactionResult(True, reward=reward)
```

### 7.4 錯誤碼定義

| 錯誤碼 | 含義 | 觸發模組 |
| ------ | ---- | -------- |
| `GATEKEEPER_000` | 反思記錄不存在 | M4.5 |
| `GATEKEEPER_001` | 反思未核准 (草稿 / 缺使用者輸入) | M4.5 |
| `GATEKEEPER_002` | 反思已結算過 (防重複) | M4.5 |
| `GATEKEEPER_003` | 邊緣 ZPD 任務禁止質押 | M4.13 |
| `GATEKEEPER_004` | XP 餘額不足 | M4.13 / M3.11 |
| `GATEKEEPER_005` | 開獎失敗, 已退款 | M3.11 |

### 7.5 異常處理

- DB 連線斷線 mid-transaction → SQLAlchemy 自動 rollback; 前端收到 500 後 retry
- 死鎖 (兩個並發交易互相鎖定) → SQLAlchemy 偵測並拋 `OperationalError`; 重試 1 次
- Supabase Free tier 連線池耗盡 → 佇列等待 5 秒; 超時返回 503

## 8. Anti-patterns (反模式)

- ❌ **不要繞過 `XPGatekeeper` 直接操作 `users.current_xp` 或 `xp_ledger`**。所有 XP 異動必須走 gatekeeper,否則無法保證原子性。
  理由:直接操作可能在 crash 後產生 XP 與 ledger 不一致。

- ❌ **不要把守門檢查放在應用層 (Python) 而不加 DB 層鎖**。純 Python `if` 檢查無法防並發; 必須搭配 `SELECT FOR UPDATE`。
  理由:並發場景下兩個 request 同時讀到 `xp_settled = false` 後都寫入。

- ❌ **不要在 Gacha 開獎後才扣費** (先給獎再扣錢)。必須先扣費, 開獎失敗時 rollback。
  理由:先給獎後扣費在 crash 時會產生「免費抽卡」。

- ❌ **不要用 `UPDATE users SET current_xp = 新值` (絕對值覆蓋)**。必須用 `current_xp = current_xp + 差值` (相對增減)。
  理由:絕對值覆蓋在並發時會覆蓋其他交易的結果。

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [ ] **MVP 階段是否需要 XP 質押 (M4.13)?** 質押屬 `[進階]` 模組,但 ACID 守門員需預留介面。是否在 MVP 中只實作 `settle_earned_xp()` 和 `deduct_xp_for_gacha()`?
- [ ] **Earned XP 的計算公式由誰決定?** 守門員只負責原子性操作,XP 金額由 M4.5 傳入。M4.5 的計算公式是否需要另外 SPEC?
- [ ] **Gacha 抽卡是否在 MVP 範圍內?** `06_implementation_phases.md` 將 M3.11 列為進階模組。若不在 MVP,本模組的 `deduct_xp_for_gacha()` 可延後實作。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 有 R08, R01 引用
- [x] §3 Schema 用 Pydantic / SQL 描述
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,有 RISK-01, RISK-07 對應
- [x] §6 測試先於程式碼
- [x] §8 列出 4 條反模式
- [x] §9 列出 3 個開放問題
