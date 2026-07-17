if (typeof window.dateShort !== 'function') {
    window.dateShort = function(v) { return v ? new Intl.DateTimeFormat(undefined, {dateStyle:'medium'}).format(new Date(v)) : '\u2014'; };
}
if (typeof window.esc !== 'function') {
    window.esc = function(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); };
}

document.addEventListener('DOMContentLoaded', function() {
    var reportSearch = document.getElementById('reportSearch');
    var reportSessions = document.getElementById('reportSessions');
    var statTotalReports = document.getElementById('statTotalReports');
    var statTotalEvaluated = document.getElementById('statTotalEvaluated');
    var statLatestReport = document.getElementById('statLatestReport');
    var statLatestCaption = document.getElementById('statLatestCaption');
    if (!reportSessions) return;

    var reports = [];

    function statusBadge(evaluated, total) {
        if (total === 0) return '<span class="status-badge rs-archived">Empty</span>';
        if (evaluated === 0) return '<span class="status-badge rs-pending">Pending</span>';
        if (evaluated < Number(total)) return '<span class="status-badge rs-partial">Partial</span>';
        return '<span class="status-badge rs-ready">Ready</span>';
    }

    function draw() {
        var q = (reportSearch ? reportSearch.value : '').toLowerCase();
        reportSessions.innerHTML = reports
            .filter(function(x) { return x.name.toLowerCase().includes(q); })
            .map(function(x) {
                var st = statusBadge(Number(x.evaluated_count), Number(x.repository_count));
                return '<div class="report-card">' +
                    '<div class="report-card-left">' +
                    '<span class="report-card-icon">PDF</span>' +
                    '</div>' +
                    '<div class="report-card-body">' +
                    '<strong class="report-card-title">' + window.esc(x.name) + '</strong>' +
                    '<div class="report-card-meta">' +
                    '<span class="report-meta-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>' + window.esc(x.evaluated_count) + '/' + window.esc(x.repository_count) + ' evaluated</span>' +
                    '<span class="report-meta-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' + window.dateShort(x.updated_at) + '</span>' +
                    '</div></div>' +
                    '<div class="report-card-end">' +
                    st +
                    '<div class="dropdown report-dropdown">' +
                    '<button class="report-menu-btn" onclick="event.stopPropagation();window.toggleReportMenu(this)">\u22ee</button>' +
                    '<div class="dropdown-menu">' +
                    '<a href="/sessions/' + x.id + '/report">Download PDF</a>' +
                    '<a href="/sessions/' + x.id + '">Open session</a>' +
                    '</div></div></div></div>';
            }).join('') || '<div class="polished-empty"><span>\u25a1</span><strong>No matching reports</strong><p>Completed evaluations will appear here.</p></div>';
    }

    window.toggleReportMenu = function(btn) {
        document.querySelectorAll('.report-dropdown .dropdown-menu.open').forEach(function(m) {
            if (m !== btn.nextElementSibling) m.classList.remove('open');
        });
        btn.nextElementSibling.classList.toggle('open');
    };

    document.addEventListener('click', function() {
        document.querySelectorAll('.report-dropdown .dropdown-menu.open').forEach(function(m) {
            m.classList.remove('open');
        });
    });

    fetch('/api/sessions')
        .then(function(r) { return r.json(); })
        .then(function(items) {
            reports = items.filter(function(x) { return Number(x.evaluated_count) > 0; });
            var totalReports = reports.length;
            var totalEvaluated = reports.reduce(function(s, x) { return s + Number(x.evaluated_count); }, 0);
            var totalRepos = reports.reduce(function(s, x) { return s + Number(x.repository_count); }, 0);
            if (statTotalReports) statTotalReports.textContent = totalReports;
            if (statTotalEvaluated) statTotalEvaluated.textContent = totalEvaluated + '/' + totalRepos;
            if (reports.length) {
                var sorted = reports.slice().sort(function(a, b) { return new Date(b.updated_at) - new Date(a.updated_at); });
                if (statLatestReport) statLatestReport.textContent = window.esc(sorted[0].name);
                if (statLatestCaption) statLatestCaption.textContent = 'Updated ' + window.dateShort(sorted[0].updated_at);
            }
            draw();
        })
        .catch(function(err) {
            var errEl = document.getElementById('reportsError');
            if (errEl) { errEl.hidden = false; errEl.textContent = 'Failed to load reports: ' + err.message; }
        });

    if (reportSearch) {
        reportSearch.addEventListener('input', draw);
    }
});