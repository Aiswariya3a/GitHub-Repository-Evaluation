import re

import requests
import pandas as pd
import subprocess
import os
import time
import json
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# -----------------------------
# CONFIGURATION
# -----------------------------


HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

CSV_FILE = "repos.csv"
CLONE_DIR = "repos"

BASE_REPO = "https://github.com/24UCS271-MiniProject/miniProjectSourceCode"

# Gemini setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# -----------------------------
# LOAD CSV
# -----------------------------

repos = pd.read_csv(CSV_FILE)
repos.columns = repos.columns.str.strip().str.lower()

repos["repo_url"] = repos["repo_url"].astype(str).str.strip()
repos["roll_number"] = repos["roll_number"].astype(str).str.strip()

# -----------------------------
# HELPERS
# -----------------------------

def clean_url(url):
    return url.strip().replace(".git", "").rstrip("/")


# -----------------------------
# CHECK REPO
# -----------------------------

def sanitize_name(roll, repo_url):
    repo_name = repo_url.split("/")[-1]
    name = f"{roll}_{repo_name}"
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    name = re.sub(r'_+', '_', name)
    return name[:80]

def check_repo(repo_url):

    repo_url = clean_url(repo_url)

    if "github.com/" not in repo_url:
        return False, False

    repo_path = repo_url.split("github.com/")[1]

    try:
        api = f"https://api.github.com/repos/{repo_path}"
        r = requests.get(api, headers=HEADERS)

        if r.status_code != 200:
            return False, False

        data = r.json()
        public = not data.get("private", True)

        contents_api = f"https://api.github.com/repos/{repo_path}/contents"
        files = requests.get(contents_api, headers=HEADERS).json()

        readme = any(
            isinstance(f, dict) and "readme" in f.get("name", "").lower()
            for f in files if isinstance(files, list)
        )

        return public, readme

    except:
        return False, False


# -----------------------------
# CLONE REPO
# -----------------------------

def clone_repo(url, roll):

    url = clean_url(url)

    name = sanitize_name(roll, url)
    path = os.path.join(CLONE_DIR, name)

    if not os.path.exists(path):

        print("Cloning:", url, "→", name)

        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        if result.returncode != 0:
            return None

    return path


# -----------------------------
# COMMIT COUNT (FIXED)
# -----------------------------

def get_commit_count(repo_url):

    repo_url = clean_url(repo_url)
    repo_path = repo_url.split("github.com/")[1]

    try:
        commits_api = f"https://api.github.com/repos/{repo_path}/commits?per_page=1"
        r = requests.get(commits_api, headers=HEADERS)

        if 'Link' in r.headers:
            link = r.headers['Link']
            last = link.split('page=')[-1].split('>')[0]
            return int(last)

        return len(r.json())

    except:
        return 0


# -----------------------------
# READ CODE
# -----------------------------

def read_code(path):

    code = ""

    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith((".py",".c",".cpp",".java",".js",".ts",".html",".css",".go",".rs")):
                try:
                    with open(os.path.join(root, f), encoding="utf8", errors="ignore") as file:
                        code += file.read() + "\n"
                except:
                    pass

    return code


# -----------------------------
# FIND trans.c (FIXED)
# -----------------------------

def extract_trans_c(path):

    for root, dirs, files in os.walk(path):
        for f in files:
            if f.lower().strip() == "trans.c":
                try:
                    with open(os.path.join(root, f), encoding="utf8", errors="ignore") as file:
                        return file.read()
                except:
                    return ""

    return ""


# -----------------------------
# DELTA CODE (BASE VS STUDENT)
# -----------------------------

def get_added_code(base_code, student_code):

    base_lines = set(line.strip() for line in base_code.splitlines() if line.strip())
    student_lines = student_code.splitlines()

    added = [
        line for line in student_lines
        if line.strip() and line.strip() not in base_lines
    ]

    return "\n".join(added)


# -----------------------------
# GEMINI EVALUATION
# -----------------------------

