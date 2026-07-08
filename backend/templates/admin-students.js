/* ── Admin Students Page ── */
let allStudents = [];

async function initPage() {
  await loadStudents();
  setupEventListeners();
}

async function loadStudents() {
  try {
    const data = await API.apiFetch('/students/');
    allStudents = Array.isArray(data) ? data : (data.results || []);
    renderStudents();
  } catch (e) {
    document.getElementById('studentsBody').innerHTML =
      '<tr class="empty-row"><td colspan="8">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

function renderStudents() {
  const tbody = document.getElementById('studentsBody');
  const q = searchQuery('searchStudents');
  const filtered = allStudents.filter(s => matchesQuery(q, s.full_name, s.first_name, s.last_name, s.email, s.matricule || ''));
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="8">' + (q ? 'Aucun résultat.' : 'Aucun étudiant.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((s, i) => '<tr>' +
    '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
    '<td>' + esc(s.matricule || '—') + '</td>' +
    '<td><strong>' + esc(s.full_name || s.first_name + ' ' + s.last_name) + '</strong></td>' +
    '<td>' + esc(s.email) + '</td>' +
    '<td>' + esc(s.class_name || '—') + '</td>' +
    '<td>' + (s.total_absences ?? '—') + '</td>' +
    '<td><span class="badge ' + (s.is_active === false ? 'badge-danger' : 'badge-success') + '">' + (s.is_active === false ? 'Inactif' : 'Actif') + '</span></td>' +
    '<td class="actions-cell">' +
      '<button class="btn sm outline" onclick="openEditStudent(' + s.id + ')">Modifier</button>' +
    '</td>' +
  '</tr>').join('');
}

async function openEditStudent(studentId) {
  let student;
  try {
    const data = await API.apiFetch('/students/' + studentId + '/');
    student = data;
  } catch (e) { showToast('Erreur: ' + e.message, 'error'); return; }
  document.getElementById('studentId').value = student.id;
  document.getElementById('studentMatricule').value = student.matricule || '';
  document.getElementById('studentLastName').value = student.last_name || '';
  document.getElementById('studentFirstName').value = student.first_name || '';
  document.getElementById('studentEmail').value = student.email || '';
  document.getElementById('studentPhone').value = student.phone || '';
  document.getElementById('studentModalTitle').textContent = 'Modifier étudiant';
  openModal('modalStudent');
}

function setupEventListeners() {
  bindSearchInput('searchStudents', renderStudents);
  document.getElementById('btnSubmitStudent')?.addEventListener('click', async () => {
    const id = document.getElementById('studentId').value;
    const body = {
      first_name: document.getElementById('studentFirstName').value.trim(),
      last_name: document.getElementById('studentLastName').value.trim(),
      email: document.getElementById('studentEmail').value.trim(),
      phone: document.getElementById('studentPhone').value.trim(),
      matricule: document.getElementById('studentMatricule').value.trim() || undefined,
    };
    if (!body.last_name || !body.first_name || !body.email) {
      showToast('Nom, prénom et email sont requis.', 'error'); return;
    }
    try {
      await API.apiFetch('/students/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
      closeModal('modalStudent');
      showToast('Étudiant modifié.', 'success');
      await loadStudents();
    } catch (e) { showToast(e.message, 'error'); }
  });
}