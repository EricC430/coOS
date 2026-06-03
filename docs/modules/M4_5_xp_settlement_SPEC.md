# M4.5 — 零摩擦 XP 自動結算引擎 (Zero-Friction XP Settlement Engine)

**標籤**:`[MVP]`
**版本**:`1.0` / `draft`
**最後更新**:2026-06-03

## 1. Purpose (目的)

從數位足跡與已核准反思自動結算 XP，但**必須等使用者核准草稿後**才發放 Earned XP。同時排程清理長期未審的殭屍草稿，防止草稿堆積導致倦怠。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §六.1 IKEA 效應 | Earned XP **必須**等 `is_reviewed = true` 才發放，使用者付出填寫努力後才獲得獎勵 |
| R08 | §五 意圖脫鉤 | XP 結算邏輯與草稿生成 (M4.4) 分離，各自獨立運作 |
| R08 | §四.2 微摩擦力 | `user_feeling` + `user_action_plan` 必填是 XP 發放的前提 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M6.4 `daily_reflections` | DB Row | `{is_reviewed: true, user_feeling: "有進步", activity_minutes: 180, role_id: "role_csie"}` |
| M6.4 `daily_reflection_segments` | DB Rows | 時段級已核准 segment |
| M6.1 `raw_tracking_logs` | DB Rows | 活動分鐘數、專案分佈等原始遙測數據 |
| M6.5 ACID 守門員 API | Transaction context | 提供交易原子性保證 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M6.2 `xp_ledger` | Insert | `{user_id: "u_001", amount: 50, xp_type: "earned", source_module: "M4.5", reason: "daily_reflection_approved"}` |
| M6.2 `users.current_xp` + `users.lifetime_xp` | Update | [RISK-14] 同一交易中同時更新兩欄 |
| M6.4 `daily_reflections.xp_settled` | Update | `{xp_settled: true, xp_settled_at: "...", earned_xp: 50}` |
| M0.4 結構化日誌 | `LogEvent` | 記錄結算成功/失敗/殭屍淘汰事件 |
| M3.4 前端 SSE 通知 | `XPGrantedEvent` | `{type: "xp_granted", amount: 50, reason: "..."}` — 走 RISK-04 L1 即時慶祝通道 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M4.4** (自然套問與草稿)：提供 `daily_reflections` 草稿記錄
- **M6.4** (`daily_reflections` 表)：讀取 `is_reviewed` 狀態決定是否結算
- **M6.5** (ACID 守門員)：XP 異動必須走原子交易，確保 `xp_ledger` + `users` + `daily_reflections` 三表一致
- **M6.2** (`users`, `xp_ledger` 表)：寫入 XP 流水帳與更新餘額

### 下游 (誰依賴我)

- **M3.3** (日報模組)：顯示已結算的 XP 金額
- **M3.5** (成就展示)：XP 累計觸發徽章解鎖
- **M3.2** (儀表板)：XP 餘額與等級顯示

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-01** | 草稿狀態下 XP 被提前發放 → IKEA 效應失效 | 結算前**強制檢查** `is_reviewed=true` AND `user_feeling IS NOT NULL` AND `user_action_plan IS NOT NULL`；三者缺一則拒絕 |
| **RISK-14** | `current_xp` 與 `lifetime_xp` 同步失敗 → 等級倒退或幻覺升級 | 獲得 XP 時同一交易內同時更新兩欄；消費 XP 時只減 `current_xp`，`lifetime_xp` 唯增不減 |
| **RISK-13** | 已結算 segment 被軟刪除後 XP 記錄不一致 | 已結算的 segment `xp_settled=true` 後不允許自動回滾 XP；需人工審核 |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m4_5/test_xp_settlement.py

import pytest

