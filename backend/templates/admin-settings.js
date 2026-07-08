/* ── Admin Settings Page ── */
let currentSettings = {};

async function initPage() {
  await loadSettings();
  setupEventListeners();
}

async function loadSettings() {
  try {
    const data = await API.apiFetch('/settings/');
    currentSettings = data || {};
    renderSettings(currentSettings);
  } catch (e) {
    document.getElementById('settingsContainer').innerHTML =
      '<div class="error-msg">Erreur: ' + esc(e.message) + '</div>';
  }
}

function renderSettings(settings) {
  const container = document.getElementById('settingsContainer');
  const groups = settings.groups || [
    {
      name: 'Général',
      fields: [
        { key: 'app_name', label: 'Nom de l\'application', type: 'text', value: settings.app_name || 'Attendify' },
        { key: 'timezone', label: 'Fuseau horaire', type: 'text', value: settings.timezone || 'Africa/Algiers' },
      ],
    },
    {
      name: 'Présence',
      fields: [
        { key: 'qr_expiry_seconds', label: 'Expiration QR (secondes)', type: 'number', value: settings.qr_expiry_seconds || 60 },
        { key: 'auto_close_session', label: 'Fermeture auto. séance (min)', type: 'number', value: settings.auto_close_minutes || 15 },
        { key: 'grace_period', label: 'Période de grâce (min)', type: 'number', value: settings.grace_period || 5 },
      ],
    },
    {
      name: 'Notifications',
      fields: [
        { key: 'sms_enabled', label: 'SMS activé', type: 'checkbox', value: settings.sms_enabled || false },
        { key: 'email_enabled', label: 'Email activé', type: 'checkbox', value: settings.email_enabled || false },
        { key: 'sms_balance', label: 'Solde SMS', type: 'text', value: settings.sms_balance || '—', readonly: true },
      ],
    },
    {
      name: 'Sécurité',
      fields: [
        { key: 'session_timeout', label: 'Timeout session (minutes)', type: 'number', value: settings.session_timeout || 120 },
        { key: 'max_login_attempts', label: 'Tentatives max connexion', type: 'number', value: settings.max_login_attempts || 5 },
      ],
    },
  ];
  let html = '';
  groups.forEach(group => {
    html += '<div class="settings-group"><h3>' + esc(group.name) + '</h3><div class="settings-fields">';
    group.fields.forEach(f => {
      const readonly = f.readonly ? ' readonly' : '';
      if (f.type === 'checkbox') {
        html += '<label class="setting-field checkbox-label">' +
          '<input type="checkbox" class="setting-checkbox" data-key="' + f.key + '"' + (f.value ? ' checked' : '') + readonly + '> ' +
          esc(f.label) + '</label>';
      } else {
        html += '<div class="setting-field">' +
          '<label>' + esc(f.label) + '</label>' +
          '<input type="' + f.type + '" class="setting-input" data-key="' + f.key + '" value="' + esc(String(f.value)) + '"' + readonly + '>' +
        '</div>';
      }
    });
    html += '</div></div>';
  });
  html += '<div class="settings-actions"><button class="btn primary" id="btnSaveSettings">💾 Enregistrer</button></div>';
  container.innerHTML = html;
}

async function saveSettings() {
  const payload = {};
  document.querySelectorAll('.setting-input').forEach(input => {
    payload[input.dataset.key] = input.value;
  });
  document.querySelectorAll('.setting-checkbox').forEach(cb => {
    payload[cb.dataset.key] = cb.checked;
  });
  try {
    await API.apiFetch('/settings/', {
      method: 'POST',
      body: JSON.stringify(payload),
      headers: { 'Content-Type': 'application/json' },
    });
    showToast('Paramètres enregistrés.', 'success');
    await loadSettings();
  } catch (e) {
    showToast('Erreur: ' + e.message, 'error');
  }
}

function setupEventListeners() {
  document.getElementById('btnRefreshSettings')?.addEventListener('click', loadSettings);
  document.getElementById('settingsContainer')?.addEventListener('click', function (e) {
    if (e.target.id === 'btnSaveSettings') saveSettings();
  });
}