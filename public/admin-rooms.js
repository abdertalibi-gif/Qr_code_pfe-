/* ── Admin Rooms Page (Blocs, Salles, Amphithéâtres) ── */
let allBlocks = [];
let allAmphis = [];

async function initPage() {
  await Promise.all([loadBlocks(), loadAmphitheaters()]);
  setupEventListeners();
}

async function loadBlocks() {
  try {
    const data = await API.apiFetch('/blocks/');
    allBlocks = Array.isArray(data) ? data : [];
    renderBlocks();
  } catch (e) {
    document.getElementById('blocksBody').innerHTML =
      '<tr class="empty-row"><td colspan="4">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

async function loadAmphitheaters() {
  try {
    const data = await API.apiFetch('/amphitheaters/');
    allAmphis = Array.isArray(data) ? data : [];
    renderAmphis();
  } catch (e) {
    document.getElementById('amphisBody').innerHTML =
      '<tr class="empty-row"><td colspan="3">Erreur: ' + esc(e.message) + '</td></tr>';
  }
}

function renderBlocks() {
  const tbody = document.getElementById('blocksBody');
  const query = searchQuery('searchBlocks');
  const filtered = allBlocks.filter(b => matchesQuery(query, b.name));
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="4">' + (query ? 'Aucun résultat.' : 'Aucun bloc.') + '</td></tr>';
    return;
  }
  var html = '';
  filtered.forEach(function (b, i) {
    var rooms = b.rooms || [];
    html += '<tr>' +
      '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
      '<td><strong>' + esc(b.name) + '</strong></td>' +
      '<td>' + (rooms.length ? rooms.length + ' salle(s)' : '—') + '</td>' +
      '<td class="actions-cell">' +
        '<button class="btn sm outline" onclick="openEditBlock(' + b.id + ')">Modifier</button>' +
        '<button class="btn sm outline" onclick="openAddRoom(' + b.id + ')">+ Salle</button>' +
        '<button class="btn sm outline" style="color:var(--red)" onclick="deleteBlock(' + b.id + ')">Supprimer</button>' +
      '</td>' +
    '</tr>';
    rooms.forEach(function (r) {
      html += '<tr class="room-sub-row">' +
        '<td></td>' +
        '<td style="padding-left:2rem"><span style="color:var(--muted)">↳</span> ' + esc(r.name) + '</td>' +
        '<td style="font-size:.85rem;color:var(--muted)">' + esc(b.name) + '</td>' +
        '<td class="actions-cell">' +
          '<button class="btn sm outline" onclick="openEditRoom(' + r.id + ', ' + b.id + ')">Modifier</button>' +
          '<button class="btn sm outline" style="color:var(--red)" onclick="deleteRoom(' + r.id + ')">Supprimer</button>' +
        '</td>' +
      '</tr>';
    });
  });
  tbody.innerHTML = html;
}

function renderAmphis() {
  const tbody = document.getElementById('amphisBody');
  const query = searchQuery('searchAmphis');
  const filtered = allAmphis.filter(a => matchesQuery(query, a.name));
  if (!filtered.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="3">' + (query ? 'Aucun résultat.' : 'Aucun amphithéâtre.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((a, i) => '<tr>' +
    '<td><span style="color:var(--muted)">' + (i + 1) + '</span></td>' +
    '<td><strong>' + esc(a.name) + '</strong></td>' +
    '<td class="actions-cell">' +
      '<button class="btn sm outline" onclick="openEditAmphi(' + a.id + ')">Modifier</button>' +
      '<button class="btn sm outline" style="color:var(--red)" onclick="deleteAmphi(' + a.id + ')">Supprimer</button>' +
    '</td>' +
  '</tr>').join('');
}

function openEditBlock(id) {
  const b = allBlocks.find(x => x.id === id);
  if (!b) return;
  document.getElementById('blkId').value = b.id;
  document.getElementById('blockModalTitle').textContent = 'Modifier le bloc';
  document.getElementById('blkName').value = b.name;
  openModal('modalBlock');
}

async function deleteBlock(id) {
  if (!confirm('Supprimer ce bloc et ses salles ?')) return;
  try {
    await API.apiFetch('/blocks/' + id + '/', { method: 'DELETE' });
    showToast('Bloc supprimé.', 'success');
    await loadBlocks();
  } catch (e) { showToast(e.message, 'error'); }
}

function openAddRoom(blockId) {
  document.getElementById('rmId').value = '';
  document.getElementById('roomModalTitle').textContent = 'Ajouter une salle';
  document.getElementById('rmName').value = '';
  const sel = document.getElementById('rmBlock');
  sel.innerHTML = '<option value="">— Sélectionner —</option>' +
    allBlocks.map(b => '<option value="' + b.id + '"' + (b.id === blockId ? ' selected' : '') + '>' + esc(b.name) + '</option>').join('');
  openModal('modalRoom');
}

async function openEditRoom(roomId, blockId) {
  try {
    const r = await API.apiFetch('/rooms/' + roomId + '/');
    document.getElementById('rmId').value = r.id;
    document.getElementById('roomModalTitle').textContent = 'Modifier la salle';
    document.getElementById('rmName').value = r.name || '';
    const sel = document.getElementById('rmBlock');
    sel.innerHTML = '<option value="">— Sélectionner —</option>' +
      allBlocks.map(b => '<option value="' + b.id + '">' + esc(b.name) + '</option>').join('');
    sel.value = r.block || blockId || '';
    openModal('modalRoom');
  } catch (e) {
    showToast('Erreur: ' + e.message, 'error');
  }
}

async function deleteRoom(id) {
  if (!confirm('Supprimer cette salle ?')) return;
  try {
    await API.apiFetch('/rooms/' + id + '/', { method: 'DELETE' });
    showToast('Salle supprimée.', 'success');
    await loadBlocks();
  } catch (e) { showToast(e.message, 'error'); }
}

function openEditAmphi(id) {
  const a = allAmphis.find(x => x.id === id);
  if (!a) return;
  document.getElementById('amId').value = a.id;
  document.getElementById('amphiModalTitle').textContent = 'Modifier l\'amphithéâtre';
  document.getElementById('amName').value = a.name;
  openModal('modalAmphi');
}

async function deleteAmphi(id) {
  if (!confirm('Supprimer cet amphithéâtre ?')) return;
  try {
    await API.apiFetch('/amphitheaters/' + id + '/', { method: 'DELETE' });
    showToast('Amphithéâtre supprimé.', 'success');
    await loadAmphitheaters();
  } catch (e) { showToast(e.message, 'error'); }
}

function setupEventListeners() {
  bindSearchInput('searchBlocks', renderBlocks);
  bindSearchInput('searchAmphis', renderAmphis);

  document.getElementById('btnOpenAddBlock')?.addEventListener('click', () => {
    document.getElementById('blkId').value = '';
    document.getElementById('blockModalTitle').textContent = 'Ajouter un bloc';
    document.getElementById('blkName').value = '';
    openModal('modalBlock');
  });

  document.getElementById('btnSubmitBlock')?.addEventListener('click', async () => {
    const id = document.getElementById('blkId').value;
    const name = document.getElementById('blkName').value.trim();
    if (!name) { showToast('Le nom est requis.', 'error'); return; }
    try {
      if (id) {
        await API.apiFetch('/blocks/' + id + '/', { method: 'PATCH', body: JSON.stringify({ name }) });
      } else {
        await API.apiFetch('/blocks/', { method: 'POST', body: JSON.stringify({ name }) });
      }
      closeModal('modalBlock');
      showToast('Bloc enregistré.', 'success');
      await loadBlocks();
    } catch (e) { showToast(e.message, 'error'); }
  });

  document.getElementById('btnOpenAddAmphi')?.addEventListener('click', () => {
    document.getElementById('amId').value = '';
    document.getElementById('amphiModalTitle').textContent = 'Ajouter un amphithéâtre';
    document.getElementById('amName').value = '';
    openModal('modalAmphi');
  });

  document.getElementById('btnSubmitAmphi')?.addEventListener('click', async () => {
    const id = document.getElementById('amId').value;
    const name = document.getElementById('amName').value.trim();
    if (!name) { showToast('Le nom est requis.', 'error'); return; }
    try {
      if (id) {
        await API.apiFetch('/amphitheaters/' + id + '/', { method: 'PATCH', body: JSON.stringify({ name }) });
      } else {
        await API.apiFetch('/amphitheaters/', { method: 'POST', body: JSON.stringify({ name }) });
      }
      closeModal('modalAmphi');
      showToast('Amphithéâtre enregistré.', 'success');
      await loadAmphitheaters();
    } catch (e) { showToast(e.message, 'error'); }
  });

  document.getElementById('btnSubmitRoom')?.addEventListener('click', async () => {
    const id = document.getElementById('rmId').value;
    const blockId = document.getElementById('rmBlock').value;
    const name = document.getElementById('rmName').value.trim();
    if (!name || !blockId) { showToast('Nom et bloc sont requis.', 'error'); return; }
    try {
      const body = { block: parseInt(blockId), name: name };
      if (id) {
        await API.apiFetch('/rooms/' + id + '/', { method: 'PATCH', body: JSON.stringify(body) });
      } else {
        await API.apiFetch('/rooms/', { method: 'POST', body: JSON.stringify(body) });
      }
      closeModal('modalRoom');
      showToast('Salle enregistrée.', 'success');
      await loadBlocks();
    } catch (e) { showToast(e.message, 'error'); }
  });
}