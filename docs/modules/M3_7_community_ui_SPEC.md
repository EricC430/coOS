# M3.7 — 社群與社會情懷模組 (Community, 前後端全鏈路)

**標籤**:`[進階]`
**版本**:`2.0` (擴充:前端 ↔ 後端 M4.13 ↔ 資料層 M6.6 全鏈路接線)
**最後更新**:2026-06-17

> **MVP 策略**: Phase 1~5 以 stub 卡片佔位即可 (見 §7.1)。本 SPEC 記錄完整前後端設計,供進階階段 (Phase 6b) 實作參考。MVP 閉環完成並產出 `docs/MVP_CLOSURE_REPORT.md` 後才可動工。
>
> **v2.0 變更**:v1.0 僅涵蓋前端 UI 與 stub。本版補齊 (1) M6.6 完整資料表 schema、(2) M4.13 後端業務邏輯契約、(3) FastAPI 路由與 SSE 接線、(4) 前後端資料流時序圖、(5) §9 開放問題已由使用者拍板,轉為 §10 已定案決策。

---

## 1. Purpose

以「社交情境隔離」為核心設計原則,提供同儕驗證、公開承諾、XP 質押對賭的社群介面——讓社會情懷的正向外部壓力在「使用者主動選擇的情境」下發揮效果,而非強迫性的社交曝光。

### 1.1 線框圖對應 (軟體介面構想.pdf §4 Community)

PDF 原稿確認以下 Bento Grid 版面結構:

```text
┌──────────────────────────────────────────────────────┬──────────────┐
│                   Community                          │ [Interview   │
│                                                      │  Preparer]   │
│  ┌──────────────────────┬───────────────────────┐   │              │
│  │ Goal / Vision /      │ Weekly/Monthly         │   │ [Total       │
│  │ Codex / Quotes /     │ Community Challenges   │   │  Strangers]  │
│  │ Rules                │                        │   │              │
│  ├──────────────────────┴──────┬────────────────┤   │ [Friend      │
│  │ Posts / Achievements        │ Tasks          │   │  Group]      │
│  │                             │ (to claim)     │   │              │
│  │ 🔵 Boyu 達成了 ... 成就     │                │   │ [Cooking     │
│  │                             │ Commitments    │   │  Lovers]     │
│  │ 🔵 Jacky 分享了鼓勵的話    ├────────────────┤   │              │
│  │    ──────────────────       │ Validation     │   │ [Study       │
│  │                             │                │   │  Group]      │
│  └─────────────────────────────┴────────────────┘   │              │
└──────────────────────────────────────────────────────┴──────────────┘
```

**版面細節** (來自 PDF):

- **整體佈局**: Bento Grid (不規則但對齊的區塊) + 右側垂直子社群導覽列
- **左上 — 社群共識區** (靜態展示): 標籤 `Goal / Vision / Codex / Quotes / Rules`;切換子社群時內容更新
- **右上 — 定期挑戰區**: `Weekly/Monthly Community Challenges`;挑戰內容由 M3.7.6 三來源生成 (見 §10.4)
- **左下 — 成就貼文動態牆** (`Posts / Achievements`): 條列式動態卡片,每則帶頭像圓圈;即時更新 (SSE)
- **右下 — 行動承諾區**: 左格 `Tasks (to claim)` + 右格 `Commitments` (上) / `Validation` (下),構成 `Tasks → Commitments → Validation` 閉環
- **最右側 — 子社群垂直導覽列**: 垂直線串聯圓形節點;點選後左側所有區塊同步切換對應社群資料

### 1.2 v2.0 新增:全鏈路範圍

本 SPEC 涵蓋三層完整接線:

```text
   [前端 M3.7]              [後端 M4.13]                 [資料層 M6.6]
  React + Zustand   <-->   FastAPI + LangGraph    <-->   PostgreSQL (L3)
  ─────────────           ──────────────────           ─────────────
  CommunityCarousel        M4.13.3 跨社群隔離中介        communities
  PostsFeed (SSE)          M4.13.2 同儕驗證閉環          community_members
  StakeXPInterface         M4.13.1 質押扣管 (→ M6.5)     social_posts
  ChallengeBoardPanel      M4.13.4 挑戰生成 (AI 審核)    validations
  SocialPressureToggle     (讀 M4.8 焦慮門禁)            stakes
                                                        challenges
```

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R09 | §第四章 SDT 在 AI 教練中的應用 | 同儕驗證滿足 SDT「連結」需求;公開承諾強化外部問責 (Fogg B=MAP 的 Prompt) |
| R09 | §第三章 / 病態使用風險 | 社交壓力切換器 (陌生人/朋友圈) 必須讓使用者可主動降低社交壓力強度 |
| R01 | §α-DPO Dropout 危機 | XP 質押對賭必須防範「質押失敗 + 社群羞辱」複合 Dropout 誘因;僅 high-confidence 任務可質押 |
| R07 | §第五章 嵌入逆向攻擊 | 社群貼文走草稿核准 + Eguard 過濾,防止 Observer 推論結果經貼文側通道洩漏 |
| R08 | §草稿與核准 | 貼文與挑戰皆 `is_draft` 預設,使用者/管理員核准後才公開 (微摩擦力) |

## 3. Inputs / Outputs

### 3.1 前端 Inputs (M3.7 從後端讀取)

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| `GET /api/m6_6/communities` | `CommunityRead[]` | `[{ id, name, type, member_cap, member_count, is_member }]` |
| `GET /api/m6_6/communities/{id}/posts` | `SocialPostRead[]` | `[{ id, author_display, content, likes_count, kind, created_at }]` |
| `GET /api/m6_6/communities/{id}/codex` | `CommunityCodex` | `{ goal, vision, codex, quotes[], rules[] }` |
| `GET /api/m6_6/communities/{id}/challenges` | `ChallengeRead[]` | `[{ id, title, period, source, status, progress }]` |
| `GET /api/m6_6/communities/{id}/commitments` | `CommitmentRead[]` | `[{ id, task_title, state, stake_id }]` |
| `GET /api/m6_6/stakes` | `StakeRead[]` | `[{ id, xp_amount, deadline, status, task_title }]` |
| SSE `GET /api/m6_6/stream?community_id=` | `CommunityEvent` | `{ type: "COMMITMENT_VALIDATED", post_id }` |
| M3.1 `xpBalance` (Zustand) | `number` | 質押餘額確認 (前端門禁) |
| M4.8 `implicitState` (Zustand) | `{ label, confidence }` | 焦慮門禁 (RISK-09) |

### 3.2 前端 Outputs (M3.7 寫到後端)

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `POST /api/m6_6/communities` | `CommunityCreate` | `{ name, type, theme, member_cap }` (使用者自建) |
| `POST /api/m6_6/communities/join` | `CommunityJoin` | `{ mode: "theme_random" \| "system_random", theme? }` |
| `POST /api/m6_6/posts/draft` | `SocialPostDraft` | `{ community_id, content, revealed_metrics }` → 回傳含 `privacy_warning` |
| `POST /api/m6_6/posts/publish` | `{ draft_id }` | 使用者明確核准後才寫入 + 上雲 |
| `POST /api/m6_6/stakes` | `StakeCreate` | `{ task_id, xp_amount, deadline, community_id }` |
| `POST /api/m6_6/validations` | `ValidationCreate` | `{ post_id, evidence_url? }` (混合:可選證據) |
| `POST /api/m6_6/challenges/{id}/approve` | `{ edits? }` | 管理員審核 AI 生成挑戰 |

### 3.3 後端 Outputs (M4.13 → 其他模組)

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M6.5 ACID 守門員 (質押扣管) | `XpHoldRequest` | `{ user_id, amount, reason: "stake_hold", source_module: "M4.13" }` |
| M2.3 Eguard (貼文上雲前過濾) | `SanitizeRequest` | `{ text: content }` → `{ sanitized, leaked_spans }` |
| `raw_tracking_logs` (M0.4) | `TrackingLog` | `{ source: "M3.7", event: "community_interaction", type }` |

## 4. Dependencies

### 上游 (我依賴誰)

- **M4.13** (損失規避與同儕驗證引擎):質押扣管 (M4.13.1)、同儕驗證閉環 (M4.13.2)、跨社群權限隔離中介 (M4.13.3)、挑戰生成與審核 (M4.13.4)
- **M6.6** (社群實體擴充):社群、成員、貼文、驗證、質押、挑戰六張資料表
- **M6.5** (ACID 守門員):質押 XP 的扣管/退還/沒收必須走原子交易,絕不繞過
- **M2.3** (Eguard):貼文 `content` 上雲前的隱私過濾
- **M4.8** (隱性狀態):焦慮偵測,作為被動質押邀請的封鎖門禁 (RISK-09)
- **M3.1** (global store):`xpBalance`、`implicitState`
- **M0.4** (結構化日誌):所有社群互動寫入 `raw_tracking_logs`