class TestM4_5_1_XPSettlement:
    def test_xp_blocked_for_draft(self, db, user):
        """[RISK-01] 草稿狀態下 XP 必不發放"""
        draft = create_reflection(is_draft=True, is_reviewed=False)
        result = xp_engine.settle(draft, user)
        assert result.granted is False
        assert result.reason == "draft_not_approved"
        assert user.current_xp == 0

    def test_xp_blocked_without_user_feeling(self, db, user):
        """[RISK-01] is_reviewed=true 但 user_feeling 為空 → 拒絕"""
        reflection = create_reflection(
            is_draft=False, is_reviewed=True,
            user_feeling=None, user_action_plan="ok"
        )
        result = xp_engine.settle(reflection, user)
        assert result.granted is False

    def test_xp_blocked_without_action_plan(self, db, user):
        """[RISK-01] user_action_plan 為空 → 拒絕"""
        reflection = create_reflection(
            is_draft=False, is_reviewed=True,
            user_feeling="ok", user_action_plan=None
        )
        result = xp_engine.settle(reflection, user)
        assert result.granted is False

    def test_xp_granted_after_full_approval(self, db, user):
        """[R08 §六.1] 完整核准後 XP 發放"""
        reflection = create_reflection(
            is_draft=False, is_reviewed=True,
            user_feeling="有進步", user_action_plan="繼續",
            activity_minutes=120
        )
        result = xp_engine.settle(reflection, user)
        assert result.granted is True
        assert result.amount > 0
        assert user.current_xp == result.amount

    def test_xp_calculation_factors(self, db, user):
        """[決策] 核准後 XP 計算包含基礎分鐘數、目標對齊、學習筆記與停留時間加成"""
        # 1. 基礎情境：120 分鐘 = 50 XP
        r_base = create_reflection(
            is_draft=False, is_reviewed=True,
            user_feeling="ok", user_action_plan="ok",
            activity_minutes=120, user_learned=None
        )
        r_base.goal_aligned = False
        res_base = xp_engine.settle(r_base, user, approval_duration_seconds=0)
        assert res_base.amount == 50

        # 2. 對齊專家目標：1.5x 加成
        r_aligned = create_reflection(
            is_draft=False, is_reviewed=True,
            user_feeling="ok", user_action_plan="ok",
            activity_minutes=120, user_learned=None
        )
        r_aligned.goal_aligned = True
        res_aligned = xp_engine.settle(r_aligned, user, approval_duration_seconds=0)
        assert res_aligned.amount == 75  # 50 * 1.5

        # 3. 填寫學習筆記：+10 XP 固定紅利
        r_learned = create_reflection(
            is_draft=False, is_reviewed=True,
            user_feeling="ok", user_action_plan="ok",
            activity_minutes=120, user_learned="學會了生命週期"
        )
        r_learned.goal_aligned = False
        res_learned = xp_engine.settle(r_learned, user, approval_duration_seconds=0)
        assert res_learned.amount == 60  # 50 + 10

        # 4. 深思熟慮加成：停留 30 秒 (每秒 0.1 XP, +3 XP)
        r_duration = create_reflection(
            is_draft=False, is_reviewed=True,
            user_feeling="ok", user_action_plan="ok",
            activity_minutes=120, user_learned=None
        )
        r_duration.goal_aligned = False
        res_duration = xp_engine.settle(r_duration, user, approval_duration_seconds=30)
        assert res_duration.amount == 53  # 50 + 3

    def test_xp_settlement_is_idempotent(self, db, user):
        """重複結算同一反思不會重複發放"""
        reflection = create_approved_reflection(activity_minutes=120)
        xp_engine.settle(reflection, user)
        xp_before = user.current_xp
        xp_engine.settle(reflection, user)  # 重複呼叫
        assert user.current_xp == xp_before  # 不變

    def test_both_xp_columns_updated(self, db, user):
        """[RISK-14] current_xp 與 lifetime_xp 同時更新"""
        reflection = create_approved_reflection(activity_minutes=120)
        xp_engine.settle(reflection, user)
        assert user.current_xp > 0
        assert user.lifetime_xp == user.current_xp

    def test_lifetime_xp_never_decreases(self, db, user):
        """[RISK-14] 消費後 lifetime_xp 不減"""
        user.current_xp = 100
        user.lifetime_xp = 100
        deduct_xp(user, 30)
        assert user.current_xp == 70
        assert user.lifetime_xp == 100

    def test_ledger_entry_created(self, db, user):
        """每次結算必產生 xp_ledger 記錄"""
        reflection = create_approved_reflection(activity_minutes=120)
        xp_engine.settle(reflection, user)
        ledger = get_latest_ledger(user.id)
        assert ledger.source_module == "M4.5"
        assert ledger.xp_type == "earned"
        assert ledger.amount > 0

    def test_ambient_xp_capped_at_5_percent(self, db, user):
        """[RISK-01] Ambient XP ≤ 每日總 XP 的 5%"""
        daily_earned = 100
        ambient = xp_engine.calculate_ambient_xp(user, daily_earned)
        assert ambient <= daily_earned * 0.05

