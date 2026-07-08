/* ── Admin Students Page ── */
let currentModuleId = null;
let modulePage = 1;
let moduleTotalPages = 1;
let allNiveaux = [];

async function initPage() {
  await loadNiveaux();
  setupEventListeners();
}

async function loadNiveaux() {
  try {
    const data = await API.apiFetch('/curriculum/niveaux/');
    allNiveaux = Array.isArray(data) ? data : [];
    const selects = ['impNiveau', 'sNiveau'];
    selects.forEach(function (id) {
      const sel = document.getElementById(id);
      if (!sel) return;
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      allNiveaux.forEach(function (n) {
        sel.innerHTML += '<option value="' + esc(n.id) + '">' + esc(n.label) + '</option>';
      });
    });
  } catch (e) { showToast('Erreur niveaux: ' + e.message, 'error'); }
}

async function loadSemestres(niveau, prefix) {
  const sel = document.getElementById(prefix + 'Semestre');
  const spinner = document.getElementById(prefix + 'SemestreSpinner');
  if (spinner) spinner.style.display = 'inline-block';
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Chargement… —</option>';
  try {
    const data = await API.apiFetch('/curriculum/semestres-par-niveau/?niveau=' + encodeURIComponent(niveau));
    const sems = Array.isArray(data) ? data : [];
    sel.innerHTML = '<option value="">— Sélectionner —</option>';
    sems.forEach(function (s) { sel.innerHTML += '<option value="' + s.id + '">' + esc(s.name) + '</option>'; });
    sel.disabled = false;
  } catch (e) { showToast('Erreur semestres: ' + e.message, 'error'); }
  if (spinner) spinner.style.display = 'none';
  resetCascade(prefix, ['Filiere', 'Module']);
}

async function loadFilieres(semestreId, prefix) {
  const sel = document.getElementById(prefix + 'Filiere');
  const spinner = document.getElementById(prefix + 'FiliereSpinner');
  if (spinner) spinner.style.display = 'inline-block';
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Chargement… —</option>';
  try {
    const data = await API.apiFetch('/curriculum/filieres/?semestre_id=' + semestreId);
    const fils = Array.isArray(data) ? data : [];
    sel.innerHTML = '<option value="">— Sélectionner —</option>';
    fils.forEach(function (f) { sel.innerHTML += '<option value="' + f.id + '">' + esc(f.name) + '</option>'; });
    sel.disabled = false;
  } catch (e) { showToast('Erreur filières: ' + e.message, 'error'); }
  if (spinner) spinner.style.display = 'none';
  resetCascade(prefix, ['Module']);
}

async function loadModules(filiereId, prefix) {
  const sel = document.getElementById(prefix + 'Module');
  const spinner = document.getElementById(prefix + 'ModuleSpinner');
  if (spinner) spinner.style.display = 'inline-block';
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Chargement… —</option>';
  try {
    const data = await API.apiFetch('/curriculum/modules/?filiere_id=' + filiereId);
    const mods = Array.isArray(data) ? data : [];
    sel.innerHTML = '<option value="">— Sélectionner —</option>';
    mods.forEach(function (m) { sel.innerHTML += '<option value="' + m.id + '">' + esc(m.name) + '</option>'; });
    sel.disabled = false;
  } catch (e) { showToast('Erreur modules: ' + e.message, 'error'); }
  if (spinner) spinner.style.display = 'none';
  if (prefix === 'imp') {
    document.getElementById('btnRunImport').disabled = false;
  }
}

function resetCascade(prefix, fields) {
  fields.forEach(function (f) {
    const el = document.getElementById(prefix + f);
    if (el) { el.innerHTML = '<option value="">— Sélectionner —</option>'; el.disabled = true; }
  });
}

/* ── Module Students (paginated table) ── */
async function loadModuleStudents(moduleId, page) {
  currentModuleId = moduleId;
  modulePage = page || 1;
  const params = new URLSearchParams();
  params.set('module', moduleId);
  params.set('page', modulePage);
  const q = searchQuery('searchModuleStudents');
  if (q) params.set('search', q);
  const emailFilter = document.getElementById('filterModuleEmail')?.value || '';
  if (emailFilter) params.set('has_email', emailFilter);

  try {
    const data = await API.apiFetch('/students/by-module/?' + params.toString());
    const results = data.results || [];
    moduleTotalPages = Math.ceil(data.count / 20) || 1;
    document.getElementById('moduleStudentsHint').style.display = 'none';
    document.getElementById('moduleStudentsWrap').style.display = 'block';
    renderModuleStudents(results);
    updateModulePagination();
    const moduleName = document.getElementById('impModule')?.selectedOptions?.[0]?.text || document.getElementById('sModule')?.selectedOptions?.[0]?.text || 'Module #' + moduleId;
    document.getElementById('moduleStudentsTitle').textContent = 'Étudiants — ' + esc(moduleName);
  } catch (e) {
    showToast('Erreur: ' + e.message, 'error');
  }
}

