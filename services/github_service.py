import os
import re
import subprocess

import requests


class GitHubService:
    def __init__(self, token=None, clone_dir="repos"):
        self.headers = {"Authorization": f"token {token}"}
        self.clone_dir = clone_dir

    def clean_url(self, url): return url.strip().replace(".git", "").rstrip("/")
    def sanitize_name(self, roll, repo_url):
        name = f"{roll}_{repo_url.split('/')[-1]}"
        return re.sub(r'_+', '_', re.sub(r'[^a-zA-Z0-9._-]', '_', name))[:80]

    def check_repository(self, repo_url):
        repo_url = self.clean_url(repo_url)
        if "github.com/" not in repo_url: return False, False
        try:
            repo_path = repo_url.split("github.com/")[1]
            response = requests.get(f"https://api.github.com/repos/{repo_path}", headers=self.headers)
            if response.status_code != 200: return False, False
            files = requests.get(f"https://api.github.com/repos/{repo_path}/contents", headers=self.headers).json()
            return not response.json().get("private", True), any(isinstance(item, dict) and "readme" in item.get("name", "").lower() for item in files if isinstance(files, list))
        except Exception: return False, False

    def clone(self, url, roll):
        url = self.clean_url(url); path = os.path.join(self.clone_dir, self.sanitize_name(roll, url))
        if not os.path.exists(path):
            print("Cloning:", url, "→", os.path.basename(path))
            if subprocess.run(["git", "clone", "--depth", "1", url, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0: return None
        return path

    def commit_count(self, repo_url):
        try:
            repo_path = self.clean_url(repo_url).split("github.com/")[1]
            response = requests.get(f"https://api.github.com/repos/{repo_path}/commits?per_page=1", headers=self.headers)
            if "Link" in response.headers: return int(response.headers["Link"].split("page=")[-1].split(">")[0])
            return len(response.json())
        except Exception: return 0

    def get_contributors(self, repo_url: str) -> list[dict]:
        repo_path = self.clean_url(repo_url).split("github.com/")[1]
        contributors = []
        url = f"https://api.github.com/repos/{repo_path}/contributors?per_page=100"
        try:
            while url:
                response = requests.get(url, headers=self.headers)
                if response.status_code != 200:
                    break
                for item in response.json():
                    if isinstance(item, dict):
                        contributors.append({
                            "login": item.get("login", ""),
                            "contributions": item.get("contributions", 0),
                        })
                link_header = response.headers.get("Link", "")
                if 'rel="next"' in link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            url = part.split(";")[0].strip().strip("<>")
                            break
                else:
                    url = None
        except Exception:
            pass
        return contributors

    def get_pull_requests(self, repo_url: str) -> tuple[int, list[dict]]:
        repo_path = self.clean_url(repo_url).split("github.com/")[1]
        prs = []
        url = f"https://api.github.com/repos/{repo_path}/pulls?state=all&per_page=100"
        try:
            while url:
                response = requests.get(url, headers=self.headers)
                if response.status_code != 200:
                    break
                for item in response.json():
                    if isinstance(item, dict):
                        prs.append({
                            "number": item.get("number", 0),
                            "title": item.get("title", ""),
                            "state": item.get("state", ""),
                        })
                link_header = response.headers.get("Link", "")
                if 'rel="next"' in link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            url = part.split(";")[0].strip().strip("<>")
                            break
                else:
                    url = None
        except Exception:
            pass
        return len(prs), prs

    def get_issues(self, repo_url: str) -> tuple[int, list[dict]]:
        repo_path = self.clean_url(repo_url).split("github.com/")[1]
        issues = []
        url = f"https://api.github.com/repos/{repo_path}/issues?state=all&per_page=100"
        try:
            while url:
                response = requests.get(url, headers=self.headers)
                if response.status_code != 200:
                    break
                for item in response.json():
                    if isinstance(item, dict) and "pull_request" not in item:
                        issues.append({
                            "number": item.get("number", 0),
                            "title": item.get("title", ""),
                            "state": item.get("state", ""),
                        })
                link_header = response.headers.get("Link", "")
                if 'rel="next"' in link_header:
                    for part in link_header.split(","):
                        if 'rel="next"' in part:
                            url = part.split(";")[0].strip().strip("<>")
                            break
                else:
                    url = None
        except Exception:
            pass
        return len(issues), issues

    def get_full_metadata(self, repo_url: str) -> dict:
        commits = self.commit_count(repo_url)
        contributors = self.get_contributors(repo_url)
        pr_count, prs = self.get_pull_requests(repo_url)
        issue_count, issues = self.get_issues(repo_url)
        return {
            "commits_count": commits,
            "contributors": contributors,
            "pull_requests_count": pr_count,
            "pull_requests": prs,
            "issues_count": issue_count,
            "issues": issues,
        }