class TestM4_5_2_ZombieDraftCleanup:
    def test_stale_drafts_deleted_after_configured_days(self, db, user):
        """[決策] 根據使用者配置的天數（預設 7 天）自動淘汰未審草稿"""
        # 配置為 3 天
        user_settings = get_user_settings(user.id)
        user_settings.zombie_cleanup_days = 3
        
        old_draft = create_reflection(
            is_draft=True, created_at=days_ago(4)
        )
        recent_draft = create_reflection(
            is_draft=True, created_at=days_ago(2)
        )
        run_zombie_cleanup_cron(user.id)
        assert get_reflection(old_draft.id) is None
        assert get_reflection(recent_draft.id) is not None

    def test_approved_reflections_never_deleted(self, db, user):
        """[決策] 已核准的反思段落與記錄永不被殭屍清理刪除"""
        approved = create_approved_reflection(created_at=days_ago(30))
        run_zombie_cleanup_cron(user.id)
        assert get_reflection(approved.id) is not None
```

## 7. Implementation Notes

### 7.1 XP 結算守門員 (M4.5.1)

```python
# services/m4_5_xp_settlement/engine.py
# [R08 §六.1 + RISK-01] XP 結算核心邏輯

from dataclasses import dataclass

@dataclass
class SettlementResult:
    granted: bool
    amount: int = 0
    reason: str = ""

# XP 計算公式與參數決策
BASE_XP_PER_HOUR = 25          # 每小時基礎 XP
GOAL_ALIGNMENT_MULTIPLIER = 1.5   # 對齊專家目標的加成倍率
LEARNING_NOTE_BONUS = 10       # 填寫學習筆記 (user_learned) 的固定紅利

# 深思熟慮加成參數
MIN_REFLECTION_SECS = 15       # 觸發加成的最少秒數
MAX_REFLECTION_SECS = 300      # 計算加成的最大上限秒數
DURATION_XP_RATE = 0.1         # 每秒深思熟慮給予的 XP (e.g. 10秒 = 1 XP)

async def settle(reflection, user, approval_duration_seconds: float = 0) -> SettlementResult:
    """
    [RISK-01] 三重守門:
    1. is_reviewed must be True
    2. user_feeling must be non-empty
    3. user_action_plan must be non-empty
    """
    # Guard 1: 草稿不結算
    if reflection.is_draft or not reflection.is_reviewed:
        return SettlementResult(False, reason="draft_not_approved")

    # Guard 2: 微摩擦力欄位必填
    if not reflection.user_feeling or not reflection.user_feeling.strip():
        return SettlementResult(False, reason="missing_user_feeling")
    if not reflection.user_action_plan or not reflection.user_action_plan.strip():
        return SettlementResult(False, reason="missing_user_action_plan")

    # Guard 3: 冪等性 — 已結算不重複
    if reflection.xp_settled:
        return SettlementResult(False, reason="already_settled")

    # 1. 基礎活動 XP
    hours = (reflection.activity_minutes or 0) / 60
    base_xp = hours * BASE_XP_PER_HOUR

    # 2. 目標對齊加成 (由 M4.6 Observer 標註的 goal_aligned 旗標判定)
    is_aligned = getattr(reflection, "goal_aligned", False)
    multiplier = GOAL_ALIGNMENT_MULTIPLIER if is_aligned else 1.0
    calculated_xp = base_xp * multiplier

    # 3. 學習筆記紅利 (當 user_learned 非空且有實質輸入時發放)
    if reflection.user_learned and reflection.user_learned.strip():
        calculated_xp += LEARNING_NOTE_BONUS

    # 4. 深思熟慮加成 (核准時所花費的時間長度，防止掛機刷分設有上限)
    if approval_duration_seconds >= MIN_REFLECTION_SECS:
        clamped_duration = min(approval_duration_seconds, MAX_REFLECTION_SECS)
        duration_bonus = int(clamped_duration * DURATION_XP_RATE)
        calculated_xp += duration_bonus

    # 取整並設定最低參與獎勵 5 XP
    earned_xp = max(int(calculated_xp), 5)

    # [RISK-14] 原子交易: xp_ledger + users + daily_reflections (即時觸發)
    await m6_5_gatekeeper.settle_reflection_xp(
        user_id=user.id,
        reflection_id=reflection.id,
        amount=earned_xp,
    )

    return SettlementResult(True, amount=earned_xp, reason="approved")