### 下游 (誰依賴我)

- **M4.13**:M3.7 的 UI 動作 (質押/驗證/發文) 觸發 M4.13 後端業務邏輯
- **M4.6** (Observer):Observer 自動發現的成就以 `visibility="private"` 寫入,等待 M3.7.5 手動核准升級為公開貼文

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-12** | Observer 推論的成就作為貼文上雲,側通道洩漏使用者行為 | (1) M3.7.5 成就貼文走手動核准流程;Observer 自動成就預設 `visibility="private"`。(2) **貼文上雲前後端強制過 M2.3 Eguard**,若 `leaked_spans` 非空則退回草稿要求使用者修改 |
| **RISK-07** | XP 質押 + ZPD 任務失敗 = 複合 Dropout 挫敗 | M3.7.8 前端禁用 (`userEstimatedSuccess < 0.70` 或 `zpd_zone == "edge"`) + **後端 M4.13.1 經 M6.5 同樣門禁,違反拋 `StakingForbidden`** (雙重門禁,前端可繞後端不可繞) |
| **RISK-09** | 高焦慮狀態下社群壓力加劇病態使用 | (1) M3.7.3 社交壓力切換器在 M4.8 偵測焦慮時建議「切換到陌生人模式降低壓力」(不強制)。(2) **被動質押邀請 / 挑戰推播在焦慮狀態絕對不送**;主動按鈕放行但顯示提示 |
| **RISK-18** | M4.13.4 AI 週期挑戰生成器讀社群歷史生成文案,聚合統計在小群組中可能退化為個人指名,比 RISK-12 更隱蔽 (使用者從未主動發布) | (1) `build_challenge_context()` 型別層級鎖死 `privacy_layer="L3"`,`raw_transcripts`/`intent_vectors` 必為空。(2) AI 生成挑戰預設 `is_draft=true`、`status="pending_review"`,**管理員審核後才 active**。(3) `member_cap ≤ 3` 的小群組使用保守措辭模板,避免統計值退化為指名 |

> 本任務組合 `M3.7 + M4.13 + M6.6 + M6.5 + M4.8 + M4.6` 已經 `audit-integration` 稽核 (2026-06-17),觸發 RISK-07 / RISK-09 / RISK-12 / RISK-18,緩解策略均已納入本 SPEC §5 / §7,並對應 §6 測試。RISK-18 為本次稽核後新增至 `05_integration_risk_audit.md` 的條目。

## 6. Acceptance Criteria

> **注意**:以下測試僅在進階階段 (Phase 6b) 動工前需要通過。MVP 階段測試僅確認 stub 卡片正確佔位。

### 6.1 前端測試 (vitest, `tests/m3_7/community_ui.test.ts`)

```typescript
describe("MVP Stub 驗收", () => {
  it("M3.7 所有子模組渲染 stub 佔位卡片,不報錯", () => {
    render(<CommunityUI stubMode={true} />);
    expect(screen.getByTestId("community-stub")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("M3.7.2 社交隔離子社群切換器 (進階)", () => {
  it("右側垂直 Carousel 切換子社群後正確載入對應貼文", async () => {
    render(<CommunityUI />);
    fireEvent.click(screen.getAllByTestId("community-item")[1]);
    await waitFor(() => {
      expect(screen.getByTestId("posts-feed")).toHaveAttribute(
        "data-community-id", mockCommunities[1].id
      );
    });
  });
});

describe("M3.7.3 社交壓力切換器 (進階 — RISK-09)", () => {
  it("切換到陌生人模式後貼文作者顯示匿名化", () => {
    render(<SocialPressureToggle mode="stranger" posts={mockPosts} />);
    screen.getAllByTestId("post-author").forEach((a) =>
      expect(a).toHaveTextContent("匿名"));
  });

  it("M4.8 偵測焦慮時,非強制地建議切換陌生人模式", () => {
    render(<SocialPressureToggle implicitState={{ label: "anxiety", confidence: 0.8 }} />);
    expect(screen.getByTestId("destress-suggestion")).toBeInTheDocument();
    expect(screen.queryByTestId("forced-stranger-mode")).not.toBeInTheDocument();
  });
});

describe("M3.7.5 成就貼文 (進階 — RISK-12)", () => {
  it("Observer 自動成就預設 visibility=private,不出現在動態牆", () => {
    render(<PostsFeed posts={[mockPrivateAchievement]} />);
    expect(screen.queryByTestId("achievement-post")).not.toBeInTheDocument();
  });

  it("手動發布成就時顯示隱私警告說明公開內容", async () => {
    render(<AchievementPublishModal achievement={mockAchievement} />);
    fireEvent.click(screen.getByTestId("publish-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("privacy-warning")).toHaveTextContent("此貼文將公開以下資訊");
    });
  });
});

describe("M3.7.8 XP 質押介面 (進階 — RISK-07)", () => {
  it("質押按鈕在任務成功率 < 70% 時顯示警示並禁用", () => {
    render(<StakeButton task={mockLowSuccessTask} userEstimatedSuccess={0.5} />);
    expect(screen.getByTestId("stake-btn")).toBeDisabled();
    expect(screen.getByTestId("stake-warning")).toBeInTheDocument();
  });

  it("質押餘額不足時禁用 (讀 M3.1 xpBalance)", () => {
    render(<StakeButton task={mockTask} xpBalance={50} requestedAmount={100} />);
    expect(screen.getByTestId("stake-btn")).toBeDisabled();
  });
});
```

