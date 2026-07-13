/**
 * repository.js — Repository detail page JavaScript
 *
 * Handles ingestion tab, evaluation detail tab, collaboration tab,
 * low-confidence indicators, and all existing repository detail page logic.
 *
 * Extracted from inline <script> block in repository_detail.html.
 */

document.addEventListener('DOMContentLoaded', () => {
    const page = document.getElementById('repositoryPage');
    if (!page) return;
    const sid = page.dataset.sessionId;
    const rid = page.dataset.repositoryId;

    let repository = null;

    // ---- Shared utilities ----

    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

    const empty = (title, text) => `<div class="polished-empty"><span>\u25C7</span><strong>${title}</strong><p>${text}</p></div>`;

    const criterionCard = x => {
        const s = x.score != null
            ? `<div class="progress-bar"><span style="width:${Math.min(100, Number(x.score) / Number(x.max_score || 8) * 100)}%"></span></div><span class="metric-score">${Number(x.score).toFixed(1)}/${Number(x.max_score || 8).toFixed(0)}</span>`
            : '';
        return `<article class="metric-card"><div class="metric-card-header"><span class="metric-orb"></span><strong>${esc(x.criterion_key || x.criterion || 'Criterion')}</strong></div><p>${esc(x.remarks || x.description || '')}</p>${s}</article>`;
    };

    // ---- New tab renderers ----

    function renderIngestionTab(ingestion) {
        const container = document.getElementById('ingestionContent');
        if (!container) return;
        if (!ingestion || !ingestion.files || !ingestion.files.length) {
            container.innerHTML = empty('No ingestion data', 'Ingestion snapshot not available for this repository.');
            return;
        }

        const rs = ingestion.repo_stats || {};
        const langBreak = rs.language_breakdown || {};

        const langEntries = Object.entries(langBreak)
            .map(([lang, count]) => `<span class="topic-tag">${esc(lang)}: ${count} files</span>`)
            .join('');
        const langSummary = langEntries ? `<div class="repo-topics" style="margin-bottom:16px">${langEntries}</div>` : '';

        const fileRows = (ingestion.files || []).map(f => {
            const loc = f.loc || f.code_loc || 0;
            return `<div class="file-row">
                <span class="file-lang">${esc(f.language || 'unknown')}</span>
                <span class="file-path">${esc(f.path)}</span>
                <span class="file-loc">${loc} lines</span>
            </div>`;
        }).join('');

        container.innerHTML = langSummary + `<div class="file-list">${fileRows}</div>`;
    }

    function renderCriterionResult(cr) {
        const conf = Number(cr.confidence || 0);
        const confClass = conf >= 0.7 ? 'high' : conf >= 0.5 ? 'medium' : 'low';
        const hasWarning = cr.confidence_warning || conf < 0.5;
        const warningStrip = hasWarning ? '<div class="warning-strip">! Low confidence \u2014 review manually</div>' : '';
        const evidenceItems = (cr.evidence || []).map(e => `<li>${esc(e)}</li>`).join('');

        return `<article class="metric-card${hasWarning ? ' low-confidence' : ''}">
            <div class="metric-card-header">
                <span class="metric-orb"></span>
                <strong>${esc(cr.criterion_key)}</strong>
                <span class="confidence-badge ${confClass}">${(conf * 100).toFixed(0)}%</span>
            </div>
            <div class="score-bar">
                <span style="width:${Math.min(100, Number(cr.score || 0) / Number(cr.max_score || 8) * 100)}%"></span>
                <span class="metric-score">${Number(cr.score || 0).toFixed(1)} / ${Number(cr.max_score || 8).toFixed(0)}</span>
            </div>
            <p class="metric-remarks">${esc(cr.remarks || '')}</p>
            ${evidenceItems ? `<details><summary>Evidence (${cr.evidence.length} items)</summary><ul>${evidenceItems}</ul></details>` : ''}
            ${warningStrip}
        </article>`;
    }

    function renderEvaluationDetailTab(evaluationResult) {
        const container = document.getElementById('evaluationContent');
        if (!container) return;
        if (!evaluationResult || !evaluationResult.criterion_results || !evaluationResult.criterion_results.length) {
            container.innerHTML = empty('No evaluation data', 'Run an evaluation to see per-criterion results.');
            return;
        }

        const criteria = evaluationResult.criterion_results;

        // Group criteria by category_code
        const groups = {};
        criteria.forEach(cr => {
            const cat = cr.category_code || 'other';
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push(cr);
        });

        let html = '';
        for (const [catCode, items] of Object.entries(groups)) {
            const catTotal = items.reduce((sum, cr) => sum + Number(cr.score || 0), 0);
            const catMax = items.reduce((sum, cr) => sum + Number(cr.max_score || 8), 0);

            html += `<div class="rubric-section"><h3>Category: ${esc(catCode)} <small>(${catTotal.toFixed(1)} / ${catMax.toFixed(0)})</small></h3>`;
            html += items.map(cr => renderCriterionResult(cr)).join('');
            html += '</div>';
        }

        container.innerHTML = html;
    }

    function renderCollaborationTab(insights) {
        const container = document.getElementById('collaborationContent');
        if (!container) return;

        // Only replace if we have rich insights data from related_data()
        if (!insights || (!insights.contributors || !insights.contributors.length) && (!insights.commits || !insights.commits.length)) return;

        const contribs = insights.contributors || [];
        const commits = insights.commits || [];
        const prs = insights.pull_requests || [];
        const issues = insights.issues || [];

        const contribRows = contribs.map(c =>
            `<div class="detail-row">
                <span>${esc(c.login || c.author || 'Unknown')}</span>
                <span>${c.contributions || 0} contributions</span>
            </div>`
        ).join('');

        const commitItems = commits.slice(0, 10).map(c =>
            `<div class="timeline-item">
                <strong>${esc(c.author || '?')}</strong>
                <span>${esc((c.message || '').split('\n')[0])}</span>
                <time>${new Date(c.date).toLocaleDateString()}</time>
            </div>`
        ).join('');

        container.innerHTML =
            '<div class="stats-grid repository-kpis">' +
                '<article class="metric-card modern-kpi violet"><p class="metric-label">Commits</p><p class="metric-value">' + commits.length + '</p></article>' +
                '<article class="metric-card modern-kpi blue"><p class="metric-label">Pull requests</p><p class="metric-value">' + prs.length + '</p></article>' +
                '<article class="metric-card modern-kpi green"><p class="metric-label">Issues</p><p class="metric-value">' + issues.length + '</p></article>' +
                '<article class="metric-card modern-kpi amber"><p class="metric-label">Contributors</p><p class="metric-value">' + contribs.length + '</p></article>' +
            '</div>' +
            '<div class="repository-detail-grid">' +
                (contribRows ? '<article class="panel"><h2>Contributors</h2>' + contribRows + '</article>' : '') +
                (commitItems ? '<article class="panel"><h2>Recent commits</h2>' + commitItems + '</article>' : '') +
            '</div>';
    }

    // ---- Existing render() function (preserved, with new tab calls added) ----

    function render(d) {
        repository = d.repository;
        const r = repository;
        const i = r.insights;
        const e = r.evaluation_data.evaluation || {};
        const f = e.final || {};
        const ev = r.evaluation_result || {};
        const er = ev.feedback || f;
        const score = Number(ev.normalized_to_20 || f.normalized_to_20 || 0);
        const ing = r.ingestion || {};
        const rs = ing.repo_stats || {};
        const gm = ing.github_metadata || {};
        const langBreak = rs.language_breakdown || {};
        const criteria = ev.criterion_results || [];

        sessionBack.href = `/sessions/${sid}`;
        repositoryTitle.textContent = r.roll_number + ' \u00B7 ' + r.repo_url.split('/').pop();
        repositoryUrl.textContent = r.repo_url;
        repositoryStatus.textContent = r.status;
        repositoryStatus.className = 'status-badge status-' + r.status.toLowerCase();
        repositoryActions.innerHTML =
            '<a class="secondary-btn" href="' + r.repo_url + '" target="_blank">Open GitHub \u2197</a>' +
            '<div class="dropdown"><button class="secondary-btn" onclick="this.nextElementSibling.classList.toggle(\'open\')">Actions \u25BE</button>' +
            '<div class="dropdown-menu"><button onclick="runEvaluation(true)">Re-evaluate</button>' +
            '<a href="/sessions/' + sid + '/repositories/' + rid + '/report">Download report</a></div></div>';

        repositoryGauge.innerHTML =
            '<div class="gauge-ring compact-gauge" style="--score:' + (score / 20 * 360) + 'deg">' +
            '<div><strong>' + score.toFixed(1) + '</strong><span>out of 20</span></div></div>' +
            '<span class="health-label">' +
            (score >= 16 ? 'Strong' : score >= 12 ? 'On track' : score >= 8 ? 'Needs review' : 'Needs attention') +
            '</span>';

        scoreMeta.innerHTML =
            '<div><span>Evaluated</span><strong>' + (r.evaluated_at ? new Date(r.evaluated_at).toLocaleDateString() : 'Never') + '</strong></div>' +
            '<div><span>Total marks</span><strong>' + Number(ev.total_score || f.total_out_of_80 || 0).toFixed(1) + '/' + Number(ev.max_score || 80).toFixed(0) + '</strong></div>' +
            '<div><span>Files</span><strong>' + (rs.file_count || r.commit_count || 0) + '</strong></div>';

        evaluateButton.textContent = r.status === 'Completed' ? 'Re-evaluate' : 'Evaluate';
        evaluateButton.onclick = () => runEvaluation(r.status === 'Completed');
        reportButton.hidden = r.status !== 'Completed';
        reportButton.href = '/sessions/' + sid + '/repositories/' + rid + '/report';

        const langEntries = Object.entries(langBreak);
        overviewMetrics.innerHTML =
            '<article class="metric-card"><p class="metric-label">Total LOC</p><p class="metric-value">' + (rs.total_loc || 0) + '</p></article>' +
            '<article class="metric-card"><p class="metric-label">Code LOC</p><p class="metric-value">' + (rs.code_loc || 0) + '</p></article>' +
            '<article class="metric-card"><p class="metric-label">Files</p><p class="metric-value">' + (rs.file_count || 0) + '</p></article>' +
            '<article class="metric-card"><p class="metric-label">Languages</p><p class="metric-value small-value">' +
            (langEntries.length ? langEntries.map(([l, n]) => esc(l) + ' (' + n + ')').join(', ') : '\u2014') + '</p></article>';

        dimensionChart.innerHTML = criteria.length
            ? criteria.map(x => {
                const label = (x.criterion_key || 'dimension').replace(/_/g, ' ');
                return '<div><span title="' + esc(x.criterion_key || '') + '">' + esc(label) + '</span>' +
                    '<div class="distribution-bar"><i style="width:' + ((x.score || 0) / (x.max_score || 8)) * 100 + '%"></i></div>' +
                    '<strong>' + Number(x.score || 0).toFixed(1) + '</strong></div>';
            }).join('')
            : empty('No score dimensions', 'Run an evaluation to generate rubric scores.');

        const warnings = [];
        const metaValid = gm.commits_count > 0 || (gm.recent_commits && gm.recent_commits.length) || (gm.contributors && gm.contributors.length);
        if (metaValid && !gm.readme_exists) warnings.push(['warning', 'README missing', 'Add clear setup and usage documentation.']);
        if (metaValid && !gm.is_public) warnings.push(['danger', 'Repository unavailable', 'Confirm repository visibility and URL access.']);
        if (score < 12) warnings.push(['warning', 'Health below target', 'Review low-scoring rubric dimensions.']);
        if (!warnings.length) warnings.push(['success', 'Healthy repository', 'No critical warnings detected.']);

        keyInsights.innerHTML = warnings.map(([tone, title, text]) =>
            '<div class="insight-alert ' + tone + '"><span>' + (tone === 'success' ? '\u2713' : '!') + '</span>' +
            '<div><strong>' + title + '</strong><p>' + text + '</p></div></div>'
        ).join('');

        const overallRemarks = er.overall_remarks || '';
        recommendations.innerHTML = overallRemarks
            ? '<div class="recommendation"><span>01</span><p>' + esc(overallRemarks) + '</p></div>'
            : empty('No recommendations yet', 'Recommendations are generated from saved evaluation results.');

        const catCriteria = { C2: [], C3: [], C5: [] };
        criteria.forEach(x => { const cat = x.category_code || ''; if (catCriteria[cat]) catCriteria[cat].push(x); });

        const evalNote = r.status === 'Evaluated' ? 'Run evaluation to generate metrics.' : 'Evaluation failed. Check errors and retry.';
        qualityContent.innerHTML = catCriteria.C3.length
            ? catCriteria.C3.map(criterionCard).join('')
            : (evalNote ? empty('Code quality', evalNote) : empty('Code quality', 'No code quality metrics available.'));
        documentationContent.innerHTML = catCriteria.C2.length
            ? catCriteria.C2.map(criterionCard).join('')
            : (evalNote ? empty('Documentation', evalNote) : empty('Documentation', 'No documentation metrics available.'));

        const commits = gm.recent_commits || [];
        const prs = gm.pull_requests || [];
        const allIssues = gm.issues || [];
        const contributors = gm.contributors || [];
        const hasMeta = gm.commits_count != null || prs.length || allIssues.length || contributors.length;
        if (hasMeta) {
            const commitRows = commits.length
                ? commits.slice(0, 5).map(c =>
                    '<div class="insight-metric"><div><span class="metric-orb"></span><strong>' + (c.sha ? c.sha.slice(0, 7) : '\u2014') + '</strong></div><p>' + esc(c.message || '') + '</p></div>'
                ).join('')
                : empty('Commits', 'No recent commits.');
            const prRows = prs.length
                ? prs.slice(0, 5).map(p =>
                    '<div class="insight-metric"><div><span class="metric-orb"></span><strong>' + esc(p.title || 'PR #' + p.number) + '</strong></div><p>' + p.html_url + '</p></div>'
                ).join('')
                : empty('Pull requests', 'No open pull requests.');
            const issueRows = allIssues.length
                ? allIssues.slice(0, 5).map(iss =>
                    '<div class="insight-metric"><div><span class="metric-orb"></span><strong>' + esc(iss.title || '#' + iss.number) + '</strong></div><p>' + iss.html_url + '</p></div>'
                ).join('')
                : empty('Issues', 'No open issues.');
            const contributorRows = contributors.length
                ? contributors.slice(0, 5).map(c =>
                    '<div class="insight-metric"><div><span class="metric-orb"></span><strong>' + esc(c.login || c.name || 'Contributor') + '</strong></div><p>' + (c.contributions ? c.contributions + ' contributions' : '') + '</p></div>'
                ).join('')
                : empty('Contributors', 'No contributors found.');

            collaborationContent.innerHTML =
                '<div class="stats-grid repository-kpis">' +
                    '<article class="metric-card modern-kpi violet"><p class="metric-label">Commits</p><p class="metric-value">' + (gm.commits_count || 0) + '</p></article>' +
                    '<article class="metric-card modern-kpi blue"><p class="metric-label">Pull requests</p><p class="metric-value">' + (prs.length || gm.pull_requests_count || 0) + '</p></article>' +
                    '<article class="metric-card modern-kpi green"><p class="metric-label">Issues</p><p class="metric-value">' + (allIssues.length || gm.issues_count || 0) + '</p></article>' +
                    '<article class="metric-card modern-kpi gold"><p class="metric-label">Contributors</p><p class="metric-value">' + (contributors.length || 0) + '</p></article>' +
                '</div>' +
                '<div class="repository-detail-grid">' +
                    '<article class="panel"><h2>Latest commits</h2>' + commitRows + '</article>' +
                    '<article class="panel"><h2>Pull requests</h2>' + prRows + '</article>' +
                    '<article class="panel"><h2>Issues</h2>' + issueRows + '</article>' +
                    '<article class="panel"><h2>Contributors</h2>' + contributorRows + '</article>' +
                '</div>';
        } else {
            collaborationContent.innerHTML = empty('Collaboration', 'No collaboration metrics available.');
        }

        const fileList = ing.files || [];
        if (fileList.length) {
            const fileRows = fileList.slice(0, 40).map(f =>
                '<div class="file-row"><span class="file-lang">' + esc(f.language || '?') + '</span>' +
                '<span class="file-path" title="' + esc(f.path) + '">' + esc(f.path) + '</span>' +
                '<span class="file-size">' + (f.size ? Math.round(f.size / 1024) + ' KB' : '\u2014') + '</span></div>'
            ).join('');
            activityContent.innerHTML =
                '<article class="panel"><h2>Files <span class="count-pill">' + fileList.length + '</span></h2><div class="file-list">' + fileRows + '</div></article>';
        } else {
            activityContent.innerHTML = '';
        }

        if (gm.commits_count || commits.length) {
            activityContent.innerHTML +=
                '<article class="panel"><h2>GitHub activity</h2><p>' +
                (gm.commits_count || commits.length) + ' commits, ' +
                (prs.length || gm.pull_requests_count || 0) + ' pull requests, ' +
                (allIssues.length || gm.issues_count || 0) + ' issues</p></article>';
        } else if (!fileList.length) {
            activityContent.innerHTML = empty('Activity', 'No activity data available.');
        }

        historyContent.innerHTML = [
            ['Repository added', r.created_at],
            ['Last updated', r.updated_at],
            ['Last evaluated', r.evaluated_at],
            ['Ingestion', ing.repository_metadata ? ing.repository_metadata.status : null],
            ['Pipeline', ev.pipeline_status]
        ].filter(([, v]) => v).map(([name, at]) =>
            '<div class="history-event"><span class="timeline-dot"></span>' +
            '<div><strong>' + name + '</strong><small>' + (at ? new Date(at).toLocaleString() : 'Not yet') + '</small></div></div>'
        ).join('');

        // ---- New calls: render new tabs ----
        renderIngestionTab(r.ingestion);
        renderEvaluationDetailTab(ev);
        renderCollaborationTab(r.insights);

        // ---- Low-confidence sidebar indicator ----
        const lowConf = ev.low_confidence_criteria || [];
        if (lowConf.length) {
            const sm = document.getElementById('scoreMeta');
            if (sm) {
                sm.innerHTML += '<div class="warning-strip">! ' + lowConf.length + ' low-confidence criteria \u2014 review needed</div>';
            }
        }
    }

    // ---- Preserved load() ----

    async function load() {
        try {
            const response = await fetch('/api/sessions/' + sid + '/repositories/' + rid);
            const d = await response.json();
            if (!response.ok) throw Error(d.error);
            render(d);
        } catch (e) {
            repositoryError.hidden = false;
            repositoryError.textContent = e.message;
        }
    }

    // ---- Preserved runEvaluation() ----

    async function runEvaluation(re) {
        if (!await confirmAction((re ? 'Re-evaluate' : 'Evaluate') + ' this repository?', 'Repository evaluation')) return;
        toast('Evaluation started');
        const response = await fetch('/api/sessions/' + sid + '/repositories/' + rid + '/' + (re ? 'reevaluate' : 'evaluate'), { method: 'POST' });
        const d = await response.json();
        if (!response.ok) toast(d.error, 'error');
        else toast('Evaluation completed');
        load();
    }

    // ---- Tab switching (event delegation) ----

    document.getElementById('repositoryTabs').addEventListener('click', e => {
        if (!e.target.dataset.tab) return;
        const tabs = document.getElementById('repositoryTabs');
        tabs.querySelectorAll('button').forEach(x => x.classList.toggle('active', x === e.target));
        document.querySelectorAll('.tab-panel').forEach(x => x.classList.toggle('active', x.id === 'tab-' + e.target.dataset.tab));
    });

    // ---- Initialize ----
    load();
});