```

### 7.2 Ambient XP (微量存在獎勵)

```python
# services/m4_5_xp_settlement/ambient.py
# [RISK-01] Ambient XP 額度極小，不需核准

AMBIENT_XP_DAILY_CAP_RATIO = 0.05  # ≤ 每日 Earned XP 的 5%
AMBIENT_XP_LOGIN = 2               # 連續登入獎勵

async def grant_ambient_xp(user_id: str):
    """
    Ambient XP: 純粹的存在獎勵 (如連續登入)。
    [RISK-01] 額度極小，不走草稿核准流程。
    """
    daily_earned = await get_today_earned_xp(user_id)
    cap = max(int(daily_earned * AMBIENT_XP_DAILY_CAP_RATIO), AMBIENT_XP_LOGIN)

    await m6_5_gatekeeper.grant_ambient_xp(
        user_id=user_id,
        amount=min(AMBIENT_XP_LOGIN, cap),
        reason="daily_login_streak",
    )
```

### 7.3 殭屍草稿淘汰 Cron (M4.5.2)

```python
# services/m4_5_xp_settlement/zombie_cleanup.py

from datetime import datetime, timedelta

DEFAULT_STALE_THRESHOLD_DAYS = 7

async def run_zombie_cleanup_cron(user_id: str):
    """
    清理過期未審的草稿，防止堆積導致倦怠。
    [決策] 預設為 7 天，但允許使用者自訂閾值。已被核准的 segment / reflection 永不刪除。
    """
    # 讀取使用者設定
    settings = await user_settings_service.get_settings(user_id)
    threshold_days = settings.zombie_cleanup_days or DEFAULT_STALE_THRESHOLD_DAYS
    
    cutoff = datetime.utcnow() - timedelta(days=threshold_days)
    stale_drafts = await db.fetch_all(
        "SELECT id FROM daily_reflections "
        "WHERE user_id = :user_id AND is_draft = TRUE AND created_at < :cutoff",
        {"user_id": user_id, "cutoff": cutoff.isoformat()}
    )
    for draft in stale_drafts:
        # 僅硬刪除 is_draft=True 的草稿紀錄，已核准的絕對不可刪除
        await db.execute(
            "DELETE FROM daily_reflections WHERE id = :id AND is_draft = TRUE",
            {"id": draft["id"]}
        )
        await log_event("zombie_draft_deleted", {"reflection_id": draft["id"]})

async def send_expiry_reminders(user_id: str):
    """
    [決策] 當草稿即將過期且使用者配置開啟通知時，發送提醒通知。
    """
    settings = await user_settings_service.get_settings(user_id)
    if not settings.enable_zombie_warning_notification:
        return
        
    threshold_days = settings.zombie_cleanup_days or DEFAULT_STALE_THRESHOLD_DAYS
    # 設定在過期前 1 天發出警報
    warning_cutoff = datetime.utcnow() - timedelta(days=threshold_days - 1)
    
    impending_drafts = await db.fetch_all(
        "SELECT id FROM daily_reflections "
        "WHERE user_id = :user_id AND is_draft = TRUE AND created_at < :warning_cutoff",
        {"user_id": user_id, "warning_cutoff": warning_cutoff.isoformat()}
    )
    
    if impending_drafts:
        await m3_9_notification_dashboard.send_system_notification(
            user_id=user_id,
            title="有未審核草稿即將過期",
            content=f"你有 {len(impending_drafts)} 筆未核准的草稿即將過期被淘汰，快來完成反思領取 XP！",
            notification_type="warning"
        )
