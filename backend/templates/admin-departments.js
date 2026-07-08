/* ── Admin Departments Page ── */
let allDepartments = [];
let editingDepartmentId = null;

async function initPage() {
  await loadDepartments();
  setupDepartmentUI();
  setupEventListeners();
}

async function loadDepartments() {
  try {
    const data = await API.apiFetch('/departments/');
    allDepartments = Array.isArray(data) ? data : (data.results || []);
    renderDepartments();
  } catch (e) {
    showToast('Erreur chargement départements: ' + esc(e.message), 'error');
  }
}

function renderDepartments() {
  const q = searchQuery('searchDepartments');
  const tbody = document.getElementById('departmentsBody');
  const list = allDepartments.filter(function (d) { return !q || d.name.toLowerCase().includes(q); });
  if (!list.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Aucun département trouvé.</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(function (d) {
    return '<tr>' +
      '<td>' + d.id + '</td>' +
      '<td><strong>' + esc(d.name) + '</strong></td>' +
      '<td>' + esc(d.head_name || '—') + '</td>' +
      '<td>' + (d.filiere_count || 0) + '</td>' +
      '<td><button class="btn sm outline" onclick="manageFiliereManagers(' + d.id + ')">🎯 Gérer</button></td>' +
      '<td class="actions-cell">' +
        '<button class="btn sm" onclick="editDepartment(' + d.id + ')">✏️ Modifier</button>' +
        '<button class="btn sm outline admin-only" onclick="deleteDepartment(' + d.id + ')">🗑️</button>' +
      '</td>' +
    '</tr>';
  }).join('');
}

async function loadDeptHeadSelect() {
  const sel = document.getElementById('deptHead');
  sel.innerHTML = '<option value="">— Non assigné —</option>';
  let teachers = [];
  try {
    const data = await API.apiFetch('/users/?role=teacher');
    teachers = Array.isArray(data) ? data : (data.results || []);
    const admins = await API.apiFetch('/users/?role=admin');
    const adminList = Array.isArray(admins) ? admins : (admins.results || []);
    teachers = teachers.concat(adminList);
  } catch (e) {
    teachers = [];
  }
  teachers.forEach(function (u) {
    const opt = document.createElement('option');
    opt.value = u.id;
    opt.textContent = (u.full_name || u.first_name + ' ' + u.last_name) + ' (' + u.email + ')';
    sel.appendChild(opt);
  });
}

function openDepartmentModal(dept) {
  document.getElementById('departmentForm').reset();
  editingDepartmentId = null;
  loadDeptHeadSelect();
  if (dept) {
    editingDepartmentId = dept.id;
    document.getElementById('departmentModalTitle').textContent = '✏️ Modifier ' + dept.name;
    document.getElementById('deptName').value = dept.name;
    if (dept.head) document.getElementById('deptHead').value = dept.head;
  } else {
    document.getElementById('departmentModalTitle').textContent = '➕ Nouveau département';
  }
  openModal('modalDepartment');
}

async function editDepartment(id) {
  const dept = allDepartments.find(function (d) { return d.id === id; });
  if (dept) openDepartmentModal(dept);
}

async function deleteDepartment(id) {
  if (!confirm('Supprimer ce département ?')) return;
  try {
    await API.apiFetch('/departments/' + id + '/', { method: 'DELETE' });
    showToast('Département supprimé', 'success');
    await loadDepartments();
  } catch (e) { showToast('Erreur: ' + esc(e.message), 'error'); }
}

async function saveDepartment() {
  const name = document.getElementById('deptName').value.trim();
  if (!name) { showToast('Le nom est requis', 'error'); return; }
  const head = document.getElementById('deptHead').value || null;
  const payload = { name: name, head: head };
  const method = editingDepartmentId ? 'PUT' : 'POST';
  const url = editingDepartmentId ? '/departments/' + editingDepartmentId + '/' : '/departments/';
  try {
    await API.apiFetch(url, { method: method, body: JSON.stringify(payload), headers: { 'Content-Type': 'application/json' } });
    showToast(editingDepartmentId ? 'Département modifié' : 'Département créé', 'success');
    closeModal('modalDepartment');
    await loadDepartments();
  } catch (e) { showToast('Erreur: ' + esc(e.message), 'error'); }
}

/* ── Filiere Managers ── */
let _currentDeptIdForManagers = null;

async function manageFiliereManagers(deptId) {
  _currentDeptIdForManagers = deptId;
  const dept = allDepartments.find(function (d) { return d.id === deptId; });
  document.getElementById('filiereManagersTitle').textContent = '🎯 Gérer les responsables — ' + (dept ? dept.name : 'Département #' + deptId);

  try {
    const filieres = await API.apiFetch('/curriculum/filieres/?department_id=' + deptId);
    const filieresList = Array.isArray(filieres) ? filieres : [];

    let eligible = [];
    try {
      const users = await API.apiFetch('/users/');
      eligible = Array.isArray(users) ? users : (users.results || []);
    } catch (e) { eligible = []; }

    const tbody = document.getElementById('filiereManagersBody');
    if (!filieresList.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="3">Aucune filière dans ce département.</td></tr>';
      document.getElementById('btnSaveFiliereManagers').disabled = true;
      openModal('modalFiliereManagers');
      return;
    }

    tbody.innerHTML = filieresList.map(function (f) {
      const currentManagerId = f.manager_id || '';
      let currentManagerName = '';
      if (currentManagerId) {
        const u = eligible.find(function (x) { return String(x.id) === String(currentManagerId); });
        currentManagerName = u ? (u.full_name || u.first_name + ' ' + u.last_name) : '#' + currentManagerId;
      }
      let options = '<option value="">— Non assigné —</option>';
      const eligibleUsers = eligible.filter(function (u) {
        return u.role === 'teacher' || u.role === 'program_manager' || u.role === 'admin';
      });
      eligibleUsers.forEach(function (u) {
        const selected = String(u.id) === String(currentManagerId) ? ' selected' : '';
        options += '<option value="' + u.id + '"' + selected + '>' + esc(u.full_name || u.first_name + ' ' + u.last_name) + ' (' + esc(u.email) + ')</option>';
      });
      return '<tr>' +
        '<td><strong>' + esc(f.name) + '</strong></td>' +
        '<td>' + esc(currentManagerName || '—') + '</td>' +
        '<td><select class="filiere-manager-select" data-filiere-id="' + f.id + '" style="width:100%">' + options + '</select></td>' +
      '</tr>';
    }).join('');

    document.getElementById('btnSaveFiliereManagers').disabled = false;
    openModal('modalFiliereManagers');
  } catch (e) {
    showToast('Erreur: ' + esc(e.message), 'error');
  }
}

document.getElementById('btnSaveFiliereManagers')?.addEventListener('click', async function () {
  const selects = document.querySelectorAll('.filiere-manager-select');
  let successCount = 0;
  let errorCount = 0;
  for (let i = 0; i < selects.length; i++) {
    const sel = selects[i];
    const filiereId = sel.dataset.filiereId;
    const managerId = sel.value || null;
    try {
      await API.apiFetch('/curriculum/filieres/' + parseInt(filiereId) + '/', {
        method: 'PATCH',
        body: JSON.stringify({ manager_id: managerId ? parseInt(managerId) : null }),
        headers: { 'Content-Type': 'application/json' },
      });
      successCount++;
    } catch (e) { errorCount++; }
  }
  showToast(successCount + ' mis à jour' + (errorCount ? ', ' + errorCount + ' erreur(s).' : '.'), errorCount ? 'error' : 'success');
  closeModal('modalFiliereManagers');
  await loadDepartments();
});

function setupDepartmentUI() {
  const isRestricted = currentUser.role === 'department_head' || currentUser.role === 'program_manager';
  if (isRestricted) {
    const deptBtn = document.getElementById('btnOpenAddDepartment');
    if (deptBtn) deptBtn.style.display = 'none';
  }
  document.getElementById('btnOpenAddDepartment')?.addEventListener('click', function () {
    openDepartmentModal(null);
  });
  document.getElementById('departmentForm')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    await saveDepartment();
  });
}

function setupEventListeners() {
  bindSearchInput('searchDepartments', renderDepartments);
}