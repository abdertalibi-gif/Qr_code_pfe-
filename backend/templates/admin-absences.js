/* ── Admin Absences Page ── */
let allRecords = [];

async function initPage() {
  await loadAbsences();
  setupEventListeners();
}

async function loadAbsences() {
  try {
    const data = await API.apiFetch('/attendance/');
    allRecords = Array.isArray(data) ? data : (data.results || []);
    renderTable();
  } catch (e) {
    document.getElementById('absencesBody').innerHTML =
      '<tr class="empty-row"><td colspan="6">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

function getFiltered() {
  const q = searchQuery('searchAbsences');
  const date = document.getElementById('filterAbDate')?.value || '';
  return allRecords.filter(function (r) {
    if (r.attendance_status !== 'absent') return false;
    if (q && !matchesQuery(q, r.student_name, r.student_code_massar, r.subject)) return false;
    if (date) {
      var d = r.session_date || (r.validation_time ? r.validation_time.split('T')[0] : '');
      if (d !== date) return false;
    }
    return true;
  });
}

function renderTable() {
  var filtered = getFiltered();
  document.getElementById('abTotal').textContent = filtered.length + ' absence(s)';
  var tbody = document.getElementById('absencesBody');
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Aucune absence trouvée.</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map(function (r, i) {
    return '<tr>' +
      '<td style="color:var(--muted)">' + (i + 1) + '</td>' +
      '<td><strong>' + esc(r.student_name) + '</strong></td>' +
      '<td><code>' + esc(r.student_code_massar) + '</code></td>' +
      '<td>' + esc(r.subject || '—') + '</td>' +
      '<td>' + esc(r.classe_session || r.classe_name || '—') + '</td>' +
      '<td>' + API.formatDate(r.session_date) + '</td>' +
    '</tr>';
  }).join('');
}

function setupEventListeners() {
  bindSearchInput('searchAbsences', renderTable);
  document.getElementById('filterAbDate')?.addEventListener('change', renderTable);
}