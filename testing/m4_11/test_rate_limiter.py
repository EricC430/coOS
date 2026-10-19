import pytest
from fastapi import HTTPException
from m4_11_zpd_pipeline.rate_limiter import SlidingWindowRateLimiter
from m4_11_zpd_pipeline.service import ZPDPipelineService


def test_sliding_window_rate_limiter():
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=3600)
    user_id = "user_rate_test"
    role_id = "role_rate_test"

    for _ in range(5):
        allowed, retry_after = limiter.is_allowed(user_id, role_id)
        assert allowed is True
        assert retry_after == 0

    # 6th request must be rejected
    allowed, retry_after = limiter.is_allowed(user_id, role_id)
    assert allowed is False
    assert retry_after > 0


def test_service_rate_limit_429(db_session):
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=3600)
    service = ZPDPipelineService(db_session=db_session, rate_limiter=limiter)

    user_id = "test_user_429"
    role_id = "test_role_429"

    service.draw_challenge(user_id=user_id, role_id=role_id, force_fallback=True)
    service.draw_challenge(user_id=user_id, role_id=role_id, force_fallback=True)

    with pytest.raises(HTTPException) as exc_info:
        service.draw_challenge(user_id=user_id, role_id=role_id, force_fallback=True)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers
