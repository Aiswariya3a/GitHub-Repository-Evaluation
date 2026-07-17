if (typeof window.dateShort !== 'function') {
    window.dateShort = function(v) { return v ? new Intl.DateTimeFormat(undefined, {dateStyle:'medium'}).format(new Date(v)) : '\u2014'; };
}
if (typeof window.esc !== 'function') {
    window.esc = function(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); };
}

// --- Dashboard page (session listing) ---
document.addEventListener('DOMContentLoaded', function() {
    var sessionDialog = document.getElementById('sessionDialog');
    if (!sessionDialog) return; // Not on dashboard page

    var sessionName = document.getElementById('sessionName');
    var sessionDescription = document.getElementById('sessionDescription');
    var formError = document.getElementById('formError');
    var sessionRubric = document.getElementById('sessionRubric');

    window.openSessionDialog = function() {
        document.getElementById('sessionForm').reset();
        if (formError) formError.textContent = '';
        sessionDialog.showModal();
    };

    function sessionCard(item) {
        var total = Number(item.repository_count || 0);
        var done = Number(item.evaluated_count || 0);
        var pct = total ? Math.round(done / total * 100) : 0;
        return '<a class="session-card new-session-card" href="/sessions/' + item.id + '">' +
            '<div class="card-top"><span class="status-badge session-' + item.status.toLowerCase() + '">' + window.esc(item.status) + '</span>' +
            '<span class="muted">' + window.dateShort(item.created_at) + '</span>' +
            '<button class="delete-btn" onclick="event.preventDefault();event.stopPropagation();deleteSession(\'' + item.id + '\',\'' + window.esc(item.name) + '\')" title="Delete session">\u00D7</button></div>' +
            '<h3>' + window.esc(item.name) + '</h3>' +
            '<p>' + window.esc(item.description || 'No description') + '</p>' +
            '<div class="completion"><div><span>' + done + ' of ' + total + ' repositories</span><strong>' + pct + '%</strong></div>' +
            '<div class="progress-bar"><span style="width:' + pct + '%"></span></div></div>' +
            '<div class="card-footer"><span>Updated ' + window.dateShort(item.updated_at) + '</span>' +
            '<span>' + window.esc(item.rubric_name || 'C-trans-Assignment') + '</span></div></a>';
    }

    window.deleteSession = async function(id, name) {
        if (!await window.confirmAction('Delete session "' + name + '" and all its repositories and evaluations? This cannot be undone.', 'Delete session')) return;
        var r = await fetch('/api/sessions/' + id, { method: 'DELETE' });
        if (!r.ok) { var d = await r.json(); window.toast(d.error || 'Failed to delete', 'error'); return; }
        window.toast('Session deleted');
        loadSessions();
    };

    async function loadSessions() {
        try {
            var response = await fetch('/api/sessions');
            if (!response.ok) throw new Error('Unable to load sessions.');
            var items = await response.json();
            var groups = { Active: [], Completed: [], Archived: [] };
            items.forEach(function(item) { (groups[item.status] || groups.Archived).push(item); });
            for (var status in groups) {
                var list = groups[status];
                var countEl = document.getElementById(status.toLowerCase() + 'Count');
                var sessionsEl = document.getElementById(status.toLowerCase() + 'Sessions');
                if (countEl) countEl.textContent = list.length;
                if (sessionsEl) {
                    sessionsEl.innerHTML = list.length
                        ? list.map(sessionCard).join('')
                        : '<div class="empty-card">No ' + status.toLowerCase() + ' sessions</div>';
                }
            }
            var repos = items.reduce(function(n, x) { return n + Number(x.repository_count || 0); }, 0);
            var statsEl = document.getElementById('dashboardStats');
            if (statsEl) {
                statsEl.innerHTML =
                    '<article class="metric-card metric-indigo"><p class="metric-label">All sessions</p><p class="metric-value">' + items.length + '</p></article>' +
                    '<article class="metric-card metric-emerald"><p class="metric-label">Active</p><p class="metric-value">' + groups.Active.length + '</p></article>' +
                    '<article class="metric-card metric-amber"><p class="metric-label">Completed</p><p class="metric-value">' + groups.Completed.length + '</p></article>' +
                    '<article class="metric-card"><p class="metric-label">Repositories</p><p class="metric-value">' + repos + '</p></article>';
            }
        } catch (error) {
            var box = document.getElementById('dashboardError');
            if (box) { box.hidden = false; box.textContent = error.message; }
        }
    }

    async function loadRubrics() {
        var items = await fetch('/api/rubrics').then(function(r) { return r.json(); });
        if (sessionRubric) {
            sessionRubric.innerHTML = items.map(function(x) {
                return '<option value="' + x.version_id + '" ' + (x.is_default ? 'selected' : '') + '>' +
                    window.esc(x.name) + ' \u00B7 v' + x.version + (x.rubric_type === 'System' ? ' (System)' : '') + '</option>';
            }).join('');
        }
    }

    window.duplicateSelectedRubric = async function() {
        if (!sessionRubric) return;
        var selected = sessionRubric.options[sessionRubric.selectedIndex];
        var r = await fetch('/api/rubrics/versions/' + sessionRubric.value + '/duplicate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: selected.text.split(' \u00B7 ')[0] + ' Copy' })
        });
        var d = await r.json();
        if (!r.ok) { window.toast(d.error, 'error'); return; }
        await loadRubrics();
        sessionRubric.value = d.version_id;
        window.toast('Editable rubric copy created');
    };

    var sessionForm = document.getElementById('sessionForm');
    if (sessionForm) {
        sessionForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            var button = event.submitter;
            button.disabled = true;
            var response = await fetch('/api/sessions', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: sessionName ? sessionName.value : '', description: sessionDescription ? sessionDescription.value : '', rubric_version_id: sessionRubric ? sessionRubric.value : '' })
            });
            var data = await response.json();
            button.disabled = false;
            if (!response.ok) { if (formError) formError.textContent = data.error || 'Unable to create session.'; return; }
            location.href = '/sessions/' + data.id;
        });
    }

    loadSessions();
    loadRubrics();
});

