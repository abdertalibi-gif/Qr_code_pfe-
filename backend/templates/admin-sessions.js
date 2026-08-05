/* ── Admin Sessions Page ── */
let allSessions = [];

async function initPage() {
  await loadSessions();
  setupEventListeners();
}

async function loadSessions() {
  try {
    const data = await API.apiFetch('/sessions/');
    allSessions = Array.isArray(data) ? data : (data.results || []);
    renderSessions();
  } catch (e) {
    document.getElementById('sessionsBody').innerHTML =
      '<tr class="empty-row"><td colspan="8">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

function renderSessions() {
  const tbody = document.getElementById('sessionsBody');
  const q = searchQuery('searchSessions');
  const filtered = allSessions.filter(s =>
    matchesQuery(q, s.title, s.class_name || '', s.matiere_name || '',
      s.teacher_name || '', s.room_name || '', s.type || '')
  );
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">' + (q ? 'Aucun résultat.' : 'Aucune séance.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((s, i) => {
    const statusClass = s.status === 'active' ? 'badge-success' : s.status === 'completed' ? 'badge-info' : 'badge-warning';
    return '<tr>' +
      '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
      '<td><strong>' + esc(s.title) + '</strong></td>' +
      '<td>' + esc(s.class_name || '—') + '</td>' +
      '<td>' + esc(s.matiere_name || '—') + '</td>' +
      '<td>' + esc(s.teacher_name || '—') + '</td>' +
      '<td>' + esc(s.room_name || '—') + '</td>' +
      '<td><span class="badge ' + statusClass + '">' + esc(s.status) + '</span></td>' +
    '</tr>';
  }).join('');
}

function setupEventListeners() {
  bindSearchInput('searchSessions', renderSessions);

  document.getElementById('btnRefreshSessions')?.addEventListener('click', loadSessions);
}