/* ── Admin Statistics Page ── */
async function initPage() {
  await loadStats();
  setupEventListeners();
}

async function loadStats() {
  const period = document.getElementById('statPeriod')?.value || '30';
  try {
    const data = await API.apiFetch('/statistics/?period=' + period);
    renderStats(data);
  } catch (e) {
    document.getElementById('statTotalPresences').textContent = '—';
    showToast('Erreur chargement statistiques: ' + e.message, 'error');
  }
}

function renderStats(data) {
  if (!data) return;
  document.getElementById('statTotalPresences').textContent = data.total_present ?? data.total_attendance ?? '—';
  const rate = data.attendance_rate ?? data.average_rate;
  document.getElementById('statAvgRate').textContent = rate != null ? rate + '%' : '—';
  document.getElementById('statActiveClasses').textContent = data.active_classes ?? data.total_classes ?? '—';
  document.getElementById('statStudents').textContent = data.total_students ?? '—';

  const rows = data.daily_attendance || data.daily || [];
  const tbody = document.getElementById('statsBody');
  if (!rows.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="3">Aucune donnée.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(function (r) {
    const date = r.date || r.day || '—';
    const present = r.present || r.presences || 0;
    const total = r.total || (r.present + r.absent) || present;
    const pct = total > 0 ? Math.round((present / total) * 100) + '%' : '—';
    return '<tr>' +
      '<td>' + esc(date) + '</td>' +
      '<td>' + present + ' / ' + total + '</td>' +
      '<td>' + pct + '</td>' +
    '</tr>';
  }).join('');
}

function setupEventListeners() {
  document.getElementById('statPeriod')?.addEventListener('change', loadStats);
}