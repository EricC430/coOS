import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from services.main import app

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    return db

@patch("services.main.update_env_file")
def test_get_settings_defaults(mock_update_env, mock_db):
    # Setup database mock
    with patch("services.main._db_adapter", mock_db):
        client = TestClient(app)
        response = client.get("/api/settings?role_id=uni_001")
        assert response.status_code == 200
        data = response.json()
        
        # Verify default properties
        assert data["content_capture"] == "off"
        assert data["voice_cloud"] is False
        assert data["cloud_sync"] is False
        assert data["theme"] == "default"
        assert data["notification_enabled"] is True
        assert data["daily_report_time"] == "22:00"
        assert data["focus_hours_start"] == "09:00"
        assert data["focus_hours_end"] == "18:00"
        assert "gemma_model" in data
        assert "ai_local_host" in data
        assert "ipad_ai_local_host" in data

@patch("services.main.update_env_file")
def test_get_settings_with_db_values(mock_update_env, mock_db):
    # Setup mock return values
    mock_db.fetch_all = AsyncMock(return_value=[
        {"consent_type": "content_capture_all", "granted": 1},
        {"consent_type": "voice_cloud", "granted": 1},
    ])
    mock_db.fetch_one = AsyncMock(return_value={
        "theme": "dark",
        "notification_enabled": 0,
        "daily_report_time": "20:30",
        "focus_hours_start": "10:00",
        "focus_hours_end": "19:00",
    })
    
    with patch("services.main._db_adapter", mock_db):
        client = TestClient(app)
        response = client.get("/api/settings?role_id=uni_001")
        assert response.status_code == 200
        data = response.json()
        
        assert data["content_capture"] == "all"
        assert data["voice_cloud"] is True
        assert data["theme"] == "dark"
        assert data["notification_enabled"] is False
        assert data["daily_report_time"] == "20:30"
        assert data["focus_hours_start"] == "10:00"
        assert data["focus_hours_end"] == "19:00"

@patch("services.main.update_env_file")
def test_post_settings_updates(mock_update_env, mock_db):
    payload = {
        "content_capture": "selected",
        "voice_cloud": True,
        "cloud_sync": False,
        "theme": "light",
        "notification_enabled": True,
        "daily_report_time": "18:00",
        "focus_hours_start": "08:00",
        "focus_hours_end": "17:00",
        "gemma_model": "test-gemma-model",
        "ai_local_host": "http://127.0.0.1:11434",
        "ipad_ai_local_host": "192.168.1.100:11434"
    }
    
    with patch("services.main._db_adapter", mock_db):
        client = TestClient(app)
        response = client.post("/api/settings?role_id=uni_001", json=payload)
        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        
        # Verify db execute calls are made
        assert mock_db.execute.call_count > 0
        
        # Verify env update call is made correctly
        mock_update_env.assert_called_once_with({
            "gemma_model": "test-gemma-model",
            "ai_local_host": "http://127.0.0.1:11434",
            "ipad_ai_local_host": "192.168.1.100:11434"
        })
