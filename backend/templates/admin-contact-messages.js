/* ── Contact Messages Admin ── */

var cm = {
  page: 1,
  pageSize: 20,
  total: 0,
  deleteId: null,

  async init() {
    await this.loadMessages();
  },

  async loadMessages() {
    var status = document.getElementById('filterStatus').value;
    var url = '/contact-messages/?page=' + cm.page + '&page_size=' + cm.pageSize;
    if (status !== 'all') url += '&status=' + status;

    try {
      var data = await API.apiFetch(url);
      cm.total = data.total;
      cm.renderTable(data.results);
      cm.renderPagination();
      cm.loadStats();
    } catch (e) {
      document.getElementById('messagesTableBody').innerHTML =
        '<tr><td colspan="7" style="text-align:center;padding:2rem;color:#EF4444">Erreur: ' + e.message + '</td></tr>';
    }
  },

  async loadStats() {
    try {
      var all = await API.apiFetch('/contact-messages/?page_size=1');
      var unread = await API.apiFetch('/contact-messages/?status=unread&page_size=1');
      var untreated = await API.apiFetch('/contact-messages/?status=untreated&page_size=1');
      var treated = await API.apiFetch('/contact-messages/?status=treated&page_size=1');
      document.getElementById('messagesStats').innerHTML =
        '<div class="stat-card"><div style="font-size:1.8rem;font-weight:800;color:var(--primary)">' + all.total + '</div><div style="font-size:0.8rem;color:var(--text-secondary)">Total</div></div>' +
        '<div class="stat-card"><div style="font-size:1.8rem;font-weight:800;color:#F59E0B">' + unread.total + '</div><div style="font-size:0.8rem;color:var(--text-secondary)">Non lus</div></div>' +
        '<div class="stat-card"><div style="font-size:1.8rem;font-weight:800;color:#EF4444">' + untreated.total + '</div><div style="font-size:0.8rem;color:var(--text-secondary)">Non traités</div></div>' +
        '<div class="stat-card"><div style="font-size:1.8rem;font-weight:800;color:#10B981">' + treated.total + '</div><div style="font-size:0.8rem;color:var(--text-secondary)">Traités</div></div>';
    } catch (e) { /* ignore */ }
  },

  renderTable(messages) {
    var tbody = document.getElementById('messagesTableBody');
    if (!messages || messages.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem;color:var(--text-secondary)">Aucun message</td></tr>';
      return;
    }
    tbody.innerHTML = messages.map(function(m) {
      var statusIcon = m.is_treated ? '<span style="color:#10B981;font-size:1.1rem" title="Traité">✅</span>'
        : m.is_read ? '<span style="color:#F59E0B;font-size:1.1rem" title="Lu">👁️</span>'
        : '<span style="color:#EF4444;font-size:1.1rem" title="Non lu">🔴</span>';
      var date = new Date(m.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      return '<tr>' +
        '<td style="text-align:center">' + statusIcon + '</td>' +
        '<td style="white-space:nowrap;font-size:0.8rem">' + date + '</td>' +
        '<td><strong>' + cm.esc(m.name) + '</strong></td>' +
        '<td><a href="mailto:' + cm.esc(m.email) + '" style="color:var(--primary)">' + cm.esc(m.email) + '</a></td>' +
        '<td>' + cm.esc(m.subject) + '</td>' +
        '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + cm.esc(m.message) + '</td>' +
        '<td style="white-space:nowrap">' +
          '<button class="btn btn-sm" onclick="cm.viewDetail(' + m.id + ')" style="margin-right:0.3rem">👁️</button>' +
          (!m.is_treated ? '<button class="btn btn-sm" onclick="cm.markTreated(' + m.id + ')" style="margin-right:0.3rem" title="Marquer traité">✅</button>' : '') +
          '<button class="btn btn-sm btn-danger" onclick="cm.confirmDelete(' + m.id + ')" title="Supprimer">🗑️</button>' +
        '</td></tr>';
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
        '<div style="margin-bottom:1rem"><strong>Statut :</strong> ' + (m.is_treated ? '✅ Traité' : m.is_read ? '👁️ Lu' : '🔴 Non lu') + '</div>' +
        '<hr style="border:none;border-top:1px solid var(--border);margin:1rem 0">' +
        '<div style="white-space:pre-wrap;line-height:1.7;background:var(--bg-section);padding:1rem;border-radius:var(--radius)">' + cm.esc(m.message) + '</div>';

      document.getElementById('detailModal').style.display = 'flex';

      if (!m.is_read) {
        await API.apiFetch('/contact-messages/' + id + '/', { method: 'PATCH', body: JSON.stringify({ is_read: true }) });
        cm.loadMessages();
        cm.loadStats();
      }
    } catch (e) {
      API.showToast('Erreur: ' + e.message, 'error');
    }
  },

  closeDetail() { document.getElementById('detailModal').style.display = 'none'; },

  async markTreated(id) {
    try {
      await API.apiFetch('/contact-messages/' + id + '/', { method: 'PATCH', body: JSON.stringify({ is_treated: true, is_read: true }) });
      API.showToast('Message marqué comme traité', 'success');
      cm.loadMessages();
      cm.loadStats();
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

/* ── Wire up delete confirmation ── */
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('confirmDeleteBtn').addEventListener('click', function() { cm.deleteMessage(); });
  cm.init();
});
