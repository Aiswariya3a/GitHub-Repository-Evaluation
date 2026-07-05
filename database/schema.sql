CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS evaluation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Completed','Archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(session_id, repo_url)
);

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

CREATE INDEX IF NOT EXISTS idx_sessions_status ON evaluation_sessions(status);
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
