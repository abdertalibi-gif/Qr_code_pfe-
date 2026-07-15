/* ── Contact Messages Admin ── */

var cm = {
  page: 1,
  pageSize: 20,
  total: 0,
  deleteId: null,

  async init() {
    await this.loadMessages();
    await this.updateNavBadge();
  },

  async loadMessages() {
    var status = document.getElementById('filterStatus').value;
    var search = encodeURIComponent(document.getElementById('searchInput').value.trim());
    var url = '/contact-messages/?page=' + cm.page + '&page_size=' + cm.pageSize;
    if (status !== 'all') url += '&status=' + encodeURIComponent(status);
    if (search) url += '&search=' + search;

    try {
      var data = await API.apiFetch(url);
      cm.total = data.total;
      cm.renderTable(data.results);
      cm.renderPagination();
      cm.loadStats();
    } catch (e) {
      document.getElementById('messagesTableBody').innerHTML =
        '<tr><td colspan="6" style="text-align:center;padding:2rem;color:#EF4444">Erreur: ' + e.message + '</td></tr>';
    }
  },

  async loadStats() {
    try {
      var all = await API.apiFetch('/contact-messages/?page_size=1');
      var nouveau = await API.apiFetch('/contact-messages/?status=Nouveau&page_size=1');
      var lu = await API.apiFetch('/contact-messages/?status=Lu&page_size=1');
      var traite = await API.apiFetch('/contact-messages/?status=Trait\u00e9&page_size=1');
      document.getElementById('messagesStats').innerHTML =
        '<div class="stat-card"><div style="font-size:1.8rem;font-weight:800;color:var(--primary)">' + all.total + '</div><div style="font-size:0.8rem;color:var(--text-secondary)">Total</div></div>' +
        '<div class="stat-card"><div style="font-size:1.8rem;font-weight:800;color:#EF4444">' + nouveau.total + '</div><div style="font-size:0.8rem;color:var(--text-secondary)">Nouveaux</div></div>' +
        '<div class="stat-card"><div style="font-size:1.8rem;font-weight:800;color:#F59E0B">' + lu.total + '</div><div style="font-size:0.8rem;color:var(--text-secondary)">Lus</div></div>' +
        '<div class="stat-card"><div style="font-size:1.8rem;font-weight:800;color:#10B981">' + traite.total + '</div><div style="font-size:0.8rem;color:var(--text-secondary)">Trait\u00e9s</div></div>';
    } catch (e) { /* ignore */ }
  },

  async updateNavBadge() {
    try {
      var data = await API.apiFetch('/contact-messages/?status=Nouveau&page_size=1');
      var badge = document.querySelector('a[href="/admin/contact-messages/"] .nav-count');
      if (!badge) {
        var link = document.querySelector('a[href="/admin/contact-messages/"]');
        if (link) {
          var span = document.createElement('span');
          span.className = 'nav-count';
          span.id = 'navCntMessages';
          link.appendChild(span);
          badge = span;
        }
      }
      if (badge) {
        badge.textContent = data.total || '';
        badge.style.display = data.total > 0 ? '' : 'none';
      }
    } catch (e) { /* ignore */ }
  },

  statusBadge(status) {
    if (status === 'Nouveau') return '<span style="display:inline-flex;align-items:center;gap:0.3rem;padding:0.2rem 0.6rem;border-radius:100px;background:#FEF2F2;color:#EF4444;font-size:0.75rem;font-weight:600">🔴 Nouveau</span>';
    if (status === 'Lu') return '<span style="display:inline-flex;align-items:center;gap:0.3rem;padding:0.2rem 0.6rem;border-radius:100px;background:#FFFBEB;color:#F59E0B;font-size:0.75rem;font-weight:600">👁️ Lu</span>';
    return '<span style="display:inline-flex;align-items:center;gap:0.3rem;padding:0.2rem 0.6rem;border-radius:100px;background:#ECFDF5;color:#10B981;font-size:0.75rem;font-weight:600">✅ Traité</span>';
  },

  renderTable(messages) {
    var tbody = document.getElementById('messagesTableBody');
    if (!messages || messages.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:2rem;color:var(--text-secondary)">Aucun message</td></tr>';
      return;
    }
    tbody.innerHTML = messages.map(function(m) {
      var date = new Date(m.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      var actions = '<button class="btn btn-sm" onclick="cm.viewDetail(' + m.id + ')" title="Voir">👁️</button>';
      if (m.status === 'Nouveau') actions += ' <button class="btn btn-sm" onclick="cm.markLu(' + m.id + ')" title="Marquer comme lu">📖</button>';
      if (m.status !== 'Traité') actions += ' <button class="btn btn-sm" onclick="cm.markTraite(' + m.id + ')" title="Marquer comme traité">✅</button>';
      actions += ' <button class="btn btn-sm btn-danger" onclick="cm.confirmDelete(' + m.id + ')" title="Supprimer">🗑️</button>';
      return '<tr>' +
        '<td><strong>' + cm.esc(m.name) + '</strong></td>' +
        '<td><a href="mailto:' + cm.esc(m.email) + '" style="color:var(--primary)">' + cm.esc(m.email) + '</a></td>' +
        '<td>' + cm.esc(m.subject) + '</td>' +
        '<td style="white-space:nowrap;font-size:0.8rem">' + date + '</td>' +
        '<td>' + cm.statusBadge(m.status) + '</td>' +
        '<td style="white-space:nowrap">' + actions + '</td></tr>';
    }).join('');
  },

  renderPagination() {
    var totalPages = Math.ceil(cm.total / cm.pageSize);
    var container = document.getElementById('messagesPagination');
    if (totalPages <= 1) { container.innerHTML = ''; return; }
    var html = '';
    if (cm.page > 1) html += '<button class="btn btn-sm" onclick="cm.goPage(' + (cm.page - 1) + ')">← Précédent</button>';
    html += '<span style="padding:0.4rem 0.8rem;font-size:0.85rem">Page ' + cm.page + ' / ' + totalPages + '</span>';
    if (cm.page < totalPages) html += '<button class="btn btn-sm" onclick="cm.goPage(' + (cm.page + 1) + ')">Suivant →</button>';
    container.innerHTML = html;
  },

  goPage(p) { cm.page = p; cm.loadMessages(); },

  async viewDetail(id) {
    try {
      var m = await API.apiFetch('/contact-messages/' + id + '/');
      var date = new Date(m.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      document.getElementById('detailBody').innerHTML =
        '<div style="margin-bottom:1rem"><strong>Date :</strong> ' + date + '</div>' +
        '<div style="margin-bottom:1rem"><strong>Nom :</strong> ' + cm.esc(m.name) + '</div>' +
        '<div style="margin-bottom:1rem"><strong>Email :</strong> <a href="mailto:' + cm.esc(m.email) + '" style="color:var(--primary)">' + cm.esc(m.email) + '</a></div>' +
        '<div style="margin-bottom:1rem"><strong>Sujet :</strong> ' + cm.esc(m.subject) + '</div>' +
        '<div style="margin-bottom:1rem"><strong>Statut :</strong> ' + cm.statusBadge(m.status) + '</div>' +
        '<hr style="border:none;border-top:1px solid var(--border);margin:1rem 0">' +
        '<div style="white-space:pre-wrap;line-height:1.7;background:var(--bg-section);padding:1rem;border-radius:var(--radius)">' + cm.esc(m.message) + '</div>';

      document.getElementById('detailModal').style.display = 'flex';

      if (m.status === 'Nouveau') {
        await API.apiFetch('/contact-messages/' + id + '/', { method: 'PATCH', body: JSON.stringify({ status: 'Lu' }) });
        cm.loadMessages();
        cm.loadStats();
        cm.updateNavBadge();
      }
    } catch (e) {
      API.showToast('Erreur: ' + e.message, 'error');
    }
  },

  closeDetail() { document.getElementById('detailModal').style.display = 'none'; },

  async markLu(id) {
    try {
      await API.apiFetch('/contact-messages/' + id + '/', { method: 'PATCH', body: JSON.stringify({ status: 'Lu' }) });
      API.showToast('Message marqué comme lu', 'success');
      cm.loadMessages();
      cm.loadStats();
      cm.updateNavBadge();
    } catch (e) {
      API.showToast('Erreur: ' + e.message, 'error');
    }
  },

  async markTraite(id) {
    try {
      await API.apiFetch('/contact-messages/' + id + '/', { method: 'PATCH', body: JSON.stringify({ status: 'Traité' }) });
      API.showToast('Message marqué comme traité', 'success');
      cm.loadMessages();
      cm.loadStats();
      cm.updateNavBadge();
    } catch (e) {
      API.showToast('Erreur: ' + e.message, 'error');
    }
  },

  confirmDelete(id) {
    cm.deleteId = id;
    document.getElementById('deleteModal').style.display = 'flex';
  },

  closeDelete() { document.getElementById('deleteModal').style.display = 'none'; cm.deleteId = null; },

  async deleteMessage() {
    if (!cm.deleteId) return;
    try {
      await API.apiFetch('/contact-messages/' + cm.deleteId + '/', { method: 'DELETE' });
      API.showToast('Message supprimé', 'success');
      cm.closeDelete();
      cm.loadMessages();
      cm.loadStats();
      cm.updateNavBadge();
    } catch (e) {
      API.showToast('Erreur: ' + e.message, 'error');
    }
  },

  esc(s) {
    if (typeof s !== 'string') return s;
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(s));
    return div.innerHTML;
  }
};

/* ── Wire up ── */
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('confirmDeleteBtn').addEventListener('click', function() { cm.deleteMessage(); });
  cm.init();
});
