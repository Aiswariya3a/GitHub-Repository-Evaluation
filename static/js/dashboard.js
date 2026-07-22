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
            var groups = { Active: [], Completed: [] };
            items.forEach(function(item) {
                if (item.status === 'Completed') {
                    groups.Completed.push(item);
                } else {
                    groups.Active.push(item);
                }
            });
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

// --- Overview page (v3 executive dashboard) ---
document.addEventListener('DOMContentLoaded', function() {
    var healthCard = document.getElementById('healthCard');
    if (!healthCard) return;

    function kpiV3(label, value, tone) {
        return '<div class="kpi-card-v3 ' + tone + '"><div class="k3-val">' + value + '</div><div class="k3-lbl">' + label + '</div></div>';
    }

    async function loadDashboard() {
        try {
            var r = await fetch('/api/dashboard');
            var d = await r.json();
            if (!r.ok) throw new Error(d.error || 'Dashboard unavailable');
            var m = d.metrics;
            var dist = d.score_distribution || {};
            var dt = Object.values(dist).reduce(function(a, b) { return a + Number(b); }, 0) || 1;
            var health = Number(m.average_health || 0);
            var pTotal = Number(m.repository_count || 0);
            var pDone = Number(m.evaluated_count || 0);
            var pRun = Number(m.running_count || 0);
            var pRem = Math.max(0, pTotal - pDone - pRun);

            // 1. KPI row (4 simple cards)
            var kpiEl = document.getElementById('dashboardKpis');
            if (kpiEl) {
                kpiEl.innerHTML =
                    kpiV3(m.session_count + '<span class="k3-unit"> sessions</span>', 'Evaluation Sessions', 'violet') +
                    kpiV3(pDone + '<span class="k3-unit"> of ' + pTotal + '</span>', 'Repositories Evaluated', 'green') +
                    kpiV3(health.toFixed(1) + '<span class="k3-unit"> / 20</span>', 'Average Score', 'amber') +
                    kpiV3(pRem + '<span class="k3-unit"> pending</span>', 'Pending Evaluations', 'blue');
            }

            // 2. Project Health — simple status summary
            var avgVal = document.getElementById('avgScoreValue');
            if (avgVal) avgVal.innerHTML = health.toFixed(1) + ' <span class="hps-unit">/ 20</span>';
            var evVal = document.getElementById('evaluatedValue');
            if (evVal) evVal.innerHTML = pDone + ' <span class="hps-unit">/ ' + pTotal + '</span>';
            var pvVal = document.getElementById('pendingValue');
            if (pvVal) pvVal.textContent = d.pending_reviews || 0;
            var avVal = document.getElementById('attentionValue');
            if (avVal) avVal.textContent = (dist.review || 0) + (dist.low || 0) + ' repos';

            var statusBadge = document.getElementById('statusBadge');
            if (statusBadge) {
                var badgeCls = health >= 14 ? 'sb-green' : health >= 10 ? 'sb-yellow' : health >= 6 ? 'sb-orange' : 'sb-red';
                var badgeLabel = health >= 14 ? 'Good' : health >= 10 ? 'Fair' : health >= 6 ? 'Needs Work' : 'Critical';
                statusBadge.className = 'hps-badge ' + badgeCls;
                statusBadge.textContent = badgeLabel;
            }

            var repoStatusList = document.getElementById('repoStatusList');
            if (repoStatusList) {
                repoStatusList.innerHTML =
                    '<div class="hps-sr"><span class="hps-sr-dot dot-green"></span><span class="hps-sr-lbl">Strong</span><span class="hps-sr-val">' + (dist.strong || 0) + ' repos</span></div>' +
                    '<div class="hps-sr"><span class="hps-sr-dot dot-yellow"></span><span class="hps-sr-lbl">On Track</span><span class="hps-sr-val">' + (dist.track || 0) + ' repos</span></div>' +
                    '<div class="hps-sr"><span class="hps-sr-dot dot-orange"></span><span class="hps-sr-lbl">Needs Review</span><span class="hps-sr-val">' + (dist.review || 0) + ' repos</span></div>' +
                    '<div class="hps-sr"><span class="hps-sr-dot dot-red"></span><span class="hps-sr-lbl">Needs Attention</span><span class="hps-sr-val">' + (dist.low || 0) + ' repos</span></div>';
            }

            // 3. Activity feed with status badges
            var recentActivity = document.getElementById('recentActivity');
            if (recentActivity) {
                var items = d.recent_activity || [];
                var acCnt = document.getElementById('activityCount');
                if (acCnt) acCnt.textContent = items.length;
                if (items.length === 0) {
                    recentActivity.innerHTML = '<div class="empty-sm" style="justify-content:center;padding:20px;border:0">No recent activity</div>';
                } else {
                    recentActivity.innerHTML = items.slice(0, 8).map(function(x) {
                        var isDone = x.score != null;
                        var cls = isDone ? 'ab-green' : 'ab-yellow';
                        var label = isDone ? 'Completed' : 'In progress';
                        var reviewBadge = x.needs_review
                            ? '<span class="review-badge-sm pending" title="Needs review">!</span>'
                            : x.has_review
                            ? '<span class="review-badge-sm reviewed" title="Reviewed">&#x2713;</span>'
                            : '';
                        return '<a class="av3-row" href="/sessions/' + x.session_id + '/repositories/' + x.id + '"><span class="av3-av">' + window.esc(x.roll_number).slice(-2) + '</span><div class="av3-body"><strong>' + window.esc(x.roll_number) + '</strong><span>' + window.esc(x.session_name) + '</span></div>' + reviewBadge + '<span class="av3-badge ' + cls + '">' + label + '</span></a>';
                    }).join('');
                    if (items.length > 8) {
                        recentActivity.innerHTML += '<a class="av3-more" href="/sessions">View all ' + items.length + ' &rarr;</a>';
                    }
                }
            }

            // 4. Running bar
            var runBar = document.getElementById('runningBar');
            if (runBar) {
                runBar.hidden = false;
                runBar.innerHTML = pRun > 0
                    ? '<span class="rb3-dot"></span><strong>' + pRun + '</strong> evaluation' + (pRun > 1 ? 's' : '') + ' running'
                    : '<span class="rb3-off"></span> No evaluations running';
            }

            // 5. Repository Summary (was Portfolio / Tech)
            var techEl = document.getElementById('technologyBreakdown');
            var techCard = document.getElementById('techCard');
            var portfolioCard = document.getElementById('portfolioCard');
            var portfolioEl = document.getElementById('portfolioBreakdown');
            if (techEl && techCard && portfolioCard && portfolioEl) {
                var techData = d.technologies || [];
                if (techData.length) {
                    techCard.hidden = false;
                    portfolioCard.hidden = true;
                    var maxT = Math.max.apply(null, techData.map(function(x) { return x.count || 1; }));
                    techEl.innerHTML = techData.map(function(t) {
                        return '<div class="tb3-row"><span>' + window.esc(t.language || t.name || t) + '</span><i style="width:' + Math.min(100, (t.count || 0) / maxT * 100) + '%"></i><strong>' + (t.count || 0) + '</strong></div>';
                    }).join('');
                } else {
                    techCard.hidden = true;
                    portfolioCard.hidden = false;
                    portfolioEl.innerHTML =
                        '<div class="pv3-grid"><div><span>Total repos</span><strong>' + pTotal + '</strong></div><div><span>Evaluated</span><strong>' + pDone + '</strong></div><div><span>Pending</span><strong>' + pRem + '</strong></div><div><span>Avg score</span><strong>' + health.toFixed(1) + '</strong></div></div>';
                }
            }

            // 6. Repository Analytics — simplified, no donut
            var raBody = document.getElementById('repoAnalytics');
            if (raBody) {
                raBody.innerHTML =
                    '<div class="ra3-stat"><span>Total repositories</span><strong>' + pTotal + '</strong></div>' +
                    '<div class="ra3-stat"><span>Evaluated</span><strong>' + pDone + '</strong></div>' +
                    '<div class="ra3-stat"><span>Pending</span><strong>' + pRem + '</strong></div>' +
                    '<div class="ra3-stat"><span>Average score</span><strong>' + health.toFixed(1) + '</strong></div>' +
                    '<div class="ra3-stat"><span>Running</span><strong>' + pRun + '</strong></div>';
            }

            // 7. Leaderboard (keep top performers)
            var leaderboard = document.getElementById('leaderboard');
            if (leaderboard) {
                var mc = ['#f59e0b', '#94a3b8', '#cd7f32'];
                leaderboard.innerHTML = (d.leaderboard || []).slice(0, 5).map(function(x, i) {
                    var rn = i < 3 ? '<span class="lr3-medal" style="color:' + mc[i] + '">' + ['&#x1F947;', '&#x1F948;', '&#x1F949;'][i] + '</span>' : '<span class="lr3-num">' + (i + 1) + '</span>';
                    var rb = x.needs_review
                        ? '<span class="review-badge-sm pending" title="Needs review">!</span>'
                        : x.has_review
                        ? '<span class="review-badge-sm reviewed" title="Reviewed">&#x2713;</span>'
                        : '';
                    return '<a class="lr3-row" href="/sessions/' + x.session_id + '/repositories/' + x.id + '">' + rn + '<div class="lr3-body"><strong>' + window.esc(x.roll_number) + '</strong><span>' + window.esc(x.session_name) + '</span></div>' + rb + '<span class="lr3-pill">' + Number(x.normalized_to_20 || 0).toFixed(1) + '</span></a>';
                }).join('') || '<div class="empty-sm">No data</div>';
            }

            // 8. Recent Sessions
            var rsEl = document.getElementById('recentSessions');
            if (rsEl) {
                try {
                    var sr = await fetch('/api/sessions');
                    var sessions = await sr.json();
                    if (sr.ok && sessions.length) {
                        rsEl.innerHTML = sessions.slice(0, 5).map(function(s) {
                            var pct = s.repository_count ? Math.round(s.evaluated_count / s.repository_count * 100) : 0;
                            return '<a class="rs3-row" href="/sessions/' + s.id + '"><span class="rs3-dot ' + s.status.toLowerCase() + '"></span><div class="rs3-body"><strong>' + window.esc(s.name) + '</strong><span>' + window.esc(s.description || '') + '</span></div><span class="rs3-stat"><strong>' + s.evaluated_count + '</strong>/' + s.repository_count + '</span><div class="rs3-bar"><i style="width:' + pct + '%"></i></div></a>';
                        }).join('');
                    } else {
                        rsEl.innerHTML = '<div class="empty-sm">No sessions yet</div>';
                    }
                } catch (_) { rsEl.innerHTML = ''; }
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
