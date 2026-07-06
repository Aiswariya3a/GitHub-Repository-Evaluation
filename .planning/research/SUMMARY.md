# Research Summary

**Date:** 2026-07-06

## Key Findings

### Stack
- **Python 3.11+** with **Ollama** for local SLM inference
- **Qwen2.5-Coder 3B** (`qwen2.5-coder:3b`) for code understanding agents
- **Phi-4 Mini** (`phi-4-mini:3.8b`) for reasoning and feedback agents
- **JSON files on disk** for agent communication with JSON Schema validation
- **Pure Python** orchestration (no external frameworks)
- Existing **PostgreSQL** and **Flask** retained

### Architecture
- 3-stage pipeline: Ingestion → Capability Extraction → Rubric Evaluation → Aggregation → Feedback
- Capability extraction agents run in parallel (independent)
- Rubric criteria evaluated in parallel (per-criterion)
- Deterministic Python score aggregation (no LLM in arithmetic)
- Configurable subprocess/in-process execution

### Table Stakes
Repository cloning, GitHub metadata, AI evaluation, plagiarism detection, PDF reports, session management, custom rubrics, dashboard

### Differentiators
Multi-agent SLM architecture, rubric-agnostic evaluation, language-agnostic ingestion, deterministic scoring, evidence-based scores, local inference, per-criterion parallelism, partial results

### Watch Out For
- SLM JSON output instability → validate + re-prompt
- Context window overflow → keep agent inputs minimal
- Reproducibility → temperature=0, log everything
- Rubric-capability mapping gaps → flag low-confidence for review
- Language parsing gaps → tree-sitter with fallbacks
- Over-engineering → hardcode v1, extract patterns later
