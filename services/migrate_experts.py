#!/usr/bin/env python3
"""
M4.2 Persona - 舊專家資料批次遷移工具 (Legacy Expert Migration Tool)

功能：
- 連接本地 SQLite 資料庫。
- 尋找 persona_card 欄位為 NULL 或為空的歷史專家記錄。
- 呼叫 Gemini LLM 將舊版的純文字人設 (personality_prompt) 與 backstory 轉換為結構化的 PersonaCard v2 JSON。
- 透過 critic_check() 校驗，通過後編譯為結構化提示詞，並寫回資料庫。
"""

import sys
import os
import json
import sqlite3
import asyncio
import logging

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("migrate_experts")

# 確保 services 目錄在 import 路徑中
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import get_settings
    from m4_1_router.routing_engine import get_cloud_llm_client, PERSONA_MODEL, PERSONA_MODEL_FALLBACK
    from m4_2_persona.persona_card import persona_card_from_dict, compile_to_prompt, critic_check
except ImportError as e:
    logger.error("無法載入必要的模組，請確保在 services 目錄中執行此腳本。錯誤：%s", e)
    sys.exit(1)


async def migrate_single_expert(client, row) -> tuple[str, str] | None:
    """呼叫 LLM 結構化遷移單一專家，返回 (persona_card_json, compiled_prompt)"""
    expert_id = row["id"]
    name = row["name"]
    backstory = row["backstory"] or ""
    personality_prompt = row["personality_prompt"] or ""
    tone_default = row["tone_default"] or "empathetic"

    logger.info("正在遷移專家：%s (ID: %s)", name, expert_id)

    prompt = f"""你是一個 AI 顧問角色遷移工具。請將以下舊版 AI 專家的純文字人設與描述，結構化轉換為符合 PersonaCard v2 規格的 JSON。

舊專家資料：
- 姓名：{name}
- 背景：{backstory}
- 純文字人設（包含口吻、學經歷等）：
{personality_prompt}
- 預設語調：{tone_default}

轉換規則：
1. 角色必須有具體的出生年代、學歷與工作背景。
2. 語氣、口頭禪與缺點需要被填入。
3. 必須填寫明確的專業邊界（knowledge_boundary.expert_in 必須有值且至少包含 1 個項目）。
4. 必須定義至少 2 個個人立場（stances），用作反諂媚守則（topic/position/intensity 欄位，其中 intensity 可填 firm 或 mild）。
5. 嚴禁包含 "我是AI", "as an AI assistant" 等通用 AI 語句。
6. fillers（語氣助詞詞組）不可包含 !/!!/!!! 等感嘆號。

請輸出唯一的 JSON，格式如下（只回傳 JSON 物件，不要包裝任何 markdown ```json 標記或額外說明）：
{{
  "identity": {{
    "name": "{name}",
    "birth_year": 1985,
    "education": "台大資工畢業",
    "career": "{backstory if backstory else '資深顧問'}"
  }},
  "big_five": {{
    "O": 0.8,
    "C": 0.7,
    "E": 0.5,
    "A": 0.6,
    "N": 0.3
  }},
  "core_values": ["誠信", "專業"],
  "speech_profile": {{
    "fillers": ["嗯", "其實"],
    "quirks": ["說話尾綴喜歡用問句思考"],
    "taboos": ["我是AI", "我只是一個AI"]
  }},
  "formative_episodes": [
    {{
      "age": 22,
      "event": "大學畢業並拿到第一個 Offer",
      "impact": "奠定其專業自信"
    }}
  ],
  "knowledge_boundary": {{
    "expert_in": ["專業領域1"],
    "casual_in": ["一般話題"],
    "ignorant_of": ["不懂的領域"]
  }},
  "stances": [
    {{
      "topic": "學習態度",
      "position": "堅信只有透過動手寫程式才能真正掌握技術",
      "intensity": "firm"
    }},
    {{
      "topic": "市場趨勢",
      "position": "認為基礎功比追逐最新框架更為重要",
      "intensity": "firm"
    }}
  ]
}}"""

    try:
        raw_resp = await client.complete(prompt, max_output_tokens=2048, temperature=0.3)
    except Exception as llm_err:
        logger.error("專家 %s 呼叫 LLM 失敗：%s", name, llm_err)
        return None

    # 清理 Response 中的 Markdown code fences
    cleaned = raw_resp.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except Exception as parse_err:
        logger.error("專家 %s 的 LLM 回應無法解析為 JSON。回應：%s | 錯誤：%s", name, raw_resp[:200], parse_err)
        return None

    # 校驗結構
    try:
        card = persona_card_from_dict(data)
        passed, issues = critic_check(card)
        if not passed:
            logger.warning("專家 %s 產出的 PersonaCard 未能完全通過 Critic 校驗。問題：%s", name, issues)
            # 嘗試微調修正常見問題以提升相容性
            if not data.get("stances") or len(data["stances"]) < 2:
                data["stances"] = [
                    {"topic": "工作價值", "position": "堅持高品質與持續學習", "intensity": "firm"},
                    {"topic": "AI工具定位", "position": "AI 是輔助，思考與決策權始終在人", "intensity": "firm"}
                ]
            if not data.get("knowledge_boundary", {}).get("expert_in"):
                data["knowledge_boundary"] = {
                    "expert_in": ["專業諮詢"],
                    "casual_in": ["生活閒聊"],
                    "ignorant_of": ["無關領域"]
                }
            # 重新校驗
            card = persona_card_from_dict(data)
            passed, issues = critic_check(card)
            if not passed:
                logger.error("專家 %s 修復後依然未通過 Critic 校驗，跳過更新。最後問題：%s", name, issues)
                return None
            else:
                logger.info("專家 %s 自動修復成功，已通過 Critic 校驗。", name)

        compiled_prompt = compile_to_prompt(card)
        return json.dumps(data, ensure_ascii=False), compiled_prompt

    except Exception as card_err:
        logger.error("專家 %s PersonaCard 物件建立失敗：%s", name, card_err)
        return None


