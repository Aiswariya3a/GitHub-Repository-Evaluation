CREATE TABLE IF NOT EXISTS ingestion_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    snapshot JSONB NOT NULL,
    total_loc INTEGER NOT NULL DEFAULT 0,
    file_count INTEGER NOT NULL DEFAULT 0,
    language_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'success', 'failed', 'partial')),
    ingestion_version TEXT NOT NULL DEFAULT '1.0',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_snapshot_gin
    ON ingestion_records USING GIN (snapshot jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_ingestion_records_repo
    ON ingestion_records(repository_id);

CREATE INDEX IF NOT EXISTS idx_ingestion_records_created
    ON ingestion_records(created_at);

CREATE INDEX IF NOT EXISTS idx_ingestion_records_status
    ON ingestion_records(status);

CREATE INDEX IF NOT EXISTS idx_ingestion_records_languages
    ON ingestion_records USING GIN (language_breakdown);
