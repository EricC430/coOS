<!--
Sync Impact Report:
Version change: 1.0.0 -> 1.1.0
Modified principles: Principle II (Psychological Mechanism Invariants) expanded with ZPD Challenge Zero-Staking & Safety Retraction
Added sections: None
Removed sections: None
Follow-up TODOs: None
-->

# coOS Project Constitution

## Core Principles

### I. Three-Tier Privacy (L1 / L2 / L3)
User data must strictly adhere to the three privacy levels:
- **L1 Plaintext**: Source code, raw browser captures, chat transcripts, and Satir Iceberg hypotheses (`M5`) are stored exclusively in local SQLite. **They MUST NEVER be uploaded to cloud LLMs or cloud databases**. Cloud LLM calls MUST pass through M2.2.2 (Intent Vector compression) and M2.3 (Eguard PII filtration).
- **L2 Intent Vectors**: Compressed semantic representations produced by on-device Gemma. Stored in local SQLite buffer before syncing to cloud Neo4j. Irreversible to plaintext.
- **L3 Business State**: XP ledger, badge assets, role configurations, and community posts. Synced to cloud PostgreSQL for cross-device consistency.

### II. Psychological Mechanism Invariants (Research Invariants)
Non-negotiable behavioral invariants grounded in psychological literature:
- **Draft & Explicit Approval**: `daily_reflections.is_reviewed` MUST NEVER be automatically set to `true` [R08: IKEA Effect §VI.1].
- **XP Gatekeeper**: Earned XP is awarded strictly when all M6.5 `XPGatekeeper` conditions are satisfied: `is_draft = false`, `is_reviewed = true`, reflection fields (`user_feeling`, `user_action_plan`) are non-empty, and transaction is ACID-recorded [R01, RISK-01].
- **Micro-friction is a Feature**: Essential reflection input fields and confirmation steps MUST NOT be eliminated in the name of "streamlined UX" [R08: Micro-friction §IV.2].
- **Context-Aware Broadcast Timing**: High cognitive load periods prohibit unsolicited pushes; notifications are gated by M1.2 breakpoint detection [RISK-04].
- **Persona Counter-Comfort**: Never mirror negative emotional valence (anxious user receives calming empathy, not mirrored anxiety) [R03 §4.2, R01 α-DPO, RISK-03].
- **ZPD Challenge Zero-Staking & Safety Retraction**: Dynamic ZPD tasks generated for user skill development MUST strictly prohibit mandatory XP staking or loss-aversion penalties upon failure, preventing composite frustration and dropout crises [R01: ZONE/α-DPO, RISK-07]. When high cognitive load or anxiety is detected, ZPD boundaries must safely retract [RISK-09].

### III. Specification as Contract
Specifications in `docs/modules/*_SPEC.md` and `specs/` define approved system behavior:
- Any behavioral, API, schema, or threshold change requires a proposal with spec delta approved by the user (G1 gate) before modifying code.
- Zero tolerance for undocumented discrepancies between code and specifications.
- Any change touching 2+ modules requires an integration risk audit (`audit-integration`).

### IV. Test-First, Evidence-Driven (NON-NEGOTIABLE)
- TDD is mandatory: Acceptance criteria must be written as automated tests, observed failing for the correct expected reason (RED), and then satisfied by implementation (GREEN).
- No claim of completion or bugfix without fresh execution evidence with exact passed/failed numbers from the current session.
- Never weaken assertions to make tests pass. Modifying assertions equals modifying requirements.

### V. MVP Independence & Advanced Module Gatekeeping
- Advanced modules (`[進階]`, such as M3.11, M3.12, M4.11, M4.12, M4.13, M5) MUST NOT introduce backward hard dependencies into MVP core modules. MVP must run standalone if all advanced modules are stripped.
- Advanced modules can only proceed when `docs/MVP_CLOSURE_REPORT.md` evaluates to GO, or when explicit user waiver is granted for targeted standalone component development.

### VI. Research Citation Standard
Code annotations, architectural specifications, and commits claiming empirical basis MUST use the formal citation format: `[Rxx: Keyword §Chapter]`, where `Rxx` maps directly to `docs/03_research_index.md`. Vague citations such as "based on research" are strictly forbidden.

### VII. Full Observability
- All cross-module interactions and gamification events MUST emit structured telemetry to `raw_tracking_logs` (M0.4).
- Silent exception swallowing (`except: pass`, unlogged empty returns) is strictly prohibited.

## Architectural & Security Constraints
- **Frontend Stack**: React 18, TypeScript, Tailwind CSS, Lucide icons, Vitest + React Testing Library.
- **Backend Stack**: Python 3.11+, FastAPI, SQLAlchemy (SQLite local / PostgreSQL cloud), Alembic, Pytest.
- **Edge Inference**: Local ONNX Runtime / Gemma via M2.2.
- **Local Isolation**: Desktop app operates offline-first; network failure must gracefully degrade without freezing or crashing UI.

## Development Workflow & Quality Gates
- **Classification**:
  - **T0 Quick**: Non-behavioral changes (lint, style, doc typos) -> direct fix & test.
  - **T1 Fix**: Code diverges from existing approved spec -> systematic debugging.
  - **T2 Change**: Modifying/adding/removing behavior or schema -> SpecKit 7-phase flow.
  - **T3 New Module**: Unimplemented module -> Full SpecKit pipeline from constitution to converge.
- **Gate 1 (G1)**: User sign-off on proposal, spec delta, and clarification before code authoring.

## Governance
This Constitution establishes the foundational laws of the coOS project and supersedes informal conventions. Any amendment requires:
1. Formal change proposal documenting the rationale, impacted principles, and migration path.
2. Explicit user ratification (G1 sign-off).
3. Semantic version increment: MAJOR for principle removal/redefinition; MINOR for new principle or structural expansion; PATCH for phrasing and typo fixes.

**Version**: 1.1.0 | **Ratified**: 2026-06-03 | **Last Amended**: 2026-10-19
