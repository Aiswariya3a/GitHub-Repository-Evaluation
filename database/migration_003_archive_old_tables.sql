-- Migration 003: Archive old evaluation tables
-- Renames old single-prompt evaluation tables to _archive suffix.
-- The new pipeline uses evaluation_results (created in migration 002).
-- Data is preserved for possible rollback; tables are not dropped.
-- Run only after verifying the new pipeline is fully functional.
--
-- Per D-02: Archive with rename, not delete.

-- Disable FK constraints temporarily for rename
-- (self-referencing FKs on old tables would prevent rename)
SET session_replication_role = 'replica';

ALTER TABLE IF EXISTS evaluations RENAME TO _archive_evaluations;
ALTER TABLE IF EXISTS evaluation_questions RENAME TO _archive_evaluation_questions;
ALTER TABLE IF EXISTS evaluation_criteria RENAME TO _archive_evaluation_criteria;
ALTER TABLE IF EXISTS evaluation_metadata RENAME TO _archive_evaluation_metadata;

-- Rename indexes for consistency
ALTER INDEX IF EXISTS idx_evaluations_repository RENAME TO idx_archive_evaluations_repository;
ALTER INDEX IF EXISTS idx_questions_evaluation RENAME TO idx_archive_questions_evaluation;
ALTER INDEX IF EXISTS idx_criteria_question RENAME TO idx_archive_criteria_question;
ALTER INDEX IF EXISTS idx_metadata_evaluation RENAME TO idx_archive_metadata_evaluation;

-- Re-enable FK constraints
SET session_replication_role = 'origin';
