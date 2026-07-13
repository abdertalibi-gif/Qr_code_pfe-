/* ── Admin Workload / Monthly Report Page ── */
let wlNiveaux = [];
let wlSemestres = [];
let wlFilieres = [];
let wlModules = [];
let wlAllTeachers = [];

function esc(str) {
  if (str == null) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function initPage() {
  await loadNiveaux();
  populateYears();
  wlOnFilterChange();
}

async function loadNiveaux() {
  try {
    const data = await API.apiFetch('/curriculum/niveaux/');
    wlNiveaux = Array.isArray(data) ? data : (data.results || []);
  } catch (e) {
    wlNiveaux = [];
  }
  const sel = document.getElementById('wlNiveau');
  if (!sel) return;
  sel.innerHTML = '<option value="">Tous les niveaux</option>';
  wlNiveaux.forEach(function (n) {
    sel.innerHTML += '<option value="' + esc(n.value || n.id || n) + '">' + esc(n.label || n.name || n.display || n) + '</option>';
  });
}

function populateYears() {
  const sel = document.getElementById('wlYear');
  if (!sel) return;
  const cur = new Date().getFullYear();
  let html = '<option value="">—</option>';
  for (let y = cur; y >= cur - 5; y--) {
    html += '<option value="' + y + '">' + y + '</option>';
  }
  sel.innerHTML = html;
  sel.value = String(cur);
  const mSel = document.getElementById('wlMonth');
  if (mSel) mSel.value = String(new Date().getMonth() + 1);
}

/* ── Cascade handlers ── */

function wlOnNiveauChange() {
  const niveau = document.getElementById('wlNiveau').value;
  const semSel = document.getElementById('wlSemestre');
  const filSel = document.getElementById('wlFiliere');
  const modSel = document.getElementById('wlModule');
  const teaSel = document.getElementById('wlTeacher');

  semSel.innerHTML = '<option value="">Chargement…</option>';
  semSel.disabled = true;
  filSel.innerHTML = '<option value="">— Sélectionnez d'abord le semestre —</option>';
  filSel.disabled = true;
  modSel.innerHTML = '<option value="">— Sélectionnez d'abord la filière —</option>';
  modSel.disabled = true;
  teaSel.innerHTML = '<option value="">Tous les enseignants</option>';
  teaSel.disabled = true;

  if (!niveau) {
    // Load ALL semestres when no niveau selected
    API.apiFetch('/curriculum/semestres/').then(function (data) {
      wlSemestres = Array.isArray(data) ? data : (data.results || []);
      semSel.innerHTML = '<option value="">Tous les semestres</option>';
      wlSemestres.forEach(function (s) {
        semSel.innerHTML += '<option value="' + s.id + '">' + esc(s.name) + '</option>';
      });
      semSel.disabled = false;
    }).catch(function () {
      semSel.innerHTML = '<option value="">— Erreur —</option>';
    });
  } else {
    API.apiFetch('/curriculum/semestres-par-niveau/?niveau=' + encodeURIComponent(niveau)).then(function (data) {
      wlSemestres = Array.isArray(data) ? data : (data.results || []);
      semSel.innerHTML = '<option value="">Tous les semestres</option>';
      wlSemestres.forEach(function (s) {
        semSel.innerHTML += '<option value="' + s.id + '">' + esc(s.name) + '</option>';
      });
      semSel.disabled = wlSemestres.length === 0;
      if (wlSemestres.length === 0) semSel.innerHTML = '<option value="">Aucun semestre</option>';
    }).catch(function () {
      semSel.innerHTML = '<option value="">— Erreur —</option>';
    });
  }
  wlOnFilterChange();
}

function wlOnSemestreChange() {
  const niveau = document.getElementById('wlNiveau').value;
  const semId = document.getElementById('wlSemestre').value;
  const filSel = document.getElementById('wlFiliere');
  const modSel = document.getElementById('wlModule');
  const teaSel = document.getElementById('wlTeacher');

  filSel.innerHTML = '<option value="">Chargement…</option>';
  filSel.disabled = true;
  modSel.innerHTML = '<option value="">— Sélectionnez d'abord la filière —</option>';
  modSel.disabled = true;
  teaSel.innerHTML = '<option value="">Tous les enseignants</option>';
  teaSel.disabled = true;

  let url = '/curriculum/filieres/?';
  if (semId) url += 'semestre_id=' + semId + '&';
  if (niveau) url += 'niveau=' + encodeURIComponent(niveau) + '&';
  API.apiFetch(url).then(function (data) {
    wlFilieres = Array.isArray(data) ? data : (data.results || []);
    filSel.innerHTML = '<option value="">Toutes les filières</option>';
    wlFilieres.forEach(function (f) {
      filSel.innerHTML += '<option value="' + f.id + '">' + esc(f.name) + '</option>';
    });
    filSel.disabled = wlFilieres.length === 0;
    if (wlFilieres.length === 0) filSel.innerHTML = '<option value="">Aucune filière</option>';
  }).catch(function () {
    filSel.innerHTML = '<option value="">— Erreur —</option>';
  });
  wlOnFilterChange();
}

function wlOnFiliereChange() {
  const filId = document.getElementById('wlFiliere').value;
  const modSel = document.getElementById('wlModule');
  const teaSel = document.getElementById('wlTeacher');

  modSel.innerHTML = '<option value="">Chargement…</option>';
  modSel.disabled = true;
  teaSel.innerHTML = '<option value="">Tous les enseignants</option>';
  teaSel.disabled = true;

  if (!filId) {
    modSel.innerHTML = '<option value="">Tous les modules</option>';
    modSel.disabled = false;
    wlModules = [];
    wlLoadTeachers();
    wlOnFilterChange();
    return;
  }

  API.apiFetch('/curriculum/modules/?filiere_id=' + filId).then(function (data) {
    wlModules = Array.isArray(data) ? data : (data.results || []);
    modSel.innerHTML = '<option value="">Tous les modules</option>';
    wlModules.forEach(function (m) {
      modSel.innerHTML += '<option value="' + m.id + '">' + esc(m.name) + '</option>';
    });
    modSel.disabled = wlModules.length === 0;
    if (wlModules.length === 0) modSel.innerHTML = '<option value="">Aucun module</option>';
    wlLoadTeachers();
  }).catch(function () {
    modSel.innerHTML = '<option value="">— Erreur —</option>';
  });
  wlOnFilterChange();
}

function wlOnModuleChange() {
  wlLoadTeachers();
  wlOnFilterChange();
}

/* ── Teacher loading ── */

function wlLoadTeachers() {
  const sel = document.getElementById('wlTeacher');
  if (!sel) return;
  API.apiFetch('/teachers/').then(function (data) {
    wlAllTeachers = Array.isArray(data) ? data : (data.results || []);
    wlUpdateTeacherOptions();
  }).catch(function () {});
}

function wlUpdateTeacherOptions() {
  const sel = document.getElementById('wlTeacher');
  if (!sel) return;
  const filId = document.getElementById('wlFiliere').value;
  const modId = document.getElementById('wlModule').value;
  let filtered = wlAllTeachers;

  if (modId && wlModules.length) {
    const mod = wlModules.find(function (m) { return String(m.id) === modId; });
    if (mod && mod.filiere_id) {
      filtered = filtered.filter(function (t) { return String(t.department_id || t.department) === String(mod.department_id || mod.department); });
    }
  } else if (filId && wlFilieres.length) {
    const fil = wlFilieres.find(function (f) { return String(f.id) === filId; });
    if (fil) {
      filtered = filtered.filter(function (t) { return String(t.department_id || t.department) === String(fil.department_id || fil.department); });
    }
  }

  sel.innerHTML = '<option value="">Tous les enseignants</option>' +
    filtered.map(function (t) {
      return '<option value="' + t.id + '">' + esc(t.full_name || t.first_name + ' ' + t.last_name) + '</option>';
    }).join('');
  sel.disabled = false;
}

/* ── Period & filter change ── */

function wlOnPeriodModeChange() {
  const mode = document.getElementById('wlPeriodMode').value;
  document.getElementById('wlMonthGroup').style.display = mode === 'month' ? '' : 'none';
  document.getElementById('wlYearGroup').style.display = mode === 'month' ? '' : 'none';
  document.getElementById('wlDateStartGroup').style.display = mode === 'range' ? '' : 'none';
  document.getElementById('wlDateEndGroup').style.display = mode === 'range' ? '' : 'none';
  wlOnFilterChange();
}

function wlOnFilterChange() {
  const mode = document.getElementById('wlPeriodMode').value;
  const month = document.getElementById('wlMonth').value;
  const year = document.getElementById('wlYear').value;
  const dateStart = document.getElementById('wlDateStart').value;
  const hasPeriod = (mode === 'month' && month && year) || (mode === 'range' && dateStart);
  document.getElementById('btnGenerateReport').disabled = !hasPeriod;
  document.getElementById('btnGenerateReportPdf').disabled = !hasPeriod;
}

/* ── Export helpers ── */

async function wlExport(format) {
  const params = new URLSearchParams();
  const niveau = document.getElementById('wlNiveau').value;
  const semId = document.getElementById('wlSemestre').value;
  const filId = document.getElementById('wlFiliere').value;
  const modId = document.getElementById('wlModule').value;
  const teacherId = document.getElementById('wlTeacher').value;
  const mode = document.getElementById('wlPeriodMode').value;

  if (niveau) params.set('niveau', niveau);
  if (semId) params.set('semestre_id', semId);
  if (filId) params.set('filiere_id', filId);
  if (modId) params.set('module_id', modId);
  if (teacherId) params.set('teacher_id', teacherId);
  if (mode === 'month') {
    const m = document.getElementById('wlMonth').value;
    const y = document.getElementById('wlYear').value;
    if (m) params.set('month', m);
    if (y) params.set('year', y);
  } else {
    const ds = document.getElementById('wlDateStart').value;
    const de = document.getElementById('wlDateEnd').value;
    if (ds) params.set('start_date', ds);
    if (de) params.set('end_date', de);
  }
  params.set('format', format);

  const token = API.getToken();
  const url = '/api/v1/teacher-monthly-report/?' + params.toString();
  try {
    const resp = await fetch(url, {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!resp.ok) {
      const err = await resp.json().catch(function () { return { detail: 'Erreur inconnue' }; });
      showToast('Erreur: ' + (err.detail || resp.statusText), 'error');
      return;
    }
    const blob = await resp.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    const month = document.getElementById('wlMonth').value;
    const year = document.getElementById('wlYear').value;
    const ext = format === 'pdf' ? 'pdf' : 'xlsx';
    link.download = 'Charge_Horaire_Enseignants_' + (month || 'MM') + '_' + (year || 'YYYY') + '.' + ext;
    link.click();
    URL.revokeObjectURL(link.href);
    showToast('Rapport généré avec succès !', 'success');
  } catch (e) {
    showToast('Erreur réseau: ' + e.message, 'error');
  }
}

document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('btnGenerateReport').addEventListener('click', function () { wlExport('xlsx'); });
  document.getElementById('btnGenerateReportPdf').addEventListener('click', function () { wlExport('pdf'); });
});

if (typeof initPage === 'function') window.initPage = initPage;
