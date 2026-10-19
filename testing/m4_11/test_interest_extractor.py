import pytest
from m4_11_zpd_pipeline.interest_extractor import InterestExtractor, ExtractedContext


def test_interest_extractor_cold_start(db_session):
    """
    Test cold start fallback when there are no prior chat transcripts.
    Should return sensible domain defaults without crashing.
    """
    extractor = InterestExtractor(db_session=db_session)
    result = extractor.extract(user_id="new_user", role_id="role_csie")

    assert isinstance(result, ExtractedContext)
    assert result.is_cold_start is True
    assert result.interest_topic is not None
    assert len(result.interest_topic) > 0
    assert result.friction_point is None


def test_interest_extractor_with_friction_and_topics(db_session):
    """
    Test keyword-based pattern mining from simulated local chat transcripts.
    Extracts high-level topics and friction points without leaking raw L1 text.
    """
    extractor = InterestExtractor(db_session=db_session)

    # Simulate transcripts text mining
    sample_text = (
        "我今天在用 Docker network bridge 時遇到了 connection refused 錯誤，卡關了很久。"
        "一直想嘗試把容器之間的 DNS ping 通，但一直出現 failed 狀態。"
    )

    result = extractor.analyze_text(
        text=sample_text,
        role_id="role_csie",
    )

    assert result.is_cold_start is False
    assert "Docker" in result.interest_topic or "network" in result.interest_topic or "容器" in result.interest_topic
    assert result.friction_point is not None
    assert any(w in result.friction_point for w in ["錯誤", "卡關", "failed", "refused", "連線"])
