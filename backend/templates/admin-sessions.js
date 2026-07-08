/* ── Admin Sessions Page ── */
let allSessions = [];
let allClasses = [];
let allMatieres = [];
let allTeachers = [];

async function initPage() {
  await Promise.all([loadSessions(), loadClasses(), loadMatieres(), loadTeachers()]);
  setupEventListeners();
}

async function loadSessions() {
  try {
    const data = await API.apiFetch('/sessions/');
    allSessions = Array.isArray(data) ? data : (data.results || []);
    renderSessions();
  } catch (e) {
    document.getElementById('sessionsBody').innerHTML =
      '<tr class="empty-row"><td colspan="7">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

async function loadClasses() {
  try {
    const data = await API.apiFetch('/classes/');
    allClasses = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { allClasses = []; }
}

async function loadMatieres() {
  try {
    const data = await API.apiFetch('/curriculum/subjects/');
    allMatieres = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { allMatieres = []; }
}

async function loadTeachers() {
  try {
    const data = await API.apiFetch('/users/?role=teacher');
    allTeachers = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { allTeachers = []; }
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
      '<td class="actions-cell">' +
        '<button class="btn sm outline" onclick="openEditSession(' + s.id + ')">Modifier</button>' +
        '<button class="btn sm outline" style="color:var(--red)" onclick="deleteSession(' + s.id + ')">Supprimer</button>' +
      '</td>' +
    '</tr>';
  }).join('');
}

async function populateSessionForm() {
  const classSel = document.getElementById('sClass');
  classSel.innerHTML = '<option value="">— Sélectionner —</option>' +
    allClasses.map(c => '<option value="' + c.id + '">' + esc(c.name) + '</option>').join('');

  const matSel = document.getElementById('sMatiere');
  matSel.innerHTML = '<option value="">— Sélectionner —</option>' +
    allMatieres.map(m => '<option value="' + m.id + '">' + esc(m.name) + '</option>').join('');

  const teacherSel = document.getElementById('sTeacher');
  teacherSel.innerHTML = '<option value="">— Non assigné —</option>' +
    allTeachers.map(t => '<option value="' + t.id + '">' + esc(t.full_name || t.first_name + ' ' + t.last_name) + '</option>').join('');
}

async function openEditSession(id) {
  const s = allSessions.find(x => x.id === id);
  if (!s) return;
  if (window.SessionForm) {
    await SessionForm.init({ isAdmin: true, userRole: currentUser?.role });
    SessionForm.open(s.classe);
  } else {
    showToast('Le formulaire de séance n\'est pas chargé.', 'error');
  }
}

async function deleteSession(id) {
  if (!confirm('Supprimer cette séance ?')) return;
  try {
    await API.apiFetch('/sessions/' + id + '/', { method: 'DELETE' });
    showToast('Séance supprimée.', 'success');
    await loadSessions();
  } catch (e) { showToast(e.message, 'error'); }
}

function setupEventListeners() {
  bindSearchInput('searchSessions', renderSessions);

  document.getElementById('btnRefreshSessions')?.addEventListener('click', loadSessions);

  document.getElementById('btnOpenAddSession')?.addEventListener('click', async () => {
    if (window.SessionForm) {
      await SessionForm.init({ isAdmin: true, userRole: currentUser?.role });
      SessionForm.open(null);
    } else {
      showToast('Le formulaire de séance n\'est pas chargé.', 'error');
    }
  });
}