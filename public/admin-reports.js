/* ── Admin Reports Page ── */
let allSemestres = [];
let allFilieres = [];
let allModules = [];
let allClasses = [];
let allTeachers = [];

async function initPage() {
  await Promise.all([loadSemestres(), loadFilieres(), loadTeachers()]);
  setupEventListeners();
  const today = new Date().toISOString().split('T')[0];
  const firstDay = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
  document.getElementById('repStartDate').value = firstDay;
  document.getElementById('repEndDate').value = today;
}

async function loadSemestres() {
  try {
    const data = await API.apiFetch('/curriculum/semestres/');
    allSemestres = Array.isArray(data) ? data : [];
    const sel = document.getElementById('repSemestre');
    sel.innerHTML = '<option value="">— Tous —</option>';
    allSemestres.forEach(function (s) {
      sel.innerHTML += '<option value="' + s.id + '">' + esc(s.name) + '</option>';
    });
  } catch (e) { showToast('Erreur semestres: ' + e.message, 'error'); }
}

async function loadFilieres() {
  try {
    const data = await API.apiFetch('/curriculum/filieres/');
    allFilieres = Array.isArray(data) ? data : [];
  } catch (e) { allFilieres = []; }
}

async function loadTeachers() {
  try {
    const data = await API.apiFetch('/users/?role=teacher');
    allTeachers = Array.isArray(data) ? data : (data.results || []);
    const sel = document.getElementById('repEnseignant');
    sel.innerHTML = '<option value="">— Tous les enseignants —</option>';
    allTeachers.forEach(function (t) {
      sel.innerHTML += '<option value="' + t.id + '">' + esc(t.full_name || t.first_name + ' ' + t.last_name) + '</option>';
    });
  } catch (e) { allTeachers = []; }
}

function repLoadFilieres(semestreId) {
  const sel = document.getElementById('repFiliere');
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Tous —</option>';
  const filtered = semestreId ? allFilieres.filter(function (f) { return String(f.semestre_id) === String(semestreId); }) : allFilieres;
  filtered.forEach(function (f) {
    sel.innerHTML += '<option value="' + f.id + '">' + esc(f.name) + '</option>';
  });
  sel.disabled = false;
  repLoadModules('');
}

async function repLoadModules(filiereId) {
  const sel = document.getElementById('repModule');
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Tous —</option>';
  if (!filiereId) { sel.disabled = false; repLoadClasses(''); return; }
  allModules = [];
  try {
    const data = await API.apiFetch('/curriculum/modules/?filiere_id=' + filiereId);
    allModules = Array.isArray(data) ? data : [];
    allModules.forEach(function (m) {
      sel.innerHTML += '<option value="' + m.id + '">' + esc(m.name) + '</option>';
    });
  } catch (e) { /* silently fail */ }
  sel.disabled = false;
  repLoadClasses('');
}

async function repLoadClasses(filiereId) {
  const sel = document.getElementById('repClasse');
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Toutes —</option>';
  if (!filiereId) {
    allClasses.forEach(function (c) {
      sel.innerHTML += '<option value="' + c.id + '">' + esc(c.name) + '</option>';
    });
    sel.disabled = false;
    return;
  }
  try {
    let data = await API.apiFetch('/classes/?filiere_id=' + filiereId);
    allClasses = Array.isArray(data) ? data : (data.results || []);
    allClasses.forEach(function (c) {
      sel.innerHTML += '<option value="' + c.id + '">' + esc(c.name) + '</option>';
    });
  } catch (e) { /* silently fail */ }
  sel.disabled = false;
}

async function generateReport() {
  const startDate = document.getElementById('repStartDate').value;
  const endDate = document.getElementById('repEndDate').value;
  if (!startDate || !endDate) { showToast('Les dates de début et fin sont requises.', 'error'); return; }

  const params = new URLSearchParams();
  params.set('start_date', startDate);
  params.set('end_date', endDate);
  const semestre = document.getElementById('repSemestre').value;
  const filiere = document.getElementById('repFiliere').value;
  const moduleId = document.getElementById('repModule').value;
  const classeId = document.getElementById('repClasse').value;
  const type = document.getElementById('repType').value;
  const mode = document.getElementById('repMode').value;
  const enseignant = document.getElementById('repEnseignant').value;
  if (semestre) params.set('semestre', semestre);
  if (filiere) params.set('filiere', filiere);
  if (moduleId) params.set('module', moduleId);
  if (classeId) params.set('classe_id', classeId);
  if (type) params.set('export_type', type);
  if (mode) params.set('export_mode', mode);
  if (enseignant) params.set('enseignant_id', enseignant);

  const progressArea = document.getElementById('repProgressArea');
  progressArea.style.display = 'block';
  document.getElementById('repSpinner').style.display = 'inline-block';
  document.getElementById('repProgressText').textContent = 'Génération du fichier Excel en cours...';
  document.getElementById('btnGenerateReport').disabled = true;

  try {
    const resp = await fetch('/attendance/export-wizard/?' + params.toString(), {
      headers: { 'Authorization': 'Bearer ' + (API.getToken() || '') },
    });
    if (!resp.ok) {
      const err = await resp.json().catch(function () { return { detail: 'Erreur ' + resp.status }; });
      throw new Error(err.detail || 'Erreur génération');
    }
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'rapport_presence_' + startDate + '_' + endDate + '.xlsx';
    a.click();
    window.URL.revokeObjectURL(url);
    showToast('Rapport généré !', 'success');
  } catch (e) {
    showToast('Erreur: ' + e.message, 'error');
  }
  progressArea.style.display = 'none';
  document.getElementById('btnGenerateReport').disabled = false;
}

function setupEventListeners() {
  document.getElementById('repSemestre')?.addEventListener('change', function () {
    repLoadFilieres(this.value);
  });
  document.getElementById('repFiliere')?.addEventListener('change', function () {
    repLoadModules(this.value);
  });
  document.getElementById('repModule')?.addEventListener('change', function () {
    const filiere = document.getElementById('repFiliere').value;
    repLoadClasses(filiere || '');
  });

  document.getElementById('btnGenerateReport')?.addEventListener('click', generateReport);

  document.getElementById('btnOpenExportWizard')?.addEventListener('click', function () {
    const now = new Date();
    document.getElementById('repEndDate').value = now.toISOString().split('T')[0];
    const past = new Date(now.getTime() - 30 * 86400000);
    document.getElementById('repStartDate').value = past.toISOString().split('T')[0];
  });
}