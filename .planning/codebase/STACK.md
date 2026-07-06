# Technology Stack

**Analysis Date:** 2026-07-06

## Languages

**Primary:**
- Python 3.11.9 - All backend logic, evaluation pipeline, API endpoints, report generation

**Secondary:**
- HTML (Jinja2 templates) - Server-rendered frontend views in `templates/`
- CSS - Styling in `static/styles.css` and `static/dashboard.css`
- JavaScript (vanilla, inline in templates) - Minimal frontend interactivity (command palette, toasts, dialogs)

## Runtime

**Environment:**
- Python 3.11 (compatible with 3.7+ per project docs)

**Package Manager:**
- pip
- Lockfile: `requirements.txt` (pinned versions)

## Frameworks

**Core Web Framework:**
- Flask 3.1.3 - WSGI web application with Blueprint-based routing
  - Entry point: `app.py` (`create_app()` factory)
  - Blueprints: `session_controller`, `repository_controller`, `evaluation_controller`, `report_controller`, `rubric_controller`

**Template Engine:**
- Jinja2 (included with Flask) - Server-side HTML rendering (`templates/*.html`)

**Testing:**
- Not detected (no test files, no pytest/vitest/jest config)

**Build/Dev:**
- No build tools, bundlers, or transpilers. All CSS is hand-written, JS is inline.

## Key Dependencies

**Critical:**
- `google-generativeai==0.8.6` - Google Gemini API client for AI-based code evaluation (`main.py`, `evaluate_code()`)
- `requests==2.32.5` - GitHub REST API calls for repository validation and commit count (`services/github_service.py`)
- `psycopg[binary]==3.2.9` - PostgreSQL adapter for all persistence (`database/postgres.py`)
- `scikit-learn==1.8.0` - TF-IDF vectorization + cosine similarity for plagiarism detection (`main.py`)
- `flask==3.1.3` - Web framework for the dashboard/management UI (`app.py`)
- `python-dotenv==1.2.2` - `.env` file loading for secrets

**Infrastructure:**
- `GitPython==3.1.46` - Git operations (used only indirectly; actual cloning uses `git clone` subprocess in `services/github_service.py`)
- `reportlab==4.4.10` - PDF generation for student reports (`pdf_gen.py`)
- `PyPDF2==3.0.1` - PDF merging for consolidated reports (`pdf_gen.py`)
- `pandas==3.0.1` - Data manipulation for PDF report generation (`pdf_gen.py`)
- `numpy==2.4.3` - Numerical operations (dependency of scikit-learn and pandas)

## Configuration

**Environment:**
- `.env` file (root directory, not committed per `.gitignore`)
- Variables loaded via `dotenv.load_dotenv()` in `app.py` and `main.py`

**Key Configs Required:**
- `GITHUB_TOKEN` - GitHub personal access token for API calls
- `GEMINI_API_KEY` - Google Gemini API key for AI evaluation
- `DATABASE_URL` - PostgreSQL connection string (e.g. `postgresql://postgres:postgres@localhost:5432/repository_evaluation`)

**Build:**
- No build configuration files detected

## Platform Requirements

**Development:**
- Python 3.7+
- PostgreSQL database (create `repository_evaluation` database)
- `pip install -r requirements.txt`
- `.env` file with GITHUB_TOKEN, GEMINI_API_KEY, DATABASE_URL

**Production:**
- Flask development server (`app.run(debug=True, host="0.0.0.0", port=5000)`) — not production-ready
- No production server configuration (no gunicorn/uvicorn config)
- No containerization (no Dockerfile detected)
- No deployment scripts detected

---

*Stack analysis: 2026-07-06*
