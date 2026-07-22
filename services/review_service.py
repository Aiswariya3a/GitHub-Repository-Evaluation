from repositories import ReviewQueueRepository, ScoreOverrideRepository, AuditLogRepository, EvaluationRepository


class ReviewService:
    def __init__(self, review_queue=None, score_overrides=None, audit_log=None, evaluations=None):
        self.review_queue = review_queue or ReviewQueueRepository()
        self.score_overrides = score_overrides or ScoreOverrideRepository()
        self.audit_log = audit_log or AuditLogRepository()
        self.evaluations = evaluations or EvaluationRepository()

    # ── Queue Management ──────────────────────────────────────────────

    def auto_queue_repository(self, repository_id, session_id, flag_reason='low_confidence'):
        """Auto-add to review queue if evaluation has low confidence and not already queued."""
        if not self.evaluation_has_low_confidence(repository_id):
            return None
        existing = self.review_queue.get(repository_id, session_id)
        if existing is not None:
            return None
        entry = self.review_queue.add(repository_id, session_id, flag_reason)
        self.audit_log.append(
            repository_id, session_id, 'auto_queued',
            old_value='', new_value=flag_reason,
            reasoning='Auto-queued due to low-confidence criteria',
            performed_by='system',
        )
        return entry

    def start_review(self, repository_id, session_id, reviewer='instructor'):
        ok = self.review_queue.set_status(repository_id, session_id, 'in_review')
        if ok:
            self.audit_log.append(
                repository_id, session_id, 'review_started',
                old_value='pending', new_value='in_review',
                reasoning='', performed_by=reviewer,
            )
        return ok

    def complete_review(self, repository_id, session_id, reviewer='instructor'):
        ok = self.review_queue.set_status(repository_id, session_id, 'reviewed')
        if ok:
            self.audit_log.append(
                repository_id, session_id, 'review_completed',
                old_value='in_review', new_value='reviewed',
                reasoning='', performed_by=reviewer,
            )
        return ok

    def list_queue(self, session_id, status=None):
        return self.review_queue.list_by_session(session_id, status)

    def pending_count(self, session_id):
        return self.review_queue.pending_count(session_id)

    def get_queue_entry(self, repository_id, session_id):
        return self.review_queue.get(repository_id, session_id)

    # ── Score Overrides ───────────────────────────────────────────────

    def override_score(self, repository_id, session_id, criterion_key,
                       overridden_score, reasoning, performed_by='instructor'):
        eval_result = self.evaluations.get_evaluation_result(repository_id, session_id)
        original_score = 0
        if eval_result and eval_result.get("criterion_results"):
            for cr in eval_result["criterion_results"]:
                key = cr.get("key") or cr.get("criterion_key", "")
                if key == criterion_key:
                    original_score = float(cr.get("score", 0))
                    break
        record = self.score_overrides.create(
            repository_id, session_id, criterion_key,
            original_score, overridden_score, reasoning, performed_by,
        )
        self.audit_log.append(
            repository_id, session_id, 'score_override',
            old_value=str(original_score),
            new_value=str(overridden_score),
            reasoning=reasoning,
            performed_by=performed_by,
        )
        self.evaluations.apply_override(
            repository_id, session_id, criterion_key, overridden_score,
        )
        return record

    def get_overrides(self, repository_id, session_id):
        return self.score_overrides.list_by_repository(repository_id, session_id)

    # ── Audit ─────────────────────────────────────────────────────────

    def get_audit_trail(self, repository_id, session_id):
        return self.audit_log.list_by_repository(repository_id, session_id)

    def get_all_audit_logs(self, session_id=None, action=None):
        return self.audit_log.list_all(session_id, action)

    def get_distinct_actions(self):
        return self.audit_log.distinct_actions()

    def has_review_override(self, repository_id, session_id):
        overrides = self.score_overrides.list_by_repository(repository_id, session_id)
        return len(overrides) > 0

    # ── Helpers ───────────────────────────────────────────────────────

    def evaluation_has_low_confidence(self, repository_id):
        """Check if evaluation_results has a non-null, non-empty low_confidence_criteria."""
        from database import connect
        with connect() as db:
            row = db.execute("""
                SELECT low_confidence_criteria FROM evaluation_results
                WHERE repository_id=%s
                ORDER BY evaluation_completed_at DESC LIMIT 1
            """, (repository_id,)).fetchone()
        if row is None:
            return False
        lcc = row.get("low_confidence_criteria")
        if lcc is None:
            return False
        if isinstance(lcc, (list, tuple)):
            return len(lcc) > 0
        if isinstance(lcc, str):
            return bool(lcc.strip())
        return bool(lcc)

    def needs_review(self, repository_id, session_id):
        """Check if repository has a review_queue entry with status != 'reviewed'."""
        entry = self.review_queue.get(repository_id, session_id)
        if entry is None:
            return False
        return entry.get("status") != "reviewed"
