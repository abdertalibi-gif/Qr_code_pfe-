/* ── Admin Assistants Page (is_also_teacher) ── */
let allAssistants = [];

async function initPage() {
  await loadAssistants();
  setupEventListeners();
}

async function loadAssistants() {
  try {
    const data = await API.apiFetch('/users/');
    let users = Array.isArray(data) ? data : (data.results || []);
    allAssistants = users.filter(function (u) { return u.is_also_teacher; });
    renderTable();
  } catch (e) {
    document.getElementById('assistantsBody').innerHTML =
      '<tr class="empty-row"><td colspan="6">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

function renderTable() {
  var q = searchQuery('searchAssistants');
  var filtered = allAssistants.filter(function (a) {
    return !q || matchesQuery(q, a.full_name, a.first_name, a.last_name, a.email);
  });
  var tbody = document.getElementById('assistantsBody');
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">' + (q ? 'Aucun résultat.' : 'Aucun assistant.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map(function (a, i) {
    return '<tr>' +
      '<td style="color:var(--muted)">' + (i + 1) + '</td>' +
      '<td><strong>' + esc(a.full_name || a.first_name + ' ' + a.last_name) + '</strong></td>' +
      '<td>' + esc(a.email) + '</td>' +
      '<td>' + esc(a.role || '—') + '</td>' +
      '<td>' + esc(a.phone || '—') + '</td>' +
      '<td><span class="badge ' + (a.is_active === false ? 'badge-absent' : 'badge-present') + '">' + (a.is_active === false ? 'Inactif' : 'Actif') + '</span></td>' +
    '</tr>';
  }).join('');
}

function setupEventListeners() {
  bindSearchInput('searchAssistants', renderTable);
}