### 6.2 後端測試 (pytest, `testing/m4_13/test_community_engine.py`)

```python
import pytest

@pytest.mark.integration_risk("RISK-07")
def test_edge_zpd_blocks_staking():
    """RISK-07: 邊緣 ZPD 任務不可質押 (後端門禁,前端可繞後端不可)"""
    task = make_task(zpd_zone="edge", success_prob=0.4)
    with pytest.raises(StakingForbidden):
        m4_13.create_stake(task=task, amount=100, user_estimated_success=0.4)

@pytest.mark.integration_risk("RISK-07")
def test_low_confidence_blocks_staking():
    """RISK-07: 主觀成功率 < 0.70 不可質押"""
    with pytest.raises(StakingForbidden):
        m4_13.create_stake(task=make_task(), amount=100, user_estimated_success=0.5)

def test_stake_hold_goes_through_acid_gatekeeper():
    """質押扣管必須經 M6.5 ACID,絕不直接改 current_xp"""
    stake = m4_13.create_stake(task=make_task(), amount=100, user_estimated_success=0.8)
    assert m6_5.last_hold.reason == "stake_hold"
    assert m6_5.last_hold.source_module == "M4.13"

@pytest.mark.integration_risk("RISK-12")
def test_post_content_passes_eguard_before_publish():
    """RISK-12: 貼文上雲前必過 Eguard,洩漏 span 非空則退回草稿"""
    draft = m4_13.draft_post(community_id=CID, content="我用 OpenStack 解了 30 天 RL 題")
    result = m4_13.publish_post(draft_id=draft.id)
    assert result.eguard_passed is True
    # 若 leaked_spans 非空:
    assert result.status in ("published", "returned_to_draft")

@pytest.mark.integration_risk("RISK-12")
def test_observer_achievement_defaults_private():
    """RISK-12: Observer 自動成就預設 private,不自動上雲"""
    ach = observer.detect_achievement(...)
    assert ach.default_visibility == "private"
    draft = m4_13.propose_social_post(ach)
    assert draft.requires_explicit_publish is True

def test_cross_community_isolation():
    """M4.13.3: 讀書會貼文不可出現在陌生人社群 feed"""
    posts = m4_13.get_feed(community_id=STUDY_GROUP_ID, requester=USER)
    assert all(p.community_id == STUDY_GROUP_ID for p in posts)

def test_member_cap_enforced():
    """§10.1: 成員上限 (2~8) 達上限時拒絕加入"""
    community = make_community(member_cap=2, member_count=2)
    with pytest.raises(CommunityFull):
        m4_13.join_community(community_id=community.id, user=NEW_USER)

@pytest.mark.integration_risk("RISK-09")
def test_anxiety_blocks_passive_stake_invite():
    """RISK-09: 焦慮狀態下不主動推播質押邀請"""
    with patch_implicit_state(label="anxiety", confidence=0.8):
        assert m4_13.can_push_stake_invite(USER) is False

@pytest.mark.integration_risk("RISK-18")
def test_ai_challenge_reads_only_l3_aggregates():
    """RISK-18: AI 生成挑戰僅讀 L3 聚合,不碰任何成員 L1/L2"""
    ctx = m4_13.build_challenge_context(community_id=CID)
    assert ctx.privacy_layer == "L3"
    assert ctx.raw_transcripts == []
    assert ctx.intent_vectors == []

@pytest.mark.integration_risk("RISK-18")
def test_ai_challenge_requires_admin_approval():
    """RISK-18 / §10.4: AI 生成挑戰預設 is_draft=True,管理員核准前不公開"""
    ch = m4_13.generate_challenge(community_id=CID)
    assert ch.is_draft is True
    assert ch.status == "pending_review"

@pytest.mark.integration_risk("RISK-18")
def test_small_community_uses_conservative_challenge_template():
    """RISK-18: member_cap<=3 的小群組用保守措辭模板,避免統計值退化為指名"""
    small_community = make_community(member_cap=3, member_count=2)
    ch = m4_13.generate_challenge(community_id=small_community.id)
    assert ch.template_tier == "conservative"
```

