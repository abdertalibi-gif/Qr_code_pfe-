/* ── Admin Teachers Page ── */
let allTeachers = [];

async function initPage() {
  await loadTeachers();
  setupEventListeners();
}

async function loadTeachers() {
  try {
    const data = await API.apiFetch('/users/?role=teacher');
    allTeachers = Array.isArray(data) ? data : (data.results || []);
    renderTeachers();
  } catch (e) {
    document.getElementById('teachersBody').innerHTML =
      '<tr class="empty-row"><td colspan="7">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

function renderTeachers() {
  const tbody = document.getElementById('teachersBody');
  const q = searchQuery('searchTeachers');
  const filtered = allTeachers.filter(t => matchesQuery(q, t.full_name, t.first_name, t.last_name, t.email, t.matricule || ''));
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">' + (q ? 'Aucun résultat.' : 'Aucun enseignant.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((t, i) => '<tr>' +
    '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
    '<td>' + esc(t.matricule || '—') + '</td>' +
    '<td><strong>' + esc(t.full_name || t.first_name + ' ' + t.last_name) + '</strong></td>' +
    '<td>' + esc(t.email) + '</td>' +
    '<td>' + (t.phone || '—') + '</td>' +
    '<td>' + (t.class_count ?? '—') + '</td>' +
    '<td class="actions-cell">' +
      '<button class="btn sm outline" onclick="openEditTeacher(' + t.id + ')">Modifier</button>' +
    '</td>' +
  '</tr>').join('');
}

async function openEditTeacher(userId) {
  let user;
  try {
    const data = await API.apiFetch('/users/' + userId + '/');
    user = data;
  } catch (e) { showToast('Erreur: ' + e.message, 'error'); return; }
  document.getElementById('teacherId').value = user.id;
  document.getElementById('teacherMatricule').value = user.matricule || '';
  document.getElementById('teacherLastName').value = user.last_name || '';
  document.getElementById('teacherFirstName').value = user.first_name || '';
  document.getElementById('teacherEmail').value = user.email || '';
  document.getElementById('teacherPhone').value = user.phone || '';
  document.getElementById('teacherModalTitle').textContent = 'Modifier enseignant';
  openModal('modalTeacher');
}

function setupEventListeners() {
  bindSearchInput('searchTeachers', renderTeachers);
  document.getElementById('btnSubmitTeacher')?.addEventListener('click', async () => {
    const id = document.getElementById('teacherId').value;
    const body = {
      first_name: document.getElementById('teacherFirstName').value.trim(),
      last_name: document.getElementById('teacherLastName').value.trim(),
      email: document.getElementById('teacherEmail').value.trim(),
      phone: document.getElementById('teacherPhone').value.trim(),
      matricule: document.getElementById('teacherMatricule').value.trim() || undefined,
    };
    if (!body.last_name || !body.first_name || !body.email) {
      showToast('Nom, prénom et email sont requis.', 'error'); return;
    }
    try {
      await API.apiFetch('/users/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
      closeModal('modalTeacher');
      showToast('Enseignant modifié.', 'success');
      await loadTeachers();
    } catch (e) { showToast(e.message, 'error'); }
  });
}