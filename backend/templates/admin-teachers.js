/* ── Admin Teachers Page ── */
let allTeachers = [];
let teacherClasses = [];
let editingTeacherId = null;
let currentUserRole = 'admin';

/* ── Import Report Display ── */
function displayTeacherImportReport(result, containerId) {
  const reportDiv = document.getElementById(containerId);
  if (!reportDiv) return;

  reportDiv.innerHTML = '';
  reportDiv.classList.remove('hidden');

  // Display import summary cards at the top
  const summaryContainer = document.createElement('div');
  summaryContainer.className = 'import-summary-cards';
  summaryContainer.innerHTML = `
    <div class="summary-card success">
      <div class="card-icon">✅</div>
      <div class="card-content">
        <div class="card-label">Nouveaux inscrits</div>
        <div class="card-value">${result.created_teachers || result.created?.length || 0}</div>
      </div>
    </div>
    <div class="summary-card warning">
      <div class="card-icon">🔄</div>
      <div class="card-content">
        <div class="card-label">Déjà existants</div>
        <div class="card-value">${result.updated_teachers || result.updated?.length || 0}</div>
      </div>
    </div>
    <div class="summary-card error">
      <div class="card-icon">❌</div>
      <div class="card-content">
        <div class="card-label">Erreurs</div>
        <div class="card-value">${result.errors?.length || 0}</div>
      </div>
    </div>
  `;
  reportDiv.appendChild(summaryContainer);

  // Display detailed error table if there are errors
  if (result.errors && result.errors.length > 0) {
    const errorTableContainer = document.createElement('div');
    errorTableContainer.className = 'error-table-container';
    errorTableContainer.innerHTML = `
      <div class="error-table-header">
        <h4>Détail des Erreurs</h4>
      </div>
      <div class="error-table-wrapper">
        <table class="error-table">
          <thead>
            <tr>
              <th style="width: 80px;">Ligne</th>
              <th style="width: 120px;">Type</th>
              <th style="width: 120px;">Champ</th>
              <th>Message</th>
              <th style="width: 120px;">Valeur</th>
            </tr>
          </thead>
          <tbody>
            ${result.errors.map(error => {
              const rowNumber = error.line || '—';
              const type = error.code ? error.code : (error.type || 'Erreur');
              const field = error.field || error.code || '—';
              const message = error.messages && error.messages.join ? error.messages.join(', ') : (Array.isArray(error.messages) ? error.messages.join(', ') : (error.messages || '—'));
              const value = error.value || '—';
              const typeBadgeClass = type === 'Erreur' ? 'error' : type === 'Avertissement' ? 'warning' : type === 'Succès' ? 'success' : '';
              const typeDisplay = type === 'Erreur' ? '🔴 Erreur' : type === 'Avertissement' ? '🟠 Avertissement' : type === 'Succès' ? '🟢 Succès' : type;
              return `
                <tr>
                  <td>${rowNumber}</td>
                  <td><span class="error-badge ${type === 'Erreur' ? 'error' : type === 'Avertissement' ? 'warning' : type === 'Succès' ? 'success' : ''}">${typeDisplay}</span></td>
                  <td>${field}</td>
                  <td class="error-message-cell">${esc(message)}</td>
                  <td>${esc(value)}</td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
    reportDiv.appendChild(errorTableContainer);
  }

  // Show raw JSON in collapsed section for debugging
  const rawJsonSection = document.createElement('div');
  rawJsonSection.className = 'raw-json-section';
  rawJsonSection.innerHTML = `
    <div class="raw-json-toggle" onclick="this.nextSibling.style.display = this.nextSibling.style.display === 'none' ? 'block' : 'none';">
      <span>Débogage: Afficher/Cacher les données brutes</span>
    </div>
    <div class="raw-json-content" style="display: none;">
      <pre>${esc(JSON.stringify(result, null, 2))}</pre>
    </div>
  `;
  reportDiv.appendChild(rawJsonSection);
}

// Helper function to escape HTML strings
function esc(str) {
  if (typeof str !== 'string') return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

// Helper function to match search query
function matchesQuery(q, ...fields) {
  if (!q) return true;
  const lower = q.toLowerCase();
  return fields.some(f => f && f.toString().toLowerCase().includes(lower));
}

// Helper function to get search query value
function searchQuery(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}

async function initPage() {
  await Promise.all([loadTeachers(), teacherLoadClasses()]);
  setupEventListeners();
}

async function initTeachersTab(userRole) {
  currentUserRole = userRole || 'admin';
  await initPage();
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

async function teacherLoadClasses() {
  try {
    const data = await API.apiFetch('/classes/');
    teacherClasses = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { teacherClasses = []; }
}

function renderTeachers() {
  const tbody = document.getElementById('teachersBody');
  const q = searchQuery('searchTeachers');
  const filtered = allTeachers.filter(t => matchesQuery(q, t.full_name, t.first_name, t.last_name, t.email, t.cin || ''));
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="12">' + (q ? 'Aucun résultat.' : 'Aucun enseignant.') + '</td></tr>';
    return;
  }
  const isRestricted = currentUserRole === 'department_head' || currentUserRole === 'program_manager';
  tbody.innerHTML = filtered.map((t, i) => '<tr>' +
    '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
    '<td><strong>' + esc(t.full_name || t.first_name + ' ' + t.last_name) + '</strong></td>' +
    '<td>' + esc(t.email) + '</td>' +
    '<td>' + esc(t.phone || '—') + '</td>' +
    '<td>' + esc(t.cin || '—') + '</td>' +
    '<td>' + esc((t.department_name || t.department) || '—') + '</td>' +
    '<td>' + esc((t.filiere_name || t.filiere) || '—') + '</td>' +
    '<td>' + esc(t.grade || '—') + '</td>' +
    '<td>' + esc(t.speciality || '—') + '</td>' +
    '<td>' + (t.class_count ?? (t.assigned_class_ids ? t.assigned_class_ids.length : '—')) + '</td>' +
    '<td><span class="badge ' + (t.is_active === false ? 'badge-absent' : 'badge-present') + '">' + (t.is_active === false ? 'Inactif' : 'Actif') + '</span></td>' +
    (isRestricted
      ? '<td class="actions-cell"></td>'
      : '<td class="actions-cell admin-only">' +
        '<button class="btn sm outline admin-only" onclick="openEditTeacher(' + t.id + ')">Modifier</button>' +
        '<button class="btn sm outline admin-only" onclick="toggleTeacherActive(' + t.id + ')">' + (t.is_active === false ? 'Activer' : 'Désactiver') + '</button>' +
      '</td>') +
  '</tr>').join('');
}

function populateTeacherSelects(prefix) {
  const classSel = document.getElementById(prefix + 'Classes');
  if (classSel) {
    classSel.innerHTML = teacherClasses.map(c =>
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
    const token = API.getToken();
    const resp = await fetch('/api/v1/teachers/import-excel/template/', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!resp.ok) throw new Error('Erreur téléchargement');
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'teacher_import_template.xlsx'; a.click();
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
    displayTeacherImportReport(result, 'teacherImportReport');
    showToast('Import terminé !', 'success');
    await loadTeachers();
  } catch (e) {
    document.getElementById('impTeacherSpinner').style.display = 'none';
    showToast('Erreur: ' + e.message, 'error');
  }
}