function renderModuleStudents(students) {
  const tbody = document.getElementById('moduleStudentsBody');
  if (!students.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">Aucun étudiant inscrit.</td></tr>';
    return;
  }
  tbody.innerHTML = students.map(function (s, i) {
    return '<tr>' +
      '<td><span style="color:var(--muted)">' + ((modulePage - 1) * 20 + i + 1) + '</span></td>' +
      '<td><code>' + esc(s.code_massar) + '</code></td>' +
      '<td><strong>' + esc(s.first_name + ' ' + s.last_name) + '</strong></td>' +
      '<td>' + esc(s.email || '—') + '</td>' +
      '<td>' + esc(s.phone || '—') + '</td>' +
      '<td>' + esc(s.classe_name || '—') + '</td>' +
      '<td>' + (s.enrolled_at ? formatDate(s.enrolled_at) : '—') + '</td>' +
    '</tr>';
  }).join('');
}

function updateModulePagination() {
  const info = document.getElementById('modulePageInfo');
  if (info) info.textContent = 'Page ' + modulePage + ' / ' + moduleTotalPages;
  document.getElementById('btnModulePrev').disabled = modulePage <= 1;
  document.getElementById('btnModuleNext').disabled = modulePage >= moduleTotalPages;
  const wrap = document.getElementById('moduleStudentsPagination');
  if (wrap) wrap.classList.toggle('hidden', moduleTotalPages <= 1);
}

/* ── Import ── */
async function runStudentImport() {
  const moduleId = document.getElementById('impModule').value;
  if (!moduleId) { showToast('Veuillez sélectionner un module.', 'error'); return; }
  const fileInput = document.getElementById('impFile');
  if (!fileInput.files.length) { showToast('Veuillez sélectionner un fichier.', 'error'); return; }
  const formData = new FormData();
  formData.append('module_id', moduleId);
  formData.append('file', fileInput.files[0]);
  try {
    const resp = await fetch('/api/v1/students/import/', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + (API.getToken() || '') },
      body: formData,
    });
    const result = await resp.json();
    const reportDiv = document.getElementById('importReport');
    if (!resp.ok) {
      reportDiv.innerHTML = '<div class="error-msg">' + esc(result.detail || 'Échec import') + '</div>';
      reportDiv.classList.remove('hidden');
      return;
    }
    reportDiv.innerHTML = '<pre>' + esc(JSON.stringify(result, null, 2)) + '</pre>';
    reportDiv.classList.remove('hidden');
    showToast('Import terminé !', 'success');
    if (currentModuleId) await loadModuleStudents(currentModuleId);
  } catch (e) { showToast('Erreur: ' + e.message, 'error'); }
}

async function runCompleteImport() {
  const fileInput = document.getElementById('impCompleteFile');
  if (!fileInput.files.length) { showToast('Veuillez sélectionner un fichier.', 'error'); return; }
  document.getElementById('impCompleteSpinner').style.display = 'inline-block';
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  try {
    const resp = await fetch('/api/v1/students/import-complete/', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + (API.getToken() || '') },
      body: formData,
    });
    const result = await resp.json();
    document.getElementById('impCompleteSpinner').style.display = 'none';
    const reportDiv = document.getElementById('importCompleteReport');
    if (!resp.ok) {
      reportDiv.innerHTML = '<div class="error-msg">' + esc(result.detail || 'Échec import') + '</div>';
      reportDiv.classList.remove('hidden');
      return;
    }
    reportDiv.innerHTML = '<pre>' + esc(JSON.stringify(result, null, 2)) + '</pre>';
    reportDiv.classList.remove('hidden');
    showToast('Import complet terminé !', 'success');
  } catch (e) {
    document.getElementById('impCompleteSpinner').style.display = 'none';
    showToast('Erreur: ' + e.message, 'error');
  }
}

