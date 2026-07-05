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