## 7. Implementation Notes

### 7.1 MVP Stub 實作 (不變,保留)

```tsx
// apps/desktop/src/components/m3_7_community/index.tsx
export function CommunityUI({ stubMode = true }: { stubMode?: boolean }) {
  if (stubMode) {
    return (
      <div data-testid="community-stub" className="...">
        <p>社群功能將在進階階段開放</p>
      </div>
    );
  }
  return <FullCommunityUI />;   // Phase 6b
}
```

### 7.2 子模組結構 (進階階段)

```text
apps/desktop/src/components/m3_7_community/
  ├── index.tsx                  # stub / 完整版切換 (已存在)
  ├── FullCommunityUI.tsx        # M3.7.1 Bento Grid 組裝
  ├── BentoGridLayout.tsx        # M3.7.1 版面
  ├── CommunityCarousel.tsx      # M3.7.2 右側垂直 Carousel + 切換社群
  ├── SocialPressureToggle.tsx   # M3.7.3 陌生人/朋友圈 + 焦慮建議
  ├── CommunityCodexPanel.tsx    # M3.7.4 Goal / Vision / Codex
  ├── PostsFeed.tsx              # M3.7.5 SSE 動態牆 + 隱私核准
  ├── ChallengeBoardPanel.tsx    # M3.7.6 三來源挑戰展板
  ├── CommitmentClosedLoop.tsx   # M3.7.7 Tasks → Commitments → Validation
  ├── StakeXPInterface.tsx       # M3.7.8 質押 (前端門禁)
  └── api.ts                     # fetch wrappers + useCommunityStream (SSE)

services/m4_13_community_engine/
  ├── __init__.py
  ├── routes.py                  # APIRouter prefix=/api/m6_6 (在 main.py include)
  ├── stake_engine.py            # M4.13.1 質押扣管 (→ M6.5)
  ├── validation_loop.py         # M4.13.2 同儕驗證閉環
  ├── isolation_middleware.py    # M4.13.3 跨社群權限隔離
  ├── challenge_generator.py     # M4.13.4 AI 挑戰生成 + 審核流
  ├── schemas.py                 # Pydantic v2 request/response models
  └── stream.py                  # SSE event broker (community-scoped)

services/m6_6_community/
  ├── __init__.py
  ├── models.py                  # SQLAlchemy 2.0 ORM (L3 cloud PostgreSQL)
  └── repository.py              # CRUD + member_cap / isolation queries
```

### 7.3 M6.6 資料表 Schema (L3 雲端 PostgreSQL)

> 全部屬 **L3 業務狀態**,可跨裝置同步。**禁止承載 L1 逐字稿或 L2 可還原意圖向量** (CLAUDE.md 隱私三層)。