def evaluate_code(code, roll):

    if not code.strip():
        return {"error": "No meaningful student code found"}

    prompt = f"""
You are evaluating student-added modifications ONLY.

Focus on:
- New logic
- Improvements
- Added features

Ignore base/template code.

Return STRICT JSON only.

Strictly follow score limits:
- 5 means max 5
- 10 means max 10
- 20 means max 20
Any violation is incorrect.

{{
  "roll_number": "{roll}",
  "scores": {{
    "general": {{"self_effort": {{"score": 0,"remarks": ""}},"total": 0}},
    "comprehension": {{"domain_knowledge": {{"score": 0,"remarks": ""}},"added_functionality_ideas": {{"score": 0,"remarks": ""}},"code_comprehension": {{"score": 0,"remarks": ""}},"total": 0}},
    "modification": {{"code_improvement": {{"score": 0,"remarks": ""}},"functional_decomposition": {{"score": 0,"remarks": ""}},"memory_optimization": {{"score": 0,"remarks": ""}},"speed_optimization": {{"score": 0,"remarks": ""}},"total": 0}},
    "innovation": {{"new_features_basic": {{"score": 0,"remarks": ""}},"requirement_translation": {{"score": 0,"remarks": ""}},"added_functionality_simple": {{"score": 0,"remarks": ""}},"added_functionality_advanced": {{"score": 0,"remarks": ""}},"total": 0}}
  }},
  "final": {{"total_out_of_100": 0,"normalized_to_10": 0,"overall_remarks": ""}}
}}

Code:
{code[:12000]}
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        text = re.sub(r"^```json", "", text)
        text = re.sub(r"```$", "", text).strip()

        start = text.find("{")
        end = text.rfind("}") + 1

        text = text[start:end]

        data = json.loads(text)

        # recompute totals safely
        total = 0
        for sec in data["scores"].values():
            MAX_SCORES = {
                    "general": {
                        "self_effort": 5
                    },
                    "comprehension": {
                        "domain_knowledge": 5,
                        "added_functionality_ideas": 5,
                        "code_comprehension": 5
                    },
                    "modification": {
                        "code_improvement": 5,
                        "functional_decomposition": 10,
                        "memory_optimization": 10,
                        "speed_optimization": 10
                    },
                    "innovation": {
                        "new_features_basic": 5,
                        "requirement_translation": 10,
                        "added_functionality_simple": 10,
                        "added_functionality_advanced": 20
                    }
                }
            total = 0

            for sec_name, sec in data["scores"].items():

                sec_total = 0

                for field, value in sec.items():

                    if isinstance(value, dict) and "score" in value:

                        max_allowed = MAX_SCORES[sec_name].get(field, 0)

                        # clamp score
                        score = max(0, min(value["score"], max_allowed))

                        value["score"] = score
                        sec_total += score

                sec["total"] = sec_total
                total += sec_total

        data["final"]["total_out_of_100"] = total
        data["final"]["normalized_to_10"] = round((total/100)*10, 2)

        return data

    except Exception as e:
        return {"error": "JSON parsing failed", "raw": str(e)}


# -----------------------------
# MAIN
# -----------------------------

os.makedirs(CLONE_DIR, exist_ok=True)

print("Cloning base repo...")
BASE_PATH = clone_repo(BASE_REPO, "BASE")
BASE_CODE = read_code(BASE_PATH)

results = []
evaluation_results = []

code_corpus = []
repo_names = []
roll_numbers = []

for i, row in repos.iterrows():

    repo = clean_url(row["repo_url"])
    roll = row["roll_number"]

    print(f"[{i+1}] Processing:", repo)

    public, readme = check_repo(repo)
    path = clone_repo(repo, roll)

    commit_count = get_commit_count(repo)

    code = ""
    trans_code = ""
    added_code = ""

    if path:
        code = read_code(path)
        trans_code = extract_trans_c(path)
        added_code = get_added_code(BASE_CODE, code)

    # plagiarism corpus → ONLY added code
    if added_code.strip():
        code_corpus.append(added_code)
        repo_names.append(repo)
        roll_numbers.append(roll)

    eval_code = added_code if added_code.strip() else trans_code

    evaluation = evaluate_code(eval_code, roll)

    evaluation_results.append({
        "roll_number": roll,
        "repo": repo,
        "evaluation": json.dumps(evaluation)
    })

    results.append({
        "roll_number": roll,
        "repo": repo,
        "public": public,
        "readme_exists": readme,
        "commit_count": commit_count
    })

    time.sleep(1.2)


# -----------------------------
# PLAGIARISM
# -----------------------------

print("Running plagiarism...")

plag_pairs = []

if len(code_corpus) > 1:

    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(code_corpus)

    similarity = cosine_similarity(tfidf)

    for i in range(len(repo_names)):
        for j in range(i+1, len(repo_names)):
            if similarity[i][j] > 0.8:
                plag_pairs.append({
                    "roll1": roll_numbers[i],
                    "roll2": roll_numbers[j],
                    "similarity": float(similarity[i][j])
                })


# -----------------------------
# SAVE
# -----------------------------

pd.DataFrame(results).to_csv("repo_report.csv", index=False)
pd.DataFrame(plag_pairs).to_csv("plagiarism_report.csv", index=False)
pd.DataFrame(evaluation_results).to_csv("evaluation_report.csv", index=False)

print("Done.")