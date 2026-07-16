#!/usr/bin/env python3
import re
<<<<<<< Updated upstream:archive/main.py
import argparse
=======
import warnings
>>>>>>> Stashed changes:main.py

import os
import time
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

warnings.simplefilter("ignore", FutureWarning)

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# -----------------------------
# CONFIGURATION
# -----------------------------


HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

CLONE_DIR = "repos"

BASE_REPO = "https://github.com/24UCS271-MiniProject/miniProjectSourceCode"

# Gemini setup
if GEMINI_API_KEY and genai is not None:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None

# -----------------------------
# LOAD SESSION REPOSITORIES FROM POSTGRESQL
# -----------------------------

parser = argparse.ArgumentParser()
parser.add_argument("--session-id", required=True)
args = parser.parse_args()

from services.repository_service import RepositoryService
from services.github_service import GitHubService
from services.analysis_service import AnalysisService
from services.rubric_service import RubricService
from repositories.session_repository import SessionRepository

session_store = RepositoryService()
github_service = GitHubService(GITHUB_TOKEN, CLONE_DIR)
analysis_service = AnalysisService(session_store)
rubric_service = RubricService()
evaluation_session = SessionRepository().get(args.session_id)
rubric = rubric_service.get_version(evaluation_session["rubric_version_id"])
repos = [
    repository for repository in session_store.list_repositories(args.session_id)
    if repository["status"] == "Evaluating"
]

# -----------------------------
# HELPERS
# -----------------------------

def clean_url(url):
    return github_service.clean_url(url)


# -----------------------------
# CHECK REPO
# -----------------------------

def sanitize_name(roll, repo_url):
    return github_service.sanitize_name(roll, repo_url)

def check_repo(repo_url):
    return github_service.check_repository(repo_url)


# -----------------------------
# CLONE REPO
# -----------------------------

def clone_repo(url, roll):
<<<<<<< Updated upstream:archive/main.py
    return github_service.clone(url, roll)
=======

    url = clean_url(url)

    name = sanitize_name(roll, url)
    path = os.path.join(CLONE_DIR, name)

    if not os.path.exists(path):

        print("Cloning:", url, "->", name)

        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        if result.returncode != 0:
            return None

    return path
>>>>>>> Stashed changes:main.py


# -----------------------------
# COMMIT COUNT (FIXED)
# -----------------------------

def get_commit_count(repo_url):
    return github_service.commit_count(repo_url)


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
    return analysis_service.added_code(base_code, student_code)


# -----------------------------
# GEMINI EVALUATION
# -----------------------------