```sql
-- M6.6.1 社群實體
CREATE TABLE m6_6_communities (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    type          TEXT NOT NULL,          -- 'study_group'|'strangers'|'friends'|'interview'|'cooking'|'custom'
    theme         TEXT,                   -- 主題隨機分派用 (§10.1)
    origin        TEXT NOT NULL,          -- 'system_default'|'user_created'|'theme_random'|'system_random'
    member_cap    SMALLINT NOT NULL DEFAULT 8 CHECK (member_cap BETWEEN 2 AND 8), -- §10.1 可配置上限
    created_by    UUID REFERENCES users(id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- M6.6.2 成員關係 (含管理員角色,供挑戰審核)
CREATE TABLE m6_6_community_members (
    community_id  UUID REFERENCES m6_6_communities(id) ON DELETE CASCADE,
    user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
    role          TEXT NOT NULL DEFAULT 'member', -- 'admin'|'member'
    joined_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (community_id, user_id)
);

-- M6.6.3 社群貼文 (RISK-12: 上雲前過 Eguard)
CREATE TABLE m6_6_social_posts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id  UUID NOT NULL REFERENCES m6_6_communities(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES users(id),
    kind          TEXT NOT NULL,          -- 'achievement'|'text'|'commitment'
    content       TEXT NOT NULL,          -- 已過 Eguard 的明文摘要,不含 L1
    revealed_metrics JSONB DEFAULT '[]',  -- 透明列出公開的指標
    visibility    TEXT NOT NULL DEFAULT 'private', -- RISK-12: Observer 成就預設 private
    likes_count   INT NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- M6.6.4 同儕驗證 (混合:evidence_url 可選, §10.3)
CREATE TABLE m6_6_validations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id       UUID NOT NULL REFERENCES m6_6_social_posts(id) ON DELETE CASCADE,
    validator_id  UUID NOT NULL REFERENCES users(id),
    evidence_url  TEXT,                   -- 可選證據;若提供則 weight 較高
    validated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (post_id, validator_id)        -- 一人對一貼文只驗證一次
);

-- M6.6.5 XP 質押 (與系統對賭, §10.2;扣管走 M6.5 不在此表直接動 XP)
CREATE TABLE m6_6_stakes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id),
    community_id  UUID REFERENCES m6_6_communities(id),
    task_id       UUID NOT NULL,          -- 質押標的任務
    xp_amount     INT NOT NULL CHECK (xp_amount > 0),
    deadline      TIMESTAMPTZ NOT NULL,
    status        TEXT NOT NULL DEFAULT 'held', -- 'held'|'won'|'forfeited'
    hold_txn_id   UUID,                   -- M6.5 ACID 交易 ID (扣管憑證)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- M6.6.6 週期挑戰 (三來源, §10.4;AI 生成預設 is_draft)
CREATE TABLE m6_6_challenges (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id  UUID NOT NULL REFERENCES m6_6_communities(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    description   TEXT,
    period        TEXT NOT NULL,          -- 'weekly'|'monthly'
    source        TEXT NOT NULL,          -- 'ai_reviewed'|'member_rotation'|'admin'
    status        TEXT NOT NULL DEFAULT 'pending_review', -- 'pending_review'|'active'|'closed'
    is_draft      BOOLEAN NOT NULL DEFAULT TRUE,  -- R08: AI 生成需管理員核准
    created_by    UUID REFERENCES users(id),
    starts_at     TIMESTAMPTZ,
    ends_at       TIMESTAMPTZ
);
```

> Migration 由 Alembic 產生;**不可 `--autogenerate` 後直接 apply,必須先讓使用者審** (CLAUDE.md 授權邊界)。

### 7.4 FastAPI 路由契約 (`services/m4_13_community_engine/routes.py`)

```python
# router = APIRouter(prefix="/api/m6_6", tags=["m3_7_community"])
# main.py: app.include_router(m6_6_router)   # 比照 m1_4_webhook_router 模式

GET    /api/m6_6/communities                      -> list[CommunityRead]
POST   /api/m6_6/communities                       -> CommunityRead        # 使用者自建
POST   /api/m6_6/communities/join                  -> CommunityRead        # theme/system 隨機分派
GET    /api/m6_6/communities/{id}/codex            -> CommunityCodex
GET    /api/m6_6/communities/{id}/posts            -> list[SocialPostRead] # 經 M4.13.3 隔離過濾
GET    /api/m6_6/communities/{id}/challenges       -> list[ChallengeRead]
GET    /api/m6_6/communities/{id}/commitments      -> list[CommitmentRead]

POST   /api/m6_6/posts/draft                        -> SocialPostDraft     # 回 privacy_warning + Eguard 預檢
POST   /api/m6_6/posts/publish                      -> PublishResult       # 強制 Eguard,leaked 退草稿
POST   /api/m6_6/posts/{id}/like                    -> {likes_count}

GET    /api/m6_6/stakes                              -> list[StakeRead]
POST   /api/m6_6/stakes                              -> StakeRead          # RISK-07 雙重門禁 -> M6.5 hold
POST   /api/m6_6/validations                         -> ValidationRead     # M4.13.2 閉環

POST   /api/m6_6/challenges/{id}/approve             -> ChallengeRead       # 管理員審核 AI 草稿
GET    /api/m6_6/stream?community_id=                -> SSE CommunityEvent  # 即時動態牆
```

