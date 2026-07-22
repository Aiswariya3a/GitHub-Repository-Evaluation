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

    function evalConfClass(conf) {
        return conf >= 0.7 ? 'high' : conf >= 0.5 ? 'medium' : 'low';
    }

    function evalStatusIcon(conf, score, maxScore) {
        const ratio = maxScore > 0 ? score / maxScore : 0;
        if (conf < 0.5 || ratio < 0.3) return { cls: 'fail', icon: '\u2718' };
        if (conf < 0.7 || ratio < 0.6) return { cls: 'review', icon: '\u26A0' };
        return { cls: 'pass', icon: '\u2713' };
    }

    function renderCriterionRow(cr, idx) {
        const conf = Number(cr.confidence || 0);
        const confCls = cr.overridden ? 'high' : evalConfClass(conf);
        const status = cr.overridden ? { cls: 'pass', icon: '\u2713' } : evalStatusIcon(conf, Number(cr.score || 0), Number(cr.max_score || 8));
        const evItems = (cr.evidence || []);
        const evId = 'ev-' + idx;

        const evToggle = evItems.length
            ? `<span class="eval-evidence-toggle" onclick="document.getElementById('${evId}').classList.toggle('open');this.classList.toggle('open')">${evItems.length} evidence item${evItems.length > 1 ? 's' : ''}</span>`
            : '';

        const evBody = evItems.length
            ? `<div id="${evId}" class="eval-evidence-body">${evItems.map(e => {
                const lines = e.split('\n');
                const first = esc(lines[0]);
                const rest = lines.slice(1).filter(Boolean).map(l => esc(l));
                return `<div class="eval-evidence-item">${rest.length ? `<strong>${first}</strong>${rest.map(r => `<br>${r}`).join('')}` : first}</div>`;
              }).join('')}</div>`
            : '';

        const remarks = cr.remarks
            ? `<div style="grid-column:1/-1;padding:2px 0 4px 28px;font-size:.74rem;color:var(--muted);line-height:1.4">${esc(cr.remarks)}</div>`
            : '';

        return `<div class="eval-criterion">
            <span class="eval-criterion-status ${status.cls}">${status.icon}</span>
            <span class="eval-criterion-name">${esc(cr.criterion_key.replace(/_/g, ' '))}</span>
            <span class="eval-criterion-score">${Number(cr.score || 0).toFixed(1)} <span class="max">/ ${Number(cr.max_score || 8).toFixed(0)}</span></span>
            <span class="eval-criterion-conf ${confCls}">${cr.overridden ? 'Reviewed' : (conf * 100).toFixed(0) + '%'}</span>
            ${evToggle}
            ${remarks}
            ${evBody}
        </div>`;
    }

    function renderEvaluationDetailTab(evaluationResult) {
        const container = document.getElementById('evaluationContent');
        if (!container) return;
        if (!evaluationResult || !evaluationResult.criterion_results || !evaluationResult.criterion_results.length) {
            container.innerHTML = empty('No evaluation data', 'Run an evaluation to see per-criterion results.');
            const oldHero = document.getElementById('evalHero');
            if (oldHero) oldHero.remove();
            return;
        }

        const criteria = evaluationResult.criterion_results;

        const groups = {};
        criteria.forEach(cr => {
            const cat = cr.category_code || 'other';
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push(cr);
        });

        const allScores = criteria.map(cr => Number(cr.score || 0));
        const allMaxes = criteria.map(cr => Number(cr.max_score || 8));
        const totalScore = allScores.reduce((s, v) => s + v, 0);
        const totalMax = allMaxes.reduce((s, v) => s + v, 0);
        const totalPct = totalMax > 0 ? (totalScore / totalMax * 100) : 0;

        const passed = criteria.filter(cr => (Number(cr.confidence || 0) >= 0.7 || cr.overridden) && (Number(cr.score || 0) / Number(cr.max_score || 8)) >= 0.6).length;
        const needsReview = criteria.filter(cr => {
            if (cr.overridden) return false;
            const c = Number(cr.confidence || 0);
            const r = Number(cr.score || 0) / Number(cr.max_score || 8);
            return (c >= 0.5 && c < 0.7) || (r >= 0.3 && r < 0.6);
        }).length;
        const avgConf = criteria.reduce((s, cr) => s + Number(cr.confidence || 0), 0) / criteria.length;
        const grade = totalPct >= 90 ? 'A' : totalPct >= 80 ? 'B' : totalPct >= 70 ? 'C' : totalPct >= 60 ? 'D' : 'F';

        const scoreTone = totalPct >= 70 ? 'pass' : totalPct >= 45 ? 'review' : 'fail';
        const statusLabel = totalPct >= 70 ? 'Good' : totalPct >= 45 ? 'Needs review' : 'Needs attention';
        const scoreColor = scoreTone === 'pass' ? 'var(--score-pass)' : scoreTone === 'review' ? 'var(--score-needs-review)' : 'var(--score-concerning)';
        const lowConfKeys = evaluationResult.low_confidence_criteria || [];
        const lowConfCount = lowConfKeys.filter(function(k) {
            var parts = k.split('.');
            var cat = parts.length > 1 ? parts[0] : '';
            var key = parts.length > 1 ? parts[1] : k;
            return !criteria.some(function(cr) { return (cr.category_code === cat || !cat) && (cr.criterion_key === key) && cr.overridden; });
        }).length;

        // ---- Hero: render at grid level to span both columns ----
        const layout = document.querySelector('.repository-page-layout');
        const oldHero = document.getElementById('evalHero');
        if (oldHero) oldHero.remove();

        if (!layout) return;

        const heroHtml = `<div id="evalHero" class="eval-hero">
            <div class="eval-hero-heading">Evaluation Summary</div>
            <div class="eval-hero-body">
                <div class="eval-hero-metrics">
                    <div class="eval-hero-metric">
                        <span class="eval-hero-metric-label">Overall Score</span>
                        <span class="eval-hero-metric-value" style="color:${scoreColor}">${totalScore.toFixed(1)}<span class="eval-hero-metric-divider">/</span><span class="eval-hero-metric-total">${totalMax.toFixed(0)}</span></span>
                    </div>
                    <div class="eval-hero-metric">
                        <span class="eval-hero-metric-label">Grade</span>
                        <span class="eval-hero-metric-value" style="color:${scoreColor}">${grade}</span>
                    </div>
                    <div class="eval-hero-metric">
                        <span class="eval-hero-metric-label">Categories</span>
                        <span class="eval-hero-metric-value">${Object.keys(groups).length}</span>
                    </div>
                    <div class="eval-hero-metric">
                        <span class="eval-hero-metric-label">Criteria</span>
                        <span class="eval-hero-metric-value">${criteria.length}</span>
                    </div>
                    <div class="eval-hero-metric">
                        <span class="eval-hero-metric-label">Confidence</span>
                        <span class="eval-hero-metric-value">${(avgConf * 100).toFixed(0)}<span class="eval-hero-metric-pct">%</span></span>
                    </div>
                    <div class="eval-hero-metric">
                        <span class="eval-hero-metric-label">Status</span>
                        <span class="eval-hero-status-badge ${scoreTone}">${statusLabel}</span>
                    </div>
                </div>
                <div class="eval-hero-footer">
                    <span class="eval-hero-footer-item">Evaluated: ${repository.evaluated_at ? new Date(repository.evaluated_at).toLocaleDateString() : 'Never'}</span>
                    <span class="eval-hero-footer-item">Files: ${(repository.ingestion && repository.ingestion.repo_stats && repository.ingestion.repo_stats.file_count) || repository.commit_count || 0}</span>
                    <span class="eval-hero-footer-item">Manual Review: ${needsReview + lowConfCount}</span>
                    <button class="eval-hero-review-btn" data-tab="review">Review scores</button>
                </div>
                <div class="eval-hero-actions">
                    <button id="heroEvaluateButton" class="primary-btn">Re-evaluate</button>
                    <a class="secondary-btn" id="heroReportLink" href="#">Download Report</a>
                </div>
            </div>
        </div>`;

        layout.insertAdjacentHTML('afterbegin', heroHtml);

        // ---- Category sections ----
        let catIdx = 0;
        let html = '';
        for (const [catCode, items] of Object.entries(groups)) {
            const catTotal = items.reduce((sum, cr) => sum + Number(cr.score || 0), 0);
            const catMax = items.reduce((sum, cr) => sum + Number(cr.max_score || 8), 0);
            const catPct = catMax > 0 ? (catTotal / catMax * 100) : 0;
            const catConf = items.reduce((s, cr) => s + Number(cr.confidence || 0), 0) / items.length;
            const catConfCls = evalConfClass(catConf);
            const catReviewCount = items.filter(cr => {
                if (cr.overridden) return false;
                const c = Number(cr.confidence || 0);
                return c < 0.7 || cr.confidence_warning;
            }).length;
            const catId = 'cat-' + catIdx;

            const catTone = catPct >= 70 ? 'var(--emerald)' : catPct >= 45 ? 'var(--amber)' : 'var(--red)';

            const criteriaHtml = items.map((cr, i) => renderCriterionRow(cr, catIdx + '-' + i)).join('');

            html += `<article class="eval-category" id="${catId}">
                <div class="eval-category-header" onclick="document.getElementById('${catId}').classList.toggle('open')">
                    <span class="eval-category-toggle">\u25B8</span>
                    <div class="eval-category-info">
                        <span class="eval-category-code">${esc(catCode)}</span>
                        <span class="eval-category-name">${esc(catCode.replace(/^C(\d+)$/, 'Category $1'))}</span>
                        <div class="eval-category-meta">
                            <span>${items.length} criter${items.length > 1 ? 'ia' : 'ion'}</span>
                            ${catReviewCount > 0 ? `<span style="color:var(--score-needs-review)">${catReviewCount} need${catReviewCount > 1 ? '' : 's'} review</span>` : ''}
                            <div class="eval-category-progress"><span style="width:${catPct}%;background:${catTone}"></span></div>
                        </div>
                    </div>
                    <div class="eval-category-badges">
                        <span class="eval-criterion-conf ${catConfCls}" style="font-size:.7rem">${(catConf * 100).toFixed(0)}%</span>
                        <span class="eval-category-score" style="color:${catTone}">${catTotal.toFixed(1)}<span style="font-weight:400;color:var(--muted);font-size:.72rem">/${catMax.toFixed(0)}</span></span>
                    </div>
                </div>
                <div class="eval-category-body">${criteriaHtml}</div>
            </article>`;

            catIdx++;
        }

        container.innerHTML = html;
    }

    function renderCollaborationTab() {
        const container = document.getElementById('collaborationContent');
        if (!container) return;

        const gm = (repository.ingestion && repository.ingestion.github_metadata) || {};
        const insights = repository.insights || {};
        const ev = repository.evaluation_result || {};

        const contributors = (insights.contributors && insights.contributors.length)
            ? insights.contributors : (gm.contributors || []);
        const commits = (insights.commits && insights.commits.length)
            ? insights.commits : (gm.recent_commits || []);
        const prs = (insights.pull_requests && insights.pull_requests.length)
            ? insights.pull_requests : (gm.pull_requests || []);
        const issues = (insights.issues && insights.issues.length)
            ? insights.issues : (gm.issues || []);
        const collabTable = (insights.collaboration && insights.collaboration.length)
            ? insights.collaboration : [];

        const totalCommits = gm.commits_count || commits.length || 0;
        const totalContributors = contributors.length || 0;
        const isSolo = totalContributors <= 1;

        if (!totalCommits && !totalContributors && !prs.length && !issues.length) {
            container.innerHTML = empty('No collaboration data', 'GitHub metadata unavailable. Ensure GITHUB_TOKEN is configured and the repository is accessible.');
            return;
        }

        // ---- Build all sections ----
        let html = '';

        // 1. KPI row — compact stat pills with secondary metrics
        const latestCommitDate = commits.length
            ? new Date(Math.max(...commits.filter(c => c.date).map(c => new Date(c.date)))).toLocaleDateString()
            : '\u2014';
        const mergedPRs = prs.filter(p => (p.state || '').toLowerCase() === 'merged' || p.merged).length;
        const openPRs = prs.filter(p => (p.state || '').toLowerCase() === 'open').length;
        const closedIssues = issues.filter(i => (i.state || '').toLowerCase() === 'closed').length;
        const openIssues = issues.filter(i => (i.state || '').toLowerCase() === 'open').length;
        const activeContributors = contributors.filter(c => (c.contributions || 0) > 0).length;

        html += '<div class="stat-pills">' +
            '<div class="stat-pill violet"><span class="stat-pill-value">' + totalCommits + '</span><span class="stat-pill-label">Total commits</span><span class="stat-pill-sub">Latest: ' + latestCommitDate + '</span></div>' +
            '<div class="stat-pill blue"><span class="stat-pill-value">' + (prs.length || gm.pull_requests_count || 0) + '</span><span class="stat-pill-label">Pull requests</span><span class="stat-pill-sub">' + openPRs + ' open \u00B7 ' + mergedPRs + ' merged</span></div>' +
            '<div class="stat-pill green"><span class="stat-pill-value">' + (issues.length || gm.issues_count || 0) + '</span><span class="stat-pill-label">Issues</span><span class="stat-pill-sub">' + openIssues + ' open \u00B7 ' + closedIssues + ' closed</span></div>' +
            '<div class="stat-pill amber"><span class="stat-pill-value">' + totalContributors + '</span><span class="stat-pill-label">Contributors</span><span class="stat-pill-sub">' + activeContributors + ' active</span></div>' +
        '</div>';

        // 2. Contribution Balance / Equity Waterfall
        html += buildEquityWaterfall(contributors, totalCommits, isSolo);

        // 3. Contributor Cards
        html += buildContributorCards(contributors, commits, prs, totalCommits, isSolo);

        // 4. Collaboration Timeline
        html += buildTimeline(commits, contributors, isSolo);

        // 5. Collaboration Network (multi-contributor only)
        if (!isSolo) html += buildNetwork(contributors, commits);

        // 6. Code Review Participation
        html += buildReviewSection(prs, contributors, isSolo);

        // 7. Collaboration Health Score
        html += buildHealthScore(contributors, commits, prs, collabTable, isSolo);

        // 8. AI Collaboration Summary
        const collabAgent = ev.collaboration || {};
        if (collabAgent.summary) {
            html += '<article class="panel collaboration-summary"><div class="panel-header"><div><p class="eyebrow">AI Assessment</p><h2>Collaboration summary</h2></div></div>' +
                '<div class="ai-summary-body"><p>' + esc(collabAgent.summary) + '</p></div></article>';
        }

        container.innerHTML = html;
    }

    // ------------------------------------------------------------------
    //   Section: Equity Waterfall (Contribution Balance)
    // ------------------------------------------------------------------
    function buildEquityWaterfall(contributors, totalCommits, isSolo) {
        if (!contributors.length) return '';
        const totalContribs = contributors.reduce((s, c) => s + (c.contributions || 0), 0) || totalCommits;
        const bars = contributors.map(c => {
            const val = c.contributions || 0;
            const pct = totalContribs > 0 ? (val / totalContribs * 100) : 0;
            const flag = pct > 0 && pct < 10 ? '<span class="freeride-flag" title="Contributor made less than 10% of total work">&#9888; under 10%</span>' : '';
            return { name: c.login || c.author || c.name || 'Unknown', pct, val, flag };
        }).sort((a, b) => b.pct - a.pct);

        const gini = computeGini(bars.map(b => b.val));
        const giniLabel = gini > 0.4 ? 'high' : gini > 0.25 ? 'moderate' : 'low';
        const giniBadge = `<span class="gini-badge gini-${giniLabel}">Gini: ${gini.toFixed(2)}</span>`;

        const barHtml = bars.map(b => `
            <div class="equity-row">
                <span class="equity-name">${esc(b.name)}${b.flag}</span>
                <div class="equity-bar-track">
                    <div class="equity-bar-fill" style="width:${b.pct}%"></div>
                </div>
                <span class="equity-pct">${b.pct.toFixed(1)}%</span>
            </div>
        `).join('');

        const soloNote = isSolo ? '<p class="collab-note">Solo project \u2014 single contributor, full ownership.</p>' : '';
        const warning = gini > 0.4 ? '<div class="warning-strip">! High inequality (Gini > 0.4) \u2014 workload may be unbalanced</div>' : '';

        return '<article class="panel"><div class="panel-header"><div><p class="eyebrow">Work distribution</p><h2>Contribution equity</h2></div>' + giniBadge + '</div>' +
            soloNote + warning +
            '<div class="equity-chart">' + barHtml + '</div></article>';
    }

    function computeGini(values) {
        if (!values.length) return 0;
        const sorted = values.slice().sort((a, b) => a - b);
        const n = sorted.length;
        const sum = sorted.reduce((s, v) => s + v, 0);
        if (sum === 0) return 0;
        let cum = 0;
        for (let i = 0; i < n; i++) cum += sorted[i] * (i + 1);
        return ((2 * cum) / (n * sum)) - ((n + 1) / n);
    }

    // ------------------------------------------------------------------
    //   Section: Contributor Cards
    // ------------------------------------------------------------------
    function buildContributorCards(contributors, commits, prs, totalCommits, isSolo) {
        if (!contributors.length && !commits.length) return '';

        const cards = contributors.length ? contributors.map(c => {
            const name = c.login || c.author || c.name || 'Unknown';
            const contribs = c.contributions || 0;
            const pct = totalCommits > 0 ? (contribs / totalCommits * 100) : 0;

            const byAuthor = commits.filter(cm => (cm.author || '').toLowerCase() === name.toLowerCase());
            const commitDates = byAuthor.map(cm => cm.date).filter(Boolean).map(d => new Date(d));
            const uniqueDays = new Set(commitDates.map(d => d.toDateString())).size;
            const recentDate = commitDates.length ? commitDates.sort((a, b) => b - a)[0] : null;

            const reviewed = prs.filter(p => (p.reviewer || '').toLowerCase() === name.toLowerCase()).length;
            const authored = prs.filter(p => (p.author || '').toLowerCase() === name.toLowerCase()).length;

            const density = uniqueDays > 0
                ? `<span class="contrib-density">Active ${uniqueDays} day${uniqueDays > 1 ? 's' : ''}</span>`
                : '';
            const lastActive = recentDate ? `<span class="contrib-last">Last: ${recentDate.toLocaleDateString()}</span>` : '';

            const spark = buildSparkline(commitDates);

            return `<article class="contrib-card">
                <div class="contrib-card-head">
                    <span class="contrib-avatar">${esc(name[0] || '?').toUpperCase()}</span>
                    <div>
                        <strong>${esc(name)}</strong>
                        <div class="contrib-meta">${density} ${lastActive}</div>
                    </div>
                    <span class="contrib-pct">${pct.toFixed(0)}%</span>
                </div>
                ${spark}
                <div class="contrib-stats">
                    <div><span>Commits</span><strong>${byAuthor.length || contribs}</strong></div>
                    <div><span>PRs authored</span><strong>${authored}</strong></div>
                    <div><span>PRs reviewed</span><strong>${reviewed}</strong></div>
                </div>
            </article>`;
        }).join('') : '';

        const soloMsg = isSolo && !contributors.length
            ? '<p class="collab-note">Solo project \u2014 all work attributed to the repository owner.</p>'
            : '';

        return '<article class="panel contrib-card-grid-wrapper"><div class="panel-header"><div><p class="eyebrow">Individual contribution</p><h2>Contributor profiles</h2></div></div>' +
            soloMsg +
            '<div class="contrib-card-grid">' + (cards || '<div class="polished-empty compact"><strong>No contributor data</strong><p>Contributor information not available for this repository.</p></div>') + '</div></article>';
    }

    function buildSparkline(dates) {
        if (!dates.length) return '<div class="contrib-spark"><span class="spark-empty">\u2014</span></div>';
        const dayBuckets = {};
        dates.forEach(d => { const k = d.toDateString(); dayBuckets[k] = (dayBuckets[k] || 0) + 1; });
        const counts = Object.values(dayBuckets);
        const max = Math.max(...counts, 1);
        const bars = counts.slice(-14).map(c => `<b style="height:${(c / max * 100).toFixed(0)}%"></b>`).join('');
        return '<div class="contrib-spark"><div class="sparkline">' + bars + '</div></div>';
    }

    // ------------------------------------------------------------------
    //   Section: Collaboration Timeline
    // ------------------------------------------------------------------
    function buildTimeline(commits, contributors, isSolo) {
        if (!commits.length) return '';

        const byDate = {};
        commits.forEach(c => {
            if (!c.date) return;
            const d = new Date(c.date).toDateString();
            if (!byDate[d]) byDate[d] = [];
            byDate[d].push(c);
        });

        const dates = Object.keys(byDate).sort((a, b) => new Date(a) - new Date(b));
        if (!dates.length) return '';

        const maxPerDay = Math.max(...dates.map(d => byDate[d].length), 1);
        const totalDays = dates.length;

        const byAuthor = {};
        contributors.forEach(c => { byAuthor[(c.login || c.author || c.name || '').toLowerCase()] = c; });
        const authorColors = ['#6366f1', 'var(--emerald)', 'var(--amber)', 'var(--red)', 'var(--blue)', '#a78bfa', '#f472b6', '#34d399'];
        let colorIdx = 0;
        const authorColorMap = {};
        contributors.forEach(c => {
            const key = (c.login || c.author || c.name || '').toLowerCase();
            if (key && !authorColorMap[key]) authorColorMap[key] = authorColors[colorIdx++ % authorColors.length];
        });

        const authorBands = contributors.map(c => {
            const key = (c.login || c.author || c.name || '').toLowerCase();
            const color = authorColorMap[key] || '#6366f1';
            const authorDates = commits.filter(cm => (cm.author || '').toLowerCase() === key).map(cm => new Date(cm.date).toDateString());
            const activeSet = new Set(authorDates);
            const band = dates.map(d => activeSet.has(d) ? 1 : 0);
            return { name: c.login || c.author || c.name || 'Unknown', color, band };
        });

        const ganttHtml = authorBands.map(a => `
            <div class="timeline-band-row">
                <span class="timeline-band-label" style="color:${a.color}">${esc(a.name)}</span>
                <div class="timeline-band-track">${a.band.map(active => `<span class="${active ? 'band-active' : 'band-empty'}" style="${active ? `background:${a.color}` : ''}"></span>`).join('')}</div>
            </div>
        `).join('');

        const activityBars = dates.map(d => {
            const count = byDate[d].length;
            const height = Math.max(4, (count / maxPerDay) * 38);
            return `<span class="timeline-activity-bar" style="height:${height}px;background:#818cf8;opacity:${0.3 + (count / maxPerDay) * 0.7}" title="${d}: ${count} commit${count > 1 ? 's' : ''}"></span>`;
        }).join('');

        const hasActivity = dates.length > 1
            ? '<div class="timeline-activity-bars">' + activityBars + '</div>'
            : '';

        const heatmap = dates.slice(-30).map(d => {
            const count = byDate[d].length;
            const intensity = Math.min(1, count / maxPerDay);
            const hue = 240 - (intensity * 200);
            return `<span class="heat-cell" style="background:hsla(${hue}, 70%, 50%, ${0.15 + intensity * 0.6})" title="${d}: ${count} commit${count > 1 ? 's' : ''}"></span>`;
        }).join('');

        const lastMinute = detectLastMinute(commits);
        const lastMinuteWarning = lastMinute
            ? `<div class="warning-strip">! ${lastMinute.pct}% of commits in final ${lastMinute.days} day${lastMinute.days > 1 ? 's' : ''} before deadline</div>`
            : '';

        return '<article class="panel"><div class="panel-header"><div><p class="eyebrow">Activity distribution</p><h2>Collaboration timeline</h2></div><span class="badge-muted">' + totalDays + ' active days</span></div>' +
            lastMinuteWarning +
            '<div class="timeline-gantt">' + ganttHtml + '</div>' +
            hasActivity +
            '<div class="timeline-heatmap"><span class="heat-label">Activity</span><div class="heat-track">' + heatmap + '</div></div></article>';
    }

    function detectLastMinute(commits) {
        const dated = commits.filter(c => c.date).map(c => ({ ...c, d: new Date(c.date) }));
        if (dated.length < 3) return null;
        const sorted = dated.sort((a, b) => a.d - b.d);
        const first = sorted[0].d;
        const last = sorted[sorted.length - 1].d;
        const span = (last - first) / (1000 * 60 * 60 * 24);
        if (span < 3) return null;
        const threshold = new Date(last.getTime() - 4 * 24 * 60 * 60 * 1000);
        const lastMin = sorted.filter(c => c.d >= threshold);
        const pct = Math.round(lastMin.length / sorted.length * 100);
        return pct > 40 ? { pct, days: Math.round((last - threshold) / (1000 * 60 * 60 * 24)) } : null;
    }

    // ------------------------------------------------------------------
    //   Section: Collaboration Network
    // ------------------------------------------------------------------
    function buildNetwork(contributors, commits) {
        if (contributors.length < 2) return '';

        const edges = [];
        const byAuthor = {};
        const fileAuthorSets = {};
        commits.forEach(c => {
            const author = (c.author || '').toLowerCase();
            if (!author) return;
            byAuthor[author] = (byAuthor[author] || 0) + 1;
            const files = c.files || [];
            files.forEach(f => {
                if (!fileAuthorSets[f]) fileAuthorSets[f] = new Set();
                fileAuthorSets[f].add(author);
            });
        });

        Object.values(fileAuthorSets).forEach(authors => {
            const arr = Array.from(authors);
            for (let i = 0; i < arr.length; i++) {
                for (let j = i + 1; j < arr.length; j++) {
                    const key = [arr[i], arr[j]].sort().join('::');
                    edges[key] = (edges[key] || 0) + 1;
                }
            }
        });

        const maxEdge = Math.max(...Object.values(edges), 1);
        const nodes = contributors.map(c => {
            const key = (c.login || c.author || c.name || '').toLowerCase();
            return { name: c.login || c.author || c.name || 'Unknown', weight: byAuthor[key] || c.contributions || 1, key };
        }).sort((a, b) => b.weight - a.weight);

        const edgeList = Object.entries(edges).filter(([, w]) => w > 0).sort((a, b) => b[1] - a[1]).slice(0, 15);

        const maxW = Math.max(...nodes.map(n => n.weight), 1);
        const center = nodes[0];

        const isolated = nodes.filter(n => {
            const k = n.key;
            return !edgeList.some(([key]) => key.includes(k));
        });

        const orbitHtml = nodes.map((n, i) => {
            const size = 20 + (n.weight / maxW) * 40;
            const angle = (i / nodes.length) * 360;
            const r = 60 + (n.weight / maxW) * 30;
            const isCenter = i === 0;
            if (isCenter) return '';
            const rad = angle * Math.PI / 180;
            const x = 150 + r * Math.cos(rad);
            const y = 100 + r * Math.sin(rad);
            return `<div class="network-node" style="left:${x - size / 2}px;top:${y - size / 2}px;width:${size}px;height:${size}px;background:#6366f1;font-size:${Math.max(8, size * 0.32)}px" title="${esc(n.name)} (${n.weight} commits)">${esc(n.name[0] || '?').toUpperCase()}</div>`;
        }).join('');

        const centerSize = 30 + (center.weight / maxW) * 40;
        const centerNode = `<div class="network-node network-center" style="left:${150 - centerSize / 2}px;top:${100 - centerSize / 2}px;width:${centerSize}px;height:${centerSize}px;font-size:${Math.max(10, centerSize * 0.32)}px" title="${esc(center.name)} (${center.weight} commits)">${esc(center.name[0] || '?').toUpperCase()}</div>`;

        const isolatedMsg = isolated.length > 1
            ? `<div class="warning-strip">! ${isolated.length - 1} contributor${isolated.length > 2 ? 's' : ''} isolated \u2014 connected only through ${esc(center.name)}</div>`
            : '';

        return '<article class="panel"><div class="panel-header"><div><p class="eyebrow">Team structure</p><h2>Collaboration network</h2></div></div>' +
            isolatedMsg +
            '<div class="network-canvas" style="height:220px;position:relative">' + centerNode + orbitHtml + '</div>' +
            '<div class="network-legend"><span class="legend-dot" style="background:#6366f1"></span> Contributors <span class="legend-sep">|</span> Larger node = more commits</div></article>';
    }

    // ------------------------------------------------------------------
    //   Section: Code Review Participation
    // ------------------------------------------------------------------
    function buildReviewSection(prs, contributors, isSolo) {
        if (!prs.length) {
            return isSolo
                ? '<article class="panel"><div class="panel-header"><div><p class="eyebrow">Peer review</p><h2>Code review participation</h2></div></div><p class="collab-note">No pull request data \u2014 solo project or direct-push workflow used.</p></article>'
                : '<article class="panel"><div class="panel-header"><div><p class="eyebrow">Peer review</p><h2>Code review participation</h2></div></div><p class="collab-note">No pull requests found \u2014 team may use direct-push workflow.</p></article>';
        }

        const reviewerCounts = {};
        const authorCounts = {};
        const reviewComments = {};
        let totalReviewed = 0;

        prs.forEach(p => {
            const author = (p.author || '').toLowerCase();
            if (author) authorCounts[author] = (authorCounts[author] || 0) + 1;
            const reviewer = (p.reviewer || '').toLowerCase();
            if (reviewer) {
                reviewerCounts[reviewer] = (reviewerCounts[reviewer] || 0) + 1;
                totalReviewed++;
            }
            const comments = p.comments || p.review_comments || 0;
            if (reviewer) reviewComments[reviewer] = (reviewComments[reviewer] || 0) + comments;
        });

        const allNames = new Set([...Object.keys(authorCounts), ...Object.keys(reviewerCounts), ...contributors.map(c => (c.login || c.author || c.name || '').toLowerCase()).filter(Boolean)]);
        const reviewRate = prs.length > 0 ? Math.round(totalReviewed / prs.length * 100) : 0;

        const tableRows = Array.from(allNames).filter(Boolean).map(name => {
            const authored = authorCounts[name] || 0;
            const reviewed = reviewerCounts[name] || 0;
            const comments = reviewComments[name] || 0;
            const commentsPerReview = reviewed > 0 ? (comments / reviewed).toFixed(1) : '\u2014';
            const shallow = reviewed > 0 && comments / reviewed < 1;
            return `<div class="review-row">
                <span class="review-author">${esc(name.charAt(0).toUpperCase() + name.slice(1))}</span>
                <span>${authored}</span>
                <span>${reviewed}</span>
                <span class="${shallow ? 'review-shallow' : ''}">${commentsPerReview}${shallow ? ' &#9888;' : ''}</span>
            </div>`;
        }).join('');

        const reviewWarning = reviewRate < 60
            ? `<div class="warning-strip">! Review rate ${reviewRate}% \u2014 ${prs.length - totalReviewed} PRs merged without review</div>`
            : '';

        return '<article class="panel"><div class="panel-header"><div><p class="eyebrow">Peer review</p><h2>Code review participation</h2></div><span class="badge-muted">' + reviewRate + '% review rate</span></div>' +
            reviewWarning +
            '<div class="review-grid"><div class="review-header"><span>Contributor</span><span>Authored</span><span>Reviewed</span><span>Comments/PR</span></div>' + tableRows + '</div></article>';
    }

    // ------------------------------------------------------------------
    //   Section: Collaboration Health Score
    // ------------------------------------------------------------------
    function buildHealthScore(contributors, commits, prs, collabTable, isSolo) {
        const totalContribs = contributors.reduce((s, c) => s + (c.contributions || 0), 0) || 1;
        const gini = computeGini(contributors.map(c => c.contributions || 0));

        const balanceScore = Math.round((1 - Math.min(1, gini * 2.5)) * 100);
        const prReviewRate = prs.length > 0 ? Math.round(prs.filter(p => (p.reviewer || p.reviewers || '').length > 0).length / prs.length * 100) : (isSolo ? 100 : 0);
        const reviewScore = isSolo ? 100 : Math.round(prReviewRate * 0.6 + 40);
        const maxContribPct = contributors.length > 0 ? Math.max(...contributors.map(c => (c.contributions || 0))) / totalContribs : 0;
        const busFactorScore = Math.round((1 - Math.min(1, maxContribPct * 1.5)) * 100);
        const overlapScore = computeOverlapScore(commits, contributors);
        const consistencyScore = computeConsistencyScore(commits);

        const factors = [
            { label: 'Balance', score: balanceScore, desc: balanceScore > 70 ? 'Good' : balanceScore > 40 ? 'Needs review' : 'Uneven' },
            { label: 'Reviews', score: reviewScore, desc: reviewScore > 70 ? 'Good' : reviewScore > 40 ? 'Needs' : 'Low' },
            { label: 'Overlap', score: overlapScore, desc: overlapScore > 70 ? 'Great' : overlapScore > 40 ? 'Moderate' : 'Siloed' },
            { label: 'Consistency', score: consistencyScore, desc: consistencyScore > 70 ? 'Steady' : consistencyScore > 40 ? 'Bursty' : 'Last-minute' },
            { label: 'Bus factor', score: busFactorScore, desc: busFactorScore > 70 ? 'Distributed' : busFactorScore > 40 ? 'Concentrated' : 'Single-owner' },
        ];

        const total = factors.reduce((s, f) => s + f.score, 0);
        const health = Math.round(total / factors.length);

        const barHtml = factors.map(f => {
            const fillClass = f.score >= 70 ? 'fill-success' : f.score >= 45 ? 'fill-warning' : 'fill-danger';
            const textClass = f.score >= 70 ? 'text-success' : f.score >= 45 ? 'text-warning' : 'text-danger';
            return `<div class="health-factor">
                <span class="health-factor-label">${f.label}</span>
                <div class="health-factor-track"><div class="health-factor-fill ${fillClass}" style="width:${f.score}%"></div></div>
                <span class="health-factor-score ${textClass}">${f.score}</span>
                <span class="health-factor-desc">${f.desc}</span>
            </div>`;
        }).join('');

        const badgeClass = health >= 70 ? 'health-badge-good' : health >= 45 ? 'health-badge-warning' : 'health-badge-danger';
        return '<article class="panel"><div class="panel-header"><div><p class="eyebrow">Overall assessment</p><h2>Collaboration health</h2></div><span class="health-total-badge ' + badgeClass + '">' + health + '/100</span></div>' +
            '<div class="health-factors">' + barHtml + '</div></article>';
    }

    function computeOverlapScore(commits, contributors) {
        if (!commits.length || contributors.length < 2) return 100;
        const byDay = {};
        commits.filter(c => c.date).forEach(c => {
            const d = new Date(c.date).toDateString();
            if (!byDay[d]) byDay[d] = new Set();
            byDay[d].add((c.author || '').toLowerCase());
        });
        const days = Object.values(byDay);
        const multiAuthorDays = days.filter(s => s.size >= 2).length;
        return days.length > 0 ? Math.round(multiAuthorDays / days.length * 100) : 50;
    }

    function computeConsistencyScore(commits) {
        const dated = commits.filter(c => c.date).map(c => new Date(c.date));
        if (dated.length < 3) return 100;
        const sorted = dated.sort((a, b) => a - b);
        const span = (sorted[sorted.length - 1] - sorted[0]) / (1000 * 60 * 60 * 24);
        if (span < 2) return 30;
        const perDay = sorted.length / (span + 1);
        const lastThird = new Date(sorted[sorted.length - 1].getTime() - span / 3 * 24 * 60 * 60 * 1000);
        const lastThirdCount = sorted.filter(d => d >= lastThird).length;
        const lastThirdRatio = lastThirdCount / sorted.length;
        const penalty = Math.max(0, (lastThirdRatio - 0.4) * 100);
        const consistency = Math.round(Math.min(100, Math.max(0, 90 - penalty)));
        return consistency;
    }

    // ------------------------------------------------------------------
    //   Code Quality Tab — AI Assessment Report
    // ------------------------------------------------------------------

    // Plain-language labels for known rubric category codes.
    // Falls back to the code itself when a category is not in this map
    // (staff can define arbitrary category codes).
    const KNOWN_CATEGORIES = {
        C1: { label: 'Project Organization', desc: 'Structure, file layout, and project conventions' },
        C2: { label: 'Documentation Quality', desc: 'README, inline comments, and explanatory content' },
        C3: { label: 'Code Clarity', desc: 'Readability, naming, and how easy the code is to follow' },
        C4: { label: 'Testing Practices', desc: 'Test coverage, test structure, and quality assurance' },
        C5: { label: 'Maintainability', desc: 'Modularity, extensibility, and long-term upkeep' },
    };

    function getCategoryInfo(code) {
        return KNOWN_CATEGORIES[code] || { label: code.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), desc: '' };
    }

    // Plain-language labels for internal rubric criterion keys
    const CRITERION_LABELS = {
        repository_structure: 'Project layout & conventions',
        coding_standards: 'Code style & consistency',
        modularity: 'Modular design',
        readability: 'Code readability',
        documentation_quality: 'Documentation completeness',
        readme_quality: 'README quality',
        project_scope: 'Project scope & ambition',
        testing_quality: 'Test coverage & quality',
        code_organization: 'Code organization',
        error_handling: 'Error handling',
        naming_conventions: 'Naming conventions',
        code_commenting: 'Code commenting',
    };

    function getCriterionLabel(key) {
        return CRITERION_LABELS[key] || key.replace(/_/g, ' ');
    }

    function classifyScore(score, maxScore) {
        const pct = maxScore > 0 ? score / maxScore : 0;
        if (pct >= 0.8) return { tone: 'strong', label: 'Strong', color: 'var(--score-strong)' };
        if (pct >= 0.6) return { tone: 'satisfactory', label: 'Satisfactory', color: 'var(--score-satisfactory)' };
        if (pct >= 0.4) return { tone: 'needs-work', label: 'Needs work', color: 'var(--score-needs-review)' };
        return { tone: 'concerning', label: 'Concerning', color: 'var(--score-concerning)' };
    }

    function assessConfidence(conf) {
        return conf >= 0.7 ? 'High' : conf >= 0.5 ? 'Medium' : 'Low';
    }

    function renderOverviewTab(r, ev, er, criteria) {
        const container = document.getElementById('overviewContent');
        if (!container) return;

        if (!criteria || !criteria.length) {
            container.innerHTML = empty('No assessment data', repository.status === 'Completed' ? 'Evaluation results are not available.' : 'Run an evaluation to generate an assessment.');
            return;
        }

        const allScores = criteria.map(cr => Number(cr.score || 0));
        const allMaxes = criteria.map(cr => Number(cr.max_score || 8));
        const totalScore = allScores.reduce((s, v) => s + v, 0);
        const totalMax = allMaxes.reduce((s, v) => s + v, 0);
        const totalPct = totalMax > 0 ? (totalScore / totalMax * 100) : 0;
        const overallTone = classifyScore(totalScore, totalMax);
        const grade = totalPct >= 90 ? 'A' : totalPct >= 80 ? 'B' : totalPct >= 70 ? 'C' : totalPct >= 60 ? 'D' : 'F';
        const avgConf = criteria.reduce((s, cr) => s + Number(cr.confidence || 0), 0) / criteria.length;
        const lowConfCount = criteria.filter(cr => Number(cr.confidence || 0) < 0.5 && !cr.overridden).length;
        const needsReview = criteria.filter(cr => Number(cr.confidence || 0) < 0.7 && !cr.overridden).length;
        const overallRemarks = er.overall_remarks || '';

        const sorted = criteria.slice().sort((a, b) => {
            const ap = a.max_score > 0 ? Number(a.score) / Number(a.max_score) : 0;
            const bp = b.max_score > 0 ? Number(b.score) / Number(b.max_score) : 0;
            return bp - ap;
        });
        const strengths = sorted.filter(c => c.max_score > 0 && Number(c.score) / Number(c.max_score) >= 0.7);
        const concerns = sorted.filter(c => c.max_score > 0 && Number(c.score) / Number(c.max_score) < 0.5);

        const scoreColor = overallTone.tone === 'strong' ? 'var(--score-strong)'
            : overallTone.tone === 'satisfactory' ? 'var(--score-satisfactory)'
            : overallTone.tone === 'needs-work' ? 'var(--score-needs-review)' : 'var(--score-concerning)';

        let html = '';

        // ================================================================
        // 1. Executive Summary
        // ================================================================
        const verdict = totalPct >= 70
            ? 'This submission demonstrates a satisfactory level of quality across the evaluated dimensions. The project meets expected standards and is generally well-constructed.'
            : totalPct >= 45
            ? 'This submission shows potential but has several areas that would benefit from focused improvement before final evaluation.'
            : 'This submission needs significant attention across multiple quality dimensions. Substantial revisions are recommended.';

        html += '<article class="ai-section">';
        html += '<div class="ai-section-header"><h2>Executive Summary</h2></div>';
        html += '<p class="ai-summary-text" style="font-size:.95rem">' + verdict + ' The evaluation identified ' + strengths.length + ' ' + (strengths.length === 1 ? 'strength' : 'strengths') + ' and ' + concerns.length + ' ' + (concerns.length === 1 ? 'area' : 'areas') + ' for improvement.</p>';
        html += '<div class="ai-verdict-row">';
        var vChips = [
            { label: 'Overall', value: overallTone.label, color: scoreColor },
            { label: 'Grade', value: grade, color: totalPct >= 70 ? 'var(--score-strong)' : totalPct >= 45 ? 'var(--score-needs-review)' : 'var(--score-concerning)' },
            { label: 'Confidence', value: assessConfidence(avgConf), color: avgConf >= 0.7 ? 'var(--score-strong)' : avgConf >= 0.5 ? 'var(--score-needs-review)' : 'var(--score-concerning)' },
        ];
        if (needsReview > 0) vChips.push({ label: 'Review needed', value: needsReview + ' item' + (needsReview > 1 ? 's' : ''), color: 'var(--score-concerning)' });
        vChips.forEach(function (v) {
            html += '<span class="ai-verdict-chip"><span class="ai-verdict-dot" style="background:' + v.color + '"></span>' + esc(v.label) + ': <strong>' + esc(v.value) + '</strong></span>';
        });
        html += '</div></article>';

        // ================================================================
        // 2. Overall Assessment — Hero
        // ================================================================
        html += '<article class="ov-assessment">';
        html += '<div class="ov-assessment-grade" style="color:' + scoreColor + '">' + grade + '</div>';
        html += '<div class="ov-assessment-score"><span style="color:' + scoreColor + '">' + totalScore.toFixed(1) + '</span><span class="ov-assessment-max">/' + totalMax.toFixed(0) + '</span></div>';
        html += '<div class="ov-assessment-bar"><div class="ov-assessment-bar-fill" style="width:' + totalPct + '%;background:' + scoreColor + '"></div></div>';
        html += '<div class="ov-assessment-meta">';
        html += '<span>Evaluated: ' + (r.evaluated_at ? new Date(r.evaluated_at).toLocaleDateString() : 'Never') + '</span>';
        html += '<span>Status: ' + esc(r.status || 'Unknown') + '</span>';
        if (needsReview > 0) html += '<span class="ov-review-flag">Manual review recommended</span>';
        html += '</div>';
        html += '<div class="ov-nav-row">';
        html += '<button class="ov-nav-chip" data-tab="evaluation">View full evaluation breakdown \u2192</button>';
        html += '<button class="ov-nav-chip secondary" data-tab="review">Review &amp; override scores \u2192</button>';
        html += '</div>';
        html += '</article>';

        // ================================================================
        // 3. Key Strengths — preview with navigation to Code Quality
        // ================================================================
        html += '<article class="ai-section"><div class="ai-section-header"><h2>Key Strengths</h2></div>';
        if (strengths.length) {
            html += '<div class="ai-card-grid">';
            strengths.slice(0, 3).forEach(function (cr) {
                var dim = getCategoryInfo(cr.category_code) || { label: cr.category_code, desc: '' };
                html += '<div class="ai-strength-card">';
                html += '<div class="ai-strength-head"><div><span class="ai-strength-dim">' + esc(dim.label) + '</span><span class="ai-strength-criterion">' + esc(getCriterionLabel(cr.criterion_key)) + '</span></div></div>';
                html += '<div class="ai-strength-score"><span style="color:var(--score-strong)">' + Number(cr.score).toFixed(1) + '/' + Number(cr.max_score || 8).toFixed(0) + '</span><span class="ai-strength-pct">' + (cr.max_score > 0 ? (Number(cr.score) / Number(cr.max_score) * 100).toFixed(0) : 0) + '%</span></div>';
                if (cr.remarks) html += '<p class="ai-strength-remark">' + esc(cr.remarks) + '</p>';
                html += '</div>';
            });
            html += '</div>';
            if (strengths.length > 3) {
                html += '<p class="ov-nav-hint">+' + (strengths.length - 3) + ' more strength' + (strengths.length - 3 === 1 ? '' : 's') + '. <button class="ov-nav-link" data-tab="quality">See full assessment in Code Quality \u2192</button></p>';
            } else {
                html += '<p class="ov-nav-hint"><button class="ov-nav-link" data-tab="quality">View detailed assessment in Code Quality \u2192</button></p>';
            }
        } else {
            html += '<div class="ai-empty-section"><p>No criteria scored above 70%.</p></div>';
        }
        html += '</article>';

        // ================================================================
        // 4. Areas for Improvement — preview with navigation
        // ================================================================
        html += '<article class="ai-section"><div class="ai-section-header"><h2>Areas for Improvement</h2></div>';
        if (concerns.length) {
            html += '<div class="ai-card-grid">';
            concerns.slice(0, 3).forEach(function (cr) {
                var dim = getCategoryInfo(cr.category_code) || { label: cr.category_code, desc: '' };
                var lowConf = Number(cr.confidence || 0) < 0.5;
                html += '<div class="ai-concern-card' + (lowConf ? ' needs-review' : '') + '">';
                html += '<div class="ai-concern-head"><div><span class="ai-concern-dim">' + esc(dim.label) + '</span><span class="ai-concern-criterion">' + esc(getCriterionLabel(cr.criterion_key)) + '</span></div></div>';
                html += '<div class="ai-concern-score"><span style="color:var(--score-concerning)">' + Number(cr.score).toFixed(1) + '/' + Number(cr.max_score || 8).toFixed(0) + '</span><span class="ai-concern-pct">' + (cr.max_score > 0 ? (Number(cr.score) / Number(cr.max_score) * 100).toFixed(0) : 0) + '%</span></div>';
                if (cr.remarks) html += '<p class="ai-concern-remark">' + esc(cr.remarks) + '</p>';
                if (lowConf && !cr.overridden) html += '<span class="ai-needs-review-badge">Needs manual review</span>';
                html += '</div>';
            });
            html += '</div>';
            if (concerns.length > 3) {
                html += '<p class="ov-nav-hint">+' + (concerns.length - 3) + ' more area' + (concerns.length - 3 === 1 ? '' : 's') + '. <button class="ov-nav-link" data-tab="evaluation">See all scores in Evaluation Detail \u2192</button></p>';
            } else {
                html += '<p class="ov-nav-hint"><button class="ov-nav-link" data-tab="evaluation">View per-criterion breakdown in Evaluation Detail \u2192</button></p>';
            }
        } else {
            html += '<div class="ai-empty-section success"><p>All criteria scored at or above 50%. No critical concerns detected.</p></div>';
        }
        html += '</article>';

        // ================================================================
        // 5. Recommendations (top 3-5)
        // ================================================================
        if (overallRemarks || concerns.length) {
            html += '<article class="ai-section"><div class="ai-section-header"><h2>Recommendations</h2></div>';
            if (overallRemarks) {
                html += '<div class="ai-recommendation-card"><div class="ai-rec-num">01</div><div><p class="ai-rec-text">' + esc(overallRemarks) + '</p></div></div>';
            }
            if (concerns.length) {
                html += '<div class="ai-rec-context"><p>Based on the evaluation, prioritize improving these areas:</p></div>';
                concerns.slice(0, 3).forEach(function (cr, i) {
                    var dim = getCategoryInfo(cr.category_code) || { label: cr.category_code, desc: '' };
                    var label = getCriterionLabel(cr.criterion_key);
                    var suggestion = cr.remarks || 'Review and improve the ' + label.toLowerCase() + ' aspect.';
                    var num = overallRemarks ? (i + 2) : (i + 1);
                    html += '<div class="ai-recommendation-card"><div class="ai-rec-num">0' + num + '</div><div><span class="ai-rec-dim">' + esc(dim.label) + '</span><p class="ai-rec-text">' + esc(suggestion) + '</p></div></div>';
                });
            }
            html += '</article>';
        }

        container.innerHTML = html;
    }

    function renderCodeQualityTab(ev, er, criteria) {
        const container = document.getElementById('qualityContent');
        if (!container) return;

        if (!criteria || !criteria.length) {
            const note = repository && repository.status !== 'Completed'
                ? 'Run evaluation to generate metrics.'
                : 'Evaluation failed. Check errors and retry.';
            container.innerHTML = empty('No assessment data', note);
            return;
        }

        // ---- Calculate overall stats ----
        const allScores = criteria.map(cr => Number(cr.score || 0));
        const allMaxes = criteria.map(cr => Number(cr.max_score || 8));
        const totalScore = allScores.reduce((s, v) => s + v, 0);
        const totalMax = allMaxes.reduce((s, v) => s + v, 0);
        const totalPct = totalMax > 0 ? (totalScore / totalMax * 100) : 0;
        const overallTone = classifyScore(totalScore, totalMax);
        const grade = totalPct >= 90 ? 'A' : totalPct >= 80 ? 'B' : totalPct >= 70 ? 'C' : totalPct >= 60 ? 'D' : 'F';
        const avgConf = criteria.reduce((s, cr) => s + Number(cr.confidence || 0), 0) / criteria.length;
        const lowConfCount = criteria.filter(cr => Number(cr.confidence || 0) < 0.5 && !cr.overridden).length;

        // Group criteria by category
        const groups = {};
        criteria.forEach(cr => {
            const cat = cr.category_code || 'other';
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push(cr);
        });

        // Identify strengths (top-scoring criteria) and concerns (bottom-scoring)
        const sorted = criteria.slice().sort((a, b) => {
            const ap = a.max_score > 0 ? Number(a.score) / Number(a.max_score) : 0;
            const bp = b.max_score > 0 ? Number(b.score) / Number(b.max_score) : 0;
            return bp - ap;
        });
        const strengths = sorted.filter(c => c.max_score > 0 && Number(c.score) / Number(c.max_score) >= 0.7);
        const concerns = sorted.filter(c => c.max_score > 0 && Number(c.score) / Number(c.max_score) < 0.5);

        // Score color
        const scoreColor = overallTone.tone === 'strong' ? 'var(--score-strong)'
            : overallTone.tone === 'satisfactory' ? 'var(--score-satisfactory)'
            : overallTone.tone === 'needs-work' ? 'var(--score-needs-review)' : 'var(--score-concerning)';

        const gradeColor = totalPct >= 70 ? 'var(--score-strong)' : totalPct >= 45 ? 'var(--score-needs-review)' : 'var(--score-concerning)';

        let html = '';

        // ================================================================
        // 2. Executive Summary
        // ================================================================
        const verdict = totalPct >= 70 ? 'This project demonstrates a satisfactory level of quality across the evaluated dimensions.'
            : totalPct >= 45 ? 'This project shows potential but has several areas that would benefit from focused improvement.'
            : 'This project needs significant attention across multiple quality dimensions.';

        const strengthCount = strengths.length;
        const concernCount = concerns.length;
        const summaryDetail = strengthCount > 0
            ? ' The evaluation identified ' + strengthCount + ' ' + (strengthCount === 1 ? 'strength' : 'strengths') + ' and ' + concernCount + ' ' + (concernCount === 1 ? 'area' : 'areas') + ' for improvement.'
            : '';

        html += '<article class="ai-section"><div class="ai-section-header"><h2>Executive Summary</h2></div>';
        html += '<p class="ai-summary-text">' + verdict + summaryDetail + '</p>';

        // Quick verdict badges
        html += '<div class="ai-verdict-row">';
        const verdicts = [
            { label: 'Overall', value: overallTone.label, color: scoreColor },
            { label: 'Grade', value: grade, color: gradeColor },
            { label: 'Confidence', value: assessConfidence(avgConf), color: avgConf >= 0.7 ? 'var(--score-strong)' : avgConf >= 0.5 ? 'var(--score-needs-review)' : 'var(--score-concerning)' },
        ];
        if (lowConfCount) verdicts.push({ label: 'Manual review', value: lowConfCount + ' items', color: 'var(--score-concerning)' });
        verdicts.forEach(v => {
            html += '<span class="ai-verdict-chip"><span class="ai-verdict-dot" style="background:' + v.color + '"></span>' + esc(v.label) + ': <strong>' + esc(v.value) + '</strong></span>';
        });
        html += '</div></article>';

        // ================================================================
        // 4. Strengths (what's working well)
        // ================================================================
        html += '<article class="ai-section"><div class="ai-section-header"><h2>What\u2019s Working Well</h2></div>';
        if (strengths.length) {
            html += '<div class="ai-card-grid">';
            strengths.forEach(cr => {
                const dim = getCategoryInfo(cr.category_code) || { label: cr.category_code, icon: '', desc: '' };
                const pct = cr.max_score > 0 ? (Number(cr.score) / Number(cr.max_score) * 100) : 0;
                html += '<div class="ai-strength-card">';
                html += '<div class="ai-strength-head"><div><span class="ai-strength-dim">' + esc(dim.label) + '</span><span class="ai-strength-criterion">' + esc(getCriterionLabel(cr.criterion_key)) + '</span></div></div>';
                html += '<div class="ai-strength-score"><span style="color:var(--score-strong)">' + Number(cr.score).toFixed(1) + '/' + Number(cr.max_score || 8).toFixed(0) + '</span><span class="ai-strength-pct">' + pct.toFixed(0) + '%</span></div>';
                if (cr.remarks) html += '<p class="ai-strength-remark">' + esc(cr.remarks) + '</p>';
                html += '</div>';
            });
            html += '</div>';
        } else {
            html += '<div class="ai-empty-section"><p>No criteria scored above 70%. Review the concerns and recommendations below for improvement areas.</p></div>';
        }
        html += '</article>';

        // ================================================================
        // 5. Concerns (areas for improvement)
        // ================================================================
        html += '<article class="ai-section"><div class="ai-section-header"><h2>Areas for Improvement</h2></div>';
        if (concerns.length) {
            html += '<div class="ai-card-grid">';
            concerns.forEach(cr => {
                const dim = getCategoryInfo(cr.category_code) || { label: cr.category_code, icon: '', desc: '' };
                const pct = cr.max_score > 0 ? (Number(cr.score) / Number(cr.max_score) * 100) : 0;
                const needReview = Number(cr.confidence || 0) < 0.5;
                html += '<div class="ai-concern-card' + (needReview ? ' needs-review' : '') + '">';
                html += '<div class="ai-concern-head"><div><span class="ai-concern-dim">' + esc(dim.label) + '</span><span class="ai-concern-criterion">' + esc(getCriterionLabel(cr.criterion_key)) + '</span></div></div>';
                html += '<div class="ai-concern-score"><span style="color:var(--score-concerning)">' + Number(cr.score).toFixed(1) + '/' + Number(cr.max_score || 8).toFixed(0) + '</span><span class="ai-concern-pct">' + pct.toFixed(0) + '%</span></div>';
                if (cr.remarks) html += '<p class="ai-concern-remark">' + esc(cr.remarks) + '</p>';
                if (needReview && !cr.overridden) html += '<span class="ai-needs-review-badge">Needs manual review</span>';
                html += '</div>';
            });
            html += '</div>';
        } else {
            html += '<div class="ai-empty-section success"><p>All criteria scored at or above 50%. No critical concerns detected.</p></div>';
        }
        html += '</article>';

        // ================================================================
        // 6. Recommendations
        // ================================================================
        const overallRemarks = er.overall_remarks || '';
        if (overallRemarks || concerns.length) {
            html += '<article class="ai-section"><div class="ai-section-header"><h2>Recommendations</h2></div>';

            // Primary recommendation from overall remarks
            if (overallRemarks) {
                html += '<div class="ai-recommendation-card"><div class="ai-rec-num">01</div><div><p class="ai-rec-text">' + esc(overallRemarks) + '</p></div></div>';
            }

            // Auto-generated recommendations from concerns
            if (concerns.length) {
                html += '<div class="ai-rec-context"><p>Based on the evaluation, the following areas would benefit from attention:</p></div>';
                concerns.slice(0, 3).forEach((cr, i) => {
                    const dim = getCategoryInfo(cr.category_code) || { label: cr.category_code, icon: '' };
                    const label = getCriterionLabel(cr.criterion_key);
                    const suggestion = cr.remarks
                        ? cr.remarks
                        : 'Review and improve the ' + label.toLowerCase() + ' aspect of the project.';
                    html += '<div class="ai-recommendation-card"><div class="ai-rec-num">0' + (i + 2) + '</div><div><span class="ai-rec-dim">' + esc(dim.label) + '</span><p class="ai-rec-text">' + esc(suggestion) + '</p></div></div>';
                });
            }
            html += '</article>';
        }

        // ================================================================
        // 7. Quality Dimensions — progressive disclosure
        // ================================================================
        html += '<article class="ai-section"><div class="ai-section-header"><h2>Quality Dimensions</h2><span class="ai-section-badge">Click to expand</span></div>';
        html += '<p class="ai-dimensions-intro">Each dimension below groups related evaluation criteria. Click to view the detailed breakdown including scores and evidence.</p>';

        let dimIdx = 0;
        for (const [catCode, items] of Object.entries(groups)) {
            const dim = getCategoryInfo(catCode) || { label: catCode, desc: '' };
            const catTotal = items.reduce((sum, cr) => sum + Number(cr.score || 0), 0);
            const catMax = items.reduce((sum, cr) => sum + Number(cr.max_score || 8), 0);
            const catPct = catMax > 0 ? (catTotal / catMax * 100) : 0;
            const tone = classifyScore(catTotal, catMax);
            const dimId = 'ai-dim-' + dimIdx;
            const reviewCount = items.filter(cr => {
                const c = Number(cr.confidence || 0);
                return c < 0.7 || cr.confidence_warning;
            }).length;

            html += '<div class="ai-dimension-card" id="' + dimId + '">';
            html += '<div class="ai-dimension-header" onclick="document.getElementById(\'' + dimId + '\').classList.toggle(\'open\')">';
            html += '<span class="ai-dimension-toggle">\u25B8</span>';
            
            html += '<div class="ai-dimension-info"><span class="ai-dimension-label">' + esc(dim.label) + '</span><span class="ai-dimension-desc">' + esc(dim.desc) + '</span></div>';
            html += '<div class="ai-dimension-bar-track"><div class="ai-dimension-bar-fill" style="width:' + catPct + '%;background:' + tone.color + '"></div></div>';
            html += '<span class="ai-dimension-score" style="color:' + tone.color + '">' + catTotal.toFixed(1) + '<span class="ai-dimension-max">/' + catMax.toFixed(0) + '</span></span>';
            if (reviewCount) html += '<span class="ai-dimension-review-badge" title="Items needing manual review">' + reviewCount + '</span>';
            html += '</div>'; // end header

            // Expandable body: per-criterion breakdown
            html += '<div class="ai-dimension-body">';
            items.forEach((cr, i) => {
                const pct = cr.max_score > 0 ? (Number(cr.score) / Number(cr.max_score) * 100) : 0;
                const conf = Number(cr.confidence || 0);
                const crTone = classifyScore(Number(cr.score), Number(cr.max_score || 8));
                const evId = 'ai-ev-' + dimIdx + '-' + i;
                const evItems = cr.evidence || [];

                html += '<div class="ai-criterion-row">';
                html += '<div class="ai-criterion-top">';
                html += '<span class="ai-criterion-dot" style="background:' + crTone.color + '"></span>';
                html += '<span class="ai-criterion-name">' + esc(getCriterionLabel(cr.criterion_key)) + '</span>';
                html += '<span class="ai-criterion-bar-track"><span class="ai-criterion-bar-fill" style="width:' + pct + '%;background:' + crTone.color + '"></span></span>';
                html += '<span class="ai-criterion-score" style="color:' + crTone.color + '">' + Number(cr.score || 0).toFixed(1) + '/' + Number(cr.max_score || 8).toFixed(0) + '</span>';
                html += '<span class="ai-criterion-conf" style="color:' + (conf >= 0.7 ? 'var(--score-strong)' : conf >= 0.5 ? 'var(--score-needs-review)' : 'var(--score-concerning)') + '">' + (conf * 100).toFixed(0) + '%</span>';
                if (evItems.length) {
                    html += '<span class="ai-evidence-toggle" onclick="document.getElementById(\'' + evId + '\').classList.toggle(\'open\');this.classList.toggle(\'open\')">' + evItems.length + ' evidence</span>';
                }
                html += '</div>'; // end criterion-top

                if (cr.remarks) {
                    html += '<div class="ai-criterion-remark">' + esc(cr.remarks) + '</div>';
                }

                // Evidence (expandable)
                if (evItems.length) {
                    html += '<div id="' + evId + '" class="ai-evidence-body">';
                    evItems.forEach(e => {
                        const lines = e.split('\n');
                        const first = esc(lines[0]);
                        const rest = lines.slice(1).filter(Boolean).map(l => esc(l));
                        html += '<div class="ai-evidence-item">' + (rest.length ? '<strong>' + first + '</strong>' + rest.map(r => '<br>' + r).join('') : first) + '</div>';
                    });
                    html += '</div>';
                }

                html += '</div>'; // end ai-criterion-row
            });
            html += '</div>'; // end dimension body
            html += '</div>'; // end dimension card

            dimIdx++;
        }

        html += '</article>';

        // ================================================================
        // 8. Footer note
        // ================================================================
        html += '<div class="ai-report-footer">';
        html += '<span>This assessment was generated by an AI evaluation engine. Scores are based on automated analysis of the repository content and should be reviewed by a human evaluator for final grading.</span>';
        html += '</div>';

        container.innerHTML = html;
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
        const criteria = ev.criterion_results || [];

        sessionBack.href = `/sessions/${sid}`;
        var repoName = r.repo_url.split('/').pop();
        repositoryTitle.textContent = r.roll_number + ' \u00B7 ' + repoName;
        repositoryUrl.textContent = r.repo_url;
        (function() {
            var avatar = document.getElementById('repoAvatar');
            if (!avatar) return;
            function getInitials(n) {
                n = (n || '').replace(/\.git$/i, '');
                var parts = n.split(/[-_\s]+/).filter(Boolean);
                if (parts.length >= 2 && parts[0].length > 0 && parts[1].length > 0) return (parts[0][0] + parts[1][0]).toUpperCase();
                return n.slice(0, 2).toUpperCase() || '?';
            }
            function getColor(n) {
                var colors = ['#6366f1','#8b5cf6','#a855f7','#ec4899','#f43f5e','var(--red)','#f97316','#eab308','#84cc16','#22c55e','#14b8a6','#06b6d4','#3b82f6'];
                var hash = 0;
                for (var i = 0; i < (n || '').length; i++) hash = n.charCodeAt(i) + ((hash << 5) - hash);
                return colors[Math.abs(hash) % colors.length];
            }
            var c = getColor(repoName);
            avatar.textContent = getInitials(repoName);
            avatar.style.background = c + '26';
            avatar.style.color = c;
        })();
        repositoryStatus.textContent = r.status;
        repositoryStatus.className = 'status-badge status-' + r.status.toLowerCase();
        var progressPanel = document.getElementById('evalProgress');
        var progressLabel = document.getElementById('evalProgressLabel');
        var progressBar = document.getElementById('evalProgressBar');
        if (r.status === 'Evaluating') {
            progressPanel.style.display = 'block';
            var pct = Number(r.progress_pct) || 0;
            var step = r.current_step || 'Evaluating';
            if (progressLabel) progressLabel.textContent = step + ' \u00B7 ' + pct + '%';
            if (progressBar) progressBar.style.width = pct + '%';
        } else {
            progressPanel.style.display = 'none';
        }
        repositoryActions.innerHTML =
            '<a class="secondary-btn" href="' + r.repo_url + '" target="_blank">Open GitHub \u2197</a>' +
            '<div class="dropdown"><button class="secondary-btn" onclick="this.nextElementSibling.classList.toggle(\'open\')">Actions \u25BE</button>' +
            '<div class="dropdown-menu"><button id="dropdownEvalButton">Re-evaluate</button>' +
            '<a href="/sessions/' + sid + '/repositories/' + rid + '/report">Download report</a></div></div>';
        const dropdownEvalBtn = document.getElementById('dropdownEvalButton');
        if (dropdownEvalBtn) {
            dropdownEvalBtn.onclick = () => runEvaluation(true);
        }

        renderOverviewTab(r, ev, er, criteria);
        renderCodeQualityTab(ev, er, criteria);

        // ---- New calls: render new tabs ----
        renderIngestionTab(r.ingestion);
        renderEvaluationDetailTab(ev);
        renderCollaborationTab();

        const heroEvalBtn = document.getElementById('heroEvaluateButton');
        if (heroEvalBtn) {
            heroEvalBtn.textContent = r.status === 'Completed' ? 'Re-evaluate' : 'Evaluate';
            heroEvalBtn.onclick = () => runEvaluation(r.status === 'Completed');
        }
        const heroRptLink = document.getElementById('heroReportLink');
        if (heroRptLink) {
            heroRptLink.href = '/sessions/' + sid + '/repositories/' + rid + '/report';
            heroRptLink.hidden = r.status !== 'Completed';
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
        fetch('/api/sessions/' + sid + '/repositories/' + rid + '/' + (re ? 'reevaluate' : 'evaluate'), { method: 'POST' })
            .then(function(r) { if (!r.ok) r.json().then(function(d) { toast(d.error || 'Evaluation failed to start', 'error'); }); })
            .catch(function() {});
        pollUntilDone();
    }

    function pollUntilDone() {
        if (window._evalPoll) clearInterval(window._evalPoll);
        window._evalPoll = setInterval(async function() {
            try {
                var resp = await fetch('/api/sessions/' + sid + '/repositories/' + rid);
                var d = await resp.json();
                var status = d.repository && d.repository.status;
                if (status === 'Completed') {
                    clearInterval(window._evalPoll);
                    window._evalPoll = null;
                    toast('Evaluation completed');
                    load();
                } else if (status === 'Failed' || status === 'Error') {
                    clearInterval(window._evalPoll);
                    window._evalPoll = null;
                    toast('Evaluation failed', 'error');
                    load();
                } else if (status === 'Evaluating' && d.repository) {
                    var pct = Number(d.repository.progress_pct) || 0;
                    var step = d.repository.current_step || 'Evaluating';
                    var progressPanel = document.getElementById('evalProgress');
                    var progressLabel = document.getElementById('evalProgressLabel');
                    var progressBar = document.getElementById('evalProgressBar');
                    if (progressPanel) progressPanel.style.display = 'block';
                    if (progressLabel) progressLabel.textContent = step + ' \u00B7 ' + pct + '%';
                    if (progressBar) progressBar.style.width = pct + '%';
                    repositoryStatus.textContent = 'Evaluating';
                    repositoryStatus.className = 'status-badge status-evaluating';
                }
            } catch (e) {
                clearInterval(window._evalPoll);
                window._evalPoll = null;
            }
        }, 3000);
    }

    // ---- Tab switching (re-fetch for data tabs to reflect overrides) ----

    document.addEventListener('click', e => {
        const tab = e.target.dataset.tab;
        if (!tab) return;
        const tabs = document.getElementById('repositoryTabs');
        if (!tabs) return;
        tabs.querySelectorAll('button').forEach(x => x.classList.toggle('active', x.dataset.tab === tab));
        document.querySelectorAll('.tab-panel').forEach(x => x.classList.toggle('active', x.id === 'tab-' + tab));
        if (tab === 'evaluation' || tab === 'overview' || tab === 'quality') {
            fetch('/api/sessions/' + sid + '/repositories/' + rid)
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    if (!d.repository) return;
                    repository = d.repository;
                    var ev = repository.evaluation_result || {};
                    var er = ev.feedback || {};
                    var criteria = ev.criterion_results || [];
                    if (tab === 'evaluation') renderEvaluationDetailTab(ev);
                    else if (tab === 'overview') renderOverviewTab(repository, ev, er, criteria);
                    else if (tab === 'quality') renderCodeQualityTab(ev, er, criteria);
                }).catch(function() {});
        }
    });

    // ---- Initialize ----
    load();
});
