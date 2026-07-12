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
    const data = await API.apiFetch('/users/?role=program_manager');
    return Array.isArray(data) ? data : (data.results || []);
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
      '<button class="btn sm outline admin-only" onclick="openManageModules(' + f.id + ')">📦 Modules</button>' +
      '<button class="btn sm outline admin-only" onclick="openEditFiliere(' + f.id + ')">Modifier</button>' +
      '<button class="btn sm outline admin-only" style="color:var(--red)" onclick="deleteFiliere(' + f.id + ')">Supprimer</button>' +
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

  const fiSemestreGroup = document.getElementById('fSemestre')?.closest('.field');

  document.getElementById('btnOpenAddFiliere')?.addEventListener('click', async function () {
    await populateFiliereFormSelects();
    document.getElementById('fId').value = '';
    document.getElementById('filiereModalTitle').textContent = 'Ajouter une filière';
    document.getElementById('fName').value = '';
    document.getElementById('fNiveau').value = '';
    if (fiSemestreGroup) fiSemestreGroup.style.display = 'none';
    openModal('modalFiliere');
  });

  window.openEditFiliere = function (id) {
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
      if (fiSemestreGroup) fiSemestreGroup.style.display = '';
      openModal('modalFiliere');
    });
  };

  document.getElementById('btnSubmitFiliere')?.addEventListener('click', async () => {
    const id = document.getElementById('fId').value;
    const body = {
      name: document.getElementById('fName').value.trim(),
      niveau: document.getElementById('fNiveau').value || '',
      department_id: document.getElementById('fDepartment').value || null,
      manager_id: document.getElementById('fManager').value || null,
    };
    if (!body.name) {
      showToast('Le nom est requis.', 'error'); return;
    }
    try {
      if (id) {
        body.semestre_id = document.getElementById('fSemestre').value || null;
        if (!body.semestre_id) {
          showToast('Le semestre est requis pour la modification.', 'error'); return;
        }
        await API.apiFetch('/curriculum/filieres/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
        closeModal('modalFiliere');
        showToast('Filière modifiée.', 'success');
      } else {
        const resp = await API.apiFetch('/curriculum/filieres/', {
          method: 'POST',
          body: JSON.stringify(body),
        });
        closeModal('modalFiliere');
        if (resp.message) {
          showToast(resp.message, 'success');
        } else {
          showToast('Filière créée.', 'success');
        }
      }
      await loadFilieres();
    } catch (e) { showToast(e.message, 'error'); }
  });

  /* ── Module Management ── */
  let _currentModuleFiliereId = null;

  window.openManageModules = async function (filiereId) {
    _currentModuleFiliereId = filiereId;
    const container = document.getElementById('modulesBySemester');
    container.innerHTML = '<div class="curriculum-loading">Chargement…</div>';
    openModal('modalManageModules');

    try {
      const data = await API.apiFetch('/curriculum/filieres/' + filiereId + '/modules-by-semester/');
      document.getElementById('modulesFiliereName').textContent = data.filiere_name + ' — ' + data.niveau_label;

      if (!data.semesters.length) {
        container.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--muted)">Aucun semestre disponible.</div>';
        return;
      }

      container.innerHTML = data.semesters.map(sem => `
        <div class="curriculum-section" style="margin-bottom:.75rem">
          <div class="curriculum-header" style="padding:.5rem .75rem;background:var(--surface2);border-radius:6px;font-weight:600">
            📘 ${esc(sem.semestre_name)}
            ${sem.filiere_id
              ? '<button class="btn sm outline" style="float:right;margin-top:-2px" onclick="addModuleToSemester(' + sem.filiere_id + ', \'' + esc(sem.semestre_name) + '\')">+ Ajouter un module</button>'
              : '<span style="float:right;font-size:.8rem;color:var(--muted)">Aucune filière</span>'
            }
          </div>
          <div class="filiere-modules" style="padding:.5rem .75rem">
            ${sem.modules.length
              ? sem.modules.map(m => `
                <span class="module-tag" style="display:inline-flex;align-items:center;gap:.4rem;margin:.2rem">
                  <span class="module-name-display" data-module-id="${m.id}" data-original="${esc(m.name)}">${esc(m.name)}</span>
                  <input class="module-name-input" data-module-id="${m.id}" style="display:none;width:180px;padding:2px 6px;font-size:.85rem" />
                  <button class="btn-icon" onclick="editModuleName(${m.id})" title="Modifier">✏️</button>
                  <button class="btn-icon" onclick="saveModuleName(${m.id})" style="display:none" title="Enregistrer">💾</button>
                  <button class="btn-icon" onclick="cancelEditModuleName(${m.id})" style="display:none" title="Annuler">❌</button>
                  <button class="btn-icon" style="color:var(--red)" onclick="deleteModule(${m.id})" title="Supprimer">🗑️</button>
                </span>
              `).join('')
              : '<span style="color:var(--muted);font-size:.85rem">Aucun module.</span>'
            }
          </div>
        </div>
      `).join('');
    } catch (e) {
      container.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--red)">Erreur: ' + esc(e.message) + '</div>';
    }
  };

  window.addModuleToSemester = async function (filiereId, semestreName) {
    const name = prompt('Nom du nouveau module (' + semestreName + '):');
    if (!name || !name.trim()) return;
    try {
      await API.apiFetch('/curriculum/subjects/', {
        method: 'POST',
        body: JSON.stringify({ name: name.trim(), filiere_id: filiereId }),
      });
      showToast('Module ajouté.', 'success');
      await openManageModules(_currentModuleFiliereId);
    } catch (e) { showToast(e.message, 'error'); }
  };

  window.editModuleName = function (moduleId) {
    const display = document.querySelector('.module-name-display[data-module-id="' + moduleId + '"]');
    const input = document.querySelector('.module-name-input[data-module-id="' + moduleId + '"]');
    if (!display || !input) return;
    display.style.display = 'none';
    input.value = display.dataset.original;
    input.style.display = 'inline-block';
    input.focus();
    input.nextElementSibling.style.display = '';   // save btn
    input.nextElementSibling.nextElementSibling.style.display = '';  // cancel btn
  };

  window.saveModuleName = async function (moduleId) {
    const input = document.querySelector('.module-name-input[data-module-id="' + moduleId + '"]');
    if (!input || !input.value.trim()) return;
    try {
      await API.apiFetch('/curriculum/subjects/' + moduleId + '/', {
        method: 'PATCH',
        body: JSON.stringify({ name: input.value.trim() }),
      });
      showToast('Module renommé.', 'success');
      await openManageModules(_currentModuleFiliereId);
    } catch (e) { showToast(e.message, 'error'); }
  };

  window.cancelEditModuleName = function (moduleId) {
    const display = document.querySelector('.module-name-display[data-module-id="' + moduleId + '"]');
    const input = document.querySelector('.module-name-input[data-module-id="' + moduleId + '"]');
    if (!display || !input) return;
    display.style.display = '';
    input.style.display = 'none';
    input.nextElementSibling.style.display = 'none';
    input.nextElementSibling.nextElementSibling.style.display = 'none';
  };

  window.deleteModule = async function (moduleId) {
    if (!confirm('Supprimer ce module ?')) return;
    try {
      await API.apiFetch('/curriculum/subjects/' + moduleId + '/', { method: 'DELETE' });
      showToast('Module supprimé.', 'success');
      await openManageModules(_currentModuleFiliereId);
    } catch (e) { showToast(e.message, 'error'); }
  };
}