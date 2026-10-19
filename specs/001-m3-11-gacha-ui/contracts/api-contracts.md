# API & Event Contracts: M3.11 Gamification Gacha & Visual Studio

## 1. Gacha Draw Endpoint

- **Endpoint**: `POST /api/gacha/draw`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "user_id": "string",
    "cost": 100,
    "pool_mode": "curated" | "hybrid"
  }
  ```
- **Response 200 (Success)**:
  ```json
  {
    "success": true,
    "item": {
      "id": "bg_cyber_study",
      "name": "賽博龐克研究室",
      "description": "...",
      "category": "background",
      "rarity": "epic",
      "image_url": "data:image/svg+xml;utf8,...",
      "has_transparency": false,
      "scene_description": "...",
      "is_user_generated": false,
      "in_gacha_pool": true,
      "hidden": false,
      "unlocked_at": "2026-10-19T20:00:00.000Z"
    },
    "cost": 100,
    "remaining_xp": 400
  }
  ```
- **Response 400 (Insufficient XP)**:
  ```json
  {
    "success": false,
    "cost": 0,
    "remaining_xp": 60,
    "error": "需要 100 XP（餘額不足）"
  }
  ```
- **Response 429 (Rate Limit Exceeded - 5 draws/hour)**:
  ```json
  {
    "success": false,
    "error": "已達 1 小時上限（5/5）冷卻中",
    "cooldown_remaining_ms": 1800000
  }
  ```

---

## 2. Free Image Harmonization (Image-to-Image) Contract

- **Client Provider**: Pollinations.ai / Hugging Face Free API / Canvas 2D Fallback
- **Request Parameters**:
  ```typescript
  interface HarmonizeRequest {
    base64_draft: string;            // 2D 畫布底稿 Data URL
    scene_description?: string;      // 背景場景描述
    objects_summary?: string;        // 各物體語意特徵摘要
  }
  ```
- **Response (Success - AI Mode)**:
  ```typescript
  interface HarmonizeResult {
    image_url: string;               // 融合完成之影像 URL
    is_fallback: false;
    provider: "pollinations" | "huggingface_free";
  }
  ```
- **Response (Degraded - Fallback Mode)**:
  ```typescript
  interface HarmonizeResult {
    image_url: string;               // 2D 畫布底稿 Base64
    is_fallback: true;
    provider: "canvas_2d_fallback";
  }
  ```

---

## 3. WebSocket Realtime Broadcast: Hidden Achievement

- **Channel / Protocol**: `ws://127.0.0.1:8000/ws/achievements`
- **Message Payload**:
  ```json
  {
    "type": "HIDDEN_ACHIEVEMENT_UNLOCKED",
    "item": {
      "id": "ach_quantum_leap",
      "name": "量子躍遷隱藏榮譽",
      "description": "...",
      "category": "badge",
      "rarity": "legendary",
      "image_url": "...",
      "has_transparency": true,
      "hidden": true,
      "unlocked_at": "2026-10-19T20:00:00.000Z"
    }
  }
  ```

---

## 4. Local L1 Telemetry Logging: raw_tracking_logs

- **Endpoint**: `POST /api/events`
- **Payload**:
  ```json
  {
    "module": "M3.11",
    "event_type": "gacha_draw_success" | "canvas_harmonize_completed" | "custom_theme_applied",
    "timestamp": "2026-10-19T20:00:00.000Z",
    "metadata": {
      "item_id": "string",
      "rarity": "string"
    }
  }
  ```
