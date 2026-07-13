/* ── Admin Workload / Monthly Report Page ── */
let allTeachers = [];
let allSemestres = [];
let allFilieres = [];
let allDepartments = [];

function esc(str) {
  if (str == null) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function initPage() {
  await Promise.all([loadSemestres(), loadFilieres(), loadDepartments(), loadTeachers()]);
  populateYears();
  onFilterChange();
}

async function loadSemestres() {
  try {
    const data = await API.apiFetch('/semestres/');
    allSemestres = Array.isArray(data) ? data : (data.results || []);
    const sel = document.getElementById('wlSemestre');
    sel.innerHTML = '<option value="">Tous les semestres</option>' +
      allSemestres.map(s => '<option value="' + s.id + '">' + esc(s.name) + '</option>').join('');
  } catch (e) { /* ignore */ }
}

async function loadFilieres() {
  try {
    const data = await API.apiFetch('/filieres/');
    allFilieres = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { /* ignore */ }
}

async function loadDepartments() {
  try {
    const data = await API.apiFetch('/departments/');
    allDepartments = Array.isArray(data) ? data : (data.results || []);
    const sel = document.getElementById('wlDepartment');
    sel.innerHTML = '<option value="">Tous les départements</option>' +
      allDepartments.map(d => '<option value="' + d.id + '">' + esc(d.name) + '</option>').join('');
  } catch (e) { /* ignore */ }
}

async function loadTeachers() {
  try {
    const data = await API.apiFetch('/teachers/');
    allTeachers = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { /* ignore */ }
}

function populateYears() {
  const sel = document.getElementById('wlYear');
  const cur = new Date().getFullYear();
  let html = '<option value="">—</option>';
  for (let y = cur; y >= cur - 5; y--) {
    html += '<option value="' + y + '">' + y + '</option>';
  }
  sel.innerHTML = html;
  sel.value = String(cur);
  document.getElementById('wlMonth').value = String(new Date().getMonth() + 1);
}

function onPeriodModeChange() {
  const mode = document.getElementById('wlPeriodMode').value;
  const monthGroup = document.getElementById('wlMonthGroup');
  const yearGroup = document.getElementById('wlYearGroup');
  const dateStartGroup = document.getElementById('wlDateStartGroup');
  const dateEndGroup = document.getElementById('wlDateEndGroup');
  if (mode === 'month') {
    monthGroup.style.display = '';
    yearGroup.style.display = '';
    dateStartGroup.style.display = 'none';
    dateEndGroup.style.display = 'none';
  } else {
    monthGroup.style.display = 'none';
    yearGroup.style.display = 'none';
    dateStartGroup.style.display = '';
    dateEndGroup.style.display = '';
  }
  onFilterChange();
}

function onSemestreChange() {
  const semId = document.getElementById('wlSemestre').value;
  const sel = document.getElementById('wlFiliere');
  let html = '<option value="">Toutes les filières</option>';
  if (semId) {
    allFilieres
      .filter(f => String(f.semestre_id || f.semestre) === semId)
      .forEach(f => { html += '<option value="' + f.id + '">' + esc(f.name) + '</option>'; });
    sel.disabled = false;
  } else {
    allFilieres.forEach(f => { html += '<option value="' + f.id + '">' + esc(f.name) + '</option>'; });
    sel.disabled = false;
  }
  sel.innerHTML = html;
  onFilterChange();
}

function onFiliereChange() {
  updateTeacherOptions();
  onFilterChange();
}

function updateTeacherOptions() {
  const deptId = document.getElementById('wlDepartment').value;
  const filId = document.getElementById('wlFiliere').value;
  const sel = document.getElementById('wlTeacher');
  let html = '<option value="">Tous les enseignants</option>';
  let filtered = allTeachers;
  if (filId) {
    /* Try to match teachers whose department is in the filiere's department */
    const filiere = allFilieres.find(f => String(f.id) === filId);
    if (filiere) {
      filtered = filtered.filter(t => {
        /* t.department_name comes from /teachers/ endpoint */
        return String(t.department_id || t.department) === String(filiere.department_id || filiere.department);
      });
    }
  } else if (deptId) {
    filtered = filtered.filter(t => String(t.department_id || t.department) === deptId);
  }
  filtered.forEach(t => {
    html += '<option value="' + t.id + '">' + esc(t.full_name || t.first_name + ' ' + t.last_name) + '</option>';
  });
  sel.innerHTML = html;
}

function onFilterChange() {
  const deptId = document.getElementById('wlDepartment').value;
  const semId = document.getElementById('wlSemestre').value;
  const filId = document.getElementById('wlFiliere').value;
  const teacherId = document.getElementById('wlTeacher').value;
  const mode = document.getElementById('wlPeriodMode').value;
  const month = document.getElementById('wlMonth').value;
  const year = document.getElementById('wlYear').value;
  const dateStart = document.getElementById('wlDateStart').value;
  const dateEnd = document.getElementById('wlDateEnd').value;

  const hasMonthFilter = mode === 'month' && month && year;
  const hasRangeFilter = mode === 'range' && dateStart;
  document.getElementById('btnGenerateReport').disabled = !(hasMonthFilter || hasRangeFilter);
}

/* ── Preview (optional) / Generate Excel ── */
async function buildQueryString() {
  const params = new URLSearchParams();
  const deptId = document.getElementById('wlDepartment').value;
  const semId = document.getElementById('wlSemestre').value;
  const filId = document.getElementById('wlFiliere').value;
  const teacherId = document.getElementById('wlTeacher').value;
  const mode = document.getElementById('wlPeriodMode').value;
  const month = document.getElementById('wlMonth').value;
  const year = document.getElementById('wlYear').value;
  const dateStart = document.getElementById('wlDateStart').value;
  const dateEnd = document.getElementById('wlDateEnd').value;

  if (deptId) params.set('department_id', deptId);
  if (semId) params.set('semestre_id', semId);
  if (filId) params.set('filiere_id', filId);
  if (teacherId) params.set('teacher_id', teacherId);
  if (mode === 'month') {
    if (month) params.set('month', month);
    if (year) params.set('year', year);
  } else {
    if (dateStart) params.set('start_date', dateStart);
    if (dateEnd) params.set('end_date', dateEnd);
  }
  return params.toString();
}

document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('btnGenerateReport').addEventListener('click', async function () {
    const qs = await buildQueryString();
    const token = API.getToken();
    const url = '/api/v1/teacher-monthly-report/?' + qs;
    try {
      const resp = await fetch(url, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Erreur inconnue' }));
        showToast('Erreur: ' + (err.detail || resp.statusText), 'error');
        return;
      }
      const blob = await resp.blob();
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      const month = document.getElementById('wlMonth').value;
      const year = document.getElementById('wlYear').value;
      link.download = 'Charge_Horaire_Enseignants_' + (month || 'MM') + '_' + (year || 'YYYY') + '.xlsx';
      link.click();
      URL.revokeObjectURL(link.href);
      showToast('Rapport généré avec succès !', 'success');
    } catch (e) {
      showToast('Erreur réseau: ' + e.message, 'error');
    }
  });
});

/* Export for page init (called by admin_base.html after auth check) */
if (typeof initPage === 'function') window.initPage = initPage;
