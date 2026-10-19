"""
Generate per-persona example_exchanges and write them into ai_experts.persona_card.

Usage:
  cd services && python generate_example_exchanges.py

Requires: GOOGLE_API_KEY or GEMINI_API_KEY in environment / .env

Research: [R12: Character-LLM] Example grounding
          [R05: Paralinguistic] Speech rhythm demonstration
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# Add services/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "coos.db"

GENERATION_PROMPT = """\
你是一個對話語氣設計師。根據以下人設資料，生成 3 組「理想回覆範例」。

這些範例要展示這個人在 LINE/WhatsApp 上傳訊息的真實語氣和節奏。

人設資料：
名字：{name}
職業/背景：{career}
性格：{traits}
說話習慣：{quirks}
口頭禪：{catchphrase}

要求：
1. 每組包含一個使用者訊息 + 1~2 則短回覆（每則不超過 15 字）
2. 三組情境分別是：
   - context: "user_anxious" — 使用者焦慮或壓力大
   - context: "casual_greeting" — 使用者隨便打招呼
   - context: "user_resistant" — 使用者表達抗拒或不耐煩
3. 回覆必須用繁體中文
4. 回覆要像這個人真的在傳訊息，不是寫作文
5. 不要用表情符號

回傳嚴格 JSON 格式（不要 markdown code block）：
[
  {{"context": "user_anxious", "user": "...", "assistant": ["...", "..."]}},
  {{"context": "casual_greeting", "user": "...", "assistant": ["..."]}},
  {{"context": "user_resistant", "user": "...", "assistant": ["..."]}}
]
"""


def _get_api_key() -> str:
    try:
        from config import get_settings
        key = get_settings().gemini_api_key
        if key:
            return key
    except Exception:
        pass
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("ERROR: GEMINI_API_KEY or GOOGLE_API_KEY not set")
        sys.exit(1)
    return key


def _call_gemini_sync(prompt: str, api_key: str) -> str:
    """Synchronous Gemini API call."""
    import httpx

    model = "gemini-2.0-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 800},
    }

    resp = httpx.post(url, json=payload, timeout=30.0)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return text.strip()


def _extract_traits(persona_card: dict) -> str:
    bf = persona_card.get("big_five", {})
    traits = []
    if bf.get("O", 0.5) > 0.7:
        traits.append("有創造力")
    elif bf.get("O", 0.5) < 0.3:
        traits.append("務實")
    if bf.get("C", 0.5) > 0.7:
        traits.append("自律有條理")
    if bf.get("E", 0.5) > 0.7:
        traits.append("外向有活力")
    elif bf.get("E", 0.5) < 0.3:
        traits.append("內斂")
    if bf.get("A", 0.5) > 0.7:
        traits.append("溫暖")
    elif bf.get("A", 0.5) < 0.3:
        traits.append("直來直往")
    if bf.get("N", 0.5) < 0.3:
        traits.append("情緒穩定")
    return "、".join(traits) if traits else "中性"


def main():
    api_key = _get_api_key()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT id, name, persona_card FROM ai_experts WHERE is_active=1 AND persona_card IS NOT NULL"
    ).fetchall()

    print(f"Found {len(rows)} active experts with persona_card")

    for row in rows:
        expert_id = row["id"]
        name = row["name"]
        card_raw = row["persona_card"]

        try:
            card = json.loads(card_raw)
        except json.JSONDecodeError:
            print(f"  SKIP {name}: invalid JSON in persona_card")
            continue

        # Check if already has example_exchanges
        if card.get("example_exchanges"):
            print(f"  SKIP {name}: already has example_exchanges")
            continue

        identity = card.get("identity", {})
        sp = card.get("speech_profile", {})
        traits = _extract_traits(card)
        quirks = "、".join(sp.get("quirks", [])[:3]) or "無特殊"
        catchphrase = sp.get("catchphrase") or sp.get("口頭禪") or "無"

        prompt = GENERATION_PROMPT.format(
            name=name,
            career=identity.get("career", "未知"),
            traits=traits,
            quirks=quirks,
            catchphrase=catchphrase,
        )

        print(f"  Generating for {name}...", end=" ", flush=True)
        try:
            raw_response = _call_gemini_sync(prompt, api_key)
            # Strip markdown code block if present
            if raw_response.startswith("```"):
                raw_response = raw_response.split("\n", 1)[1]
                if raw_response.endswith("```"):
                    raw_response = raw_response[:-3]
                elif "```" in raw_response:
                    raw_response = raw_response[:raw_response.rfind("```")]
            raw_response = raw_response.strip()

            examples = json.loads(raw_response)
            if not isinstance(examples, list) or len(examples) < 2:
                raise ValueError(f"Expected list of 3, got {type(examples)}")

            # Validate structure
            for ex in examples:
                assert "context" in ex and "user" in ex and "assistant" in ex

            card["example_exchanges"] = examples
            updated_card_json = json.dumps(card, ensure_ascii=False)

            conn.execute(
                "UPDATE ai_experts SET persona_card = ? WHERE id = ?",
                (updated_card_json, expert_id),
            )
            conn.commit()
            print(f"OK ({len(examples)} examples)")

        except Exception as e:
            print(f"FAILED: {e}")

        # Rate limit courtesy
        time.sleep(2)

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