### 7.5 前後端資料流時序 — XP 質押 (RISK-07 雙重門禁)

```text
[StakeXPInterface]                [M4.13.1 stake_engine]         [M6.5 ACID]
      │ 1. 前端門禁:                                                
      │    success>=0.70 且 zone!=edge 且 xpBalance>=amount         
      │    (任一不過 -> 按鈕 disabled,不送出)                       
      │ 2. POST /api/m6_6/stakes ───────►                          
      │                            3. 後端門禁 (可繞前端不可繞):    
      │                               can_stake_on_task() 失敗      
      │                               -> raise StakingForbidden 422 
      │                            4. 通過 -> hold XP ──────────►   
      │                                                  原子扣管   
      │                                          ◄──── hold_txn_id  
      │                            5. INSERT m6_6_stakes(status=held)
      │ ◄──── 200 StakeRead ───────                                
      │ 6. M3.1 xpBalance 樂觀更新 + 寫 raw_tracking_logs           
```

> 結算:任務到期由 M4.13.1 對賬 → 成功則經 M6.5 退還 (status=won),失敗則沒收進獎池 (status=forfeited)。**結算只動 M6.5,不在路由層直接改 XP**。

### 7.6 前後端資料流 — 貼文核准 (RISK-12)

```text
[PostsFeed / AchievementPublishModal]   [M4.13]            [M2.3 Eguard]
   │ POST /api/m6_6/posts/draft ──────►                    
   │                              propose_social_post():   
   │                              pre-scan content ───────► sanitize
   │                                              ◄── {sanitized, leaked_spans}
   │ ◄── SocialPostDraft{privacy_warning, requires_explicit_publish=true}
   │ (顯示「此貼文將公開以下資訊」)                          
   │ 使用者按 publish:                                       
   │ POST /api/m6_6/posts/publish ────►                    
   │                              強制 Eguard 再過一次 ────► sanitize
   │                              if leaked_spans: status=returned_to_draft
   │                              else: INSERT visibility=public + 上雲 + 廣播 SSE
   │ ◄── PublishResult{status, eguard_passed}              
```

### 7.7 SSE 接線 (即時動態牆)

- 前端 `useCommunityStream(communityId)` hook 訂閱 `GET /api/m6_6/stream?community_id=`,事件型別 `COMMITMENT_VALIDATED` / `POST_PUBLISHED` / `CHALLENGE_ACTIVATED`
- **斷線降級**:WebSocket/SSE 斷線時改 30s 輪詢 `GET .../posts` 補齊 (見 §7.8)
- **隔離**:broker 只向 `m6_6_community_members` 中該社群成員推送 (M4.13.3)

### 7.8 異常處理

- 社群 API 離線 → 顯示「社群暫時無法使用」,不影響其他 M3.x 模組 (MVP 隔離)
- 質押交易失敗 (M6.5 拒絕) → 顯示失敗原因,**不靜默重試**
- SSE 斷線 → 降級為輪詢補齊未收到事件
- Eguard 偵測洩漏 → 貼文退回草稿,高亮 `leaked_spans`,要求使用者改寫 (不自動發布)
- 成員已滿 (`CommunityFull`) → 提示已達上限,引導建立新社群或加入其他

## 8. Anti-patterns

