/* ── Admin Curriculum Page (Subjects/Modules) ── */
let allSubjects = [];
let allFilieres = [];
let allSemestres = [];

async function initPage() {
  await Promise.all([loadSubjects(), loadFilieres(), loadSemestres()]);
  setupEventListeners();
}

async function loadSubjects() {
  try {
    const data = await API.apiFetch('/curriculum/subjects/');
    allSubjects = Array.isArray(data) ? data : (data.results || []);
    renderSubjects();
  } catch (e) {
    document.getElementById('curriculumBody').innerHTML =
      '<tr class="empty-row"><td colspan="8">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

async function loadFilieres() {
  try {
    const data = await API.apiFetch('/curriculum/filieres/');
    allFilieres = Array.isArray(data) ? data : (data.results || []);
    const sel = document.getElementById('filterSubjectFiliere');
    if (sel) {
      sel.innerHTML = '<option value="">Toutes les filières</option>' +
        allFilieres.map(f => '<option value="' + f.id + '">' + esc(f.name) + '</option>').join('');
    }
  } catch (e) { allFilieres = []; }
}

async function loadSemestres() {
  try {
    const data = await API.apiFetch('/curriculum/semestres/');
    allSemestres = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { allSemestres = []; }
}

function renderSubjects() {
  const tbody = document.getElementById('curriculumBody');
  const q = searchQuery('searchSubjects');
  const filtreFiliere = document.getElementById('filterSubjectFiliere')?.value || '';
  const filtered = allSubjects.filter(s =>
    matchesQuery(q, s.name, s.code, s.filiere_name || '') &&
    (!filtreFiliere || String(s.filiere_id) === filtreFiliere)
  );
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="8">' + (q ? 'Aucun résultat.' : 'Aucune matière.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((s, i) => '<tr>' +
    '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
    '<td><strong>' + esc(s.name) + '</strong></td>' +
    '<td><code>' + esc(s.code || '—') + '</code></td>' +
    '<td>' + esc(s.filiere_name || '—') + '</td>' +
    '<td>' + (s.coefficient ?? '—') + '</td>' +
    '<td>' + (s.total_hours || '—') + '</td>' +
    '<td>' + (s.teacher_name || '—') + '</td>' +
    '<td class="actions-cell">' +
      '<button class="btn sm outline" onclick="openEditSubject(' + s.id + ')">Modifier</button>' +
      '<button class="btn sm outline" style="color:var(--red)" onclick="deleteSubject(' + s.id + ')">Supprimer</button>' +
    '</td>' +
  '</tr>').join('');
}

async function populateSubjectForm() {
  const filSel = document.getElementById('subFiliere');
  filSel.innerHTML = '<option value="">— Sélectionner —</option>' +
    allFilieres.map(f => '<option value="' + f.id + '">' + esc(f.name) + '</option>').join('');

  const semSel = document.getElementById('subSemestre');
  semSel.innerHTML = '<option value="">— Sélectionner —</option>' +
    allSemestres.map(s => '<option value="' + s.id + '">' + esc(s.name) + '</option>').join('');

  try {
    const data = await API.apiFetch('/users/?role=teacher');
    const teachers = Array.isArray(data) ? data : (data.results || []);
    const tSel = document.getElementById('subTeacher');
    tSel.innerHTML = '<option value="">— Non assigné —</option>' +
      teachers.map(t => '<option value="' + t.id + '">' + esc(t.full_name || t.first_name + ' ' + t.last_name) + '</option>').join('');
  } catch (e) { }
}

async function openEditSubject(id) {
  const s = allSubjects.find(x => x.id === id);
  if (!s) return;
  await populateSubjectForm();
  document.getElementById('subId').value = s.id;
  document.getElementById('subjectModalTitle').textContent = 'Modifier la matière';
  document.getElementById('subName').value = s.name || '';
  document.getElementById('subCode').value = s.code || '';
  if (s.filiere_id) document.getElementById('subFiliere').value = s.filiere_id;
  if (s.semestre_id) document.getElementById('subSemestre').value = s.semestre_id;
  if (s.teacher) document.getElementById('subTeacher').value = s.teacher;
  document.getElementById('subCoefficient').value = s.coefficient || 1;
  document.getElementById('subHours').value = s.total_hours || '';
  openModal('modalSubject');
}

async function deleteSubject(id) {
  if (!confirm('Supprimer cette matière ?')) return;
  try {
    await API.apiFetch('/curriculum/subjects/' + id + '/', { method: 'DELETE' });
    showToast('Matière supprimée.', 'success');
    await loadSubjects();
  } catch (e) { showToast(e.message, 'error'); }
}

function setupEventListeners() {
  bindSearchInput('searchSubjects', renderSubjects);
  document.getElementById('filterSubjectFiliere')?.addEventListener('change', renderSubjects);

  document.getElementById('btnRefreshCurriculum')?.addEventListener('click', loadSubjects);

  document.getElementById('btnOpenAddSubject')?.addEventListener('click', async () => {
    await populateSubjectForm();
    document.getElementById('subId').value = '';
    document.getElementById('subjectModalTitle').textContent = 'Ajouter une matière';
    document.getElementById('subName').value = '';
    document.getElementById('subCode').value = '';
    document.getElementById('subCoefficient').value = 1;
    document.getElementById('subHours').value = '';
    openModal('modalSubject');
  });

  document.getElementById('btnSubmitSubject')?.addEventListener('click', async () => {
    const id = document.getElementById('subId').value;
    const body = {
      name: document.getElementById('subName').value.trim(),
      code: document.getElementById('subCode').value.trim() || undefined,
      filiere_id: document.getElementById('subFiliere').value || null,
      semestre_id: document.getElementById('subSemestre').value || null,
      teacher: document.getElementById('subTeacher').value || null,
      coefficient: parseInt(document.getElementById('subCoefficient').value) || 1,
      total_hours: document.getElementById('subHours').value || null,
    };
    if (!body.name || !body.filiere_id) {
      showToast('Nom et filière sont requis.', 'error'); return;
    }
    try {
      if (id) {
        await API.apiFetch('/curriculum/subjects/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
      } else {
        await API.apiFetch('/curriculum/subjects/', { method: 'POST', body: JSON.stringify(body) });
      }
      closeModal('modalSubject');
      showToast('Matière enregistrée.', 'success');
      await loadSubjects();
    } catch (e) { showToast(e.message, 'error'); }
  });
}