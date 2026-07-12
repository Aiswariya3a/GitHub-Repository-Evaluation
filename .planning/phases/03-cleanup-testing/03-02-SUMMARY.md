---
phase: 03-cleanup-testing
plan: 02
subsystem: "models, repositories, database"
tags: ["cleanup", "dead-code", "migration", "archival"]
requires: []
provides: ["CLN-02: Archive old evaluation tables", "CLN-04: Remove legacy Evaluation class and repository methods"]
affects: ["models/domain.py", "models/__init__.py", "repositories/evaluation_repository.py", "database/migration_003_archive_old_tables.sql"]
tech-stack:
  added: []
  patterns: ["SQL session_replication_role trick for FK-safe rename"]
key-files:
  created:
    - "database/migration_003_archive_old_tables.sql"
  modified:
    - "models/domain.py"
    - "models/__init__.py"
    - "repositories/evaluation_repository.py"
decisions: []
metrics:
  duration: "~5 min"
  completed_date: "2026-07-12"
---

# Phase 3 Plan 2: Remove Legacy Evaluation Models & Archive Old Tables

**One-liner:** Removed the dead `Evaluation` dataclass from domain models, cleaned up old `save()`/`hydrate()` methods from `evaluation_repository.py`, and created migration SQL to rename old single-prompt evaluation tables to `_archive` suffix with data preservation.

## Deviations from Plan

**None** — plan executed exactly as written.

## Task Results

| Task | Name | Status | Commit |
|------|------|--------|--------|
| 1 | Remove Evaluation class from domain models | ✅ Complete | `8aee466` |
| 2 | Remove old save() and hydrate() from evaluation_repository.py | ✅ Complete | `b3e10d4` |
| 3 | Create migration 003 — archive old evaluation tables | ✅ Complete | `dfa9a74` |

## Task Details

### Task 1: Remove Evaluation class from domain models

**Changes:**
- `models/domain.py`: Removed `Evaluation` dataclass (6 fields with Decimal scores) and its `from decimal import Decimal` import (only used by Evaluation)
- `models/__init__.py`: Removed `Evaluation` from import statement and `__all__` list
- `EvaluationSession` and `Repository` dataclasses untouched
- `models/evaluation_models.py` untouched (new pipeline dataclasses)

**Verification:**
```
[OK] EvaluationSession and Repository importable
[OK] Evaluation correctly removed from models
```

### Task 2: Remove old save() and hydrate() from evaluation_repository.py

**Removed:**
- `flatten_metadata()` helper function (only used by old `save()`)
- `hydrate(self, row)` method (joins and queries old tables: `evaluations`, `evaluation_questions`, `evaluation_criteria`, `evaluation_metadata`)
- `save(self, repository_id, evaluation, rubric_version_id)` method (inserts into old `evaluations` table)
- `import json` (only used by `hydrate()`'s `json.loads()` call)

**Kept:**
- `save_evaluation_result()` — new pipeline persistence (lines 21-83)
- `get_evaluation_result()` — new pipeline retrieval (lines 85-90)
- `save_plagiarism()` — plagiarism detection (lines 10-15)
- `plagiarism()` — plagiarism retrieval (lines 17-19)

**Verification:**
```
[OK] save_evaluation_result(), get_evaluation_result() present
[OK] save_plagiarism(), plagiarism() present
[OK] hydrate(), save() removed
```

### Task 3: Create migration 003 — archive old evaluation tables

**Created:** `database/migration_003_archive_old_tables.sql` with:

- **4 table renames:** `evaluations`, `evaluation_questions`, `evaluation_criteria`, `evaluation_metadata` → `_archive_` prefix
- **4 index renames:** matching `idx_archive_*` naming
- **FK safety:** Uses `SET session_replication_role = 'replica'` to bypass FK constraints during rename, restores with `'origin'`
- **Safety:** Uses `ALTER TABLE IF EXISTS` / `ALTER INDEX IF EXISTS` — idempotent
- **Data preservation:** No DROP statements — data fully recoverable with reverse rename

## Verification Checklist

- [x] `Evaluation` class removed from `models/domain.py`
- [x] `Evaluation` removed from `models/__init__.py` imports and `__all__`
- [x] `flatten_metadata()` removed from `repositories/evaluation_repository.py`
- [x] `hydrate()` removed from `EvaluationRepository`
- [x] `save()` removed from `EvaluationRepository`
- [x] `save_evaluation_result()` is still present and functional
- [x] `get_evaluation_result()` is still present and functional
- [x] `save_plagiarism()` and `plagiarism()` are still present
- [x] `migration_003_archive_old_tables.sql` exists with 4 RENAME statements
- [x] No module fails to import due to missing Evaluation class

## Success Criteria

1. ✅ `from models import EvaluationSession, Repository` works; `from models import Evaluation` raises ImportError
2. ✅ `EvaluationRepository` has no `hydrate()` or `save()` methods
3. ✅ `EvaluationRepository` retains `save_evaluation_result()`, `get_evaluation_result()`, `save_plagiarism()`, `plagiarism()`
4. ✅ Migration SQL is valid PostgreSQL DDL that renames tables to `_archive_` prefix
5. ✅ Both cleanup tasks are independent of Plan 03-01 — can run in parallel Wave 1

## Commits

| Commit | Message |
|--------|---------|
| `8aee466` | refactor(03-cleanup-testing): remove Evaluation class from domain models |
| `b3e10d4` | refactor(03-cleanup-testing): remove old save() and hydrate() from evaluation_repository |
| `dfa9a74` | feat(03-cleanup-testing): create migration 003 to archive old evaluation tables |

## Threat Flags

None — all changes are within scope and the threat register's mitigations (session-scoped FK disable) are correctly applied.

## Known Stubs

None.

## Self-Check

- [x] `models/domain.py` exists — verified
- [x] `models/__init__.py` exists — verified
- [x] `repositories/evaluation_repository.py` exists — verified
- [x] `database/migration_003_archive_old_tables.sql` exists — verified
- [x] Commit `8aee466` exists in git log — verified
- [x] Commit `b3e10d4` exists in git log — verified
- [x] Commit `dfa9a74` exists in git log — verified
