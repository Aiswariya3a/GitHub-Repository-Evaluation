# Technology Stack

**Analysis Date:** 2026-07-13

## Languages

**Primary:**
- Python 3.11.9 - All application, service, controller, model, and test code

**Secondary:**
- JavaScript/TypeScript (detected via `config/extensions.json`) - Student repositories being evaluated may contain JS/TS; no server-side JS used
- C, C++, Java, Go, Rust, Ruby (detected via `config/extensions.json`) - Student repositories may contain these languages; the ingestion pipeline (`services/ingestion/code_parser.py`) uses regex-based pattern extraction for JS, TS, Python, and Java

**Frontend:**
- HTML (Jinja2 templates in `templates/`) - 12 template files for the web dashboard
- CSS (`static/styles.css`, `static/dashboard.css`) - Dark-theme UI styling

## Runtime

**Environment:**
- CPython 3.11.9
- Virtual environment managed by `uv` (v0.11.13) at `.venv/`

**Package Manager:**
- `pip` via `requirements.txt`
- Lock file: Not detected (no `requirements.lock` or `poetry.lock`)
- Dependency installer: `uv` (v0.11.13) detected from `pyvenv.cfg`

## Frameworks

**Core Web:**
- Flask 3.x (implicit, via `flask` import in `app.py`) - HTTP server, blueprint routing, Jinja2 templating
- ASGI wrapper: `asgiref.wsgi.WsgiToAsgi` (`app.py:3`) - Wraps Flask WSGI app for ASGI server compatibility

**ASGI Server:**
- uvicorn 0.34.3 - Production ASGI server (`app.py:33-34`), configured on port 5001

**Testing:**
- pytest >=8.0,<9.0 - Test framework, configured in `pytest.ini`

**Object Validation:**
- pydantic 2.12.5 (`pydantic_core` 2.41.5) - Not actively imported in source code; present as transitive dependency

**Data Science & ML:**
- pandas 3.0.1 - CSV report generation, score aggregation in `pdf_gen.py`
- scikit-learn 1.8.0 - Available but not imported in application source; potential future use
- numpy 2.4.3 - Transitive dependency via pandas/scikit-learn
- joblib 1.5.3 - Transitive dependency
- scipy 1.17.1 - Transitive dependency

**PDF Generation:**
- reportlab 4.4.10 - PDF document generation (`pdf_gen.py`)
- PyPDF2 3.0.1 - PDF merging (`pdf_gen.py:428`)
- pillow 12.1.1 - Image handling for reportlab

## Key Dependencies

**Critical:**
| Package | Version | Why it matters |
|---------|---------|----------------|
| Flask | (latest 3.x) | Web framework, all HTTP routes, template rendering |
| psycopg[binary] | 3.2.9 | PostgreSQL database driver, all persistence |
| requests | 2.32.5 | Ollama HTTP client + GitHub API client |
| GitPython | 3.1.46 | Repository cloning in ingestion pipeline |
| uvicorn | 0.34.3 | Production ASGI server |
| asgiref | 3.11.1 | Flask-to-ASGI bridging |
| python-dotenv | 1.2.2 | Environment variable loading from `.env` |
| jsonschema | (transitive) | Agent output validation against JSON Schema (draft-07) |
| tqdm | 4.67.3 | Progress bars for CLI operations |

**Infrastructure:**
| Package | Version | Purpose |
|---------|---------|---------|
| google-generativeai | 0.8.6 | Installed but NOT imported in any source file — unused dependency |
| google-ai-generativelanguage | 0.6.15 | Transitive dependency of google-generativeai |
| google-api-python-client | 2.193.0 | Transitive dependency |
| google-auth | 2.49.1 | Transitive dependency |
| cryptography | 46.0.5 | Transitive dependency of PyMySQL/psycopg |
| colorama | 0.4.6 | Terminal color output |

## Configuration

**Environment:**
- `.env` file (present, listed in `.gitignore`) - Loaded by `python-dotenv` in `app.py:7`
- `example.env` - Documents required env vars
- Required env vars: `GITHUB_TOKEN`, `DATABASE_URL`

**Ollama Configuration (env vars):**
- `OLLAMA_HOST` (default: `http://localhost`) - Ollama server host
- `OLLAMA_PORT` (default: `11434`) - Ollama server port
- `OLLAMA_TIMEOUT` (default: `300`) - Inference timeout in seconds
- `OLLAMA_CODE_MODEL` (default: `qwen2.5-coder:3b`) - Model for code tasks
- `OLLAMA_REASONING_MODEL` (default: `phi-4-mini:3.8b`) - Model for reasoning tasks

**Build/Config files:**
- `pytest.ini` - Test runner config, marker definitions, test paths
- `config/extensions.json` - Language extension definitions for file discovery

## Platform Requirements

**Development:**
- Python 3.11+
- PostgreSQL 14+ (locally or remotely)
- Ollama server running locally with models pulled (`qwen2.5-coder:3b`, `phi-4-mini:3.8b`)
- GitHub personal access token (for API calls)

**Production:**
- ASGI-compatible server (uvicorn)
- PostgreSQL database
- Ollama server accessible from the application host
- GitHub token for repository metadata fetching

---

*Stack analysis: 2026-07-13*
