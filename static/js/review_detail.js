if (typeof window.esc !== 'function') {
    window.esc = function(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); };
}
if (typeof window.date !== 'function') {
    window.date = function(v) { return v ? new Intl.DateTimeFormat(undefined, {dateStyle:'medium', timeStyle:'short'}).format(new Date(v)) : '\u2014'; };
}

document.addEventListener('DOMContentLoaded', function() {
    var panel = document.getElementById('reviewPanelContent');
    if (!panel) return;

    var page = document.querySelector('[data-session-id], [data-repository-id]');
    var sessionId = page ? page.dataset.sessionId : null;
    var repoId = page ? page.dataset.repositoryId : null;

    var match = window.location.pathname.match(/\/sessions\/([^/]+)\/repositories\/([^/]+)/);
    if (match) { sessionId = sessionId || match[1]; repoId = repoId || match[2]; }

    if (!sessionId || !repoId) { panel.innerHTML = '<p class="empty-state">Repository context not found.</p>'; return; }

    var reviewData = null;
    var currentIndex = 0;
    var overrideValues = {};
    var overrideReasons = {};
    var reviewStarted = false;

    function stars(n, outOf) {
        var full = Math.round(n);
        var s = '';
        for (var i = 0; i < outOf; i++) s += i < full ? '\u2605' : '\u2606';
        return s;
    }

    function confidenceLabel(val) {
        if (val == null) return '';
        var pct = Math.round(val * 100);
        if (val >= 0.7) return '<span class="c-conf high">\u2713 High Confidence \u00B7 ' + pct + '%</span>';
        if (val >= 0.5) return '<span class="c-conf medium">\u26A0 Medium Confidence \u00B7 ' + pct + '%</span>';
        return '<span class="c-conf low">\u26A0 Needs Review \u00B7 ' + pct + '%</span>';
    }

    function catName(catCode) {
        if (!reviewData || !reviewData.rubric) return catCode;
        var c = reviewData.rubric.categories.find(function(c) { return c.code === catCode; });
        return c ? c.name : catCode;
    }

    function critName(catCode, critKey) {
        if (!reviewData || !reviewData.rubric) return critKey;
        var c = reviewData.rubric.categories.find(function(c) { return c.code === catCode; });
        if (!c || !c.criteria) return critKey;
        var k = c.criteria.find(function(k) { return k.criterion_key === critKey; });
        return k ? k.name : critKey;
    }

    function buildCriterionList() {
        if (!reviewData || !reviewData.evaluation) return [];
        var results = reviewData.evaluation.criterion_results || [];
        if (reviewData.rubric && reviewData.rubric.categories) {
            var list = [];
            reviewData.rubric.categories.forEach(function(cat) {
                (cat.criteria || []).forEach(function(k) {
                    var r = results.find(function(r) { return r.criterion_key === k.criterion_key && r.category_code === cat.code; });
                    list.push({
                        category_code: cat.code,
                        category_name: cat.name,
                        criterion_key: k.criterion_key,
                        criterion_name: k.name,
                        max_score: k.max_score,
                        score: r ? r.score : null,
                        confidence: r ? r.confidence : null,
                        evidence: r ? (r.evidence || []) : [],
                        remarks: r ? (r.remarks || '') : '',
                        confidence_warning: r ? r.confidence_warning : false,
                        overridden: r ? r.overridden : false,
                    });
                });
            });
            return list;
        }
        return results.map(function(r) {
            return {
                category_code: r.category_code,
                category_name: catName(r.category_code),
                criterion_key: r.criterion_key,
                criterion_name: critName(r.category_code, r.criterion_key),
                max_score: r.max_score,
                score: r.score,
                confidence: r.confidence,
                evidence: r.evidence || [],
                remarks: r.remarks || '',
                confidence_warning: r.confidence_warning,
                overridden: r.overridden,
            };
        });
    }

    function getCriterionKey(catCode, critKey) {
        return catCode + '.' + critKey;
    }

    function effectiveScore(catCode, critKey) {
        var fullKey = getCriterionKey(catCode, critKey);
        if (overrideValues[fullKey] !== undefined) return overrideValues[fullKey];
        var item = buildCriterionList().find(function(c) { return c.criterion_key === critKey && c.category_code === catCode; });
        return item ? item.score : 0;
    }

    function totalScore() {
        var list = buildCriterionList();
        var total = 0;
        list.forEach(function(item) {
            total += Number(effectiveScore(item.category_code, item.criterion_key));
        });
        return total;
    }

    function countApproved() {
        var list = buildCriterionList();
        var count = 0;
        list.forEach(function(item) {
            var fk = getCriterionKey(item.category_code, item.criterion_key);
            if (overrideValues[fk] !== undefined || item.overridden) count++;
        });
        return count;
    }

    function autoStartReview() {
        if (reviewStarted) return;
        reviewStarted = true;
        fetch('/api/reviews/' + sessionId + '/' + repoId + '/start', { method: 'POST' }).catch(function() {});
    }

    async function loadReviewData(resetIndex) {
        try {
            var r = await fetch('/api/reviews/' + sessionId + '/' + repoId);
            if (!r.ok) { panel.innerHTML = '<p class="empty-state">No review data available.</p>'; return; }
            reviewData = await r.json();
            if (resetIndex !== false) currentIndex = 0;
            overrideValues = {};
            renderReviewPanel();
        } catch (err) {
            panel.innerHTML = '<p class="empty-state">Failed to load review data.</p>';
        }
    }

    function thenReload() {
        loadReviewData();
    }

    function renderReviewPanel() {
        var evaluation = reviewData.evaluation || {};
        var audit = reviewData.audit || [];
        var criteria = buildCriterionList();

        if (!evaluation.total_score && criteria.length === 0) {
            panel.innerHTML = '<p class="empty-state">This repository has no review data yet. Evaluations with low-confidence criteria are automatically queued.</p>';
            return;
        }

        var maxTotal = evaluation.max_score || 80;

        // ── Progress bar ──
        var approved = countApproved();
        var total = criteria.length;
        var pct = total ? Math.round(approved / total * 100) : 0;
        var allDone = approved === total && total > 0;
        var html = '<div class="review-progress-bar"><div class="rpb-label">' +
            '<strong>' + approved + '</strong> of <strong>' + total + '</strong> criteria reviewed' +
            (allDone ? ' <span class="rpb-all-done">\u2713 All criteria reviewed</span>' : ' <span class="rpb-remaining">' + (total - approved) + ' remaining</span>') +
            '</div><div class="rpb-track"><span class="rpb-fill" style="width:' + pct + '%"></span></div></div>';

        // ── Criterion accordion ──
        if (criteria.length === 0) {
            html += '<p class="empty-state">No criteria found for this evaluation.</p>';
        } else {
            html += '<div class="review-accordion" id="reviewAccordion">';
            criteria.forEach(function(item, idx) {
                var fk = getCriterionKey(item.category_code, item.criterion_key);
                var aiScore = item.score;
                var maxSc = item.max_score;
                var isLast = idx === criteria.length - 1;
                var isApproved = item.overridden || overrideValues[fk] !== undefined;
                var instScore = effectiveScore(item.category_code, item.criterion_key);
                var isChanged = instScore !== aiScore;
                var isOpen = idx === currentIndex;
                var lowConf = item.confidence != null && item.confidence < 0.7;
                var starOutOf = Math.round(maxSc);

                html += '<div class="rc-card ' + (isOpen ? 'rc-open' : '') + '">' +
                    '<button class="rc-header" onclick="window.selectCriterion(' + idx + ')">' +
                    '<span class="rc-index ' + (isApproved ? 'rc-index-done' : '') + '">' + (isApproved ? '\u2713' : (idx + 1)) + '</span>' +
                    '<span class="rc-meta"><strong>' + window.esc(item.criterion_name) + '</strong>' +
                    '<span class="rc-cat">' + window.esc(item.category_name) + '</span></span>' +
                    '<span class="rc-stars">' + stars(instScore, starOutOf) + ' <span class="rc-score-num">' + Number(instScore).toFixed(1) + '/' + maxSc + '</span></span>' +
                    (lowConf && !isApproved ? '<span class="rc-warn">!</span>' : '') +
                    '<span class="rc-arrow">' + (isOpen ? '\u25B2' : '\u25BC') + '</span>' +
                    '</button>';

                if (isOpen) {
                    var evidenceHtml = (item.evidence && item.evidence.length)
                        ? item.evidence.map(function(e) { return '<li>' + window.esc(e) + '</li>'; }).join('')
                        : '<li class="rc-ev-none">No evidence recorded</li>';

                    var changedClass = isChanged ? ' rc-changed' : '';

                    html += '<div class="rc-body">' +
                        '<div class="rc-ai-box">' +
                        '<div class="rc-ai-left">' +
                        '<span class="rc-ai-label">AI Score</span>' +
                        '<span class="rc-ai-value">' + (aiScore != null ? aiScore.toFixed(1) : '--') + ' <small>/ ' + maxSc + '</small></span>' +
                        '<span class="rc-ai-stars">' + stars(aiScore || 0, starOutOf) + '</span>' +
                        '</div>' +
                        '<div class="rc-ai-right">' +
                        (item.confidence != null ? '<div class="rc-conf">' + confidenceLabel(item.confidence) + '</div>' : '') +
                        (item.remarks ? '<div class="rc-reasoning"><strong>Why?</strong><p>' + window.esc(item.remarks) + '</p></div>' : '') +
                        '</div>' +
                        '</div>' +
                        '<div class="rc-evidence"><strong>Evidence</strong><ul>' + evidenceHtml + '</ul></div>' +
                        '<div class="rc-instructor-box">' +
                        '<div class="rc-instructor-row">' +
                        '<span class="rc-ai-badge">AI</span>' +
                        '<span class="rc-ai-val-display">' + (aiScore != null ? aiScore.toFixed(1) : '--') + '</span>' +
                        (isChanged ? '<span class="rc-arrow-dn">\u2193</span>' : '') +
                        '<span class="rc-you-badge">You</span>' +
                        '<input type="number" class="rc-instructor-input' + changedClass + '" step="0.01" min="0" max="' + maxSc + '" ' +
                        'value="' + (overrideValues[fk] !== undefined ? overrideValues[fk] : (aiScore != null ? aiScore : '')) + '" ' +
                        'data-fk="' + fk + '" data-ai="' + (aiScore != null ? aiScore : '') + '" data-max="' + maxSc + '" ' +
                        'onchange="window.onInstructorScoreChange(this)" ' +
                        'onfocus="this.select()">' +
                        '<span class="rc-max-label">/ ' + maxSc + '</span>' +
                        '</div>' +
                        (isChanged || overrideValues[fk] !== undefined
                            ? '<div class="rc-reason-box"><label>Reason for change</label><textarea rows="2" placeholder="Explain why you changed the score..." data-fk="' + fk + '" oninput="window.onReasonChange(this)">' +
                            window.esc(overrideReasons[fk] || '') +
                            '</textarea></div>'
                            : '') +
                        '<button class="primary-btn rc-approve-btn" onclick="window.approveCriterion(' + idx + ')">' +
                        (isLast ? 'Save &amp; Finish' : 'Approve &amp; Next \u2192') +
                        '</button>' +
                        '</div>' +
                        '</div>';
                }
                html += '</div>';
            });
            html += '</div>';

            // ── Overall Score ──
            var tScore = totalScore();
            html += '<div class="rc-overall"><div class="rc-overall-left">' +
                '<span class="rc-overall-label">Overall Score</span>' +
                '<span class="rc-overall-value">' + tScore.toFixed(1) + ' <small>/ ' + maxTotal + '</small></span>' +
                '<span class="rc-overall-norm">' + (maxTotal ? (tScore / maxTotal * 20).toFixed(2) : '--') + ' / 20</span>' +
                '</div>' +
                '<div class="rc-overall-right"><span class="rc-auto-badge">Auto-calculated from individual criteria</span></div></div>';
        }

        // ── History ──
        if (audit.length > 0) {
            html += '<div class="rc-history"><button class="rc-history-toggle" onclick="this.parentElement.classList.toggle(\'rc-history-open\')">' +
                'History <span class="rc-history-count">' + audit.length + '</span> <span class="rc-history-arrow">\u25BC</span></button>' +
                '<div class="rc-history-body">';
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

        panel.innerHTML = html;
    }

    window.selectCriterion = function(idx) {
        currentIndex = idx;
        renderReviewPanel();
        var accordion = document.getElementById('reviewAccordion');
        if (accordion) {
            var cards = accordion.querySelectorAll('.rc-card');
            if (cards[idx]) cards[idx].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        autoStartReview();
    };

    window.onInstructorScoreChange = function(input) {
        var fk = input.dataset.fk;
        var aiScore = parseFloat(input.dataset.ai);
        var newVal = input.value.trim() !== '' ? parseFloat(input.value) : aiScore;
        if (isNaN(newVal) || newVal < 0) newVal = aiScore;
        overrideValues[fk] = newVal;
        renderReviewPanel();
        autoStartReview();
    };

    window.onReasonChange = function(textarea) {
        var fk = textarea.dataset.fk;
        overrideReasons[fk] = textarea.value;
    };

    function tryAutoComplete() {
        var criteria = buildCriterionList();
        var allDone = criteria.every(function(item) {
            var fk = getCriterionKey(item.category_code, item.criterion_key);
            return item.overridden || overrideValues[fk] !== undefined;
        });
        if (allDone && criteria.length > 0 && reviewData.queue && reviewData.queue.status === 'in_review') {
            fetch('/api/reviews/' + sessionId + '/' + repoId + '/complete', { method: 'POST' }).catch(function() {});
        }
    }

    window.approveCriterion = function(idx) {
        var criteria = buildCriterionList();
        var item = criteria[idx];
        var fk = getCriterionKey(item.category_code, item.criterion_key);
        var aiScore = item.score;
        var instScore = overrideValues[fk] !== undefined ? overrideValues[fk] : aiScore;
        var reason = overrideReasons[fk] || '';

        if (instScore !== aiScore && !reason.trim()) {
            window.toast('Please provide a reason for changing the score.', 'error');
            return;
        }

        autoStartReview();

        fetch('/api/reviews/' + sessionId + '/' + repoId + '/override', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                criterion_key: fk,
                overridden_score: instScore,
                reasoning: reason,
                performed_by: 'instructor'
            })
        }).then(function(r) {
            if (!r.ok) throw new Error('Override failed');
            return r.json();
        }).then(function() {
            var hasNext = idx < criteria.length - 1;
            window.toast('\u2713 ' + item.criterion_name + (instScore !== aiScore ? ' saved' : ' approved'));
            if (hasNext) {
                currentIndex = idx + 1;
            }
            loadReviewData(false);
            if (hasNext) {
                setTimeout(function() {
                    var open = document.querySelector('#reviewAccordion .rc-card.rc-open');
                    if (open) open.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 100);
            }
            setTimeout(tryAutoComplete, 500);
        }).catch(function(e) { window.toast(e.message, 'error'); });
    };

    loadReviewData();
});