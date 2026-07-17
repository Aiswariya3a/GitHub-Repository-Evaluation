// Shared utilities — loaded before other JS files
window.esc = function(v) {
    return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
};

window.date = function(v) {
    return v ? new Intl.DateTimeFormat(undefined, {dateStyle:'medium', timeStyle:'short'}).format(new Date(v)) : 'Never';
};

window.dateShort = function(v) {
    return v ? new Intl.DateTimeFormat(undefined, {dateStyle:'medium'}).format(new Date(v)) : '—';
};

window.when = function(v) {
    return v ? new Intl.RelativeTimeFormat(undefined, {numeric:'auto'}).format(Math.round((new Date(v) - Date.now()) / 60000), 'minute') : '—';
};

window.toast = function(message, tone) {
    if (tone === undefined) tone = 'success';
    const item = document.createElement('div');
    item.className = 'toast ' + tone;
    item.innerHTML = '<span>' + (tone === 'success' ? '✓' : '!') + '</span><p>' + message + '</p>';
    document.getElementById('toastStack').appendChild(item);
    requestAnimationFrame(function() { item.classList.add('show'); });
    setTimeout(function() { item.classList.remove('show'); setTimeout(function() { item.remove(); }, 250); }, 3500);
};

window.confirmAction = function(message, title) {
    if (title === undefined) title = 'Confirm action';
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    document.getElementById('confirmDialog').showModal();
    return new Promise(function(resolve) { window.confirmationResolver = resolve; });
};

window.resolveConfirmation = function(value) {
    document.getElementById('confirmDialog').close();
    if (window.confirmationResolver) window.confirmationResolver(value);
    window.confirmationResolver = null;
};

window.statusTone = function(s) {
    return 'status-' + String(s).toLowerCase().replaceAll(' ', '-');
};

window.empty = function(title, text) {
    return '<div class="polished-empty"><span>◇</span><strong>' + title + '</strong><p>' + text + '</p></div>';
};

// --- Theme Toggle ---
(function() {
    var theme = localStorage.getItem('theme');
    if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    }
})();

window.toggleTheme = function() {
    var html = document.documentElement;
    var isLight = html.getAttribute('data-theme') === 'light';
    if (isLight) {
        html.removeAttribute('data-theme');
        localStorage.setItem('theme', 'dark');
    } else {
        html.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
    }
};
