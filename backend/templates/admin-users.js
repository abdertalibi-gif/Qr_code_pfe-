/* ── Admin Users Page ── */
let allUsers = [];
let allClasses = [];
let allDepartments = [];
let allFilieres = [];

async function initPage() {
  await Promise.all([loadUsers(), loadDepartments(), loadFilieres(), loadClasses()]);
  setupEventListeners();
}

async function loadUsers() {
  try {
    const data = await API.apiFetch('/users/');
    allUsers = Array.isArray(data) ? data : (data.results || []);
    renderUsers();
  } catch (e) {
    document.getElementById('usersBody').innerHTML =
      '<tr class="empty-row"><td colspan="6">Erreur: ' + esc(e.message) + '</td></tr>';
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

const roleLabel = {
  admin: 'Admin',
  teacher: 'Enseignant',
  student: 'Étudiant',
  department_head: 'Chef de département',
  program_manager: 'Responsable de filière',
};

function renderUsers() {
  const tbody = document.getElementById('usersBody');
  const query = searchQuery('searchUsers');
  const filtered = allUsers.filter(u => matchesQuery(
    query,
    u.first_name, u.last_name, u.first_name + ' ' + u.last_name,
    u.email, u.role, roleLabel[u.role]
  ));
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="6">' + (query ? 'Aucun résultat.' : 'Aucun utilisateur.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((u, i) => '<tr>' +
    '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
    '<td><strong>' + esc(u.first_name) + ' ' + esc(u.last_name) + '</strong></td>' +
    '<td style="color:var(--muted)">' + esc(u.email) + '</td>' +
    '<td><span class="badge badge-' + u.role + '">' + (roleLabel[u.role] || u.role) + '</span></td>' +
    '<td><span class="badge ' + (u.is_active ? 'badge-present' : 'badge-absent') + '">' + (u.is_active ? 'Actif' : 'Inactif') + '</span></td>' +
    '<td class="actions-cell">' +
      '<button class="btn sm outline" onclick="openEditUser(' + u.id + ')">Modifier</button>' +
      '<button class="btn sm outline" onclick="toggleUserActive(' + u.id + ')">' + (u.is_active ? 'Désactiver' : 'Activer') + '</button>' +
      '<button class="btn sm outline" style="color:var(--red)" onclick="deleteUser(' + u.id + ')">Supprimer</button>' +
    '</td>' +
  '</tr>').join('');
}

/* ─── Role-based field visibility ─── */

function showFieldsForRole(role, prefix) {
  const suffix = prefix === 'u' ? '' : '-edit';
  document.querySelectorAll('.role-field' + suffix).forEach(function (el) {
    const roles = (el.dataset.roles || '').split(',');
    el.style.display = roles.includes(role) ? 'block' : 'none';
  });
}

function populateRoleSelects(prefix) {
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
  const studentClasseSel = document.getElementById(prefix + 'StudentClasse');
  if (studentClasseSel) {
    studentClasseSel.innerHTML = '<option value="">— Sélectionner —</option>' +
      allClasses.map(c => '<option value="' + c.id + '">' + esc(c.name) + '</option>').join('');
  }
  const studentFiliereSel = document.getElementById(prefix + 'StudentFiliere');
  if (studentFiliereSel) {
    studentFiliereSel.innerHTML = '<option value="">— Sélectionner —</option>' +
      allFilieres.map(f => '<option value="' + f.id + '">' + esc(f.name) + '</option>').join('');
  }
}

/* ─── CRUD ─── */

async function openEditUser(id) {
  let u;
  try {
    const data = await API.apiFetch('/users/' + id + '/');
    u = data;
  } catch (e) { showToast('Erreur: ' + e.message, 'error'); return; }

  populateRoleSelects('eu');
  document.getElementById('euId').value = u.id;
  document.getElementById('euFirstName').value = u.first_name;
  document.getElementById('euLastName').value = u.last_name;
  document.getElementById('euEmail').value = u.email;
  document.getElementById('euRole').value = u.role;
  document.getElementById('euPassword').value = '';
  document.getElementById('euPhone').value = u.phone || '';
  document.getElementById('euCin').value = u.cin || '';
  document.getElementById('euGrade').value = u.grade || '';
  document.getElementById('euSpeciality').value = u.speciality || '';
  showFieldsForRole(u.role, 'eu');

  const deptSel = document.getElementById('euDepartment');
  if (u.managed_department && deptSel) deptSel.value = u.managed_department.id;
  const filSel = document.getElementById('euFiliere');
  if (u.managed_filieres && u.managed_filieres.length && filSel) filSel.value = u.managed_filieres[0].id;

  const assigned = u.assigned_class_ids || [];
  const sel = document.getElementById('euClasses');
  if (sel) Array.from(sel.options).forEach(o => { o.selected = assigned.includes(Number(o.value)); });

  openModal('modalEditUser');
}

async function toggleUserActive(id) {
  try {
    await API.apiFetch('/users/' + id + '/toggle-active/', { method: 'POST' });
    showToast('Statut mis à jour.', 'success');
    await loadUsers();
  } catch (e) { showToast(e.message, 'error'); }
}

async function deleteUser(id) {
  if (!confirm('Supprimer cet utilisateur ?')) return;
  try {
    await API.apiFetch('/users/' + id + '/', { method: 'DELETE' });
    showToast('Utilisateur supprimé.', 'success');
    await loadUsers();
  } catch (e) { showToast(e.message, 'error'); }
}

function buildPayload(prefix) {
  const body = {
    first_name: document.getElementById(prefix + 'FirstName').value.trim(),
    last_name: document.getElementById(prefix + 'LastName').value.trim(),
    email: document.getElementById(prefix + 'Email').value.trim(),
    role: document.getElementById(prefix + 'Role').value,
  };
  const passwordEl = document.getElementById(prefix + 'Password');
  if (passwordEl && passwordEl.value) body.password = passwordEl.value;

  const role = body.role;
  if (role === 'teacher' || role === 'department_head' || role === 'program_manager') {
    const classSel = document.getElementById(prefix + 'Classes');
    if (classSel) {
      body.assigned_class_ids = Array.from(classSel.selectedOptions).map(o => Number(o.value));
    }
  }
  if (role === 'department_head') {
    const deptEl = document.getElementById(prefix + 'Department');
    body.department_id = deptEl ? Number(deptEl.value) || null : null;
  }
  if (role === 'program_manager') {
    const filEl = document.getElementById(prefix + 'Filiere');
    body.filiere_id = filEl ? Number(filEl.value) || null : null;
  }
  if (role === 'teacher') {
    const phoneEl = document.getElementById(prefix + 'Phone');
    if (phoneEl) body.phone = phoneEl.value.trim();
    const cinEl = document.getElementById(prefix + 'Cin');
    if (cinEl) body.cin = cinEl.value.trim() || undefined;
    const gradeEl = document.getElementById(prefix + 'Grade');
    if (gradeEl) body.grade = gradeEl.value.trim() || '';
    const specEl = document.getElementById(prefix + 'Speciality');
    if (specEl) body.speciality = specEl.value.trim() || '';
  }
  if (role === 'student') {
    const cm = document.getElementById(prefix + 'CodeMassar');
    if (cm) body.code_massar = cm.value.trim();
    const ca = document.getElementById(prefix + 'CodeApogee');
    if (ca) body.code_apogee = ca.value.trim();
  }
  return body;
}

async function populateRoleFilieresByDept(prefix, deptId) {
  const filSel = document.getElementById(prefix + 'Filiere');
  if (!filSel) return;
  if (!deptId) {
    filSel.innerHTML = '<option value="">— Sélectionner —</option>' +
      allFilieres.map(f => '<option value="' + f.id + '">' + esc(f.name) + '</option>').join('');
    return;
  }
  try {
    const data = await API.apiFetch('/curriculum/filieres/?department_id=' + deptId);
    const items = Array.isArray(data) ? data : [];
    filSel.innerHTML = '<option value="">— Sélectionner —</option>' +
      items.map(f => '<option value="' + f.id + '">' + esc(f.name) + '</option>').join('');
  } catch (e) {
    filSel.innerHTML = '<option value="">Erreur de chargement</option>';
  }
}

function setupProgManagerCascade(prefix) {
  const deptSel = document.getElementById(prefix + 'Department');
  const roleSel = document.getElementById(prefix + 'Role');
  if (deptSel && roleSel) {
    deptSel.addEventListener('change', function () {
      const role = roleSel.value;
      if (role === 'program_manager') {
        populateRoleFilieresByDept(prefix, this.value);
      }
    });
  }
}

function setupEventListeners() {
  bindSearchInput('searchUsers', renderUsers);

  /* Create form role change */
  document.getElementById('uRole')?.addEventListener('change', function (e) {
    showFieldsForRole(e.target.value, 'u');
  });

  /* Edit form role change */
  document.getElementById('euRole')?.addEventListener('change', function (e) {
    showFieldsForRole(e.target.value, 'eu');
  });

  /* Open create modal */
  document.getElementById('btnOpenAddUser')?.addEventListener('click', async function () {
    populateRoleSelects('u');
    showFieldsForRole(document.getElementById('uRole').value, 'u');
    setupProgManagerCascade('u');
    openModal('modalAddUser');
  });

  /* Submit create */
  document.getElementById('btnSubmitUser')?.addEventListener('click', async function () {
    const body = buildPayload('u');
    if (!body.first_name || !body.last_name || !body.email || !body.password) {
      showToast('Prénom, nom, email et mot de passe sont requis.', 'error'); return;
    }
    if (body.role === 'department_head' && !body.department_id) {
      showToast('Le département est obligatoire pour le chef de département.', 'error'); return;
    }
    if (body.role === 'program_manager' && !body.filiere_id) {
      showToast('La filière est obligatoire pour le responsable de filière.', 'error'); return;
    }
    try {
      await API.apiFetch('/users/', { method: 'POST', body: JSON.stringify(body) });
      closeModal('modalAddUser');
      showToast('Utilisateur créé !', 'success');
      ['uFirstName','uLastName','uEmail','uPassword','uCodeMassar','uCodeApogee'].forEach(function (id) {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      await loadUsers();
    } catch (e) { showToast(e.message, 'error'); }
  });

  /* Submit edit */
  document.getElementById('btnSubmitEditUser')?.addEventListener('click', async function () {
    const id = document.getElementById('euId').value;
    const body = buildPayload('eu');
    if (!body.first_name || !body.last_name || !body.email) {
      showToast('Prénom, nom et email sont requis.', 'error'); return;
    }
    try {
      await API.apiFetch('/users/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
      closeModal('modalEditUser');
      showToast('Utilisateur mis à jour.', 'success');
      await loadUsers();
    } catch (e) { showToast(e.message, 'error'); }
  });

  setupProgManagerCascade('u');
  setupProgManagerCascade('eu');
}