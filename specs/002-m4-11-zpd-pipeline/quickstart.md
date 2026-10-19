# Quickstart & Validation Guide: M4.11 ZPD Pipeline

**Feature**: M4.11 動態邊界任務池與 ZPD 盲盒管線 (Dynamic ZPD Gacha Pipeline)  
**Date**: 2026-10-19  
**Status**: Ready for Implementation Validation  

---

## 1. Prerequisites & Environment Setup

### 1.1 後端環境準備
```bash
# 進入 services 目錄並啟動虛擬環境
cd services
# Windows PowerShell
.venv\Scripts\Activate.ps1

# 安裝依賴 (含 FastAPI, SQLAlchemy, Pydantic, Pytest)
pip install -r requirements.txt
```

### 1.2 資料庫初始化
確保本地 SQLite 資料庫包含 `role_skill_mastery` 與 `zpd_challenges` 表：
```bash
# 執行 Alembic 遷移或單元測試初始化腳本
python -m pytest ../testing/m4_11/test_schema_migration.py -v
```

---

## 2. Automated Test Execution

執行針對 M4.11 的完整單元與整合測試套件：

```bash
# 執行 M4.11 所有後端測試 (含 BKT 演算法、ZONE 篩選、雙階降級與 ACID 派發)
cd services
python -m pytest ../testing/m4_11/ -v
```

### 關鍵驗證測試案例一覽：
* `test_bkt_bayesian_update.py`: 驗證成功時 $P(L_t)$ 漸進提升，逾期時輕微衰減，多模態因子正確加權。
* `test_zone_reject_and_grad.py`: 驗證超界任務被 `REJECT` 濾除，`GRAD` 分佈符合 ZPD 邊界。
* `test_safety_retraction_on_anxiety.py`: 模擬 M4.8 `anxiety` 信號，驗證 `stretch` 難度被禁用且時長 $\le 15$ 分鐘。
* `test_restorative_serendipity_boost.py`: 驗證疲勞狀態下生活恢復型任務權重躍升至 50%~80%。
* `test_zero_staking_invariant.py`: 驗證任何失敗或逾期情況下，XP 扣除額絕對為 0（RISK-07 鐵律）。
* `test_dual_tier_offline_fallback.py`: 斷網與推論超時（>5 秒）情況下，自動降級為種子填充，耗時 <300ms。

---

## 3. End-to-End Manual API Walkthrough

啟動後端 FastAPI 開發伺服器：
```bash
cd services
uvicorn main:app --reload --port 8000
```

### 步驟 1：抽取一個 ZPD 延伸挑戰
```bash
curl -X POST http://localhost:8000/api/m4_11/draw_challenge \
  -H "Content-Type: application/json" \
  -d '{"role_id": "role_csie", "user_id": "default_user"}'
```
**預期輸出**：
回傳 `status: "generated"` 的挑戰物件，包含標題、預估時間（15~45 分鐘）、`scaffolding_hints` 提示指針，且絕無任何扣款或質押欄位。

### 步驟 2：接受挑戰（進入單一活躍槽位）
```bash
curl -X POST http://localhost:8000/api/m4_11/accept_challenge \
  -H "Content-Type: application/json" \
  -d '{"challenge_id": "<CHALLENGE_ID>", "replace_existing": true}'
```
**預期輸出**：
挑戰狀態轉為 `accepted`，寫入 `accepted_at` 與次日 04:00 AM 的 `expires_at`。

### 步驟 3：完成挑戰並提交反思（ACID XP 派發）
```bash
curl -X POST http://localhost:8000/api/m4_11/complete_challenge \
  -H "Content-Type: application/json" \
  -d '{
    "challenge_id": "<CHALLENGE_ID>",
    "user_feeling": "搞懂了 Docker 自訂 bridge 的原理，之前一直連不上原來是因為沒有在同一個網路命名空間！",
    "user_action_plan": "下一步要把這個設定寫進正式環境的 docker-compose.yml 裡。",
    "actual_minutes": 25
  }'
```
**預期輸出**：
```json
{
  "success": true,
  "awarded_xp": 50,
  "transaction_id": "tx_acid_9a8b7c",
  "new_p_mastery": 0.42
}
```
* M6.5 `XPGatekeeper` 原子寫入 XP 帳本。
* BKT 模型將該領域掌握度從 0.30 提升至 0.42。
* 狀態轉為 `completed`。

### 步驟 4：驗證離線種子槽位降級備援
模擬中斷網路或本地 Gemma 模型超時：
```bash
curl -X POST http://localhost:8000/api/m4_11/draw_challenge \
  -H "Content-Type: application/json" \
  -d '{"role_id": "role_csie", "force_fallback": true}'
```
**預期輸出**：
在 300 毫秒內自本地種子庫組裝完成並回傳任務，保證離線可用性。
