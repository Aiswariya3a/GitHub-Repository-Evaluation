/**
 * review_detail.js — Review panel for repository detail page
 *
 * Loads review data from the API and renders the review panel UI
 * including status, action buttons, score override controls,
 * submitted overrides list, and audit trail timeline.
 */

if (typeof window.esc !== 'function') {
    window.esc = function(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); };
}
if (typeof window.date !== 'function') {
    window.date = function(v) { return v ? new Intl.DateTimeFormat(undefined, {dateStyle:'medium', timeStyle:'short'}).format(new Date(v)) : '\u2014'; };
}

document.addEventListener('DOMContentLoaded', function() {
    var panel = document.getElementById('reviewPanelContent');
    if (!panel) return;

    // Extract session and repository IDs from page context
    // Try to get from data attributes or URL
    var page = document.querySelector('[data-session-id], [data-repository-id]');
    var sessionId = page ? page.dataset.sessionId : null;
    var repoId = page ? page.dataset.repositoryId : null;

    // Fallback: extract from URL
    var match = window.location.pathname.match(/\/sessions\/([^/]+)\/repositories\/([^/]+)/);
    if (match) { sessionId = sessionId || match[1]; repoId = repoId || match[2]; }

    if (!sessionId || !repoId) { panel.innerHTML = '<p class="empty-state">Repository context not found.</p>'; return; }

    async function loadReviewData() {
        try {
            var r = await fetch('/api/reviews/' + sessionId + '/' + repoId);
            if (!r.ok) { panel.innerHTML = '<p class="empty-state">No review data available.</p>'; return; }
            var data = await r.json();
            renderReviewPanel(data);
        } catch (err) {
            panel.innerHTML = '<p class="empty-state">Failed to load review data.</p>';
        }
    }

    function renderReviewPanel(data) {
        var queue = data.queue || null;
        var evaluation = data.evaluation || {};
        var overrides = data.overrides || [];
        var audit = data.audit || [];
        var criterionResults = evaluation.criterion_results || {};
        var feedback = evaluation.feedback || {};

        var status = queue ? queue.status : 'not_queued';
        var flagReason = queue ? queue.flag_reason : '';
        var reviewer = queue ? queue.assigned_reviewer : '';

        var statusColor = { pending: 'status-pending', in_review: 'status-evaluating', reviewed: 'status-completed', not_queued: '' };

        // Build status bar
        var html = '<div class="review-hero">' +
            '<div class="review-hero-top">' +
            '<span class="status-badge ' + (statusColor[status] || '') + '">' + window.esc(status.replace('_', ' ')) + '</span>' +
            (flagReason ? '<span class="flag-badge">Flagged: ' + window.esc(flagReason.replace('_', ' ')) + '</span>' : '') +
            '</div>' +
            '<div class="review-hero-actions">' +
            (status === 'pending' ? '<button class="primary-btn" id="startReviewBtn">Start Review</button>' : '') +
            (status === 'in_review' ? '<button class="primary-btn" id="completeReviewBtn">Complete Review</button>' : '') +
            (status === 'reviewed' ? '<span class="reviewed-label">Review completed</span>' : '') +
            '</div></div>';

        // Score override section
        html += '<div class="review-section"><h3>Score Overrides</h3>';
        html += '<div class="override-criteria" id="overrideFields">';

        // Overall score override
        var overallOriginal = evaluation.total_score || 0;
        var latestOverride = overrides.length > 0 ? overrides[0] : null;
        html += '<div class="override-row"><div class="override-info"><span class="override-label">Overall Score</span>' +
            '<span class="override-original">Original: ' + overallOriginal + '</span></div>' +
            '<input type="number" class="override-input" id="overrideOverall" step="0.01" placeholder="' + overallOriginal + '" data-criterion="">' +
            '</div>';

        // Per-criterion overrides
        if (criterionResults && typeof criterionResults === 'object') {
            Object.keys(criterionResults).forEach(function(key) {
                var criterion = criterionResults[key];
                var originalScore = criterion.score || 0;
                var maxScore = criterion.max_score || '';
                var existingOverride = overrides.find(function(o) { return o.criterion_key === key; });
                html += '<div class="override-row"><div class="override-info"><span class="override-label">' + window.esc(key) + '</span>' +
                    '<span class="override-original">Original: ' + originalScore + (maxScore ? '/' + maxScore : '') + '</span></div>' +
                    '<input type="number" class="override-input" step="0.01" placeholder="' + originalScore + '" data-criterion="' + window.esc(key) + '">' +
                    '</div>';
            });
        }

        html += '</div>'; // close override-criteria

        // Reasoning field
        html += '<div class="override-reasoning"><label for="overrideReasoning">Reasoning for override <span class="required">*</span></label>' +
            '<textarea id="overrideReasoning" rows="3" placeholder="Explain why the score is being changed..."></textarea></div>' +
            '<button class="primary-btn" id="submitOverrideBtn" ' + (status === 'reviewed' ? 'disabled' : '') + '>Submit Override</button>' +
            '</div>';

        // Existing overrides list
        if (overrides.length > 0) {
            html += '<div class="review-section"><h3>Submitted Overrides</h3>';
            html += overrides.map(function(o) {
                return '<div class="override-card"><div class="override-card-top"><span class="override-criterion">' +
                    window.esc(o.criterion_key || 'Overall') + '</span>' +
                    '<span class="override-score"><span class="strikethrough">' + (o.original_score || '\u2014') + '</span> \u2192 <strong>' + o.overridden_score + '</strong></span></div>' +
                    '<p class="override-reason">' + window.esc(o.reasoning) + '</p>' +
                    '<small class="override-meta">By ' + window.esc(o.overridden_by) + ' \u00B7 ' + window.date(o.created_at) + '</small></div>';
            }).join('');
            html += '</div>';
        }

        // Audit trail
        if (audit.length > 0) {
            html += '<div class="review-section"><h3>Audit Trail</h3>';
            html += '<div class="audit-timeline">';
            html += audit.map(function(entry) {
                var details = '';
                if (entry.old_value || entry.new_value) {
                    details = '<span class="audit-diff">' + window.esc(entry.old_value) + ' \u2192 ' + window.esc(entry.new_value) + '</span>';
                }
                if (entry.reasoning) {
                    details += '<p class="audit-reason">' + window.esc(entry.reasoning) + '</p>';
                }
                return '<div class="audit-entry"><div class="audit-dot"></div><div class="audit-body">' +
                    '<span class="audit-action">' + window.esc(entry.action.replace(/_/g, ' ')) + '</span>' +
                    details +
                    '<span class="audit-meta">' + window.esc(entry.performed_by) + ' \u00B7 ' + window.date(entry.created_at) + '</span></div></div>';
            }).join('');
            html += '</div></div>';
        }

        if (!queue && !evaluation.total_score) {
            html = '<p class="empty-state">This repository has no review data yet. Evaluations with low-confidence criteria are automatically queued.</p>';
        }

        panel.innerHTML = html;

        // Wire up buttons
        var startBtn = document.getElementById('startReviewBtn');
        if (startBtn) startBtn.addEventListener('click', function() {
            fetch('/api/reviews/' + sessionId + '/' + repoId + '/start', { method: 'POST' })
                .then(function(r) { if (!r.ok) throw new Error('Failed'); window.toast('Review started'); loadReviewData(); })
                .catch(function(e) { window.toast(e.message, 'error'); });
        });

        var completeBtn = document.getElementById('completeReviewBtn');
        if (completeBtn) completeBtn.addEventListener('click', function() {
            fetch('/api/reviews/' + sessionId + '/' + repoId + '/complete', { method: 'POST' })
                .then(function(r) { if (!r.ok) throw new Error('Failed'); window.toast('Review completed'); loadReviewData(); })
                .catch(function(e) { window.toast(e.message, 'error'); });
        });

        var submitBtn = document.getElementById('submitOverrideBtn');
        if (submitBtn) submitBtn.addEventListener('click', function() {
            var inputs = document.querySelectorAll('#overrideFields .override-input');
            var reasoning = document.getElementById('overrideReasoning');
            if (!reasoning || !reasoning.value.trim()) {
                window.toast('Reasoning is required for score overrides', 'error');
                return;
            }
            var overridden = false;
            inputs.forEach(function(input) {
                if (input.value.trim() !== '') {
                    overridden = true;
                    var criterionKey = input.dataset.criterion || '';
                    var overrideVal = parseFloat(input.value);
                    if (isNaN(overrideVal)) return;
                    fetch('/api/reviews/' + sessionId + '/' + repoId + '/override', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            criterion_key: criterionKey,
                            overridden_score: overrideVal,
                            reasoning: reasoning.value.trim(),
                            performed_by: 'instructor'
                        })
                    }).then(function(r) {
                        if (!r.ok) throw new Error('Override failed');
                        return r.json();
                    }).then(function() {
                        window.toast('Override submitted');
                        loadReviewData();
                    }).catch(function(e) { window.toast(e.message, 'error'); });
                }
            });
            if (!overridden) {
                window.toast('Enter at least one override value', 'error');
            }
        });
    }

    loadReviewData();
});
