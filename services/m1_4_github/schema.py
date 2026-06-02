"""
M1.4 -- Git & Workflow Telemetry schemas

SPEC: docs/modules/M1_4_git_workflow_telemetry_SPEC.md
Research: [R06: 版本控制紀錄 §2.1] [R02: 時間動力學 §1.2]
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CommitInfo(BaseModel):
    hash: str
    message: str
    timestamp: str


class GitActivityPayload(BaseModel):
    repo_name: str
    repo_path: str = ""
    branch: str = "main"
    commit_count: int = 0
    files_changed: int = 0
    files: list[str] = []
    additions: int = 0
    deletions: int = 0
    commits: list[CommitInfo] = []
    changed_files: int = 0   # PR 用
    pr_number: int | None = None


class GitActivityEvent(BaseModel):
    module: Literal["M1.4.2", "M1.4.3"]
    action: Literal["commit_push", "pr_opened", "pr_closed", "local_commit"]
    payload: GitActivityPayload
