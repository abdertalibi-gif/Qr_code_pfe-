/* ── Admin Teachers Page ── */
let allTeachers = [];
let allDepartments = [];
let allFilieres = [];
let allClasses = [];
let editingTeacherId = null;

async function initPage() {
  await Promise.all([loadTeachers(), loadDepartments(), loadFilieres(), loadClasses()]);
  setupEventListeners();
}

async function loadTeachers() {
  try {
    const data = await API.apiFetch('/users/?role=teacher');
    allTeachers = Array.isArray(data) ? data : (data.results || []);
    renderTeachers();
  } catch (e) {
    document.getElementById('teachersBody').innerHTML =
      '<tr class="empty-row"><td colspan="12">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

async function loadDepartments() {
  try {
    const data = await API.apiFetch('/departments/');
    allDepartments = Array.isArray(data) ? data : [];
  } catch (e) { allDepartments = []; }
}

async function loadFilieres() {
  try {
    const data = await API.apiFetch('/curriculum/filieres/');
    allFilieres = Array.isArray(data) ? data : [];
  } catch (e) { allFilieres = []; }
}

async function loadClasses() {
  try {
    const data = await API.apiFetch('/classes/');
    allClasses = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { allClasses = []; }
}

function renderTeachers() {
  const tbody = document.getElementById('teachersBody');
  const q = searchQuery('searchTeachers');
  const filtered = allTeachers.filter(t => matchesQuery(q, t.full_name, t.first_name, t.last_name, t.email, t.cin || ''));
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="12">' + (q ? 'Aucun résultat.' : 'Aucun enseignant.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((t, i) => '<tr>' +
    '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
    '<td><strong>' + esc(t.full_name || t.first_name + ' ' + t.last_name) + '</strong></td>' +
    '<td>' + esc(t.email) + '</td>' +
    '<td>' + esc(t.phone || '—') + '</td>' +
    '<td>' + esc(t.cin || '—') + '</td>' +
    '<td>' + esc((t.department_name || t.department) || '—') + '</td>' +
    '<td>' + '—' + '</td>' +
    '<td>' + esc(t.grade || '—') + '</td>' +
    '<td>' + esc(t.speciality || '—') + '</td>' +
    '<td>' + (t.class_count ?? (t.assigned_class_ids ? t.assigned_class_ids.length : '—')) + '</td>' +
    '<td><span class="badge ' + (t.is_active === false ? 'badge-absent' : 'badge-present') + '">' + (t.is_active === false ? 'Inactif' : 'Actif') + '</span></td>' +
    '<td class="actions-cell">' +
      '<button class="btn sm outline" onclick="openEditTeacher(' + t.id + ')">Modifier</button>' +
      '<button class="btn sm outline" onclick="toggleTeacherActive(' + t.id + ')">' + (t.is_active === false ? 'Activer' : 'Désactiver') + '</button>' +
    '</td>' +
  '</tr>').join('');
}

function populateTeacherSelects(prefix) {
  const deptSel = document.getElementById(prefix + 'Department');
  if (deptSel) {
    deptSel.innerHTML = '<option value="">— Sélectionner —</option>' +
      allDepartments.map(d => '<option value="' + d.id + '">' + esc(d.name) + '</option>').join('');
  }
  const filSel = document.getElementById(prefix + 'Filiere');
  if (filSel) {
    filSel.innerHTML = '<option value="">— Sélectionner —</option>' +
      allFilieres.map(f => '<option value="' + f.id + '">' + esc(f.name) + '</option>').join('');
  }
  const classSel = document.getElementById(prefix + 'Classes');
  if (classSel) {
    classSel.innerHTML = allClasses.map(c =>
      '<option value="' + c.id + '">' + esc(c.filiere_name || '—') + ' — ' + esc(c.semestre_name || '') + ' (' + esc(c.academic_year) + ')</option>'
    ).join('');
  }
}

async function openEditTeacher(userId) {
  let user;
  try {
    const data = await API.apiFetch('/users/' + userId + '/');
    user = data;
  } catch (e) { showToast('Erreur: ' + e.message, 'error'); return; }
  editingTeacherId = user.id;
  populateTeacherSelects('et');
  document.getElementById('etFirstName').value = user.first_name || '';
  document.getElementById('etLastName').value = user.last_name || '';
  document.getElementById('etEmail').value = user.email || '';
  document.getElementById('etPhone').value = user.phone || '';
  document.getElementById('etCin').value = user.cin || '';
  document.getElementById('etGrade').value = user.grade || '';
  document.getElementById('etSpeciality').value = user.speciality || '';
  document.getElementById('etPassword').value = '';
  const assigned = user.assigned_class_ids || [];
  const sel = document.getElementById('etClasses');
  if (sel) Array.from(sel.options).forEach(o => { o.selected = assigned.includes(Number(o.value)); });
  openModal('modalEditTeacher');
}

async function toggleTeacherActive(id) {
  try {
    await API.apiFetch('/users/' + id + '/toggle-active/', { method: 'POST' });
    showToast('Statut mis à jour.', 'success');
    await loadTeachers();
  } catch (e) { showToast(e.message, 'error'); }
}

function setupEventListeners() {
  bindSearchInput('searchTeachers', renderTeachers);

  document.getElementById('btnOpenAddTeacher')?.addEventListener('click', async function () {
    editingTeacherId = null;
    populateTeacherSelects('t');
    document.getElementById('tFirstName').value = '';
    document.getElementById('tLastName').value = '';
    document.getElementById('tEmail').value = '';
    document.getElementById('tPhone').value = '';
    document.getElementById('tCin').value = '';
    document.getElementById('tGrade').value = '';
    document.getElementById('tSpeciality').value = '';
    document.getElementById('tPassword').value = '';
    openModal('modalAddTeacher');
  });

  document.getElementById('btnSubmitTeacher')?.addEventListener('click', async function () {
    const body = {
      first_name: document.getElementById('tFirstName').value.trim(),
      last_name: document.getElementById('tLastName').value.trim(),
      email: document.getElementById('tEmail').value.trim(),
      phone: document.getElementById('tPhone').value.trim(),
      cin: document.getElementById('tCin').value.trim() || undefined,
      grade: document.getElementById('tGrade').value.trim() || '',
      speciality: document.getElementById('tSpeciality').value.trim() || '',
      role: 'teacher',
      password: document.getElementById('tPassword').value || 'Pass@12345',
      assigned_class_ids: Array.from(document.getElementById('tClasses')?.selectedOptions || []).map(o => Number(o.value)),
    };
    if (!body.first_name || !body.last_name || !body.email) {
      showToast('Prénom, nom et email sont requis.', 'error'); return;
    }
    try {
      await API.apiFetch('/users/', { method: 'POST', body: JSON.stringify(body) });
      closeModal('modalAddTeacher');
      showToast('Enseignant créé !', 'success');
      await loadTeachers();
    } catch (e) { showToast(e.message, 'error'); }
  });

  document.getElementById('btnSubmitEditTeacher')?.addEventListener('click', async function () {
    const id = editingTeacherId;
    if (!id) { showToast('Erreur: ID manquant.', 'error'); return; }
    const body = {
      first_name: document.getElementById('etFirstName').value.trim(),
      last_name: document.getElementById('etLastName').value.trim(),
      email: document.getElementById('etEmail').value.trim(),
      phone: document.getElementById('etPhone').value.trim(),
      cin: document.getElementById('etCin').value.trim() || undefined,
      grade: document.getElementById('etGrade').value.trim() || '',
      speciality: document.getElementById('etSpeciality').value.trim() || '',
      assigned_class_ids: Array.from(document.getElementById('etClasses')?.selectedOptions || []).map(o => Number(o.value)),
    };
    const pwd = document.getElementById('etPassword').value;
    if (pwd) body.password = pwd;
    if (!body.first_name || !body.last_name || !body.email) {
      showToast('Prénom, nom et email sont requis.', 'error'); return;
    }
    try {
      await API.apiFetch('/users/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
      editingTeacherId = null;
      closeModal('modalEditTeacher');
      showToast('Enseignant modifié.', 'success');
      await loadTeachers();
    } catch (e) { showToast(e.message, 'error'); }
  });

  document.getElementById('btnDownloadTeacherImportTemplate')?.addEventListener('click', downloadTeacherTemplate);
  document.getElementById('btnDownloadTeacherImportTemplate2')?.addEventListener('click', downloadTeacherTemplate);
  document.getElementById('btnRunTeacherImport')?.addEventListener('click', runTeacherImport);
}

async function downloadTeacherTemplate() {
  showToast('Téléchargement du modèle...', 'info');
  try {
    const resp = await fetch('/api/v1/teachers/import-excel/template/', { headers: API._headers() });
    if (!resp.ok) throw new Error('Erreur téléchargement');
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'modele_import_enseignants.xlsx'; a.click();
    window.URL.revokeObjectURL(url);
  } catch (e) { showToast('Erreur: ' + e.message, 'error'); }
}

async function runTeacherImport() {
  const fileInput = document.getElementById('impTeacherFile');
  if (!fileInput.files.length) { showToast('Veuillez sélectionner un fichier.', 'error'); return; }
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  document.getElementById('impTeacherSpinner').style.display = 'inline-block';
  const reportDiv = document.getElementById('teacherImportReport');
  reportDiv.classList.add('hidden');
  try {
    const resp = await fetch('/api/v1/teachers/import-excel/', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + (API.getToken() || '') },
      body: formData,
    });
    const result = await resp.json();
    document.getElementById('impTeacherSpinner').style.display = 'none';
    if (!resp.ok) { showToast('Erreur: ' + (result.detail || 'Échec import'), 'error'); return; }
    reportDiv.innerHTML = '<pre>' + esc(JSON.stringify(result, null, 2)) + '</pre>';
    reportDiv.classList.remove('hidden');
    showToast('Import terminé !', 'success');
    await loadTeachers();
  } catch (e) {
    document.getElementById('impTeacherSpinner').style.display = 'none';
    showToast('Erreur: ' + e.message, 'error');
  }
}