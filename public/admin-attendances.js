/* ── Admin Attendance List Page ── */
let allRecords = [];

async function initPage() {
  await loadAttendances();
  setupEventListeners();
}

async function loadAttendances() {
  try {
    const data = await API.apiFetch('/attendance/');
    allRecords = Array.isArray(data) ? data : (data.results || []);
    renderTable();
  } catch (e) {
    document.getElementById('attendancesBody').innerHTML =
      '<tr class="empty-row"><td colspan="7">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

function getFiltered() {
  const q = searchQuery('searchAttendances');
  const status = document.getElementById('filterAtStatus')?.value || '';
  const date = document.getElementById('filterAtDate')?.value || '';
  return allRecords.filter(function (r) {
    if (q && !matchesQuery(q, r.student_name, r.student_code_massar, r.subject)) return false;
    if (status === 'present' && r.attendance_status !== 'confirmed') return false;
    if (status === 'absent' && r.attendance_status !== 'absent') return false;
    if (date) {
      var d = r.session_date || (r.validation_time ? r.validation_time.split('T')[0] : '');
      if (d !== date) return false;
    }
    return true;
  });
}

function renderTable() {
  var filtered = getFiltered();
  var total = filtered.length;
  var present = filtered.filter(function (r) { return r.attendance_status === 'confirmed'; }).length;
  var absent = total - present;
  document.getElementById('atTotal').textContent = total;
  document.getElementById('atPresent').textContent = present;
  document.getElementById('atAbsent').textContent = absent;
  var tbody = document.getElementById('attendancesBody');
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">Aucune présence trouvée.</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map(function (r, i) {
    var status = r.attendance_status === 'confirmed' ? 'Présent' : 'Absent';
    var cls = r.attendance_status === 'confirmed' ? 'badge-present' : 'badge-absent';
    return '<tr>' +
      '<td style="color:var(--muted)">' + (i + 1) + '</td>' +
      '<td><strong>' + esc(r.student_name) + '</strong></td>' +
      '<td><code>' + esc(r.student_code_massar) + '</code></td>' +
      '<td>' + esc(r.subject || '—') + '</td>' +
      '<td>' + esc(r.classe_session || r.classe_name || '—') + '</td>' +
      '<td>' + API.formatDate(r.session_date) + '</td>' +
      '<td><span class="badge ' + cls + '">' + status + '</span></td>' +
    '</tr>';
  }).join('');
}

function setupEventListeners() {
  bindSearchInput('searchAttendances', renderTable);
  document.getElementById('filterAtStatus')?.addEventListener('change', renderTable);
  document.getElementById('filterAtDate')?.addEventListener('change', renderTable);
}