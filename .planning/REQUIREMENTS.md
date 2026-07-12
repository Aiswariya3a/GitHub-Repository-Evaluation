# Requirements: GitHub Repository Evaluation — Multi-Agent SLM Pipeline

**Defined:** 2026-07-06
**Core Value:** Accurately evaluate student code against any instructor-defined rubric using a modular, rubric-agnostic pipeline of specialized SLM agents

## v1 Requirements

### Ingestion Pipeline

- [x] **ING-01**: System can clone a student GitHub repository into a working directory
- [x] **ING-02**: System fetches GitHub metadata (commits, contributors, PRs, issues) via API
- [x] **ING-03**: System discovers source files dynamically by extension and shebang (language-agnostic)
- [x] **ING-04**: System parses source files to extract functions, classes, imports, and docstrings
- [x] **ING-05**: System computes code metrics (lines of code, cyclomatic complexity, comment ratio)
- [x] **ING-06**: System compares student code against a base repository if configured (delta detection)
- [x] **ING-07**: System writes all ingestion results to structured JSON in the working directory
- [x] **ING-08**: System persists repository metadata and code metrics to PostgreSQL

### Capability Extraction Agents

- [ ] **AGN-01**: Repository Understanding Agent identifies languages, key files, and produces a structural summary
- [ ] **AGN-02**: Code Understanding Agent extracts capabilities — algorithms, APIs, data structures, functions, file operations, error handling patterns
- [ ] **AGN-03**: Collaboration Analysis Agent analyzes commits, contributors, PRs, and issues for collaboration metrics
- [ ] **AGN-04**: All capability agents run in parallel (they are independent)
- [ ] **AGN-05**: Each agent reads from ingestion JSON and writes structured capability JSON to working directory
- [x] **AGN-06**: Each agent output validates against a predefined JSON Schema

### Rubric Evaluation

- [ ] **EVA-01**: System loads rubric from PostgreSQL (categories → criteria with max_score)
- [ ] **EVA-02**: Rubric Evaluation Agent evaluates one criterion at a time using only relevant extracted evidence
- [ ] **EVA-03**: Each evaluation returns score, confidence, evidence, and remarks
- [ ] **EVA-04**: All criteria are evaluated in parallel (they are independent)
- [ ] **EVA-05**: Low-confidence evaluations are flagged for human review
- [ ] **EVA-06**: Scores are aggregated deterministically in Python (no LLM in arithmetic)
- [ ] **EVA-07**: Final score is clamped to rubric maximums

### Feedback Generation

- [ ] **FDB-01**: Feedback Agent receives all criterion scores and evidence
- [ ] **FDB-02**: Feedback Agent generates strengths, weaknesses, and actionable improvement suggestions
- [ ] **FDB-03**: Structured feedback is written to working directory JSON and PostgreSQL

### Orchestrator

- [ ] **ORC-01**: Python orchestrator manages the full pipeline lifecycle
- [ ] **ORC-02**: Orchestrator supports configurable execution mode (subprocess default, in-process for debugging)
- [ ] **ORC-03**: Orchestrator validates all agent outputs against JSON Schema; re-prompts on failure (up to 2 retries)
- [ ] **ORC-04**: Orchestrator schedules independent agents for parallel execution
- [ ] **ORC-05**: Orchestrator handles partial results — if an agent fails, pipeline continues with available data
- [ ] **ORC-06**: Orchestrator creates per-session working directories with unique temp paths
- [ ] **ORC-07**: Orchestrator persists final evaluation results to PostgreSQL

### Ollama Integration

- [x] **OLL-01**: Ollama host and port are configurable via environment variables
- [x] **OLL-02**: Code understanding agents use Qwen2.5-Coder 3B (`qwen2.5-coder:3b`)
- [x] **OLL-03**: Reasoning and feedback agents use Phi-4 Mini (`phi-4-mini:3.8b`)
- [x] **OLL-04**: System validates Ollama connectivity and model availability at startup
- [x] **OLL-05**: All inference uses temperature=0 for reproducibility

