# Session-based architecture

`evaluation_sessions` is the root aggregate. PostgreSQL foreign keys enforce
that every repository belongs to one session and cascading deletes remove its
evaluations, criteria, metadata, and related records.

## Layers

- `controllers/`: Flask blueprints and HTTP request/response handling.
- `services/`: session and repository workflows, GitHub access, analysis,
  evaluator orchestration, and on-demand reports.
- `repositories/`: PostgreSQL queries and transactional evaluation writes.
- `models/`: domain model types used by service and test boundaries.
- `database/`: PostgreSQL connection and normalized schema.

## Evaluation flow

1. `SessionController` creates a session through `SessionService`.
2. `RepositoryController` adds a child through `RepositoryService`.
3. `EvaluationController` queues work through `EvaluationService`.
4. The worker entry point (`main.py`) uses `GitHubService` and
   `AnalysisService`; the existing rubric/scoring algorithm is unchanged.
5. `EvaluationRepository` saves normalized results transactionally.
6. API reads hydrate saved PostgreSQL records immediately.
7. `ReportController` asks `ReportService` to generate PDFs from stored rows.

Evaluation state is persisted as Pending, Evaluating, Completed, or Failed.
Interrupted Evaluating rows return to Pending on application startup. The
service accepts an injected runner, allowing a future queue/background worker
to replace the current subprocess without changing controllers or persistence.