def evaluate_code(code, roll):
    """
    Evaluate student code against the rubric-based criteria.
    
    Rubric Structure (Total 80 marks):
    Q1A: 8 marks - Compilation and Execution
    Q1B: 8 marks - Program Analysis and Debugging
    Q2A: 8 marks - Searching using Arrays and Strings
    Q2B: 8 marks - Sorting Account Records
    Q3A: 8 marks - Functional Decomposition
    Q3B: 8 marks - Pointer-Based Operations
    Q4A: 8 marks - Structure Enhancement
    Q4B: 8 marks - New Banking Feature Implementation
    Q5A: 8 marks - File Generation and Verification
    Q5B: 8 marks - Optimization and Error Handling
    """
    
    if not code.strip():
        return {"error": "No meaningful student code found"}

    if model is None:
        return {
            "error": "Gemini evaluation unavailable",
            "details": "Install google-generativeai and set GEMINI_API_KEY to enable AI scoring."
        }

    # Rubric definition with max marks for each component
    rubric_max_scores = {
        "Q1A": {
            "successful_compilation_and_execution": 2,
            "demonstration_of_menu_operations": 2,
            "explanation_of_control_structures": 2,
            "sample_testing_and_output": 2,
        },
        "Q1B": {
            "testing_effort": 2,
            "identification_of_issues": 3,
            "corrected_logic_and_explanation": 3,
        },
        "Q2A": {
            "proper_use_of_arrays_strings": 3,
            "searching_implementation": 3,
            "output_correctness": 2,
        },
        "Q2B": {
            "sorting_logic": 3,
            "correct_implementation": 3,
            "display_and_testing": 2,
        },
        "Q3A": {
            "function_decomposition": 4,
            "modular_design_and_readability": 4,
        },
        "Q3B": {
            "proper_pointer_implementation": 4,
            "explanation_and_correctness": 4,
        },
        "Q4A": {
            "structure_modification": 4,
            "proper_implementation_and_testing": 4,
        },
        "Q4B": {
            "feature_implementation": 4,
            "functionality_and_innovation": 4,
        },
        "Q5A": {
            "file_generation": 2,
            "file_update_verification": 3,
            "correction_of_file_issues": 3,
        },
        "Q5B": {
            "optimization_techniques": 4,
            "error_handling_implementation": 4,
        },
    }

    prompt = f"""
You are an expert C programming evaluator assessing student code against a detailed rubric.

IMPORTANT:
1. Evaluate ONLY student-added or modified code
2. Do NOT count base/template code provided to students
3. Be precise and strict in following the rubric marks limits
4. NEVER EXCEED the maximum marks specified for each component
5. Provide specific, constructive remarks for each criterion

Return ONLY valid JSON (no markdown, no backticks, no extra text).

Use this exact JSON structure with the rubric-based questions (Q1A through Q5B):

{{
  "roll_number": "{roll}",
  "questions": {{
    "Q1A": {{
      "successful_compilation_and_execution": {{"score": 0, "remarks": ""}},
      "demonstration_of_menu_operations": {{"score": 0, "remarks": ""}},
      "explanation_of_control_structures": {{"score": 0, "remarks": ""}},
      "sample_testing_and_output": {{"score": 0, "remarks": ""}},
      "total": 0
    }},
    "Q1B": {{
      "testing_effort": {{"score": 0, "remarks": ""}},
      "identification_of_issues": {{"score": 0, "remarks": ""}},
      "corrected_logic_and_explanation": {{"score": 0, "remarks": ""}},
      "total": 0
    }},
    "Q2A": {{
      "proper_use_of_arrays_strings": {{"score": 0, "remarks": ""}},
      "searching_implementation": {{"score": 0, "remarks": ""}},
      "output_correctness": {{"score": 0, "remarks": ""}},
      "total": 0
    }},
    "Q2B": {{
      "sorting_logic": {{"score": 0, "remarks": ""}},
      "correct_implementation": {{"score": 0, "remarks": ""}},
      "display_and_testing": {{"score": 0, "remarks": ""}},
      "total": 0
    }},
    "Q3A": {{
      "function_decomposition": {{"score": 0, "remarks": ""}},
      "modular_design_and_readability": {{"score": 0, "remarks": ""}},
      "total": 0
    }},
    "Q3B": {{
      "proper_pointer_implementation": {{"score": 0, "remarks": ""}},
      "explanation_and_correctness": {{"score": 0, "remarks": ""}},
      "total": 0
    }},
    "Q4A": {{
      "structure_modification": {{"score": 0, "remarks": ""}},
      "proper_implementation_and_testing": {{"score": 0, "remarks": ""}},
      "total": 0
    }},
    "Q4B": {{
      "feature_implementation": {{"score": 0, "remarks": ""}},
      "functionality_and_innovation": {{"score": 0, "remarks": ""}},
      "total": 0
    }},
    "Q5A": {{
      "file_generation": {{"score": 0, "remarks": ""}},
      "file_update_verification": {{"score": 0, "remarks": ""}},
      "correction_of_file_issues": {{"score": 0, "remarks": ""}},
      "total": 0
    }},
    "Q5B": {{
      "optimization_techniques": {{"score": 0, "remarks": ""}},
      "error_handling_implementation": {{"score": 0, "remarks": ""}},
      "total": 0
    }}
  }},
  "final": {{
    "total_out_of_80": 0,
    "normalized_to_20": 0.0,
    "overall_remarks": ""
  }}
}}

Rubric Constraints (MAX MARKS):
- Q1A total: 8 (each component max as shown)
- Q1B total: 8 (testing_effort:2, identification:3, correction:3)
- Q2A total: 8 (arrays:3, searching:3, output:2)
- Q2B total: 8 (sorting_logic:3, implementation:3, display:2)
- Q3A total: 8 (decomposition:4, modular:4)
- Q3B total: 8 (pointer:4, explanation:4)
- Q4A total: 8 (structure:4, implementation:4)
- Q4B total: 8 (feature:4, functionality:4)
- Q5A total: 8 (file_gen:2, verification:3, correction:3)
- Q5B total: 8 (optimization:4, error_handling:4)
- FINAL TOTAL: 80 MARKS MAXIMUM

Code to evaluate:
{code[:15000]}
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Extract JSON from response (handle markdown wrapping)
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
        
        start = text.find("{")
        end = text.rfind("}") + 1
        text = text[start:end]

        data = json.loads(text)

        # CRITICAL: Clamp all scores to rubric maximums and recalculate totals
        total_score = 0
        
        for question_id, question_data in data.get("questions", {}).items():
            if not isinstance(question_data, dict):
                continue
            
            question_total = 0
            max_for_question = rubric_max_scores.get(question_id, {})
            
            for component, value in question_data.items():
                if component == "total":
                    continue
                
                if isinstance(value, dict) and "score" in value:
                    max_score = max_for_question.get(component, 0)
                    
                    # Clamp score to maximum allowed
                    try:
                        original_score = float(value.get("score", 0))
                    except (ValueError, TypeError):
                        original_score = 0
                    
                    clamped_score = max(0, min(original_score, max_score))
                    value["score"] = round(clamped_score, 2)
                    question_total += clamped_score
            
            question_data["total"] = round(question_total, 2)
            total_score += question_total

        # Update final scores
        final = data.get("final", {})
        final["total_out_of_80"] = round(total_score, 2)
        final["normalized_to_20"] = round((total_score / 80) * 20, 2)

        return data

    except Exception as e:
        return {"error": "JSON parsing failed", "details": str(e)}


def evaluate_code_dynamic(code, roll, rubric_config):
    """Evaluate with a stored custom rubric; the built-in evaluator above is never routed here."""
    if not code.strip():
        return {"error": "No meaningful student code found"}
    schema = {category["code"]: {
        **{criterion["criterion_key"]: {"score": 0, "remarks": ""} for criterion in category["criteria"]},
        "total": 0,
    } for category in rubric_config["categories"]}
    constraints = "\n".join(
        f"- {category['code']} ({category['name']}): max {float(category['max_score'])}; " +
        ", ".join(f"{criterion['criterion_key']} max {float(criterion['max_score'])}" for criterion in category["criteria"])
        for category in rubric_config["categories"]
    )
    prompt = f"""You are an expert software-project evaluator.
