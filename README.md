# Automated GitHub Repository Evaluation & Plagiarism Detection

This project is a **Python-based evaluation pipeline** that:

* Validates student GitHub repositories
* Clones repositories automatically
* Extracts and compares student-added code
* Evaluates code using **Google Gemini API**
* Detects plagiarism using **TF-IDF + cosine similarity**
* Generates structured reports

---

## Features

* ✅ Repository validation (public + README check)
* ✅ Automated cloning of multiple repos
* ✅ Commit count extraction via GitHub API
* ✅ Base vs student code delta detection
* ✅ AI-based evaluation
* ✅ Plagiarism detection (cosine similarity > 0.8)
* ✅ CSV report generation

---

## Project Structure

```
.
├── repos.csv                  # Input file with repo URLs and roll numbers
├── repos/                     # Cloned repositories (auto-generated)
├── repo_report.csv            # Repo validation results
├── plagiarism_report.csv      # Plagiarism detection output
├── evaluation_report.csv      # AI evaluation results
├── script.py                  # Main pipeline script
├── .env                       # API keys (not committed)
```

---

## ⚙️ Setup

### 1. Clone the project

```bash
git clone <your-repo-url>
cd <project-folder>
```

---

### 2. Install dependencies

```bash
pip install -r re+uirements.txt
```

---

### 3. Create `.env` file

Create a file named `.env` in the root directory:

```
GITHUB_TOKEN=your_github_token
GEMINI_API_KEY=your_gemini_api_key
```

---

### 4. Prepare input CSV

`repos.csv` format:

```
roll_number,repo_url
101,https://github.com/user/repo1
102,https://github.com/user/repo2
```

---

## ▶️ How It Works

### Step 1: Load repositories

* Reads `repos.csv`
* Cleans URLs and roll numbers

---

### Step 2: Repository validation

* Checks:

  * Repository exists
  * Public or private
  * README presence

---

### Step 3: Clone repositories

* Uses `git clone --depth 1`
* Saves repos inside `/repos`

---

### Step 4: Code extraction

* Reads all source files (`.py, .c, .cpp, .java, .js, ...`)
* Extracts:

  * Full code
  * `trans.c` if present

---

### Step 5: Delta detection (IMPORTANT)

* Compares student repo with base repo
* Extracts **only newly added code**
* Ignores template/base code

---

### Step 6: AI Evaluation (Gemini)

* Evaluates:

  * Self effort
  * Code understanding
  * Modifications
  * Innovation
* Returns structured JSON
* Automatically clamps scores to allowed limits

---

### Step 7: Plagiarism detection

* Uses:

  * `TfidfVectorizer`
  * `cosine_similarity`
* Flags similarity > **0.8**

---

### Step 8: Report generation

| File                    | Description                  |
| ----------------------- | ---------------------------- |
| `repo_report.csv`       | Repo validity + commit count |
| `plagiarism_report.csv` | Similar repo pairs           |
| `evaluation_report.csv` | AI evaluation results        |

---

## 🧠 Key Functions

* `sanitize_name()` → safe folder naming
* `check_repo()` → GitHub API validation
* `clone_repo()` → shallow cloning
* `get_commit_count()` → optimized commit counting
* `read_code()` → multi-language code extraction
* `get_added_code()` → delta detection
* `evaluate_code()` → Gemini-based scoring

---

## ⚠️ Important Notes

* `.env` file must NOT be committed
* GitHub API has rate limits (use token)
* Gemini API responses are parsed → JSON must be valid
* Large repos may slow execution

---

## 🛡️ .gitignore (Recommended)

```
.env
repos/
*.csv
__pycache__/
```

---

## 🔧 Possible Improvements

* Parallel repo processing (multithreading)
* Better plagiarism threshold tuning
* AST-based code comparison (instead of TF-IDF)
* Retry mechanism for API failures
* UI dashboard for reports

---

## 🧩 Use Case

Ideal for:

* Academic evaluations
* Coding assignments
* Mini-project assessments
* Automated grading systems

---

## 📌 Summary

This system automates the entire evaluation pipeline:

**Input → Clone → Analyze → Evaluate → Detect Plagiarism → Export Reports**

It reduces manual effort while maintaining structured, scalable assessment.

---