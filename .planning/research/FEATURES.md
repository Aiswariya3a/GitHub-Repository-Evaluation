# Features Research

**Date:** 2026-07-06

## Feature Categories

### Table Stakes (Must Have)
- Repository cloning and validation
- GitHub metadata extraction (commits, contributors)
- AI-based code evaluation against rubrics
- Plagiarism detection
- PDF report generation
- Session management
- Custom rubric creation and management
- Dashboard with metrics and visualizations

### Differentiators (Competitive Advantage)
- **Multi-agent SLM architecture** — Each agent has one job; modular, debuggable, extensible
- **Rubric-agnostic evaluation** — Works with any rubric; rubric is data, not code
- **Language-agnostic ingestion** — Auto-detects language and parses accordingly
- **Deterministic scoring** — LLMs don't do arithmetic; aggregation is pure Python
- **Evidence-based scoring** — Every score includes evidence and confidence
- **Local inference** — No API costs, no data leaving the machine, works offline
- **Per-criterion parallel evaluation** — Scales with rubric size
- **Partial results** — If one agent fails, others continue

### Anti-Features (Deliberately NOT Building)
- Agent-per-rubric-item design — Wouldn't scale; rubric changes break the pipeline
- External API-dependent LLMs — Gemini API cost and latency are the current pain point
- Real-time streaming results — Adds complexity without clear benefit for batch evaluation
- Multi-tenant architecture — Not needed for current use case

## Existing Features (Preserved)
- Flask dashboard UI (updated to show agent pipeline results)
- PostgreSQL persistence
- PDF report generation
- Rubric CRUD and versioning
- Session management
- Plagiarism detection (TF-IDF + cosine similarity)

---
*Features research: 2026-07-06*