// --- Overview page (dashboard KPIs) ---
document.addEventListener('DOMContentLoaded', function() {
    var healthGauge = document.getElementById('healthGauge');
    if (!healthGauge) return; // Not on overview page

    function kpi(label, value, caption, tone, trend) {
        return '<article class="metric-card modern-kpi ' + tone + '"><div class="kpi-top"><p class="metric-label">' + label + '</p>' +
            '<span class="kpi-icon">' + trend + '</span></div><p class="metric-value">' + value + '</p>' +
            '<div class="kpi-footer"><span>' + caption + '</span><i class="sparkline"><b></b><b></b><b></b><b></b><b></b></i></div></article>';
    }

    async function loadDashboard() {
        try {
            var r = await fetch('/api/dashboard');
            var d = await r.json();
            if (!r.ok) throw new Error(d.error || 'Dashboard unavailable');
            var m = d.metrics;

            var dashboardKpis = document.getElementById('dashboardKpis');
            if (dashboardKpis) {
                dashboardKpis.innerHTML =
                    kpi('Evaluation sessions', m.session_count, 'Across all statuses', 'violet', 'S') +
                    kpi('Repositories evaluated', m.evaluated_count, 'Available in history', 'green', 'R') +
                    kpi('Average health', Number(m.average_health || 0).toFixed(1) + '/20', 'Portfolio score', 'amber', 'H') +
                    kpi('Total analyzed', m.repository_count, m.running_count + ' currently running', 'blue', 'A');
            }

            var dist = d.score_distribution || {};
            var total = Object.values(dist).reduce(function(a, b) { return a + Number(b); }, 0) || 1;
            var health = Number(m.average_health || 0);

            if (healthGauge) {
                healthGauge.innerHTML = '<div class="gauge-ring" style="--score:' + (health / 20 * 360) + 'deg"><div><strong>' + health.toFixed(1) + '</strong><span>out of 20</span></div></div>';
            }
            var healthLegend = document.getElementById('healthLegend');
            if (healthLegend) {
                healthLegend.innerHTML = '<span><i class="good"></i>' + m.evaluated_count + ' evaluated</span><span><i class="pending"></i>' + (m.repository_count - m.evaluated_count) + ' pending</span>';
            }

            var scoreChart = document.getElementById('scoreChart');
            if (scoreChart) {
                var entries = [
                    ['Needs attention', dist.low, 'red'],
                    ['Needs review', dist.review, 'amber'],
                    ['On track', dist.track, 'blue'],
                    ['Strong', dist.strong, 'green']
                ];
                scoreChart.innerHTML = entries.map(function(e) {
                    return '<div><strong>' + (e[1] || 0) + '</strong><i class="chart-bar ' + e[2] + '" style="height:' + Math.max(8, (e[1] || 0) / total * 150) + 'px"></i><span>' + e[0] + '</span></div>';
                }).join('');
            }

            var recentActivity = document.getElementById('recentActivity');
            if (recentActivity) {
                recentActivity.innerHTML = (d.recent_activity || []).map(function(x) {
                    return '<a class="activity-item" href="/sessions/' + x.session_id + '/repositories/' + x.id + '"><span class="activity-avatar">' + window.esc(x.roll_number).slice(-2) + '</span><div><strong>' + window.esc(x.roll_number) + '</strong><span>' + window.esc(x.session_name) + ' \u00B7 ' + window.esc(x.evaluation_status) + '</span></div><time>' + window.when(x.updated_at) + '</time></a>';
                }).join('') || '<div class="polished-empty"><span>\u25CE</span><strong>No recent activity</strong><p>Evaluations will appear here.</p></div>';
            }

            var runningCount = document.getElementById('runningCount');
            if (runningCount) runningCount.textContent = d.running_evaluations.length;

            var runningEvaluations = document.getElementById('runningEvaluations');
            if (runningEvaluations) {
                runningEvaluations.innerHTML = (d.running_evaluations || []).map(function(x) {
                    var detailUrl = '/sessions/' + x.session_id + '/repositories/' + x.id;
                    return '<a class="running-item" href="' + detailUrl + '"><span class="running-indicator"></span><div><strong>' + window.esc(x.roll_number) + '</strong><span>' + window.esc(x.session_name) + '</span></div><span class="muted">' + window.when(x.updated_at) + '</span></a>';
                }).join('') || '<p class="empty-state">No evaluations currently running.</p>';
            }

            var technologyBreakdown = document.getElementById('technologyBreakdown');
            if (technologyBreakdown) {
                technologyBreakdown.innerHTML = (d.technologies || []).map(function(t) {
                    return '<div><span>' + window.esc(t.language || t.name || t) + '</span><div class="distribution-bar"><i style="width:' + (t.count ? Math.min(100, t.count / Math.max.apply(null, (d.technologies || []).map(function(x) { return x.count || 1; })) * 100) : 10) + '%"></i></div><strong>' + (t.count || 0) + '</strong></div>';
                }).join('') || '<p class="empty-state">No technology data.</p>';
            }

            var leaderboard = document.getElementById('leaderboard');
            if (leaderboard) {
                leaderboard.innerHTML = (d.leaderboard || []).slice(0, 5).map(function(x) {
                    return '<a class="leaderboard-item" href="/sessions/' + x.session_id + '/repositories/' + x.id + '"><span class="leaderboard-rank">' + (x.rank || '—') + '</span><div><strong>' + window.esc(x.roll_number) + '</strong><span>' + window.esc(x.session_name) + '</span></div><strong class="leaderboard-score">' + Number(x.normalized_to_20 || 0).toFixed(1) + '</strong></a>';
                }).join('') || '<p class="empty-state">No leaderboard data yet.</p>';
            }
        } catch (e) {
            var err = document.getElementById('dashboardError');
            if (err) { err.hidden = false; err.textContent = e.message; }
        }
    }

    loadDashboard();
});