### Testing

- [ ] **TST-01**: Unit tests for each agent (mocked Ollama responses)
- [ ] **TST-02**: Unit tests for orchestrator workflow and error handling
- [ ] **TST-03**: Integration tests for the full pipeline with real repositories
- [ ] **TST-04**: JSON Schema contract tests for all agent inputs and outputs

### Cleanup

- [x] **CLN-01**: Remove old single-prompt evaluation logic from `main.py`
- [ ] **CLN-02**: Remove old evaluation data from PostgreSQL
- [x] **CLN-03**: Remove duplicate evaluation code paths (`evaluate_code` + `evaluate_code_dynamic`)
- [ ] **CLN-04**: Remove or archive legacy `models/domain.py` dead code
- [x] **CLN-05**: Ensure only one evaluation engine exists in the codebase

## v2 Requirements

- **OLL-06**: Support additional models (e.g., Qwen3-Coder, DeepSeek-Coder) via configuration
- **AGN-07**: Additional capability agents (Documentation Analysis, Complexity Analysis)
- **EVA-08**: Human-in-the-loop review for low-confidence evaluations via UI
- **TST-05**: Performance benchmark suite for agent latency
- **ING-09**: Multi-language parsing via tree-sitter

## Out of Scope

| Feature | Reason |
|---------|--------|
| Authentication/OAuth | Application assumes trusted network |
| Real-time streaming results | Adds complexity; batch evaluation is sufficient |
| Multi-tenant/SaaS deployment | Not needed for current use case |
| Containerization/Docker | No immediate deployment need |
| Binary/non-text file evaluation | Out of scope for code evaluation |
| Mobile app | Web-only |
| External API-dependent LLMs | Moving to local inference via Ollama |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ING-01 | Phase 1 | Complete |
| ING-02 | Phase 1 | Complete |
| ING-03 | Phase 1 | Complete |
| ING-04 | Phase 1 | Complete |
| ING-05 | Phase 1 | Complete |
| ING-06 | Phase 1 | Complete |
| ING-07 | Phase 1 | Complete |
| ING-08 | Phase 1 | Complete |
| AGN-01 | Phase 2 | Pending |
| AGN-02 | Phase 2 | Pending |
| AGN-03 | Phase 2 | Pending |
| AGN-04 | Phase 2 | Pending |
| AGN-05 | Phase 2 | Pending |
| AGN-06 | Phase 2 | Complete |
| EVA-01 | Phase 2 | Pending |
| EVA-02 | Phase 2 | Pending |
| EVA-03 | Phase 2 | Pending |
| EVA-04 | Phase 2 | Pending |
| EVA-05 | Phase 2 | Pending |
| EVA-06 | Phase 2 | Pending |
| EVA-07 | Phase 2 | Pending |
| FDB-01 | Phase 2 | Pending |
| FDB-02 | Phase 2 | Pending |
| FDB-03 | Phase 2 | Pending |
| ORC-01 | Phase 2 | Pending |
| ORC-02 | Phase 2 | Pending |
| ORC-03 | Phase 2 | Pending |
| ORC-04 | Phase 2 | Pending |
| ORC-05 | Phase 2 | Pending |
| ORC-06 | Phase 2 | Pending |
| ORC-07 | Phase 2 | Pending |
| OLL-01 | Phase 2 | Complete |
| OLL-02 | Phase 2 | Complete |
| OLL-03 | Phase 2 | Complete |
| OLL-04 | Phase 2 | Complete |
| OLL-05 | Phase 2 | Complete |
| TST-01 | Phase 3 | Pending |
| TST-02 | Phase 3 | Pending |
| TST-03 | Phase 3 | Pending |
| TST-04 | Phase 3 | Pending |
| CLN-01 | Phase 3 | Complete |
| CLN-02 | Phase 3 | Pending |
| CLN-03 | Phase 3 | Complete |
| CLN-04 | Phase 3 | Pending |
| CLN-05 | Phase 3 | Complete |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 45 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-06*
*Last updated: 2026-07-06 after initial definition*
