"""
JARVIS GitHub Agent - Repository analysis, commits, branches, issues.

Provides async GitHub API integration for repo intelligence, dependency
analysis, and release note summarization.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"


class GitHubAgentError(Exception):
    """Base exception for GitHub Agent errors."""


class GitHubAgent:
    """GitHub Agent for repo analysis, commits, branches, issues."""

    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get(GITHUB_TOKEN_ENV)
        self._session = requests.Session()
        if self.token:
            self._session.headers["Authorization"] = f"token {self.token}"
        self._session.headers["Accept"] = "application/vnd.github+json"
        self._session.headers["User-Agent"] = "JARVIS-AI"

    def _check_rate_limit(self) -> dict[str, Any]:
        try:
            resp = self._session.get(f"{GITHUB_API_URL}/rate_limit", timeout=10)
            resp.raise_for_status()
            rate = resp.json().get("resources", {}).get("core", {})
            return {
                "limit": rate.get("limit"),
                "remaining": rate.get("remaining"),
                "reset": rate.get("reset"),
            }
        except Exception as exc:
            logger.debug("Rate limit check failed: %s", exc)
            return {"limit": None, "remaining": None, "reset": None}

    def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        resp = self._session.request(method, url, timeout=30, **kwargs)
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            status = resp.status_code
            if status == 403:
                rate = self._check_rate_limit()
                err_msg = f"GitHub API rate limit exceeded or forbidden. Remaining: {rate.get('remaining')}"
                return {"status": "error", "error": err_msg, "data": None, "rate_limit": rate}
            err_msg = f"GitHub API error {status}: {resp.text[:500]}"
            return {"status": "error", "error": err_msg, "data": None}
        return {"status": "ok", "error": None, "data": resp.json()}

    async def analyze_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Analyze a GitHub repository metadata and basic stats."""
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
        result = await asyncio.to_thread(self._request, "GET", url)
        if result["status"] == "error":
            return result
        data = result["data"]
        dependencies: dict[str, Any] = {"detected": False, "files": [], "summary": []}
        for q in ["requirements.txt", "requirements-dev.txt", "Pipfile", "pyproject.toml", "package.json"]:
            check_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{q}"
            f_res = await asyncio.to_thread(self._request, "GET", check_url)
            if f_res["status"] == "ok" and f_res["data"]:
                dependencies["detected"] = True
                dependencies["files"].append(q)
                if q in ("requirements.txt", "requirements-dev.txt"):
                    raw_url = f_res["data"].get("download_url", "")
                    if raw_url:
                        raw_res = await asyncio.to_thread(self._request, "GET", raw_url)
                        if raw_res["status"] == "ok" and isinstance(raw_res["data"], str):
                            lines = [line.strip() for line in raw_res["data"].splitlines() if line.strip() and not line.startswith("#")]
                            dependencies["summary"].append({"file": q, "items": lines[:20]})
        return {
            "status": "ok",
            "error": None,
            "data": {
                "repo": data,
                "dependencies": dependencies,
                "rate_limit": self._check_rate_limit(),
            },
        }

    async def get_commits(self, owner: str, repo: str, limit: int = 20) -> list[dict]:
        """Fetch recent commits for a repository."""
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits?per_page={limit}&page=1"
        result = await asyncio.to_thread(self._request, "GET", url)
        if result["status"] == "error":
            return [{"error": result["error"]}]
        commits = []
        for c in result["data"][:limit]:
            commit = c.get("commit", {})
            commits.append(
                {
                    "sha": c.get("sha"),
                    "message": commit.get("message"),
                    "author": commit.get("author", {}).get("name") if commit.get("author") else None,
                    "date": commit.get("author", {}).get("date") if commit.get("author") else None,
                    "url": c.get("html_url"),
                }
            )
        return commits

    async def get_branches(self, owner: str, repo: str) -> list[dict]:
        """Fetch branches for a repository."""
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/branches?per_page=100"
        result = await asyncio.to_thread(self._request, "GET", url)
        if result["status"] == "error":
            return [{"error": result["error"]}]
        branches = []
        for b in result["data"]:
            branches.append(
                {
                    "name": b.get("name"),
                    "sha": b.get("commit", {}).get("sha"),
                    "protected": b.get("protected", False),
                    "url": b.get("commit", {}).get("html_url"),
                }
            )
        return branches

    async def get_release_notes(self, owner: str, repo: str, limit: int = 5) -> list[dict]:
        """Fetch recent releases."""
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/releases?per_page={limit}&page=1"
        result = await asyncio.to_thread(self._request, "GET", url)
        if result["status"] == "error":
            return [{"error": result["error"]}]
        releases = []
        for r in result["data"][:limit]:
            releases.append(
                {
                    "name": r.get("name"),
                    "tag": r.get("tag_name"),
                    "url": r.get("html_url"),
                    "published_at": r.get("published_at"),
                    "body": r.get("body", "")[:2000],
                    "draft": r.get("draft", False),
                    "prerelease": r.get("prerelease", False),
                }
            )
        return releases

    async def summarize_issues(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch and summarize open and closed issues."""
        open_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=open&per_page=100&page=1"
        closed_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=closed&per_page=100&page=1"
        open_result, closed_result = await asyncio.gather(
            asyncio.to_thread(self._request, "GET", open_url),
            asyncio.to_thread(self._request, "GET", closed_url),
        )
        open_issues = []
        closed_issues = []
        if open_result["status"] == "ok":
            for i in open_result["data"]:
                if "pull_request" not in i:
                    open_issues.append(
                        {
                            "number": i.get("number"),
                            "title": i.get("title"),
                            "state": i.get("state"),
                            "created_at": i.get("created_at"),
                            "user": i.get("user", {}).get("login") if i.get("user") else None,
                            "labels": [label.get("name") for label in i.get("labels", [])],
                            "url": i.get("html_url"),
                        }
                    )
        if closed_result["status"] == "ok":
            for i in closed_result["data"]:
                if "pull_request" not in i:
                    closed_issues.append(
                        {
                            "number": i.get("number"),
                            "title": i.get("title"),
                            "state": i.get("state"),
                            "closed_at": i.get("closed_at"),
                            "user": i.get("user", {}).get("login") if i.get("user") else None,
                            "url": i.get("html_url"),
                        }
                    )
        label_counts: dict[str, int] = {}
        for issue in open_issues + closed_issues:
            for label in issue.get("labels", []):
                label_counts[label] = label_counts.get(label, 0) + 1
        return {
            "status": "ok",
            "error": None,
            "data": {
                "owner": owner,
                "repo": repo,
                "open_count": len(open_issues),
                "closed_count": len(closed_issues),
                "top_labels": sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                "open_issues": open_issues[:20],
                "closed_issues": closed_issues[:20],
                "rate_limit": self._check_rate_limit(),
            },
        }

    async def get_repo_summary(self, owner: str, repo: str) -> dict[str, Any]:
        """Return a comprehensive summary combining analysis, commits, branches, and releases."""
        analysis, commits, branches, releases, issues = await asyncio.gather(
            self.analyze_repo(owner, repo),
            self.get_commits(owner, repo, limit=10),
            self.get_branches(owner, repo),
            self.get_release_notes(owner, repo, limit=5),
            self.summarize_issues(owner, repo),
        )
        return {
            "status": "ok",
            "error": None,
            "data": {
                "analysis": analysis.get("data", {}),
                "recent_commits": commits,
                "branches": branches,
                "recent_releases": releases,
                "issues": issues.get("data", {}),
            },
        }