// --- Analytics page ---
document.addEventListener('DOMContentLoaded', function() {
    var analyticsStats = document.getElementById('analyticsStats');
    if (!analyticsStats) return; // Not on analytics page

    Promise.all([
        fetch('/api/dashboard').then(function(r) { return r.json(); }),
        fetch('/api/sessions').then(function(r) { return r.json(); })
    ]).then(function(results) {
        // Clear error on success
        var errEl = document.getElementById('analyticsError');
        if (errEl) errEl.hidden = true;
        var d = results[0], s = results[1];
        var m = d.metrics;

        // KPI stats
        analyticsStats.innerHTML =
            '<article class="metric-card"><p class="metric-label">Analyzed</p><p class="metric-value">' + m.evaluated_count + '</p></article>' +
            '<article class="metric-card"><p class="metric-label">Average health</p><p class="metric-value">' + Number(m.average_health || 0).toFixed(1) + '/20</p></article>' +
            '<article class="metric-card"><p class="metric-label">Running</p><p class="metric-value">' + m.running_count + '</p></article>';

        // Score distribution
        var dist = d.score_distribution || {};
        var distContainer = document.getElementById('scoreDistribution');
        if (distContainer) {
            var distTotal = Object.values(dist).reduce(function(a, b) { return a + Number(b); }, 0) || 1;
            distContainer.innerHTML = [
                { label: 'Strong (16-20)', key: 'strong', color: '#10b981' },
                { label: 'On track (12-15)', key: 'track', color: '#6366f1' },
                { label: 'Needs review (8-11)', key: 'review', color: '#f59e0b' },
                { label: 'Needs attention (0-7)', key: 'low', color: '#ef4444' }
            ].map(function(item) {
                var count = Number(dist[item.key] || 0);
                var pct = count / distTotal * 100;
                return '<div><span>' + item.label + '</span><div class="distribution-bar"><i style="width:' + pct + '%;background:' + item.color + '"></i></div><strong>' + count + '</strong></div>';
            }).join('');
        }

        // Session comparison
        var compContainer = document.getElementById('sessionComparison');
        if (compContainer && s.length) {
            compContainer.innerHTML = '<table><thead><tr><th>Session</th><th>Status</th><th>Evaluated</th><th>Total</th><th>Completion</th></tr></thead><tbody>' +
                s.map(function(x) {
                    var pct = x.repository_count ? Math.round(x.evaluated_count / x.repository_count * 100) : 0;
                    return '<tr><td><strong>' + window.esc(x.name) + '</strong></td>' +
                        '<td><span class="status-badge session-' + x.status.toLowerCase() + '">' + window.esc(x.status) + '</span></td>' +
                        '<td>' + x.evaluated_count + '</td><td>' + x.repository_count + '</td>' +
                        '<td><div class="progress-bar"><span style="width:' + pct + '%"></span></div><span class="muted">' + pct + '%</span></td></tr>';
                }).join('') + '</tbody></table>';
        }

        // Session completion bars (existing functionality)
        var completionEl = document.getElementById('completionAnalytics');
        if (completionEl) {
            completionEl.innerHTML = s.map(function(x) {
                var pct = x.repository_count ? Math.round(x.evaluated_count / x.repository_count * 100) : 0;
                return '<div><span>' + window.esc(x.name) + '</span><div class="distribution-bar"><i style="width:' + pct + '%"></i></div><strong>' + pct + '%</strong></div>';
            }).join('') || '<p class="empty-state">No sessions available.</p>';
        }
    }).catch(function(err) {
        var errEl = document.getElementById('analyticsError');
        if (errEl) { errEl.hidden = false; errEl.textContent = 'Failed to load analytics: ' + err.message; }
    });
});
