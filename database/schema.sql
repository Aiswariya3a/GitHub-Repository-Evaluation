CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS rubrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
    rubric_type TEXT NOT NULL CHECK(rubric_type IN ('System','Custom')), is_default BOOLEAN NOT NULL DEFAULT FALSE,
    is_read_only BOOLEAN NOT NULL DEFAULT FALSE, is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS rubric_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), rubric_id UUID NOT NULL REFERENCES rubrics(id) ON DELETE CASCADE,
    version INTEGER NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(rubric_id,version)
);
CREATE TABLE IF NOT EXISTS rubric_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), rubric_version_id UUID NOT NULL REFERENCES rubric_versions(id) ON DELETE CASCADE,
    code TEXT NOT NULL, name TEXT NOT NULL, max_score NUMERIC(8,2) NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE(rubric_version_id,code)
);
CREATE TABLE IF NOT EXISTS rubric_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), category_id UUID NOT NULL REFERENCES rubric_categories(id) ON DELETE CASCADE,
    criterion_key TEXT NOT NULL, name TEXT NOT NULL, max_score NUMERIC(8,2) NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE(category_id,criterion_key)
);

CREATE TABLE IF NOT EXISTS evaluation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Completed','Archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE evaluation_sessions ADD COLUMN IF NOT EXISTS rubric_version_id UUID REFERENCES rubric_versions(id);

CREATE TABLE IF NOT EXISTS repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    roll_number TEXT NOT NULL,
    repo_url TEXT NOT NULL,
    evaluation_status TEXT NOT NULL DEFAULT 'Pending' CHECK (evaluation_status IN ('Pending','Evaluating','Completed','Failed')),
    error TEXT NOT NULL DEFAULT '',
    is_public BOOLEAN,
    readme_exists BOOLEAN,
    commit_count INTEGER,
    evaluated_at TIMESTAMPTZ,
    description TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT '',
    topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    stars_count INTEGER NOT NULL DEFAULT 0,
    forks_count INTEGER NOT NULL DEFAULT 0,
    size INTEGER NOT NULL DEFAULT 0,
    default_branch TEXT NOT NULL DEFAULT '',
    license_info TEXT NOT NULL DEFAULT '',
    open_issues_count INTEGER NOT NULL DEFAULT 0,
    watchers_count INTEGER NOT NULL DEFAULT 0,
    github_created_at TIMESTAMPTZ,
    github_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(session_id, repo_url)
);
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT '';
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS topics JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS stars_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS forks_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS size INTEGER NOT NULL DEFAULT 0;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS default_branch TEXT NOT NULL DEFAULT '';
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS license_info TEXT NOT NULL DEFAULT '';
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS open_issues_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS watchers_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS github_created_at TIMESTAMPTZ;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS github_updated_at TIMESTAMPTZ;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS progress_pct INTEGER NOT NULL DEFAULT 0;
ALTER TABLE repositories ADD COLUMN IF NOT EXISTS current_step TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL UNIQUE REFERENCES repositories(id) ON DELETE CASCADE,
    total_out_of_80 NUMERIC(7,2),
    normalized_to_20 NUMERIC(7,2),
    overall_remarks TEXT NOT NULL DEFAULT '',
    error TEXT,
    error_details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS rubric_version_id UUID REFERENCES rubric_versions(id);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS total_score NUMERIC(8,2);
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS max_score NUMERIC(8,2);

CREATE TABLE IF NOT EXISTS evaluation_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    question_code TEXT NOT NULL,
    total NUMERIC(7,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(evaluation_id, question_code)
);

CREATE TABLE IF NOT EXISTS evaluation_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES evaluation_questions(id) ON DELETE CASCADE,
    criterion_key TEXT NOT NULL,
    score NUMERIC(7,2),
    remarks TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(question_id, criterion_key)
);

CREATE TABLE IF NOT EXISTS code_quality (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, metric TEXT NOT NULL, value TEXT, score NUMERIC(7,2), remarks TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, metric));
CREATE TABLE IF NOT EXISTS documentation (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, metric TEXT NOT NULL, value TEXT, score NUMERIC(7,2), remarks TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, metric));
CREATE TABLE IF NOT EXISTS collaboration (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, metric TEXT NOT NULL, value TEXT, score NUMERIC(7,2), remarks TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, metric));
CREATE TABLE IF NOT EXISTS project_health (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, metric TEXT NOT NULL, value TEXT, score NUMERIC(7,2), remarks TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, metric));
CREATE TABLE IF NOT EXISTS technologies (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, name TEXT NOT NULL, version TEXT, category TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, name));
CREATE TABLE IF NOT EXISTS contributors (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, github_login TEXT NOT NULL, display_name TEXT, contributions INTEGER, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, github_login));
CREATE TABLE IF NOT EXISTS commits (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, sha TEXT NOT NULL, author_name TEXT, author_email TEXT, message TEXT, committed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, sha));
CREATE TABLE IF NOT EXISTS pull_requests (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, github_number INTEGER NOT NULL, title TEXT, state TEXT, author_login TEXT, opened_at TIMESTAMPTZ, closed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, github_number));
CREATE TABLE IF NOT EXISTS issues (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, github_number INTEGER NOT NULL, title TEXT, state TEXT, author_login TEXT, opened_at TIMESTAMPTZ, closed_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, github_number));
CREATE TABLE IF NOT EXISTS files (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE, path TEXT NOT NULL, language TEXT, size_bytes BIGINT, line_count INTEGER, content_hash TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(repository_id, path));
CREATE TABLE IF NOT EXISTS evaluation_metadata (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE, metadata_key TEXT NOT NULL, metadata_value TEXT, value_type TEXT NOT NULL DEFAULT 'string', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(evaluation_id, metadata_key));
CREATE TABLE IF NOT EXISTS plagiarism_results (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), session_id UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE, repository1_id UUID REFERENCES repositories(id) ON DELETE CASCADE, repository2_id UUID REFERENCES repositories(id) ON DELETE CASCADE, roll1 TEXT NOT NULL, roll2 TEXT NOT NULL, similarity DOUBLE PRECISION NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(session_id, roll1, roll2));

CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    rubric_version_id UUID REFERENCES rubric_versions(id),
    repo_understanding JSONB,
    code_understanding JSONB,
    collaboration JSONB,
    total_score NUMERIC(8,2),
    max_score NUMERIC(8,2),
    normalized_to_20 NUMERIC(7,2),
    percentage NUMERIC(7,2),
    criterion_results JSONB,
    low_confidence_criteria JSONB,
    feedback JSONB,
    pipeline_status TEXT,
    failed_agents JSONB,
    error TEXT,
    evaluation_started_at TIMESTAMPTZ,
    evaluation_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(repository_id, session_id)
);

CREATE TABLE IF NOT EXISTS review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_review','reviewed')),
    assigned_reviewer TEXT NOT NULL DEFAULT '',
    flag_reason TEXT NOT NULL DEFAULT 'low_confidence' CHECK (flag_reason IN ('low_confidence','manual_override','random_sample')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(repository_id)
);

CREATE TABLE IF NOT EXISTS score_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    criterion_key TEXT NOT NULL DEFAULT '',
    original_score NUMERIC(8,2),
    overridden_score NUMERIC(8,2) NOT NULL,
    reasoning TEXT NOT NULL,
    overridden_by TEXT NOT NULL DEFAULT 'instructor',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    old_value TEXT NOT NULL DEFAULT '',
    new_value TEXT NOT NULL DEFAULT '',
    reasoning TEXT NOT NULL DEFAULT '',
    performed_by TEXT NOT NULL DEFAULT 'instructor',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_review_queue_session ON review_queue(session_id, status);
CREATE INDEX IF NOT EXISTS idx_review_queue_repository ON review_queue(repository_id);
CREATE INDEX IF NOT EXISTS idx_score_overrides_session ON score_overrides(session_id);
CREATE INDEX IF NOT EXISTS idx_score_overrides_repository ON score_overrides(repository_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_session ON audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_repository ON audit_log(repository_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON evaluation_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_rubric ON evaluation_sessions(rubric_version_id);
CREATE INDEX IF NOT EXISTS idx_rubric_versions_rubric ON rubric_versions(rubric_id);
CREATE INDEX IF NOT EXISTS idx_rubric_categories_version ON rubric_categories(rubric_version_id);
CREATE INDEX IF NOT EXISTS idx_rubric_criteria_category ON rubric_criteria(category_id);
CREATE INDEX IF NOT EXISTS idx_repositories_session ON repositories(session_id);
CREATE INDEX IF NOT EXISTS idx_repositories_status ON repositories(session_id, evaluation_status);
CREATE INDEX IF NOT EXISTS idx_evaluations_repository ON evaluations(repository_id);
CREATE INDEX IF NOT EXISTS idx_questions_evaluation ON evaluation_questions(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_criteria_question ON evaluation_criteria(question_id);
CREATE INDEX IF NOT EXISTS idx_plagiarism_session ON plagiarism_results(session_id);
CREATE INDEX IF NOT EXISTS idx_technologies_repository ON technologies(repository_id);
CREATE INDEX IF NOT EXISTS idx_contributors_repository ON contributors(repository_id);
CREATE INDEX IF NOT EXISTS idx_commits_repository ON commits(repository_id);
CREATE INDEX IF NOT EXISTS idx_pull_requests_repository ON pull_requests(repository_id);
CREATE INDEX IF NOT EXISTS idx_issues_repository ON issues(repository_id);
CREATE INDEX IF NOT EXISTS idx_files_repository ON files(repository_id);
CREATE INDEX IF NOT EXISTS idx_code_quality_repository ON code_quality(repository_id);
CREATE INDEX IF NOT EXISTS idx_documentation_repository ON documentation(repository_id);
CREATE INDEX IF NOT EXISTS idx_collaboration_repository ON collaboration(repository_id);
CREATE INDEX IF NOT EXISTS idx_project_health_repository ON project_health(repository_id);
CREATE INDEX IF NOT EXISTS idx_metadata_evaluation ON evaluation_metadata(evaluation_id);