async def main():
    settings = get_settings()
    db_path = settings.local_db_path
    if not os.path.exists(db_path):
        logger.error("找不到 SQLite 資料庫檔案：%s，請確認設定。", db_path)
        sys.exit(1)

    logger.info("連接資料庫：%s", db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 確保 persona_card 欄位存在
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE ai_experts ADD COLUMN persona_card TEXT")
        conn.commit()
        logger.info("資料表 ai_experts 欄位 persona_card 確保成功。")
    except Exception:
        pass

    # 查詢需要遷移的專家
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, personality_prompt, backstory, tone_default "
            "FROM ai_experts WHERE persona_card IS NULL OR persona_card = ''"
        )
        rows = cur.fetchall()
    except Exception as e:
        logger.error("讀取 ai_experts 失敗：%s", e)
        conn.close()
        sys.exit(1)

    if not rows:
        logger.info("✅ 沒有偵測到需要遷移的舊專家記錄。所有專家均已擁有結構化人設。")
        conn.close()
        return

    logger.info("共找到 %d 個需要遷移的專家。", len(rows))

    # 初始化 LLM 用戶端
    client = None
    for model in (PERSONA_MODEL, PERSONA_MODEL_FALLBACK):
        try:
            client = get_cloud_llm_client(model)
            logger.info("選用 LLM 模型：%s", model)
            break
        except Exception as e:
            logger.warning("模型 %s 初始化失敗：%s", model, e)

    if not client:
        logger.error("無法初始化任何 LLM 用戶端，請確認 GEMINI_API_KEY。")
        conn.close()
        sys.exit(1)

    success_count = 0
    fail_count = 0

    for row in rows:
        result = await migrate_single_expert(client, row)
        if result:
            card_json, compiled_prompt = result
            try:
                update_cur = conn.cursor()
                update_cur.execute(
                    "UPDATE ai_experts SET persona_card = ?, personality_prompt = ? WHERE id = ?",
                    (card_json, compiled_prompt, row["id"])
                )
                conn.commit()
                logger.info("✅ 專家 '%s' 遷移成功並已寫回資料庫。", row["name"])
                success_count += 1
            except Exception as update_err:
                logger.error("更新專家 %s 寫回 DB 失敗：%s", row["name"], update_err)
                conn.rollback()
                fail_count += 1
        else:
            logger.error("❌ 專家 '%s' 遷移失敗。", row["name"])
            fail_count += 1

    conn.close()
    logger.info("遷移作業完成！成功：%d, 失敗：%d", success_count, fail_count)


if __name__ == "__main__":
    asyncio.run(main())
