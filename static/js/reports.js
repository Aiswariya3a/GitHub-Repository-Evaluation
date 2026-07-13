if (typeof window.dateShort !== 'function') {
    window.dateShort = function(v) { return v ? new Intl.DateTimeFormat(undefined, {dateStyle:'medium'}).format(new Date(v)) : '\u2014'; };
}
if (typeof window.esc !== 'function') {
    window.esc = function(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); };
}

document.addEventListener('DOMContentLoaded', function() {
    var reportSearch = document.getElementById('reportSearch');
    var reportSessions = document.getElementById('reportSessions');
    if (!reportSessions) return;

    var reports = [];

    function draw() {
        var q = (reportSearch ? reportSearch.value : '').toLowerCase();
        reportSessions.innerHTML = reports
            .filter(function(x) { return x.name.toLowerCase().includes(q); })
            .map(function(x) {
                return '<div class="activity-item">' +
                    '<span class="activity-avatar">PDF</span>' +
                    '<div><strong>' + window.esc(x.name) + '</strong>' +
                    '<span>' + x.evaluated_count + '/' + x.repository_count + ' repositories evaluated · Updated ' + window.dateShort(x.updated_at) + '</span></div>' +
                    '<div class="dropdown"><button class="table-btn" onclick="this.nextElementSibling.classList.toggle(\'open\')">Actions ▾</button>' +
                    '<div class="dropdown-menu"><a href="/sessions/' + x.id + '/report">Download PDF</a>' +
                    '<a href="/sessions/' + x.id + '">Open session</a></div></div></div>';
            }).join('') || '<div class="polished-empty"><span>□</span><strong>No matching reports</strong><p>Completed evaluations will appear here.</p></div>';
    }

    fetch('/api/sessions')
        .then(function(r) { return r.json(); })
        .then(function(items) {
            reports = items.filter(function(x) { return Number(x.evaluated_count) > 0; });
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
