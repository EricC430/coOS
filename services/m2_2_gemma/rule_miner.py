"""M2.2 FallbackRuleMiner -- extracts rule-based fallback keywords from gemma_edge logs

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1 §7.8
Closed-loop learning: analyzes previous successful Gemma inferences to seed rule fallback dictionary.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import defaultdict

from .fallback import RuleBasedExtractor

logger = logging.getLogger(__name__)


class FallbackRuleMiner:
    """Mines correlated keywords from SQLite tracking logs to automatically expand rule-based fallbacks."""

    def __init__(self, extractor: RuleBasedExtractor) -> None:
        self.extractor = extractor

    def extract_tokens(self, text: str) -> set[str]:
        """Tokenize raw telemetry content into English and Chinese terms, cleaning stopwords."""
        # Extract English words (alphanumeric, length >= 3)
        eng_tokens = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        
        # Extract Chinese words (consecutive Han characters, length 2 to 4)
        han_tokens = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
        
        # Stopwords filter to exclude highly generic terms
        STOPWORDS = {
            "the", "and", "for", "with", "this", "that", "from", "you", "are", "web", "app", "page",
            "microsoft", "edge", "chrome", "firefox", "window", "windows", "focus", "title", "main",
            "的", "和", "是", "在", "我", "與", "個", "了", "有", "之", "於", "及", "等", "被", "或", "一", "個", "中"
        }
        
        tokens = set()
        for tok in eng_tokens:
            if tok not in STOPWORDS:
                tokens.add(tok)
        for tok in han_tokens:
            if tok not in STOPWORDS:
                tokens.add(tok)
        return tokens

    async def mine_rules_from_db(
        self,
        db_conn: sqlite3.Connection,
        min_occurrences: int = 3,
        min_correlation: float = 0.8
    ) -> list[tuple[str, str]]:
        """Query SQLite tracking logs for successful gemma_edge predictions and discover new rules.
        
        Returns a list of newly discovered rules as (pattern, label) tuples.
        """
        cursor = db_conn.cursor()
        cursor.execute(
            "SELECT payload FROM raw_tracking_logs WHERE payload LIKE '%\"inference_mode\": \"gemma_edge\"%'"
        )
        rows = cursor.fetchall()
        
        # word_intent_counts[word][intent] = count
        word_intent_counts = defaultdict(lambda: defaultdict(int))
        # word_totals[word] = total count
        word_totals = defaultdict(int)
        
        for row in rows:
            try:
                payload = json.loads(row[0])
                content_raw = payload.get("content_raw", "")
                intent_label = payload.get("intent_label", "")
                if not content_raw or not intent_label:
                    continue
                
                tokens = self.extract_tokens(content_raw)
                for token in tokens:
                    word_intent_counts[token][intent_label] += 1
                    word_totals[token] += 1
            except Exception as e:
                logger.warning("Failed to parse tracking log row. Error: %s", e)
                continue
        
        new_rules: list[tuple[str, str]] = []
        for word, totals in word_totals.items():
            if totals < min_occurrences:
                continue
            
            # Find the intent with the highest correlation
            best_intent = None
            best_count = 0
            for intent, count in word_intent_counts[word].items():
                if count > best_count:
                    best_count = count
                    best_intent = intent
            
            if best_intent and (best_count / totals) >= min_correlation:
                # Use word boundaries for English/ASCII words to prevent substring issues
                pattern = rf"\b{word}\b" if word.isascii() else word
                
                # Check existing rules to avoid duplicate insertion
                already_exists = False
                with self.extractor._lock:
                    existing_keys = list(self.extractor._intent_keywords.keys())
                
                for existing_pattern in existing_keys:
                    if word == existing_pattern or re.search(existing_pattern, word):
                        already_exists = True
                        break
                
                if not already_exists:
                    new_rules.append((pattern, best_intent))
                    
        # Apply new rules
        for pattern, intent in new_rules:
            self.extractor.add_rule(pattern, intent)
            logger.info("Automatically learned new fallback rule: %s -> %s", pattern, intent)
            
        return new_rules
