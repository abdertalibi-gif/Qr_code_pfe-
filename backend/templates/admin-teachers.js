/* ── Admin Teachers Page ── */
let allTeachers = [];
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
        <div class="card-value">${result.imported ?? result.summary?.created ?? result.created_teachers?.length ?? 0}</div>
      </div>
    </div>
    <div class="summary-card warning">
      <div class="card-icon">🔄</div>
      <div class="card-content">
        <div class="card-label">Déjà existants</div>
        <div class="card-value">${result.updated ?? result.summary?.updated ?? result.updated_teachers?.length ?? 0}</div>
      </div>
    </div>
    <div class="summary-card error">
      <div class="card-icon">❌</div>
      <div class="card-content">
        <div class="card-label">Erreurs</div>
        <div class="card-value">${result.summary?.errors ?? result.errors?.length ?? 0}</div>
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
  await loadTeachers();
  setupEventListeners();
}

async function initTeachersTab(userRole) {
  currentUserRole = userRole || 'admin';
  await initPage();
}

async function loadTeachers() {
  try {
    const data = await API.apiFetch('/teachers/');
    allTeachers = Array.isArray(data) ? data : (data.results || []);
    renderTeachers();
  } catch (e) {
    document.getElementById('teachersBody').innerHTML =
      '<tr class="empty-row"><td colspan="10">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

function renderTeachers() {
  const tbody = document.getElementById('teachersBody');
  const q = searchQuery('searchTeachers');
  const filtered = allTeachers.filter(t => matchesQuery(q, t.full_name, t.first_name, t.last_name, t.email, t.cin || ''));
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="10">' + (q ? 'Aucun résultat.' : 'Aucun enseignant.') + '</td></tr>';
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
    '<td>' + esc(t.grade || '—') + '</td>' +
    '<td>' + esc(t.speciality || '—') + '</td>' +
    '<td><span class="badge ' + (t.is_active === false ? 'badge-absent' : 'badge-present') + '">' + (t.is_active === false ? 'Inactif' : 'Actif') + '</span></td>' +
    (isRestricted
      ? '<td class="actions-cell"></td>'
      : '<td class="actions-cell admin-only">' +
        '<button class="btn sm outline admin-only" onclick="openEditTeacher(' + t.id + ')">Modifier</button>' +
        '<button class="btn sm outline admin-only" onclick="toggleTeacherActive(' + t.id + ')">' + (t.is_active === false ? 'Activer' : 'Désactiver') + '</button>' +
      '</td>') +
  '</tr>').join('');
}

async function openEditTeacher(userId) {
  let user;
  try {
    const data = await API.apiFetch('/users/' + userId + '/');
    user = data;
  } catch (e) { showToast('Erreur: ' + e.message, 'error'); return; }
  editingTeacherId = user.id;
  if (typeof populateRoleSelects === 'function') populateRoleSelects('eu');
  document.getElementById('euId').value = user.id;
  document.getElementById('euFirstName').value = user.first_name || '';
  document.getElementById('euLastName').value = user.last_name || '';
  document.getElementById('euEmail').value = user.email || '';
  document.getElementById('euRole').value = 'teacher';
  document.getElementById('euPassword').value = '';
  document.getElementById('euPhone').value = user.phone || '';
  document.getElementById('euCin').value = user.cin || '';
  document.getElementById('euGrade').value = user.grade || '';
  document.getElementById('euSpeciality').value = user.speciality || '';
  if (typeof showFieldsForRole === 'function') showFieldsForRole('teacher', 'eu');
  openModal('modalEditUser');
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
    if (typeof populateRoleSelects === 'function') populateRoleSelects('u');
    document.getElementById('uFirstName').value = '';
    document.getElementById('uLastName').value = '';
    document.getElementById('uEmail').value = '';
    document.getElementById('uPassword').value = '';
    document.getElementById('uPhone').value = '';
    document.getElementById('uCin').value = '';
    document.getElementById('uGrade').value = '';
    document.getElementById('uSpeciality').value = '';
    document.getElementById('uRole').value = 'teacher';
    if (typeof showFieldsForRole === 'function') showFieldsForRole('teacher', 'u');
    openModal('modalAddUser');
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