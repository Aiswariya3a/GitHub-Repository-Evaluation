if (typeof window.date !== 'function') {
    window.date = function(v) { return v ? new Intl.DateTimeFormat(undefined, {dateStyle:'medium', timeStyle:'short'}).format(new Date(v)) : 'Never'; };
}
if (typeof window.esc !== 'function') {
    window.esc = function(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); };
}

document.addEventListener('DOMContentLoaded', function() {
    var page = document.getElementById('sessionPage');
    if (!page) return;
    var sid = page.dataset.sessionId;
    var data = null, filter = 'All', query = '', sort = 'recent', pageNum = 1;
    var PAGE_SIZE = 6;
    var selected = new Set();

    // --- Helpers for repo avatars ---
    function getRepoInitials(name) {
        name = (name || '').replace(/\.git$/i, '');
        var parts = name.split(/[-_\s]+/).filter(Boolean);
        if (parts.length >= 2 && parts[0].length > 0 && parts[1].length > 0) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        return name.slice(0, 2).toUpperCase() || '?';
    }
    function getAvatarColor(name) {
        var colors = ['#6366f1','#8b5cf6','#a855f7','#ec4899','#f43f5e','#ef4444','#f97316','#eab308','#84cc16','#22c55e','#14b8a6','#06b6d4','#3b82f6'];
        var hash = 0;
        for (var i = 0; i < (name || '').length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
        return colors[Math.abs(hash) % colors.length];
    }

    // --- Repository card renderer ---
    function card(r) {
        var done = r.status === 'Completed', running = r.status === 'Evaluating';
        var score = Number(r.normalized || 0);
        var lang = r.language || '\u2014';
        var desc = r.description || 'No description';
        var stars = Number(r.stars_count) || 0;
        var topics = r.topics || [];
        var forks = Number(r.forks_count) || 0;
        var license = r.license_info || '';
        var watchers = Number(r.watchers_count) || 0;
        var issues = Number(r.open_issues_count) || 0;
        var name = r.repo_url.split('/').pop();
        var progressPct = running ? (Number(r.progress_pct) || 0) : (done ? 100 : 0);
        var currentStep = running ? (r.current_step || 'Evaluating') : '';
        var confidenceWarning = r.has_low_confidence
            ? '<div class="warning-strip">! Low confidence criteria</div>'
            : '';
        var progressLabel = running ? '<div class="progress-label">' + window.esc(currentStep) + ' &middot; ' + progressPct + '%</div>' : '';
        return '<article class="repository-card' + (selected.has(r.id) ? ' selected' : '') + '">' +
            '<div class="repository-card-top">' +
            '<label class="check"><input type="checkbox" ' + (selected.has(r.id) ? 'checked' : '') + ' onchange="toggleSelection(\'' + r.id + '\',this.checked)"><span></span></label>' +
            '<span class="status-badge ' + window.statusTone(r.display_status) + '">' + window.esc(r.display_status) + '</span>' +
            '<div class="context-menu"><button onclick="this.nextElementSibling.classList.toggle(\'open\')">\u2022\u2022\u2022</button>' +
            '<div><a href="/sessions/' + sid + '/repositories/' + r.id + '">View details</a>' +
            (done ? '<a href="/sessions/' + sid + '/repositories/' + r.id + '/report">Download report</a><button onclick="evaluateOne(\'' + r.id + '\',true)">Re-evaluate</button>' : '<button onclick="evaluateOne(\'' + r.id + '\',false)">Evaluate now</button>') +
            '<button onclick="deleteRepository(\'' + r.id + '\')" class="danger-text">Delete</button></div></div></div>' +
            '<a class="repository-card-title" href="/sessions/' + sid + '/repositories/' + r.id + '">' +
            '<span class="repo-icon" style="background:' + getAvatarColor(name) + '26;color:' + getAvatarColor(name) + '">' + getRepoInitials(name) + '</span><div><strong>' + window.esc(name) + '</strong>' +
            '<small>' + window.esc(r.roll_number) + '</small>' +
            '<span class="repo-desc" title="' + window.esc(r.description || '') + '">' + window.esc(desc.length > 60 ? desc.slice(0, 60) + '\u2026' : desc) + '</span></div></a>' +
            '<div class="repo-lang-strip"><span class="lang-dot"></span>' + window.esc(lang) +
            (stars ? '<span class="stars-count">\u2605 ' + stars + '</span>' : '') +
            (forks ? '<span class="meta-badge">\U000103B9 ' + forks + '</span>' : '') +
            (watchers ? '<span class="meta-badge">\u25CF ' + watchers + '</span>' : '') +
            (issues ? '<span class="meta-badge">! ' + issues + '</span>' : '') +
            (license ? '<span class="meta-badge">' + window.esc(license) + '</span>' : '') + '</div>' +
            (topics.length ? '<div class="repo-topics">' + topics.slice(0, 4).map(function(t) { return '<span class="topic-tag">' + window.esc(t) + '</span>'; }).join('') + '</div>' : '') +
            '<div class="repository-metrics">' +
            '<div><span>Health</span><strong>' + score.toFixed(1) + '<small>/20</small></strong></div>' +
            '<div><span>Commits</span><strong>' + (r.commit_count || 0) + '</strong></div>' +
            '<div><span>Evaluated</span><strong class="date-value">' + (r.evaluated_at ? new Date(r.evaluated_at).toLocaleDateString() : '\u2014') + '</strong></div></div>' +
            progressLabel +
            '<div class="progress-bar' + (running ? ' indeterminate' : '') + '"><span style="width:' + progressPct + '%"></span></div>' +
            (r.error ? '<div class="warning-strip">! ' + window.esc(r.error) + '</div>' : '') +
            confidenceWarning +
            '</article>';
    }

    // --- renderRepositories with low-confidence filter support ---
    function renderRepositories() {
        var rows = [...(data?.repositories || [])];
        rows = rows.filter(function(r) {
            var statusMatch = (filter === 'All' || r.status === filter);
            var confMatch = (filter !== 'LowConfidence' || r.has_low_confidence === true);
            var searchMatch = (r.roll_number + ' ' + r.repo_url).toLowerCase().includes(query);
            return statusMatch && confMatch && searchMatch;
        });
        rows.sort(function(a, b) {
            if (sort === 'score') return Number(b.normalized) - Number(a.normalized);
            if (sort === 'name') return a.roll_number.localeCompare(b.roll_number);
            return new Date(b.updated_at) - new Date(a.updated_at);
        });
        var pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
        pageNum = Math.min(pageNum, pages);
        var grid = document.getElementById('repositoryGrid');
        if (grid) {
            grid.innerHTML = rows.slice((pageNum - 1) * PAGE_SIZE, pageNum * PAGE_SIZE).map(card).join('') ||
                '<div class="polished-empty wide"><span>\u2315</span><strong>No repositories found</strong><p>Adjust your search or filters.</p></div>';
        }
        var countEl = document.getElementById('repositoryCount');
        if (countEl) countEl.textContent = rows.length;
        var pageLabel = document.getElementById('pageLabel');
        if (pageLabel) pageLabel.textContent = 'Page ' + pageNum + ' of ' + pages;
        var prevBtn = document.getElementById('previousPage');
        var nextBtn = document.getElementById('nextPage');
        if (prevBtn) prevBtn.disabled = pageNum === 1;
        if (nextBtn) nextBtn.disabled = pageNum === pages;
        var selectedCount = document.getElementById('selectedCount');
        if (selectedCount) selectedCount.textContent = selected.size;
        var bulkBar = document.getElementById('bulkBar');
        if (bulkBar) bulkBar.hidden = !selected.size;
    }

    // --- renderPlagiarism (NEW) ---
    function renderPlagiarism(plagiarism) {
        var container = document.getElementById('plagiarismContent');
        if (!container) return;
        if (!plagiarism || plagiarism.length === 0) {
            container.innerHTML = window.empty('No matches', 'No plagiarism matches found for this session.');
            return;
        }
        var rows = plagiarism.map(function(p) {
            return '<tr><td>' + window.esc(p.roll1) + '</td><td>' + window.esc(p.roll2) + '</td>' +
                '<td><span class="' + (Number(p.similarity) >= 0.8 ? 'status-badge status-needs-review' : '') + '">' + (Number(p.similarity) * 100).toFixed(1) + '%</span></td></tr>';
        }).join('');
        container.innerHTML = '<table class="data-table"><thead><tr><th>Repository 1</th><th>Repository 2</th><th>Similarity</th></tr></thead><tbody>' + rows + '</tbody></table>';
    }

    // --- render (full page render) ---
    function render(d) {
        data = d;
        var s = d.session, x = d.summary;
        var pct = x.total ? Math.round(x.completed / x.total * 100) : 0;

        var crumbName = document.getElementById('crumbName');
        var sessionName = document.getElementById('sessionName');
        var sessionDescription = document.getElementById('sessionDescription');
        var sessionStatus = document.getElementById('sessionStatus');
        var sessionDates = document.getElementById('sessionDates');
        var sessionStats = document.getElementById('sessionStats');
        var overallProgressLabel = document.getElementById('overallProgressLabel');
        var overallProgressBar = document.getElementById('overallProgressBar');
        var progressSubtext = document.getElementById('progressSubtext');
        var progressSteps = document.getElementById('progressSteps');
        var sessionReport = document.getElementById('sessionReport');
        var evaluationTimeline = document.getElementById('evaluationTimeline');
        var technologyInsights = document.getElementById('technologyInsights');
        var scoreDistrib = document.getElementById('scoreDistribution');

        if (crumbName) crumbName.textContent = s.name;
        if (sessionName) sessionName.textContent = s.name;
        if (sessionDescription) sessionDescription.textContent = s.description || 'No description';
        if (sessionStatus) {
            sessionStatus.textContent = s.status;
            sessionStatus.className = 'status-badge session-' + s.status.toLowerCase();
        }
        if (sessionDates) sessionDates.textContent = 'Created ' + window.date(s.created_at) + ' \u00B7 Updated ' + window.date(s.updated_at);

        if (sessionStats) {
            sessionStats.innerHTML =
                '<article class="metric-card modern-kpi violet"><p class="metric-label">Repositories</p><p class="metric-value">' + x.total + '</p><span class="metric-caption">In this session</span></article>' +
                '<article class="metric-card modern-kpi green"><p class="metric-label">Evaluated</p><p class="metric-value">' + x.completed + '</p><span class="metric-caption">Results saved</span></article>' +
                '<article class="metric-card modern-kpi amber"><p class="metric-label">Needs action</p><p class="metric-value">' + x.pending + '</p><span class="metric-caption">Pending or failed</span></article>' +
                '<article class="metric-card modern-kpi blue"><p class="metric-label">Average health</p><p class="metric-value">' + x.average + '/20</p><span class="metric-caption">Completed repositories</span></article>';
        }

        if (overallProgressLabel) overallProgressLabel.textContent = pct + '%';
        if (overallProgressBar) overallProgressBar.style.width = pct + '%';
        if (progressSubtext) progressSubtext.textContent = x.completed + ' of ' + x.total + ' repositories evaluated';
        if (progressSteps) {
            progressSteps.innerHTML = ['Session created', 'Repositories added', 'Evaluation', 'Review complete'].map(function(v, i) {
                return '<span class="' + (i < (pct === 100 ? 4 : pct > 0 ? 3 : 2) ? 'done' : '') + '"><i>' + (i + 1) + '</i>' + v + '</span>';
            }).join('');
        }
        if (sessionReport) sessionReport.href = '/sessions/' + sid + '/report';

        renderRepositories();

        var z = d.insights || {};
        if (evaluationTimeline) {
            evaluationTimeline.innerHTML = (z.timeline || []).map(function(v) {
                return '<a href="/sessions/' + sid + '/repositories/' + v.repository_id + '"><span class="timeline-dot"></span><div><strong>' + window.esc(v.roll_number) + '</strong><small>' + window.esc(v.status) + ' \u00B7 ' + window.date(v.at) + '</small></div></a>';
            }).join('') || '<div class="polished-empty compact"><strong>No activity yet</strong></div>';
        }
        if (technologyInsights) {
            technologyInsights.innerHTML = (z.technologies || []).map(function(t) {
                return '<span class="topic-tag">' + window.esc(t.language || t.name || t) + ' <small>\u00D7' + (t.count || 0) + '</small></span>';
            }).join('') || '<div class="polished-empty compact"><strong>No tech data</strong></div>';
        }
        if (scoreDistrib) {
            var sd = z.score_distribution || {};
            var totalScores = Object.values(sd).reduce(function(a, b) { return a + Number(b); }, 0) || 1;
            scoreDistrib.innerHTML = [
                { label: 'Strong (16-20)', key: '16-20', color: '#10b981' },
                { label: 'On track (12-15)', key: '12-15', color: '#6366f1' },
                { label: 'Needs review (8-11)', key: '8-11', color: '#f59e0b' },
                { label: 'Needs attention (0-7)', key: '0-7', color: '#ef4444' }
            ].map(function(item) {
                var count = Number(sd[item.key] || 0);
                var pctVal = count / totalScores * 100;
                return '<div><span>' + item.label + '</span><div class="distribution-bar"><i style="width:' + pctVal + '%;background:' + item.color + '"></i></div><strong>' + count + '</strong></div>';
            }).join('');
        }

        // Render plagiarism section
        if (d.plagiarism) {
            renderPlagiarism(d.plagiarism);
        }

        // Update low-confidence filter chip count
        var lowConfCount = (d.repositories || []).filter(function(r) { return r.has_low_confidence; }).length;
        var lowConfChip = document.querySelector('[data-status="LowConfidence"]');
        if (lowConfChip) {
            lowConfChip.textContent = 'Low confidence (' + lowConfCount + ')';
        }
    }

    // --- load ---
    async function load() {
        try {
            var r = await fetch('/api/sessions/' + sid);
            var d = await r.json();
            if (!r.ok) throw new Error(d.error);
            render(d);
        } catch (e) {
            var err = document.getElementById('sessionError');
            if (err) { err.hidden = false; err.textContent = e.message; }
        }
    }

    // --- toggleSelection ---
    window.toggleSelection = function(id, on) {
        if (on) { selected.add(id); } else { selected.delete(id); }
        renderRepositories();
    };

    function clearSelection() {
        selected.clear();
        renderRepositories();
    }

    // --- evaluateOne ---
    window.evaluateOne = async function(id, re) {
        re = re || false;
        if (data?.repositories) {
            var repo = data.repositories.find(function(x) { return x.id === id; });
            if (repo) {
                repo.status = 'Evaluating';
                repo.display_status = 'Evaluating';
                renderRepositories();
            }
        }
        window.toast('Evaluation started', 'success');
        fetch('/api/sessions/' + sid + '/repositories/' + id + '/' + (re ? 'reevaluate' : 'evaluate'), { method: 'POST' })
            .then(function(r) { if (!r.ok) r.json().then(function(d) { window.toast(d.error || 'Evaluation failed to start', 'error'); }); })
            .catch(function() {});
        pollOneUntilDone(id);
    };

    function pollOneUntilDone(id) {
        if (window._evalPoll) clearInterval(window._evalPoll);
        window._evalPoll = setInterval(async function() {
            try {
                var resp = await fetch('/api/sessions/' + sid + '/repositories/' + id);
                var d = await resp.json();
                var status = d.repository && d.repository.status;
                if (status === 'Completed') {
                    clearInterval(window._evalPoll);
                    window._evalPoll = null;
                    window.toast('Evaluation completed');
                    load();
                } else if (status === 'Failed' || status === 'Error') {
                    clearInterval(window._evalPoll);
                    window._evalPoll = null;
                    window.toast('Evaluation failed', 'error');
                    load();
                } else if (status === 'Evaluating' && d.repository && data) {
                    var found = false;
                    data.repositories.forEach(function(r) {
                        if (r.id === id) {
                            r.progress_pct = d.repository.progress_pct;
                            r.current_step = d.repository.current_step;
                            found = true;
                        }
                    });
                    if (found) renderRepositories();
                }
            } catch (e) {
                clearInterval(window._evalPoll);
                window._evalPoll = null;
            }
        }, 3000);
    }

    window.bulkEvaluate = async function() {
        if (!await window.confirmAction('Evaluate ' + selected.size + ' selected repositories?', 'Bulk evaluation')) return;
        for (var id of [...selected]) {
            var r = data.repositories.find(function(x) { return x.id === id; });
            await evaluateOne(id, r && r.status === 'Completed');
        }
        selected.clear();
        renderRepositories();
    };

    async function evaluateAll() {
        if (!await window.confirmAction('Evaluate every pending repository in this session?', 'Evaluate pending')) return;
        window.toast('Batch evaluation started');
        var r = await fetch('/api/sessions/' + sid + '/evaluate', { method: 'POST' });
        var d = await r.json();
        if (!r.ok) { window.toast(d.error, 'error'); } else { window.toast(d.evaluated + ' repositories evaluated'); }
        load();
    }

    async function changeSessionStatus() {
        var next = data.session.status === 'Active' ? 'Completed' : 'Active';
        if (!await window.confirmAction('Mark this session ' + next.toLowerCase() + '?', 'Change session status')) return;
        await fetch('/api/sessions/' + sid, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: next }) });
        window.toast('Session marked ' + next.toLowerCase());
        load();
    }

    // --- deleteRepository ---
    window.deleteRepository = async function(id) {
        var repo = data.repositories.find(function(x) { return x.id === id; });
        if (!await window.confirmAction('Delete repository "' + (repo?.roll_number || id) + '" and all its evaluation data? This cannot be undone.', 'Delete repository')) return;
        var r = await fetch('/api/sessions/' + sid + '/repositories/' + id, { method: 'DELETE' });
        if (!r.ok) { var d = await r.json(); window.toast(d.error || 'Failed to delete', 'error'); return; }
        selected.delete(id);
        window.toast('Repository deleted');
        load();
    };

    // --- Event bindings ---
    var filterChips = document.getElementById('filterChips');
    if (filterChips) {
        filterChips.addEventListener('click', function(e) {
            if (!e.target.dataset.status) return;
            filter = e.target.dataset.status;
            pageNum = 1;
            [...filterChips.children].forEach(function(x) { x.classList.toggle('active', x === e.target); });
            renderRepositories();
        });
    }

    var repositorySearch = document.getElementById('repositorySearch');
    if (repositorySearch) {
        repositorySearch.addEventListener('input', function(e) {
            query = e.target.value.toLowerCase();
            pageNum = 1;
            renderRepositories();
        });
    }

    var repositorySort = document.getElementById('repositorySort');
    if (repositorySort) {
        repositorySort.addEventListener('change', function(e) {
            sort = e.target.value;
            renderRepositories();
        });
    }

    var previousPage = document.getElementById('previousPage');
    if (previousPage) {
        previousPage.onclick = function() { pageNum--; renderRepositories(); };
    }

    var nextPage = document.getElementById('nextPage');
    if (nextPage) {
        nextPage.onclick = function() { pageNum++; renderRepositories(); };
    }

    var repositoryForm = document.getElementById('repositoryForm');
    if (repositoryForm) {
        repositoryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            var repoUrl = document.getElementById('repositoryUrl');
            var rollNum = document.getElementById('rollNumber');
            var formError = document.getElementById('repositoryFormError');
            var resp = await fetch('/api/sessions/' + sid + '/repositories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repositories: [{ repo_url: repoUrl.value, roll_number: rollNum.value }] })
            });
            var d = await resp.json();
            if (!resp.ok) { if (formError) formError.textContent = d.error; return; }
            var dialog = document.getElementById('repositoryDialog');
            if (dialog) dialog.close();
            e.target.reset();
            window.toast('Repository added');
            if (d.repositories?.length && data?.repositories) {
                d.repositories.forEach(function(repo) {
                    data.repositories.unshift({ ...repo, status: 'Pending', display_status: 'Pending', evaluation_status: 'Pending', commit_count: 0, normalized: 0, error: '', evaluated_at: null, updated_at: new Date().toISOString() });
                });
                renderRepositories();
            } else {
                load();
            }
        });
    }

    // --- Tab switching for plagiarism tab ---
    var tabBar = document.querySelector('.tab-bar');
    if (tabBar) {
        tabBar.addEventListener('click', function(e) {
            if (e.target && e.target.dataset && e.target.dataset.tab) {
                var tabs = tabBar.querySelectorAll('button');
                tabs.forEach(function(t) { t.classList.remove('active'); });
                e.target.classList.add('active');
                var panels = document.querySelectorAll('.tab-panel');
                panels.forEach(function(p) { p.classList.remove('active'); });
                var panel = document.getElementById('tab-' + e.target.dataset.tab);
                if (panel) panel.classList.add('active');
            }
        });
    }

    // --- Clear selection ---
    var clearSelBtn = document.querySelector('#bulkBar button:last-child');
    if (clearSelBtn) {
        clearSelBtn.addEventListener('click', clearSelection);
    }

    // --- Quick actions ---
    var evaluateAllBtn = document.querySelector('[onclick="evaluateAll()"]');
    if (evaluateAllBtn) {
        evaluateAllBtn.addEventListener('click', evaluateAll);
    }

    var changeStatusBtn = document.querySelector('[onclick="changeSessionStatus()"]');
    if (changeStatusBtn) {
        changeStatusBtn.addEventListener('click', changeSessionStatus);
    }

    // --- Auto-refresh ---
    setInterval(function() { if (!document.hidden) load(); }, 5000);

    // --- Initialize ---
    load();
});