Evaluate only the supplied repository code against the rubric below. Be strict and constructive.
Return ONLY valid JSON using this exact structure:
{json.dumps({'roll_number': roll, 'questions': schema, 'final': {'total_out_of_max': 0, 'normalized_to_20': 0, 'overall_remarks': ''}}, indent=2)}

Rubric: {rubric_config['name']} version {rubric_config['version']}
{constraints}

Code to evaluate:
{code[:15000]}"""
    try:
        text = model.generate_content(prompt).text.strip()
        text = re.sub(r"^```json\s*", "", text); text = re.sub(r"\s*```$", "", text).strip()
        data = json.loads(text[text.find("{"):text.rfind("}")+1])
        total = 0
        for category in rubric_config["categories"]:
            question = data.setdefault("questions", {}).setdefault(category["code"], {})
            category_total = 0
            for criterion in category["criteria"]:
                value = question.setdefault(criterion["criterion_key"], {"score": 0, "remarks": ""})
                try: score = float(value.get("score", 0))
                except (TypeError, ValueError): score = 0
                score = max(0, min(score, float(criterion["max_score"])))
                value["score"] = round(score, 2); category_total += score
            question["total"] = round(category_total, 2); total += category_total
        maximum = float(rubric_config["total_score"] or 1)
        data["final"] = {**data.get("final", {}), "total_out_of_80": round(total, 2),
                         "total_out_of_max": round(total, 2), "max_score": maximum,
                         "normalized_to_20": round(total / maximum * 20, 2)}
        return data
    except Exception as exc:
        return {"error": "JSON parsing failed", "details": str(exc)}


# -----------------------------
# MAIN
# -----------------------------

os.makedirs(CLONE_DIR, exist_ok=True)

print("Cloning base repo...")
BASE_PATH = clone_repo(BASE_REPO, "BASE")
BASE_CODE = read_code(BASE_PATH)

code_corpus = []
repo_names = []
roll_numbers = []

for i, row in enumerate(repos):

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

    evaluation = evaluate_code(eval_code, roll) if rubric["is_default"] else evaluate_code_dynamic(eval_code, roll, rubric)

    repo_result = {
        "roll_number": roll,
        "repo": repo,
        "public": public,
        "readme_exists": readme,
        "commit_count": commit_count
    }
    analysis_service.save_result(row["id"], repo_result, evaluation, rubric["version_id"])

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


analysis_service.save_plagiarism(args.session_id, plag_pairs)

print("Done.")
