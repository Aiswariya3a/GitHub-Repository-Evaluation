-- Migration 002: Evaluation Pipeline Results
-- Stores structured evaluation results from the multi-agent pipeline.
-- Separate from existing evaluation tables — new pipeline results stored here.
-- Old tables (evaluations, evaluation_questions, evaluation_criteria) remain
-- until Phase 3 cleanup.

CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    rubric_version_id UUID NOT NULL REFERENCES rubric_versions(id),

    -- Capability extraction outputs (JSONB for flexible schema)
    repo_understanding JSONB,
    code_understanding JSONB,
    collaboration JSONB,

    -- Aggregated scores
    total_score NUMERIC(8,2) NOT NULL DEFAULT 0,
    max_score NUMERIC(8,2) NOT NULL DEFAULT 0,
    normalized_to_20 NUMERIC(7,2) NOT NULL DEFAULT 0,
    percentage NUMERIC(7,2) NOT NULL DEFAULT 0,

    -- Criterion-level results
    criterion_results JSONB NOT NULL DEFAULT '[]'::jsonb,
    low_confidence_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Feedback
    feedback JSONB,

    -- Pipeline metadata
    pipeline_version TEXT NOT NULL DEFAULT '2.0',
    pipeline_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (pipeline_status IN ('pending', 'running', 'success', 'partial', 'failed')),
    failed_agents JSONB NOT NULL DEFAULT '[]'::jsonb,
    error TEXT,
    evaluation_started_at TIMESTAMPTZ,
    evaluation_completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(repository_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_eval_results_session ON evaluation_results(session_id);
CREATE INDEX IF NOT EXISTS idx_eval_results_status ON evaluation_results(pipeline_status);
CREATE INDEX IF NOT EXISTS idx_eval_results_repo ON evaluation_results(repository_id);
