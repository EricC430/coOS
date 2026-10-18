"""
M2.3 -- PII patterns must work next to Chinese text (review D6)

`\\b` does not fire between a CJK character and a letter/digit, because Python
treats CJK as `\\w`. Patterns now use alphanumeric lookarounds instead, and card
numbers must also pass a Luhn check to cut false positives on long digit runs
(timestamps, order numbers) inside Chinese sentences.

[R07: §5 Eguard] discrete text masking before upload
SPEC: docs/modules/M2_3_eguard_crypto_filter_SPEC.md §7.3
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services"))

from m2_3_eguard.filter import EguardFilter  # noqa: E402

VALID_VISA = "4111111111111111"      # Luhn valid
VALID_AMEX = "378282246310005"       # Luhn valid, 15 digits
INVALID_16 = "1234567812345678"      # Luhn invalid
TIMESTAMP_14 = "20261018093000"      # Luhn invalid
GOOGLE_KEY = "AIzaSy" + "A" * 33


@pytest.fixture
def eguard():
    return EguardFilter()


class TestCJKAdjacentMasking:
    @pytest.mark.parametrize(
        "text, secret, entity",
        [
            ("身分證A123456789", "A123456789", "TAIWAN_ID"),
            ("我的身分證是A123456789喔", "A123456789", "TAIWAN_ID"),
            (f"卡號{VALID_VISA}", VALID_VISA, "CREDIT_CARD"),
            (f"美國運通{VALID_AMEX}到期", VALID_AMEX, "CREDIT_CARD"),
            ("主機192.168.1.10連不上", "192.168.1.10", "IPV4"),
            (f"金鑰{GOOGLE_KEY}外洩", GOOGLE_KEY, "API_KEY_GOOGLE"),
        ],
    )
    def test_masked_next_to_chinese(self, eguard, text, secret, entity):
        result = eguard.mask_pii(text, role_id="r")
        assert secret not in result.sanitized_text
        assert entity in result.masked_entities
        assert result.flagged is True

    def test_spaced_and_dashed_cards_masked(self, eguard):
        result = eguard.mask_pii("卡號 4111 1111 1111 1111、5500-0000-0000-0004", role_id="r")
        assert "4111" not in result.sanitized_text
        assert "5500" not in result.sanitized_text
        assert result.sanitized_text.count("[REDACTED_CARD]") == 2


class TestLuhnFalsePositives:
    def test_luhn_invalid_16_digits_not_masked(self, eguard):
        result = eguard.mask_pii(f"訂單編號{INVALID_16}", role_id="r")
        assert INVALID_16 in result.sanitized_text
        assert "CREDIT_CARD" not in result.masked_entities

    def test_luhn_invalid_spaced_number_not_masked(self, eguard):
        """Before Luhn, any 13-16 digit run separated by spaces was masked as a card."""
        result = eguard.mask_pii(f"order {INVALID_16} shipped", role_id="r")
        assert INVALID_16 in result.sanitized_text
        assert result.flagged is False

    def test_timestamp_not_masked(self, eguard):
        result = eguard.mask_pii(f"時間戳{TIMESTAMP_14}", role_id="r")
        assert TIMESTAMP_14 in result.sanitized_text
        assert result.flagged is False

    def test_long_digit_run_not_partially_masked(self, eguard):
        """A 20-digit run must not have a 16-digit card carved out of its middle."""
        run = "9" + VALID_VISA + "999"
        result = eguard.mask_pii(f"序號{run}", role_id="r")
        assert run in result.sanitized_text


class TestPreservedBehavior:
    def test_letter_prefixed_id_not_masked(self, eguard):
        """Alphanumeric boundary still applies: XA123456789 is not a Taiwan ID."""
        result = eguard.mask_pii("代碼 XA123456789", role_id="r")
        assert "XA123456789" in result.sanitized_text

    def test_version_string_not_masked_as_ip(self, eguard):
        result = eguard.mask_pii("升級到 v1.2.3.4 版", role_id="r")
        assert "v1.2.3.4" in result.sanitized_text

    def test_localhost_skipped_in_code_context(self, eguard):
        result = eguard.mask_pii("連到127.0.0.1:8000", role_id="r", is_code_context=True)
        assert "127.0.0.1" in result.sanitized_text

    def test_spaced_english_still_masked(self, eguard):
        result = eguard.mask_pii(f"card {VALID_VISA} and id A123456789", role_id="r")
        assert VALID_VISA not in result.sanitized_text
        assert "A123456789" not in result.sanitized_text
