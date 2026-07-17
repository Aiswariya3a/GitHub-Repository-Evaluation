let statusCache = null;

async function refreshStatus() {
  const app = document.getElementById('adminApp');
  if (app) app.style.opacity = '0.45';
  try {
    const res = await fetch('/api/system/status');
    statusCache = await res.json();
    renderStatus(statusCache);
  } catch (e) {
    window.toast('Failed to load system status: ' + e.message, 'error');
  } finally {
    if (app) app.style.opacity = '1';
  }
}

function renderStatus(d) {
  renderHealthCards(d);
  renderDbTable(d);
  renderConfig(d);
  renderRuntime(d);
}

function renderHealthCards(d) {
  const dbOk = d.database && d.database.database === 'connected';
  const dbCount = d.database && d.database.table_counts
    ? Object.values(d.database.table_counts).reduce((a, b) => a + b, 0) : 0;
  const healthCards = [
    {
      icon: 'DB',
      value: dbOk ? 'Connected' : 'Error',
      label: 'Database',
      status: dbOk ? 'green' : 'red',
      detail: dbCount + ' rows across ' + (d.database && d.database.table_counts ? Object.keys(d.database.table_counts).length : 0) + ' tables',
      spark: true,
    },
    {
      icon: 'WR',
      value: d.worker ? d.worker.type.split(' ')[0] : '—',
      label: 'Worker',
      status: 'violet',
      detail: d.worker ? d.worker.mode : '—',
      spark: false,
    },
    {
      icon: 'AI',
      value: d.ollama && d.ollama.code_model ? d.ollama.code_model.split(':')[0] : '—',
      label: 'AI Model',
      status: 'blue',
      detail: d.ollama ? (d.ollama.reasoning_model || '').split(':')[0] + ' (reasoning)' : '—',
      spark: false,
    },
    {
      icon: 'ST',
      value: formatBytes(dbCount * 512),
      label: 'Est. Storage',
      status: 'amber',
      detail: dbCount + ' records',
      spark: true,
    },
  ];
  document.getElementById('healthCards').innerHTML = healthCards.map(h => `
    <article class="admin-card ${h.status}">
      <div class="admin-card-top"><div class="admin-card-icon">${h.icon}</div></div>
      <div class="admin-card-value">${h.value}</div>
      <div class="admin-card-label">${h.label}</div>
      <div class="admin-card-detail">${h.detail}</div>
      ${h.spark ? '<div class="admin-spark"><b></b><b></b><b></b><b></b><b></b></div>' : ''}
    </article>
  `).join('');
}

function renderDbTable(d) {
  const tc = d.database && d.database.table_counts ? d.database.table_counts : {};
  const keys = Object.keys(tc);
  const maxVal = Math.max(...Object.values(tc), 1);
  const badge = document.getElementById('dbStatusBadge');
  if (badge) {
    const ok = d.database && d.database.database === 'connected';
    badge.textContent = ok ? 'Connected' : 'Disconnected';
    badge.className = 'admin-badge ' + (ok ? 'badge-ok' : 'badge-err');
  }
  document.getElementById('dbTableBody').innerHTML = keys.length
    ? keys.map(k => {
        const pct = (tc[k] / maxVal) * 100;
        return `<div class="admin-table-row"><span class="admin-table-name">${k.replace(/_/g, ' ')}</span><div class="admin-table-track"><span style="width:${Math.max(pct, 2)}%"></span></div><span class="admin-table-count">${tc[k].toLocaleString()}</span></div>`;
      }).join('')
    : '<p class="admin-empty">No table data available.</p>';
}

function renderConfig(d) {
  const items = [];
  if (d.ollama && d.ollama.host) {
    items.push({ key: 'Ollama Host', val: d.ollama.host });
    items.push({ key: 'Code Model', val: d.ollama.code_model || '—' });
    items.push({ key: 'Reasoning Model', val: d.ollama.reasoning_model || '—' });
    items.push({ key: 'Inference Timeout', val: (d.ollama.timeout || '—') + 's' });
  }
  if (d.worker) {
    items.push({ key: 'Worker Type', val: d.worker.type || '—' });
    items.push({ key: 'Execution Mode', val: d.worker.mode || '—' });
  }
  if (!items.length) items.push({ key: 'Config', val: 'No runtime configuration detected.' });
  document.getElementById('configBody').innerHTML = items.map(i =>
    `<div class="admin-config-row"><span class="admin-config-key">${i.key}</span><span class="admin-config-val">${i.val}</span></div>`
  ).join('');
}

function renderRuntime(d) {
  const sys = d.system || {};
  const items = [
    { key: 'Python', val: sys.python_version || '—' },
    { key: 'Platform', val: sys.platform || '—' },
    { key: 'Hostname', val: sys.hostname || '—' },
    { key: 'Server Time', val: sys.server_time ? new Date(sys.server_time).toLocaleString() : '—' },
  ];
  document.getElementById('runtimeBody').innerHTML = items.map(i =>
    `<div class="admin-config-row"><span class="admin-config-key">${i.key}</span><span class="admin-config-val">${i.val}</span></div>`
  ).join('') + '<p class="admin-uptime-hint">Server time is reported in local timezone.</p>';
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

document.addEventListener('DOMContentLoaded', refreshStatus);