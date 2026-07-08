/* ── Admin Classes Page ── */
let allClasses = [];
let allTeachers = [];
let allFilieres = [];
let allDepartments = [];

async function initPage() {
  await Promise.all([loadClasses(), loadTeachers(), loadFilieres(), loadDepartments()]);
  setupEventListeners();
}

async function loadClasses() {
  try {
    const data = await API.apiFetch('/classes/');
    allClasses = Array.isArray(data) ? data : (data.results || []);
    renderClasses();
  } catch (e) {
    document.getElementById('classesBody').innerHTML =
      '<tr class="empty-row"><td colspan="7">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

async function loadTeachers() {
  try {
    const data = await API.apiFetch('/users/?role=teacher');
    allTeachers = Array.isArray(data) ? data : (data.results || []);
    const adminData = await API.apiFetch('/users/?role=admin');
    const admins = Array.isArray(adminData) ? adminData : (adminData.results || []);
    allTeachers = allTeachers.concat(admins);
  } catch (e) { allTeachers = []; }
}

async function loadFilieres() {
  try {
    const data = await API.apiFetch('/curriculum/filieres/');
    allFilieres = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { allFilieres = []; }
}

async function loadDepartments() {
  try {
    const data = await API.apiFetch('/departments/');
    allDepartments = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { allDepartments = []; }
}

function renderClasses() {
  const tbody = document.getElementById('classesBody');
  const q = searchQuery('searchClasses');
  const filtered = allClasses.filter(c => matchesQuery(q, c.name, c.code, c.department_name || ''));
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">' + (q ? 'Aucun résultat.' : 'Aucune classe.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((c, i) => '<tr>' +
    '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
    '<td><strong>' + esc(c.name) + '</strong></td>' +
    '<td><code>' + esc(c.code || '—') + '</code></td>' +
    '<td>' + esc(c.department_name || '—') + '</td>' +
    '<td>' + esc(c.teacher_name || '—') + '</td>' +
    '<td>' + (c.student_count ?? '—') + '</td>' +
    '<td class="actions-cell">' +
      '<button class="btn sm outline" onclick="openEditClass(' + c.id + ')">Modifier</button>' +
      '<button class="btn sm outline" style="color:var(--red)" onclick="deleteClass(' + c.id + ')">Supprimer</button>' +
    '</td>' +
  '</tr>').join('');
}

async function populateClassForm() {
  const deptSel = document.getElementById('cDepartment');
  deptSel.innerHTML = '<option value="">— Sélectionner —</option>' +
    allDepartments.map(d => '<option value="' + d.id + '">' + esc(d.name) + '</option>').join('');

  const teacherSel = document.getElementById('cTeacher');
  teacherSel.innerHTML = '<option value="">— Non assigné —</option>' +
    allTeachers.map(t => '<option value="' + t.id + '">' + esc(t.full_name || t.first_name + ' ' + t.last_name) + '</option>').join('');
}

async function openEditClass(id) {
  const c = allClasses.find(x => x.id === id);
  if (!c) return;
  await populateClassForm();
  document.getElementById('classId').value = c.id;
  document.getElementById('classModalTitle').textContent = 'Modifier la classe';
  document.getElementById('cName').value = c.name || '';
  document.getElementById('cCode').value = c.code || '';
  if (c.department_id) document.getElementById('cDepartment').value = c.department_id;
  if (c.teacher) document.getElementById('cTeacher').value = c.teacher;
  document.getElementById('cLevel').value = c.level || '';
  openModal('modalClass');
}

async function deleteClass(id) {
  if (!confirm('Supprimer cette classe ?')) return;
  try {
    await API.apiFetch('/classes/' + id + '/', { method: 'DELETE' });
    showToast('Classe supprimée.', 'success');
    await loadClasses();
  } catch (e) { showToast(e.message, 'error'); }
}

function setupEventListeners() {
  bindSearchInput('searchClasses', renderClasses);

  document.getElementById('btnOpenAddClass')?.addEventListener('click', async () => {
    await populateClassForm();
    document.getElementById('classId').value = '';
    document.getElementById('classModalTitle').textContent = 'Ajouter une classe';
    document.getElementById('cName').value = '';
    document.getElementById('cCode').value = '';
    document.getElementById('cLevel').value = '';
    openModal('modalClass');
  });

  document.getElementById('btnSubmitClass')?.addEventListener('click', async () => {
    const id = document.getElementById('classId').value;
    const body = {
      name: document.getElementById('cName').value.trim(),
      code: document.getElementById('cCode').value.trim() || undefined,
      department_id: document.getElementById('cDepartment').value || null,
      teacher: document.getElementById('cTeacher').value || null,
      level: document.getElementById('cLevel').value || '',
    };
    if (!body.name) { showToast('Le nom est requis.', 'error'); return; }
    try {
      if (id) {
        await API.apiFetch('/classes/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
      } else {
        await API.apiFetch('/classes/', { method: 'POST', body: JSON.stringify(body) });
      }
      closeModal('modalClass');
      showToast('Classe enregistrée.', 'success');
      await loadClasses();
    } catch (e) { showToast(e.message, 'error'); }
  });
}