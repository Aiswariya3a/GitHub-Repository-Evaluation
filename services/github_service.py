import logging
import os
import re
import shutil
import subprocess

import requests


logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self, token=None, clone_dir="repos"):
        if token is None:
            token = os.environ.get("GITHUB_TOKEN", "")
        self.token = token
        self.clone_dir = clone_dir
        self._session: requests.Session | None = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Accept": "application/vnd.github.v3+json",
            })
            if self.token:
                self._session.headers.update({"Authorization": f"Bearer {self.token}"})
        return self._session

    def clean_url(self, url):
        return url.strip().replace(".git", "").rstrip("/")

    def sanitize_name(self, roll, repo_url):
        name = f"{roll}_{repo_url.split('/')[-1]}"
        return re.sub(r'_+', '_', re.sub(r'[^a-zA-Z0-9._-]', '_', name))[:80]

    def _api_get(self, endpoint: str) -> requests.Response | None:
        url = f"https://api.github.com{endpoint}"
        try:
            resp = self._get_session().get(url, timeout=15)
            if resp.status_code == 401:
                logger.warning("GitHub API 401 on GET %s — token may be invalid", endpoint)
            elif resp.status_code == 403:
                logger.warning("GitHub API 403 on GET %s — rate limited or forbidden", endpoint)
            elif resp.status_code == 404:
                logger.warning("GitHub API 404 on GET %s — not found", endpoint)
            elif resp.status_code != 200:
                logger.warning("GitHub API %d on GET %s", resp.status_code, endpoint)
            return resp
        except requests.RequestException as e:
            logger.error("GitHub API request failed on GET %s: %s", endpoint, e)
            return None

    def get_repo_metadata(self, repo_url: str) -> dict:
        repo_url = self.clean_url(repo_url)
        if "github.com/" not in repo_url:
            return {}
        try:
            repo_path = repo_url.split("github.com/")[1]
            resp = self._api_get(f"/repos/{repo_path}")
            if resp is None or resp.status_code != 200:
                return {}
            data = resp.json()
            return {
                "description": data.get("description") or "",
                "language": data.get("language") or "",
                "topics": data.get("topics") or [],
                "stars_count": data.get("stargazers_count") or 0,
                "forks_count": data.get("forks_count") or 0,
                "size": data.get("size") or 0,
                "default_branch": data.get("default_branch") or "",
                "license_info": (data.get("license") or {}).get("spdx_id") or "",
                "open_issues_count": data.get("open_issues_count") or 0,
                "watchers_count": data.get("watchers_count") or 0,
                "github_created_at": data.get("created_at") or "",
                "github_updated_at": data.get("updated_at") or "",
                "is_public": not data.get("private", True),
            }
        except Exception:
            return {}

    def check_repository(self, repo_url):
        repo_url = self.clean_url(repo_url)
        if "github.com/" not in repo_url:
            return False, False
        try:
            repo_path = repo_url.split("github.com/")[1]
            resp = self._api_get(f"/repos/{repo_path}")
            if resp is None or resp.status_code != 200:
                return False, False
            files_resp = self._api_get(f"/repos/{repo_path}/contents")
            files = files_resp.json() if files_resp and files_resp.status_code == 200 else []
            return not resp.json().get("private", True), any(
                isinstance(item, dict) and "readme" in item.get("name", "").lower()
                for item in files if isinstance(files, list)
            )
        except Exception:
            return False, False

    def _has_source_files(self, path: str) -> bool:
        """Check if a directory contains any files beyond .git."""
        try:
            for entry in os.scandir(path):
                if entry.name != ".git":
                    return True
            return False
        except OSError:
            return False

    def clone(self, url, roll):
        url = self.clean_url(url)
        path = os.path.join(self.clone_dir, self.sanitize_name(roll, url))
        if os.path.exists(path):
            if not self._has_source_files(path):
                print("Incomplete clone detected (only .git), re-cloning:", url)
                shutil.rmtree(path, ignore_errors=True)
                if os.path.exists(path):
                    subprocess.run(
                        ["rmdir", "/s", "/q", path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        shell=True,
                    )
            else:
                return path
        print("Cloning:", url, "\u2192", os.path.basename(path))
        if subprocess.run(
            ["git", "clone", "--depth", "1", url, path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode != 0:
            return None
        return path

    def commit_count(self, repo_url):
        try:
            repo_path = self.clean_url(repo_url).split("github.com/")[1]
            resp = self._api_get(f"/repos/{repo_path}/commits?per_page=1")
            if resp is None or resp.status_code != 200:
                return 0
            if "Link" in resp.headers:
                try:
                    return int(resp.headers["Link"].split("page=")[-1].split(">")[0])
                except (ValueError, IndexError):
                    pass
            commits = resp.json()
            return len(commits) if isinstance(commits, list) else 0
        except Exception:
            return 0

    def get_commits(self, repo_url: str, max_pages: int = 2) -> list[dict]:
        repo_path = self.clean_url(repo_url).split("github.com/")[1]
        commits = []
        url_path = f"/repos/{repo_path}/commits?per_page=50"
        pages = 0
        try:
            while url_path and pages < max_pages:
                resp = self._api_get(url_path)
                if resp is None or resp.status_code != 200:
                    break
                for item in resp.json():
                    if isinstance(item, dict):
                        author = item.get("commit", {}).get("author", {})
                        commits.append({
                            "sha": item.get("sha", "")[:12],
                            "author": author.get("name", item.get("author", {}).get("login", "unknown")),
                            "date": author.get("date", ""),
                            "message": item.get("commit", {}).get("message", "").split("\n")[0],
                        })
                link_header = resp.headers.get("Link", "")
                if 'rel="next"' in link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            next_url = part.split(";")[0].strip().strip("<>")
                            url_path = next_url.replace("https://api.github.com", "")
                            break
                else:
                    url_path = None
                pages += 1
        except Exception:
            pass
        return commits

    def get_contributors(self, repo_url: str) -> list[dict]:
        repo_path = self.clean_url(repo_url).split("github.com/")[1]
        contributors = []
        url_path = f"/repos/{repo_path}/contributors?per_page=100"
        try:
            while url_path:
                resp = self._api_get(url_path)
                if resp is None or resp.status_code != 200:
                    break
                for item in resp.json():
                    if isinstance(item, dict):
                        contributors.append({
                            "login": item.get("login", ""),
                            "contributions": item.get("contributions", 0),
                            "html_url": item.get("html_url", ""),
                            "avatar_url": item.get("avatar_url", ""),
                        })
                link_header = resp.headers.get("Link", "")
                if 'rel="next"' in link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            next_url = part.split(";")[0].strip().strip("<>")
                            url_path = next_url.replace("https://api.github.com", "")
                            break
                else:
                    url_path = None
        except Exception:
            pass
        return contributors

    def get_pull_requests(self, repo_url: str) -> tuple[int, list[dict]]:
        repo_path = self.clean_url(repo_url).split("github.com/")[1]
        prs = []
        url_path = f"/repos/{repo_path}/pulls?state=all&per_page=100"
        try:
            while url_path:
                resp = self._api_get(url_path)
                if resp is None or resp.status_code != 200:
                    break
                for item in resp.json():
                    if isinstance(item, dict):
                        prs.append({
                            "number": item.get("number", 0),
                            "title": item.get("title", ""),
                            "state": item.get("state", ""),
                            "author": item.get("user", {}).get("login", ""),
                            "created_at": item.get("created_at", ""),
                            "closed_at": item.get("closed_at", ""),
                            "merged_at": item.get("merged_at", None),
                        })
                link_header = resp.headers.get("Link", "")
                if 'rel="next"' in link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            next_url = part.split(";")[0].strip().strip("<>")
                            url_path = next_url.replace("https://api.github.com", "")
                            break
                else:
                    url_path = None
        except Exception:
            pass
        return len(prs), prs

    def get_issues(self, repo_url: str) -> tuple[int, list[dict]]:
        repo_path = self.clean_url(repo_url).split("github.com/")[1]
        issues = []
        url_path = f"/repos/{repo_path}/issues?state=all&per_page=100"
        try:
            while url_path:
                resp = self._api_get(url_path)
                if resp is None or resp.status_code != 200:
                    break
                for item in resp.json():
                    if isinstance(item, dict) and "pull_request" not in item:
                        issues.append({
                            "number": item.get("number", 0),
                            "title": item.get("title", ""),
                            "state": item.get("state", ""),
                            "author": item.get("user", {}).get("login", ""),
                            "created_at": item.get("created_at", ""),
                            "closed_at": item.get("closed_at", ""),
                        })
                link_header = resp.headers.get("Link", "")
                if 'rel="next"' in link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            next_url = part.split(";")[0].strip().strip("<>")
                            url_path = next_url.replace("https://api.github.com", "")
                            break
                else:
                    url_path = None
        except Exception:
            pass
        return len(issues), issues

    def get_full_metadata(self, repo_url: str) -> dict:
        commits = self.commit_count(repo_url)
        recent_commits = self.get_commits(repo_url)
        contributors = self.get_contributors(repo_url)
        pr_count, prs = self.get_pull_requests(repo_url)
        issue_count, issues = self.get_issues(repo_url)

        is_public = False
        has_readme = False
        try:
            repo_path = self.clean_url(repo_url).split("github.com/")[1]
            resp = self._api_get(f"/repos/{repo_path}")
            if resp and resp.status_code == 200:
                data = resp.json()
                is_public = not data.get("private", True)
                files_resp = self._api_get(f"/repos/{repo_path}/contents")
                if files_resp and files_resp.status_code == 200:
                    files = files_resp.json()
                    if isinstance(files, list):
                        has_readme = any(
                            isinstance(item, dict) and "readme" in item.get("name", "").lower()
                            for item in files
                        )
        except Exception:
            pass

        if not commits and not recent_commits and not contributors:
            logger.warning(
                "GitHub metadata all-zero for %s — check token validity and rate limits",
                repo_url,
            )

        return {
            "commits_count": commits,
            "recent_commits": recent_commits,
            "contributors": contributors,
            "pull_requests_count": pr_count,
            "pull_requests": prs,
            "issues_count": issue_count,
            "issues": issues,
            "is_public": is_public,
            "readme_exists": has_readme,
        }
