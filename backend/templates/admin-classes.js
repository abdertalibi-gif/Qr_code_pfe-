/* ── Admin Classes Page ── */
let allClasses = [];
let allNiveaux = [];
let allSemestres = [];
let allFilieres = [];
let allModules = [];
let allBlocks = [];
let allRooms = [];
let allAmphis = [];

async function initPage() {
  await Promise.all([loadClasses(), loadNiveaux(), loadSemestres(), loadBlocks(), loadAmphis()]);
  setupEventListeners();
}

async function loadClasses() {
  try {
    const data = await API.apiFetch('/classes/');
    allClasses = Array.isArray(data) ? data : (data.results || []);
    renderClasses();
  } catch (e) {
    document.getElementById('classesBody').innerHTML =
      '<tr class="empty-row"><td colspan="8">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

async function loadNiveaux() {
  try {
    const data = await API.apiFetch('/curriculum/niveaux/');
    allNiveaux = Array.isArray(data) ? data : [];
    const sel = document.getElementById('clNiveau');
    sel.innerHTML = '<option value="">— Sélectionner —</option>' +
      allNiveaux.map(n => '<option value="' + n.id + '">' + esc(n.label) + '</option>').join('');
  } catch (e) { allNiveaux = []; }
}

async function loadSemestres() {
  try {
    const data = await API.apiFetch('/curriculum/semestres/');
    allSemestres = Array.isArray(data) ? data : [];
  } catch (e) { allSemestres = []; }
}

async function loadFilieres() {
  try {
    const data = await API.apiFetch('/curriculum/filieres/');
    allFilieres = Array.isArray(data) ? data : [];
  } catch (e) { allFilieres = []; }
}

async function loadModules() {
  try {
    const data = await API.apiFetch('/curriculum/modules/');
    allModules = Array.isArray(data) ? data : [];
  } catch (e) { allModules = []; }
}

async function loadBlocks() {
  try {
    const data = await API.apiFetch('/blocks/');
    allBlocks = Array.isArray(data) ? data : [];
    const sel = document.getElementById('clBlock');
    sel.innerHTML = '<option value="">— Sélectionner —</option>' +
      allBlocks.map(b => '<option value="' + b.id + '">' + esc(b.name) + '</option>').join('');
    allRooms = [];
    allBlocks.forEach(function (b) {
      if (b.rooms) allRooms = allRooms.concat(b.rooms);
    });
  } catch (e) { allBlocks = []; }
}

async function loadAmphis() {
  try {
    const data = await API.apiFetch('/amphitheaters/');
    allAmphis = Array.isArray(data) ? data : [];
    const sel = document.getElementById('clAmphi');
    sel.innerHTML = '<option value="">— Sélectionner —</option>' +
      allAmphis.map(a => '<option value="' + a.id + '">' + esc(a.name) + '</option>').join('');
  } catch (e) { allAmphis = []; }
}

function renderClasses() {
  const tbody = document.getElementById('classesBody');
  const q = searchQuery('searchClasses');
  const filtered = allClasses.filter(function (c) {
    return !q || (c.name && c.name.toLowerCase().includes(q)) || (c.filiere_name && c.filiere_name.toLowerCase().includes(q));
  });
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="8">' + (q ? 'Aucun résultat.' : 'Aucune classe.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map(function (c, i) {
    return '<tr>' +
      '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
      '<td><strong>' + esc(c.name) + '</strong></td>' +
      '<td>' + esc(c.filiere_name || '—') + '</td>' +
      '<td>' + esc(c.niveau_id || '—') + '</td>' +
      '<td>' + esc(c.semestre_name || '—') + '</td>' +
      '<td>' + esc(c.module_name || '—') + '</td>' +
      '<td>' + (c.student_count ?? '—') + '</td>' +
      '<td class="actions-cell">' +
        '<button class="btn sm outline" onclick="openEditClass(' + c.id + ')">Modifier</button>' +
        '<button class="btn sm outline" style="color:var(--red)" onclick="deleteClass(' + c.id + ')">Supprimer</button>' +
      '</td>' +
    '</tr>';
  }).join('');
}

function cascadeSemestre(niveauId) {
  const sel = document.getElementById('clSemestre');
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Sélectionner —</option>';
  if (!niveauId) { sel.disabled = false; cascadeFiliere(''); return; }
  API.apiFetch('/curriculum/semestres-par-niveau/?niveau=' + encodeURIComponent(niveauId))
    .then(function (data) {
      var sems = Array.isArray(data) ? data : [];
      sems.forEach(function (s) {
        sel.innerHTML += '<option value="' + s.id + '">' + esc(s.name) + '</option>';
      });
      sel.disabled = false;
    })
    .catch(function () { sel.disabled = false; cascadeFiliere(''); });
}

function cascadeFiliere(semestreId) {
  const sel = document.getElementById('clFiliere');
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Sélectionner —</option>';
  if (!semestreId) { sel.disabled = false; cascadeModule(''); return; }
  var filtered = allFilieres.filter(function (f) { return String(f.semestre_id) === String(semestreId); });
  filtered.forEach(function (f) {
    sel.innerHTML += '<option value="' + f.id + '">' + esc(f.name) + '</option>';
  });
  sel.disabled = false;
  cascadeModule('');
}

function cascadeModule(filiereId) {
  const sel = document.getElementById('clModule');
  sel.disabled = true;
  sel.innerHTML = '<option value="">— Sélectionner —</option>';
  if (!filiereId) { sel.disabled = false; return; }
  API.apiFetch('/curriculum/modules/?filiere_id=' + filiereId)
    .then(function (data) {
      var mods = Array.isArray(data) ? data : [];
      mods.forEach(function (m) {
        sel.innerHTML += '<option value="' + m.id + '">' + esc(m.name) + '</option>';
      });
      sel.disabled = false;
    })
    .catch(function () { sel.disabled = false; });
}

function cascadeRoom(blockId) {
  const sel = document.getElementById('clRoom');
  sel.innerHTML = '<option value="">— Sélectionner —</option>';
  if (!blockId) return;
  var block = allBlocks.find(function (b) { return b.id == blockId; });
  if (block && block.rooms) {
    block.rooms.forEach(function (r) {
      sel.innerHTML += '<option value="' + r.id + '">' + esc(r.name) + '</option>';
    });
  }
}

function toggleLocation(locationType) {
  var showBlock = locationType === 'BLOC' || locationType === 'BOTH_ALLOWED';
  var showAmphi = locationType === 'AMPHI' || locationType === 'BOTH_ALLOWED';
  document.getElementById('clBlockGroup').style.display = showBlock ? '' : 'none';
  document.getElementById('clAmphiGroup').style.display = showAmphi ? '' : 'none';
}

function openEditClass(id) {
  var c = allClasses.find(function (x) { return x.id === id; });
  if (!c) return;
  document.getElementById('clId').value = c.id;
  document.getElementById('modalClasseTitle').textContent = 'Modifier la classe';
  if (c.niveau_id) {
    document.getElementById('clNiveau').value = c.niveau_id;
    cascadeSemestre(c.niveau_id);
    setTimeout(function () {
      if (c.semestre_id) {
        document.getElementById('clSemestre').value = c.semestre_id;
        cascadeFiliere(c.semestre_id);
        setTimeout(function () {
          if (c.filiere_id) {
            document.getElementById('clFiliere').value = c.filiere_id;
            cascadeModule(c.filiere_id);
            setTimeout(function () {
              if (c.module_id) document.getElementById('clModule').value = c.module_id;
            }, 100);
          }
        }, 100);
      }
    }, 100);
  }
  document.getElementById('clYear').value = c.academic_year || '';
  if (c.location_type) {
    document.getElementById('clLocationType').value = c.location_type;
    toggleLocation(c.location_type);
    if (c.block_id) {
      document.getElementById('clBlock').value = c.block_id;
      cascadeRoom(c.block_id);
      if (c.room_id) setTimeout(function () { document.getElementById('clRoom').value = c.room_id; }, 100);
    }
    if (c.amphitheater_id) document.getElementById('clAmphi').value = c.amphitheater_id;
  }
  openModal('modalClasse');
}

async function deleteClass(id) {
  if (!confirm('Supprimer cette classe ?')) return;
  try {
    await API.apiFetch('/classes/' + id + '/', { method: 'DELETE' });
    showToast('Classe supprimée.', 'success');
    await loadClasses();
  } catch (e) { showToast(e.message, 'error'); }
}

function resetClassForm() {
  document.getElementById('clId').value = '';
  document.getElementById('modalClasseTitle').textContent = 'Ajouter une classe';
  document.getElementById('clNiveau').value = '';
  cascadeSemestre('');
  document.getElementById('clYear').value = '';
  document.getElementById('clLocationType').value = '';
  toggleLocation('');
  document.getElementById('clBlock').value = '';
  cascadeRoom('');
  document.getElementById('clAmphi').value = '';
}

function setupEventListeners() {
  bindSearchInput('searchClasses', renderClasses);

  document.getElementById('clNiveau')?.addEventListener('change', function () {
    cascadeSemestre(this.value);
  });
  document.getElementById('clSemestre')?.addEventListener('change', function () {
    cascadeFiliere(this.value);
  });
  document.getElementById('clFiliere')?.addEventListener('change', function () {
    cascadeModule(this.value);
  });
  document.getElementById('clLocationType')?.addEventListener('change', function () {
    toggleLocation(this.value);
  });
  document.getElementById('clBlock')?.addEventListener('change', function () {
    cascadeRoom(this.value);
  });

  document.getElementById('btnOpenAddClasse')?.addEventListener('click', function () {
    resetClassForm();
    openModal('modalClasse');
  });

  document.getElementById('btnSubmitClasse')?.addEventListener('click', async function () {
    var id = document.getElementById('clId').value;
    var body = {
      niveau: document.getElementById('clNiveau').value || '',
      semestre_id: document.getElementById('clSemestre').value || null,
      filiere_id: document.getElementById('clFiliere').value || null,
      module_id: document.getElementById('clModule').value || null,
      academic_year: document.getElementById('clYear').value.trim(),
      location_type: document.getElementById('clLocationType').value || '',
      block_id: document.getElementById('clBlock').value || null,
      room_id: document.getElementById('clRoom').value || null,
      amphitheater_id: document.getElementById('clAmphi').value || null,
    };
    if (!body.filiere_id || !body.semestre_id) {
      showToast('Niveau, semestre et filière sont requis.', 'error'); return;
    }
    try {
      if (id) {
        await API.apiFetch('/classes/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
      } else {
        await API.apiFetch('/classes/', { method: 'POST', body: JSON.stringify(body) });
      }
      closeModal('modalClasse');
      showToast('Classe enregistrée.', 'success');
      await loadClasses();
    } catch (e) { showToast(e.message, 'error'); }
  });
}