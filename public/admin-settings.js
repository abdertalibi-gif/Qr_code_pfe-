/* ── Admin Settings Page ── */
async function initPage() {
  await loadSettings();
  setupEventListeners();
}

async function loadSettings() {
  try {
    const data = await API.apiFetch('/settings/');
    applySettings(data);
    await loadSystemInfo();
  } catch (e) {
    showToast('Erreur chargement paramètres: ' + e.message, 'error');
  }
}

function applySettings(data) {
  if (!data) return;
  const fields = {
    qr_expiry_minutes: 'setQrExpiry',
    geo_radius: 'setGeoRadius',
    scan_limit: 'setScanLimit',
  };
  Object.entries(fields).forEach(function (_ref) {
    const key = _ref[0], id = _ref[1];
    const el = document.getElementById(id);
    if (el && data[key] !== undefined) el.value = data[key];
  });
}

async function loadSystemInfo() {
  const container = document.getElementById('systemInfo');
  try {
    const data = await API.apiFetch('/system-info/');
    if (!container) return;
    let html = '<div class="stats-grid" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr))">';
    Object.entries(data).forEach(function (_ref2) {
      const k = _ref2[0], v = _ref2[1];
      html += '<div class="stat-card"><strong>' + esc(k) + '</strong><span>' + esc(String(v)) + '</span></div>';
    });
    html += '</div>';
    container.innerHTML = html;
  } catch (e) {
    if (container) container.innerHTML = '<p style="color:var(--muted)">Informations non disponibles.</p>';
  }
}

async function saveSettings() {
  const body = {
    qr_expiry_minutes: parseInt(document.getElementById('setQrExpiry').value) || 20,
    geo_radius: parseInt(document.getElementById('setGeoRadius').value) || 50,
    scan_limit: parseInt(document.getElementById('setScanLimit').value) || 1,
  };
  try {
    await API.apiFetch('/settings/', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    });
    showToast('Paramètres enregistrés.', 'success');
  } catch (e) {
    showToast('Erreur: ' + e.message, 'error');
  }
}

function setupEventListeners() {
  document.getElementById('btnSaveSettings')?.addEventListener('click', saveSettings);
}