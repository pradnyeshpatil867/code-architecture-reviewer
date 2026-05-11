import httpx
import base64
from typing import Optional
import re


class GitHubService:
    BASE = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.headers = {"Accept": "application/vnd.github+json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def parse_repo(self, url: str) -> tuple[str, str]:
        match = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {url}")
        return match.group(1), match.group(2).rstrip("/")

    async def get_repo_info(self, owner: str, repo: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.BASE}/repos/{owner}/{repo}",
                headers=self.headers
            )
            r.raise_for_status()
            return r.json()

    async def get_tree(self, owner: str, repo: str, branch: str = "main") -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.BASE}/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": "1"},
                headers=self.headers,
                timeout=30,
            )
            if r.status_code == 404:
                r = await client.get(
                    f"{self.BASE}/repos/{owner}/{repo}/git/trees/master",
                    params={"recursive": "1"},
                    headers=self.headers,
                    timeout=30,
                )
            r.raise_for_status()
            return r.json().get("tree", [])

    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.BASE}/repos/{owner}/{repo}/contents/{path}",
                headers=self.headers,
                timeout=20,
            )
            if r.status_code != 200:
                return ""
            data = r.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
            return data.get("content", "")

    async def get_languages(self, owner: str, repo: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.BASE}/repos/{owner}/{repo}/languages",
                headers=self.headers
            )
            r.raise_for_status()
            return r.json()