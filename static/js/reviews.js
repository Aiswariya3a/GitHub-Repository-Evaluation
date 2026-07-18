if (typeof window.esc !== 'function') {
    window.esc = function(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); };
}

document.addEventListener('DOMContentLoaded', function() {
    var reviewsStats = document.getElementById('reviewsStats');
    if (!reviewsStats) return;

    var sessionFilter = document.getElementById('sessionFilter');
    var filterChips = document.getElementById('reviewFilterChips');
    var reviewsBody = document.getElementById('reviewsBody');
    var statPending = document.getElementById('statPending');
    var statInReview = document.getElementById('statInReview');
    var statReviewed = document.getElementById('statReviewed');
    var statTotal = document.getElementById('statTotal');

    var currentStatus = '';
    var sessionsMap = {};

    // --- Load sessions for filter dropdown ---
    fetch('/api/sessions')
        .then(function(r) { return r.json(); })
        .then(function(sessions) {
            sessions.forEach(function(s) { sessionsMap[s.id] = s.name; });
            if (sessionFilter) {
                sessionFilter.innerHTML = '<option value="">All sessions</option>' +
                    sessions.map(function(s) {
                        return '<option value="' + window.esc(s.id) + '">' + window.esc(s.name) + '</option>';
                    }).join('');
            }
        })
        .catch(function(err) {
            console.error('Failed to load sessions:', err);
        });

    // --- Status filter chips ---
    if (filterChips) {
        filterChips.addEventListener('click', function(e) {
            var btn = e.target;
            if (!btn.dataset || btn.dataset.status === undefined) return;
            currentStatus = btn.dataset.status;
            Array.from(filterChips.children).forEach(function(chip) {
                chip.classList.toggle('active', chip === btn);
            });
            loadReviews();
        });
    }

    // --- Session filter change ---
    if (sessionFilter) {
        sessionFilter.addEventListener('change', function() {
            loadReviews();
        });
    }

    // --- Load reviews ---
    async function loadReviews() {
        try {
            var sessionId = sessionFilter ? sessionFilter.value : '';
            var allEntries = [];
            var sessionsUsed = [];

            if (sessionId) {
                // Single session
                var resp = await fetch('/api/reviews/' + sessionId + '?status=' + currentStatus);
                var data = await resp.json();
                if (!resp.ok) throw new Error(data.error || 'Failed to load reviews');
                allEntries = (data.queue || []).map(function(entry) {
                    entry._session_name = sessionsMap[sessionId] || sessionId;
                    entry._session_id = sessionId;
                    return entry;
                });
                sessionsUsed.push(sessionId);
            } else {
                // All sessions — fetch sessions list first, then each session's reviews
                var sessionsResp = await fetch('/api/sessions');
                var sessions = await sessionsResp.json();
                if (!sessionsResp.ok) throw new Error('Failed to load sessions');
                var results = await Promise.all(sessions.map(async function(s) {
                    try {
                        var r = await fetch('/api/reviews/' + s.id + '?status=' + currentStatus);
                        var d = await r.json();
                        if (!r.ok) return [];
                        return (d.queue || []).map(function(entry) {
                            entry._session_name = s.name;
                            entry._session_id = s.id;
                            return entry;
                        });
                    } catch (_) { return []; }
                }));
                for (var i = 0; i < results.length; i++) {
                    allEntries = allEntries.concat(results[i]);
                    if (results[i].length) sessionsUsed.push(sessions[i].id);
                }
            }

            renderReviews(allEntries);
        } catch (err) {
            var errEl = document.getElementById('reviewsError');
            if (errEl) { errEl.hidden = false; errEl.textContent = err.message; }
        }
    }

    // --- Render reviews table ---
    function renderReviews(entries) {
        var pending = 0, inReview = 0, reviewed = 0;

        if (reviewsBody) {
            if (!entries.length) {
                reviewsBody.innerHTML = '<tr><td colspan="7" class="empty-table">No flagged repositories found' +
                    (currentStatus ? ' with status "' + currentStatus + '"' : '') + '.</td></tr>';
            } else {
                reviewsBody.innerHTML = entries.map(function(entry) {
                    var status = (entry.status || 'pending').toLowerCase();
                    if (status === 'pending') pending++;
                    else if (status === 'in_review') inReview++;
                    else if (status === 'reviewed') reviewed++;

                    var statusBadge = '';
                    if (status === 'pending') statusBadge = '<span class="status-badge status-pending">Pending</span>';
                    else if (status === 'in_review') statusBadge = '<span class="status-badge status-in-review">In Review</span>';
                    else if (status === 'reviewed') statusBadge = '<span class="status-badge status-reviewed">Reviewed</span>';

                    var score = entry.score != null ? Number(entry.score).toFixed(1) : '\u2014';
                    var flagReason = entry.flag_reason || entry.flag_reason === '' ? window.esc(entry.flag_reason) : 'Flagged for review';
                    var repoName = entry.repo_url ? entry.repo_url.split('/').pop() : (entry.repository_name || '\u2014');
                    var repoUrl = entry.repo_url || '#';
                    var rollNum = window.esc(entry.roll_number || '\u2014');
                    var sessionName = window.esc(entry._session_name || '\u2014');
                    var sid = entry._session_id || '';
                    var rid = entry.repository_id || entry.id || '';
                    var isReviewed = status === 'reviewed';

                    var actionBtn = '';
                    if (status === 'pending') {
                        actionBtn = '<button class="table-btn" onclick="startReview(\'' + window.esc(sid) + '\',\'' + window.esc(rid) + '\')">Start Review</button>';
                    }
                    var viewLink = '<a class="table-btn" href="/sessions/' + window.esc(sid) + '/repositories/' + window.esc(rid) + '">View</a>';

                    return '<tr' + (isReviewed ? ' class="reviewed-row"' : '') + '>' +
                        '<td>' + sessionName + '</td>' +
                        '<td><a href="' + window.esc(repoUrl) + '" target="_blank">' + window.esc(repoName) + '</a></td>' +
                        '<td>' + rollNum + '</td>' +
                        '<td>' + score + '</td>' +
                        '<td>' + flagReason + '</td>' +
                        '<td>' + statusBadge + '</td>' +
                        '<td class="action-cell">' + actionBtn + ' ' + viewLink + '</td>' +
                        '</tr>';
                }).join('');
            }
        }

        // Update stats
        var totalFlagged = entries.length;
        if (statPending) statPending.textContent = pending;
        if (statInReview) statInReview.textContent = inReview;
        if (statReviewed) statReviewed.textContent = reviewed;
        if (statTotal) statTotal.textContent = totalFlagged;
    }

    // --- Start review (global function) ---
    window.startReview = async function(sessionId, repositoryId) {
        try {
            var resp = await fetch('/api/reviews/' + sessionId + '/' + repositoryId + '/start', { method: 'POST' });
            var data = await resp.json();
            if (!resp.ok) {
                window.toast(data.error || 'Failed to start review', 'error');
                return;
            }
            window.toast('Review started', 'success');
            loadReviews();
        } catch (err) {
            window.toast('Failed to start review: ' + err.message, 'error');
        }
    };

    // --- Initial load ---
    loadReviews();
});