```

### 7.4 異常處理

- **M6.5 交易失敗 (deadlock/timeout)** → [決策] 靜默重試 (Silent Retry)。自動寫入重試佇列，靜默嘗試直到發放成功，不主動彈窗通知使用者。
- **`users` 表行鎖等待超時** → `SELECT ... FOR UPDATE` 加 `NOWAIT`，失敗時排入下一批次重試。
- **XP 計算結果為負數** → 拒絕結算，記錄 `negative_xp_calculation` 異常事件
- **Supabase 雲端不可達** → 結算結果暫存本地 SQLite `pending_xp_sync`，恢復後同步

## 8. Anti-patterns (反模式)

❌ **不要在 `is_reviewed = false` 時發放任何 Earned XP**
   理由：CLAUDE.md 鐵律第 6 條；RISK-01；R08 IKEA 效應。這是**最重要的風險之一**。

❌ **不要讓 `mood_score` 影響 XP 計算**
   理由：使用者會為了多 XP 虛報心情，破壞數據真實性 (M6.4 反模式)。

❌ **不要在結算交易中只更新 `current_xp` 而忘記 `lifetime_xp`**
   理由：RISK-14。兩欄必須在同一交易中同時更新，否則等級計算失真。

❌ **不要讓 Ambient XP 超過每日 Earned XP 的 5%**
   理由：RISK-01 分流設計。Ambient XP 若過大，使用者不核准草稿也能拿到大量 XP → 草稿機制形同虛設。

❌ **不要硬刪除已結算的反思或 segment**
   理由：RISK-13。已結算的 XP 記錄不可自動回滾，需走軟刪除 + 人工審核。

## 9. Open Questions (已拍板決策)

- **[決策] XP 計算公式的具體參數**：
  除了依據每小時 `25 XP` 固定數值計算基礎 XP 外，還包含以下動態加成因子：
  1. **目標對齊加成 (Goal Alignment Multiplier)**：工作/討論若對齊專家目標，給予 `1.5x` 加成倍率。
  2. **學習筆記紅利 (Learning Note Bonus)**：核准時有寫入自己學到了什麼 (`user_learned` 非空)，給予 `+10 XP` 固定紅利。
  3. **深思熟慮加成 (Reflection Duration Bonus)**：依據核准時花費的時間長度，超過 15 秒（上限 300 秒）每秒給予 `0.1 XP` 加成。
- **[決策] 殭屍草稿的清理閾值**：
  預設為 7 天，允許使用者自訂天數。已被核准的 segment 絕不可刪除。可配置是否發送「草稿即將過期」的提醒通知。
- **[決策] 結算排程的觸發時機**：
  **即時結算**。當使用者於前端核准時，立即觸發結算引擎並發放 XP。
- **[決策] XP 結算失敗時的處理**：
  **靜默重試 (Silent Retry)**。系統自動重試發放至成功為止，不通知/打擾使用者。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責，不能拆解 — XP 結算 + 殭屍清理
- [x] §2 至少 1 個 `Rxx` 引用 — R08 ×3
- [x] §3 Schema 用 dataclass — `SettlementResult`
- [x] §4 依賴是真實模組編號 — M4.4, M6.4, M6.5, M6.2
- [x] §5 grep 過 `05_integration_risk_audit.md` — RISK-01, RISK-13, RISK-14
- [x] §6 測試先於程式碼 — 12 條驗收測試
- [x] §8 至少 3 條反模式 — 5 條
- [x] §9 至少 1 個開放問題 — 4 個

---

## 附錄：子模組拆分決策

> **結論：M4.5.1 + M4.5.2 合併為單一 SPEC，不分開寫。**

| 評估維度 | M4.5 子模組情況 |
| -------- | -------------- |
| **部署邊界** | 同一 FastAPI sidecar 內，共用 M6.5 ACID 守門員 |
| **技術棧** | 全是 Python (M4.5.1 結算邏輯 + M4.5.2 arq Cron) |
| **耦合度** | 中高 — M4.5.2 清理的殭屍草稿正是 M4.5.1 尚未結算的記錄；兩者共享 `daily_reflections` 表的讀寫 |
| **共享狀態** | 共用 `daily_reflections.is_draft` / `xp_settled` 狀態旗標 |
| **獨立部署** | 不建議 — 殭屍清理的閾值需與結算邏輯協調 (例如清理前必須確認沒有 pending 結算) |
| **子模組數** | 僅 2 個，拆分收益極低 |
