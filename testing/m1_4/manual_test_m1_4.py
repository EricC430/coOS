import hmac
import hashlib
import json
import requests
import time
import os

# --- Configurations ---
BASE_URL = "http://127.0.0.1:8000"
# Priority: 1. Env var, 2. Default "testsecret"
WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "testsecret")

def send_mock_webhook():
    print(f"Testing M1.4.2 GitHub Webhook with secret length: {len(WEBHOOK_SECRET)}...")
    url = f"{BASE_URL}/api/v1/webhooks/github"
    
    payload = {
        "repository": {"name": "test-repo"},
        "commits": [
            {
                "id": "abc123456789",
                "message": "test: manual webhook verification",
                "timestamp": "2026-06-07T10:00:00Z",
                "modified": ["src/test.py"]
            }
        ]
    }
    
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    
    headers = {
        "X-GitHub-Event": "push",
        "X-Hub-Signature-256": signature,
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(url, data=body, headers=headers)
        print(f"Response: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_local_git_binding(repo_path):
    print(f"\nTesting M1.4 Local Git Binding for {repo_path}...")
    url = f"{BASE_URL}/api/m1_4/bind_source"
    
    payload = {
        "source_type": "local_git",
        "repo_path": repo_path
    }
    
    try:
        resp = requests.post(url, json=payload)
        print(f"Response: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # You might need to set GITHUB_WEBHOOK_SECRET in your environment before running
    # os.environ["GITHUB_WEBHOOK_SECRET"] = "testsecret"
    
    send_mock_webhook()
    
    # Example usage:
    # test_local_git_binding("C:\\path\\to\\your\\repo")
