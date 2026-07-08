/* ── Admin Filieres Page ── */
let allFilieres = [];
let allSemestres = [];
let allDepartments = [];

async function initPage() {
  await Promise.all([loadFilieres(), loadSemestres(), loadDepartments()]);
  setupEventListeners();
}

async function loadFilieres() {
  try {
    const data = await API.apiFetch('/curriculum/filieres/');
    allFilieres = Array.isArray(data) ? data : (data.results || []);
    renderFilieres();
  } catch (e) {
    document.getElementById('filieresBody').innerHTML =
      '<tr class="empty-row"><td colspan="7">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

async function loadSemestres() {
  try {
    const data = await API.apiFetch('/curriculum/semestres/');
    allSemestres = Array.isArray(data) ? data : (data.results || []);
    const sel = document.getElementById('filterFiliereSemestre');
    if (sel) {
      sel.innerHTML = '<option value="">Tous les semestres</option>' +
        allSemestres.map(s => '<option value="' + s.id + '">' + esc(s.name) + '</option>').join('');
    }
  } catch (e) { allSemestres = []; }
}

async function loadDepartments() {
  try {
    const data = await API.apiFetch('/departments/');
    allDepartments = Array.isArray(data) ? data : (data.results || []);
  } catch (e) { allDepartments = []; }
}

async function loadUsersForManagerSelect() {
  try {
    const data = await API.apiFetch('/users/?role=teacher');
    let users = Array.isArray(data) ? data : (data.results || []);
    const adminData = await API.apiFetch('/users/?role=admin');
    const admins = Array.isArray(adminData) ? adminData : (adminData.results || []);
    users = users.concat(admins);
    return users;
  } catch (e) { return []; }
}

function renderFilieres() {
  const tbody = document.getElementById('filieresBody');
  const query = searchQuery('searchFilieres');
  const semestreFilter = document.getElementById('filterFiliereSemestre')?.value || '';
  const filtered = allFilieres.filter(f =>
    matchesQuery(query, f.name, f.semestre_name || '', f.niveau || '', f.department_name || '') &&
    (!semestreFilter || String(f.semestre) === semestreFilter)
  );
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">' + (query ? 'Aucun résultat.' : 'Aucune filière.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((f, i) => '<tr>' +
    '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
    '<td><strong>' + esc(f.name) + '</strong></td>' +
    '<td>' + esc(f.semestre_name || '—') + '</td>' +
    '<td>' + esc(f.niveau || '—') + '</td>' +
    '<td>' + esc(f.manager_name || '—') + '</td>' +
    '<td>' + (f.module_count ?? '—') + '</td>' +
    '<td class="actions-cell">' +
      '<button class="btn sm outline" onclick="openEditFiliere(' + f.id + ')">Modifier</button>' +
      '<button class="btn sm outline" style="color:var(--red)" onclick="deleteFiliere(' + f.id + ')">Supprimer</button>' +
    '</td>' +
  '</tr>').join('');
}

async function populateFiliereFormSelects() {
  const semSel = document.getElementById('fSemestre');
  semSel.innerHTML = '<option value="">— Sélectionner —</option>' +
    allSemestres.map(s => '<option value="' + s.id + '">' + esc(s.name) + '</option>').join('');

  const deptSel = document.getElementById('fDepartment');
  deptSel.innerHTML = '<option value="">— Sélectionner —</option>' +
    allDepartments.map(d => '<option value="' + d.id + '">' + esc(d.name) + '</option>').join('');

  const users = await loadUsersForManagerSelect();
  const mgrSel = document.getElementById('fManager');
  mgrSel.innerHTML = '<option value="">— Non assigné —</option>' +
    users.map(u => '<option value="' + u.id + '">' + esc(u.full_name || u.first_name + ' ' + u.last_name) + ' (' + esc(u.email) + ')</option>').join('');
}

function openEditFiliere(id) {
  const f = allFilieres.find(x => x.id === id);
  if (!f) return;
  populateFiliereFormSelects().then(() => {
    document.getElementById('fId').value = f.id;
    document.getElementById('filiereModalTitle').textContent = 'Modifier la filière';
    document.getElementById('fName').value = f.name || '';
    if (f.semestre) document.getElementById('fSemestre').value = f.semestre;
    document.getElementById('fNiveau').value = f.niveau || '';
    if (f.department_id) document.getElementById('fDepartment').value = f.department_id;
    if (f.manager_id) document.getElementById('fManager').value = f.manager_id;
    openModal('modalFiliere');
  });
}

async function deleteFiliere(id) {
  if (!confirm('Supprimer cette filière ?')) return;
  try {
    await API.apiFetch('/curriculum/filieres/' + id + '/', { method: 'DELETE' });
    showToast('Filière supprimée.', 'success');
    await loadFilieres();
  } catch (e) { showToast(e.message, 'error'); }
}

function setupEventListeners() {
  bindSearchInput('searchFilieres', renderFilieres);
  document.getElementById('filterFiliereSemestre')?.addEventListener('change', renderFilieres);

  document.getElementById('btnRefreshFilieres')?.addEventListener('click', loadFilieres);

  document.getElementById('btnSubmitFiliere')?.addEventListener('click', async () => {
    const id = document.getElementById('fId').value;
    const body = {
      name: document.getElementById('fName').value.trim(),
      semestre: document.getElementById('fSemestre').value || null,
      niveau: document.getElementById('fNiveau').value || '',
      department_id: document.getElementById('fDepartment').value || null,
      manager_id: document.getElementById('fManager').value || null,
    };
    if (!body.name || !body.semestre) {
      showToast('Nom et semestre sont requis.', 'error'); return;
    }
    try {
      if (id) {
        await API.apiFetch('/curriculum/filieres/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
      } else {
        await API.apiFetch('/curriculum/filieres/', { method: 'POST', body: JSON.stringify(body) });
      }
      closeModal('modalFiliere');
      showToast('Filière enregistrée.', 'success');
      await loadFilieres();
    } catch (e) { showToast(e.message, 'error'); }
  });
}