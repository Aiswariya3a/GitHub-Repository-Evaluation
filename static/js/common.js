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
    updateAriaLabel();
})();

function updateAriaLabel() {
    var btn = document.querySelector('.theme-toggle');
    if (!btn) return;
    var isLight = document.documentElement.getAttribute('data-theme') === 'light';
    btn.setAttribute('aria-label', isLight ? 'Switch to Dark Mode' : 'Switch to Light Mode');
}

window.toggleTheme = function() {
    var html = document.documentElement;
    var btn = document.querySelector('.theme-toggle');
    var isLight = html.getAttribute('data-theme') === 'light';

    if (isLight) {
        html.removeAttribute('data-theme');
        localStorage.setItem('theme', 'dark');
        spawnStars(btn);
    } else {
        html.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
    }

    updateAriaLabel();
};

function spawnStars(btn) {
    if (!btn) return;
    var existing = btn.querySelectorAll('.theme-star');
    for (var i = 0; i < existing.length; i++) existing[i].remove();
    for (var j = 0; j < 4; j++) {
        var star = document.createElement('span');
        star.className = 'theme-star';
        star.style.left = (20 + Math.random() * 60) + '%';
        star.style.top = (10 + Math.random() * 60) + '%';
        star.style.animationDelay = (Math.random() * 0.15) + 's';
        star.style.width = star.style.height = (2 + Math.random() * 2) + 'px';
        btn.appendChild(star);
        setTimeout(function(s) { if (s && s.parentNode) s.remove(); }, 700 + Math.random() * 300, star);
    }
}

document.addEventListener('keydown', function(e) {
    if (e.key === 't' && (e.ctrlKey || e.metaKey) && e.shiftKey) {
        e.preventDefault();
        toggleTheme();
    }
});