/* ── Add Student Modal ── */
async function submitAddStudent() {
  const body = {
    first_name: document.getElementById('sFirstName').value.trim(),
    last_name: document.getElementById('sLastName').value.trim(),
    code_massar: document.getElementById('sCode').value.trim(),
    email: document.getElementById('sEmail').value.trim() || '',
    password: document.getElementById('sPassword').value || '',
    module_id: parseInt(document.getElementById('sModule').value) || null,
  };
  if (!body.first_name || !body.last_name || !body.code_massar) {
    showToast('Prénom, nom et code Massar sont requis.', 'error'); return;
  }
  if (!body.module_id) { showToast('Veuillez sélectionner un module.', 'error'); return; }
  try {
    await API.apiFetch('/students/', { method: 'POST', body: JSON.stringify(body) });
    closeModal('modalAddStudent');
    showToast('Étudiant ajouté !', 'success');
    if (currentModuleId) await loadModuleStudents(currentModuleId);
  } catch (e) { showToast(e.message, 'error'); }
}

function setupEventListeners() {
  /* Import cascade */
  document.getElementById('impNiveau')?.addEventListener('change', function () {
    if (this.value) {
      const niv = allNiveaux.find(n => n.id === this.value);
      if (niv) loadSemestres(niv.id, 'imp');
    } else { resetCascade('imp', ['Semestre', 'Filiere', 'Module']); }
  });
  document.getElementById('impSemestre')?.addEventListener('change', function () {
    if (this.value) loadFilieres(this.value, 'imp');
  });
  document.getElementById('impFiliere')?.addEventListener('change', function () {
    if (this.value) loadModules(this.value, 'imp');
  });
  document.getElementById('impModule')?.addEventListener('change', function () {
    if (this.value) {
      currentModuleId = this.value;
      loadModuleStudents(this.value, 1);
    }
  });

  /* Add student cascade */
  document.getElementById('sNiveau')?.addEventListener('change', function () {
    if (this.value) {
      const niv = allNiveaux.find(n => n.id === this.value);
      if (niv) loadSemestres(niv.id, 's');
    } else { resetCascade('s', ['Semestre', 'Filiere', 'Module']); }
  });
  document.getElementById('sSemestre')?.addEventListener('change', function () {
    if (this.value) loadFilieres(this.value, 's');
  });
  document.getElementById('sFiliere')?.addEventListener('change', function () {
    if (this.value) loadModules(this.value, 's');
  });

  /* Buttons */
  document.getElementById('btnRunImport')?.addEventListener('click', runStudentImport);
  document.getElementById('btnRunCompleteImport')?.addEventListener('click', runCompleteImport);
  document.getElementById('btnSubmitStudent')?.addEventListener('click', submitAddStudent);

  document.getElementById('btnDownloadImportTemplate')?.addEventListener('click', async function () {
    try {
      const resp = await fetch('/api/v1/students/import/template/', { headers: API._headers() });
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'modele_import_etudiants.xlsx'; a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) { showToast('Erreur: ' + e.message, 'error'); }
  });

  document.getElementById('btnDownloadCompleteImportTemplate')?.addEventListener('click', async function () {
    try {
      const resp = await fetch('/api/v1/students/import-complete/template/', { headers: API._headers() });
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'import_etudiants_complet.xlsx'; a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) { showToast('Erreur: ' + e.message, 'error'); }
  });

  document.getElementById('btnOpenAddStudent')?.addEventListener('click', function () {
    document.getElementById('sFirstName').value = '';
    document.getElementById('sLastName').value = '';
    document.getElementById('sCode').value = '';
    document.getElementById('sEmail').value = '';
    document.getElementById('sPassword').value = '';
    openModal('modalAddStudent');
  });

  /* Pagination */
  document.getElementById('btnModulePrev')?.addEventListener('click', function () {
    if (modulePage > 1 && currentModuleId) loadModuleStudents(currentModuleId, modulePage - 1);
  });
  document.getElementById('btnModuleNext')?.addEventListener('click', function () {
    if (modulePage < moduleTotalPages && currentModuleId) loadModuleStudents(currentModuleId, modulePage + 1);
  });

  /* Search & filter */
  bindSearchInput('searchModuleStudents', function () {
    if (currentModuleId) loadModuleStudents(currentModuleId, 1);
  });
  document.getElementById('filterModuleEmail')?.addEventListener('change', function () {
    if (currentModuleId) loadModuleStudents(currentModuleId, 1);
  });
}