- ❌ **不要在 MVP 階段實作 M3.7 任何完整功能**。使用 stub 佔位,防止對 M4.13、M6.6 建立硬連結,確保 MVP 在進階模組全數移除時仍可獨立運作 (CLAUDE.md §7)
- ❌ **不要允許 Observer 自動推論的成就直接發布為社群貼文**。必須走草稿核准;預設 `visibility="private"` (RISK-12)
- ❌ **不要在質押路由層直接 `UPDATE users SET current_xp`**。所有 XP 扣管/退還/沒收必須經 M6.5 ACID 守門員,留 `hold_txn_id` 憑證 (M4.5/M6.5 不變式)
- ❌ **不要在使用者焦慮狀態下推播質押邀請或挑戰**。前端 M3.7.8 讀 M4.8;後端 M4.13 同有門禁 (RISK-07、RISK-09)
- ❌ **不要讓跨社群資料混用**。讀書會貼文不可出現在陌生人 feed,由 M4.13.3 隔離中介軟體保障 (查詢必帶 `community_id` + 成員資格檢查)
- ❌ **不要讓 AI 挑戰生成器讀取成員 L1 逐字稿或 L2 意圖向量**。只讀 L3 聚合統計 (完成率、目標標籤、XP 趨勢);AI 生成挑戰預設 `is_draft=true` 待管理員核准 (RISK-18 + R08)
- ❌ **不要讓小群組 (member_cap ≤ 3) 的 AI 挑戰用一般措辭模板**。聚合統計在小群組中容易退化為個人指名,必須用保守模板 (RISK-18)
- ❌ **不要讓貼文 `content` 承載未過 Eguard 的原文**。上雲前強制 sanitize,洩漏即退草稿

## 9. (已移至 §10) — v1.0 的開放問題已於 2026-06-17 由使用者拍板

## 10. 已定案決策 (2026-06-17 使用者拍板)

### 10.1 社群建立模式 — 三種並存,成員上限可配置 (2~8)

社群建立支援三種來源 (`m6_6_communities.origin`):

1. **`user_created`** — 使用者自建並命名,可設 `member_cap` (2~8)
2. **`theme_random`** — 使用者選擇主題,系統依主題隨機分派至同主題小群
3. **`system_random`** — 系統完全隨機分派

**小群上限 2~8 人** (DB `CHECK (member_cap BETWEEN 2 AND 8)`):刻意維持小群,降低 R09 病態社交曝光、強化 SDT 連結品質。達上限拋 `CommunityFull`。
PDF 線框的 5 個固定子社群以 `origin='system_default'` 預載。

### 10.2 XP 質押對賭對象 — 與系統對賭

質押 XP 經 M6.5 扣管進「保留」狀態 (`status=held`),到期由 M4.13.1 對賬:成功經 M6.5 退還 (`won`,可加紅利),失敗沒收進系統獎池 (`forfeited`)。**不需配對真實使用者**,避免放大 RISK-07/RISK-09 複合挫敗,且結算可控、可測。

### 10.3 同儕驗證標準 — 混合 (可選證據)

預設社交點贊式驗證 (`m6_6_validations` 無 `evidence_url`);承諾人**可選擇**附上 `evidence_url` (截圖/連結) 提高驗證權重。
**注意**:若附證據連結,前端須提示「證據可能含個人資訊」,且該連結不經 Eguard 自動掃描 (使用者自負揭露責任),預設僅社群成員可見。

### 10.4 週期挑戰生成 — 三層,以 AI 審核制為主

1. **`ai_reviewed`(主要)** — M4.13.4 AI 系統性檢核社群歷史/目標/近況**(僅 L3 聚合)**生成挑戰草稿 (`is_draft=true`, `status=pending_review`),**管理員手動審核/修改後核准**才 `active`
2. **`member_rotation`** — 成員輪流設定/修改挑戰
3. **`admin`** — 管理員直接配置

AI 生成嚴守 **RISK-18** (`05_integration_risk_audit.md` 新增條目):`build_challenge_context()` 只讀 L3 聚合 (`privacy_layer="L3"`),`raw_transcripts` / `intent_vectors` 必為空;`member_cap ≤ 3` 小群組強制保守措辭模板 (見 §6.2 測試)。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 說明核心原則:社交情境隔離 + v2.0 全鏈路範圍
- [x] §2 至少 4 個 `Rxx §章節` 引用 (R09×2, R01, R07, R08)
- [x] §3 Schema 完整 (前端 In/Out + 後端 Out 三向)
- [x] §4 依賴是真實模組編號 (M4.13/M6.6/M6.5/M2.3/M4.8/M3.1/M0.4)
- [x] §5 RISK-07、RISK-09、RISK-12、RISK-18 均標注 + 已過 audit-integration (RISK-18 為本次新增條目)
- [x] §6 測試含 MVP Stub + 前端進階 + 後端整合風險測試
- [x] §7 含 M6.6 SQL schema、FastAPI 路由、前後端時序圖、SSE 接線
- [x] §8 至少 7 條反模式含 MVP 守門 + ACID + 隱私
- [x] §10 v1.0 開放問題已全數由使用者拍板定案
