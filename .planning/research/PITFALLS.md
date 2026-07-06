# Pitfalls Research

**Date:** 2026-07-06

## Domain-Specific Pitfalls

### Pitfall 1: SLM JSON Output Instability
**Warning signs:** Agent returns malformed JSON, missing fields, or incorrect types.
**Prevention:** Always validate against JSON Schema before accepting output. Re-prompt with the schema on failure (up to 2 retries). Use `ollama` with `format="json"` parameter where supported.
**Phase:** Evaluation Pipeline (Phase 2)

### Pitfall 2: Context Window Overflow
**Warning signs:** Agent output is truncated, missing evidence, or hallucinated content.
**Prevention:** Each agent receives only the minimum context. Ingestion pre-filters and summarizes before passing to agents. Set conservative `num_ctx` in Ollama (8192 tokens default is sufficient for focused agents).
**Phase:** Evaluation Pipeline (Phase 2)

### Pitfall 3: Reproducibility Across Runs
**Warning signs:** Same repository gets different scores on re-evaluation.
**Prevention:**
- Temperature=0 for all evaluation agents
- Log all agent inputs and outputs (JSON files are the audit trail)
- Deterministic aggregation (no LLM in scoring)
**Phase:** Evaluation Pipeline (Phase 2)

### Pitfall 4: Rubric Criteria That Don't Map to Extracted Capabilities
**Warning signs:** Rubric evaluation agent returns low-confidence scores or "insufficient evidence."
**Prevention:** Capability extraction agents should be broad enough to cover common rubric dimensions. The orchestration layer should detect low-confidence criteria and flag them for human review.
**Phase:** Capability Extraction (Phase 1/2)

### Pitfall 5: Language-Agnostic Parsing Gaps
**Warning signs:** New programming language not parsed correctly; functions/classes missed.
**Prevention:** Use tree-sitter or regex-based parsing with per-language extensions. Start with C, Python, Java, JavaScript. Fall back to line-by-line analysis for unknown languages.
**Phase:** Ingestion Pipeline (Phase 1)

### Pitfall 6: Ollama Not Running or Wrong Model Name
**Warning signs:** Agent crashes with connection error or model not found.
**Prevention:** Validate Ollama connectivity and model availability at startup. Configurable host/port and model names in `.env`. Clear error messages telling the user to run `ollama pull <model>`.
**Phase:** Evaluation Pipeline (Phase 2)

### Pitfall 7: Over-Engineering the Agent Framework
**Warning signs:** Adding abstraction layers, plugin systems, or dynamic agent loading before the core pipeline works.
**Prevention:** Hardcode the first pipeline end-to-end. Extract abstractions only when a clear pattern emerges. The configurable agent registry can come in a later phase.
**Phase:** All phases

### Pitfall 8: Leaving Old Evaluation Logic as Dead Code
**Warning signs:** Old `main.py` evaluation code remains, creating confusion and maintenance burden.
**Prevention:** After the new pipeline is verified, systematically remove the old evaluation logic, old evaluation tables if desired, and references to the old `evaluate_code` functions.
**Phase:** Cleanup (Phase 3)

---
*Pitfalls research: 2026-07-06*
