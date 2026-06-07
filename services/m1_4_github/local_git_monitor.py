"""
M1.4.3 -- Local Git Monitor

SPEC: docs/modules/M1_4_git_workflow_telemetry_SPEC.md §7.3
Research:
  [R06: 版本控制紀錄 §2.1] Git commit history as cognitive state sensor
  [R02: 時間動力學 §1.2] Commit interval burst features

100% offline operation — no network required.
Scans watched local .git directories every SCAN_INTERVAL_S seconds,
emitting GitActivityEvent for each new commit detected since last scan.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
from collections.abc import Callable, Awaitable
from pathlib import Path

logger = logging.getLogger(__name__)

SCAN_INTERVAL_S = 60


class LocalGitMonitor:
    """[R06 §2.1] Periodically scan local Git repos for new commits."""

    def __init__(self, watched_paths: list[str], emit_fn: Callable[[dict], Awaitable[None]]):
        self._watched_paths = watched_paths
        self._emit_fn = emit_fn
        # repo_path -> last seen HEAD hash
        self._last_seen: dict[str, str] = {}

    async def scan_loop(self) -> None:
        """Background loop — call as asyncio task."""
        while True:
            for path in self._watched_paths:
                await self._check_repo(path)
            await asyncio.sleep(SCAN_INTERVAL_S)

    async def _check_repo(self, repo_path: str) -> None:
        """[R06 §2.1] Check one repo for new commits since last scan."""
        try:
            latest_hash = self._git(repo_path, ["log", "--format=%H", "-1"])
            if not latest_hash:
                return

            last_seen = self._last_seen.get(repo_path)
            if last_seen == latest_hash:
                return  # no new commits

            commits = self._get_new_commits(repo_path, since_hash=last_seen)
            if not commits:
                self._last_seen[repo_path] = latest_hash
                return

            stats = self._get_diff_stats(repo_path, since_hash=last_seen)
            branch = self._git(repo_path, ["branch", "--show-current"]) or "detached"

            event: dict = {
                "module": "M1.4.3",
                "action": "local_commit",
                "payload": {
                    "repo_name": Path(repo_path).name,
                    "repo_path": repo_path,         # absolute path — L1 local only
                    "branch": branch,
                    "commit_count": len(commits),
                    "files_changed": stats["files_changed"],
                    "files": stats["files"],         # relative paths only
                    "additions": stats["additions"],
                    "deletions": stats["deletions"],
                    "commits": commits,
                },
            }
            await self._emit_fn(event)
            self._last_seen[repo_path] = latest_hash

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # Repo gone or git not installed — silently skip
            pass

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------

    def _git(self, repo_path: str, args: list[str], timeout: int = 5) -> str:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()

    def _get_new_commits(self, repo_path: str, since_hash: str | None) -> list[dict]:
        """[R02 §1.2] Retrieve commits since last seen hash."""
        if since_hash:
            args = ["log", f"{since_hash}..HEAD", "--format=%H%x1F%s%x1F%ai"]
        else:
            # First scan: show only the latest commit (HEAD~1 may not exist)
            args = ["log", "--max-count=1", "--format=%H%x1F%s%x1F%ai"]

        raw = self._git(repo_path, args)
        if not raw:
            return []

        commits = []
        for line in raw.splitlines():
            parts = line.split("\x1f")
            if len(parts) >= 2:
                commits.append({
                    "hash": parts[0][:12],
                    "message": parts[1],
                    "timestamp": parts[2] if len(parts) > 2 else "",
                })
        return commits

    def _get_diff_stats(self, repo_path: str, since_hash: str | None) -> dict:
        """[R02 §1.2] Get diff statistics (additions, deletions, files) since last hash."""
        if since_hash:
            raw = self._git(repo_path, ["diff", "--numstat", f"{since_hash}..HEAD"])
        else:
            # First commit: diff against empty tree
            empty_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            raw = self._git(repo_path, ["diff", "--numstat", empty_tree, "HEAD"])
        additions = 0
        deletions = 0
        files: list[str] = []

        for line in raw.splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                try:
                    additions += int(parts[0])
                    deletions += int(parts[1])
                except ValueError:
                    pass
                # Store relative file path only (never absolute)
                rel_path = parts[2].lstrip("/").lstrip("\\")
                files.append(rel_path)

        return {
            "files_changed": len(files),
            "files": files,
            "additions": additions,
            "deletions": deletions,
        }
