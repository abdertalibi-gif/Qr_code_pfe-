/* ── Teacher Workload Dashboard ── */

var wld = {
  data: null,
  teachers: [],
  totals: {},
  chartData: {},
  filtered: [],
  sortKey: 'equivalent',
  sortDir: -1,
  page: 0,
  pageSize: 15,

  async init() {
    await Promise.all([
      this._loadDepts(),
      this._loadSemestresAll(),
      this._loadAcademicYears(),
      this._loadTeachers(),
    ]);
    this._initPeriod();
    await this._loadNiveaux('');
    await this.loadData();
  },

  /* ── Load filter options ── */

  async _loadDepts() {
    try {
      var data = await API.apiFetch('/departments/');
      var depts = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldDept');
      depts.forEach(function (d) {
        var o = document.createElement('option');
        o.value = d.id;
        o.textContent = d.name;
        sel.appendChild(o);
      });
    } catch (e) { /* silent */ }
  },

  async _loadNiveaux(deptId) {
    try {
      var url = '/curriculum/filieres/' + (deptId ? '?department_id=' + deptId : '');
      var data = await API.apiFetch(url);
      var fils = Array.isArray(data) ? data : (data.results || []);
      var niveaux = new Set();
      fils.forEach(function (f) { if (f.niveau) niveaux.add(f.niveau); });
      var sel = document.getElementById('wldNiveau');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      Array.from(niveaux).sort().forEach(function (n) {
        var o = document.createElement('option');
        o.value = n;
        o.textContent = n;
        sel.appendChild(o);
      });
      sel.disabled = false;
    } catch (e) { /* silent */ }
  },

  async _loadSemestres(niveau) {
    try {
      var data = await API.apiFetch('/curriculum/semestres-par-niveau/?niveau=' + encodeURIComponent(niveau));
      var sems = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldSemestre');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      sems.forEach(function (s) {
        var o = document.createElement('option');
        o.value = s.id;
        o.textContent = s.name;
        sel.appendChild(o);
      });
      sel.disabled = false;
    } catch (e) { /* silent */ }
  },

  async _loadSemestresAll() {
    try {
      var data = await API.apiFetch('/curriculum/semestres/');
      var sems = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldSemestre');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      sems.forEach(function (s) {
        var o = document.createElement('option');
        o.value = s.id;
        o.textContent = s.name;
        sel.appendChild(o);
      });
      sel.disabled = false;
    } catch (e) { /* silent */ }
  },

  async _loadFilieres(deptId, semestreId) {
    try {
      var params = [];
      if (deptId) params.push('department_id=' + deptId);
      if (semestreId) params.push('semestre_id=' + semestreId);
      var url = '/curriculum/filieres/' + (params.length ? '?' + params.join('&') : '');
      var data = await API.apiFetch(url);
      var fils = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldFiliere');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      fils.forEach(function (f) {
        var o = document.createElement('option');
        o.value = f.id;
        o.textContent = f.name;
        sel.appendChild(o);
      });
      sel.disabled = false;
    } catch (e) { /* silent */ }
  },

  async _loadModules(filiereId) {
    try {
      var url = '/curriculum/modules/?filiere_id=' + filiereId;
      var data = await API.apiFetch(url);
      var mods = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldModule');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      mods.forEach(function (m) {
        var o = document.createElement('option');
        o.value = m.id;
        o.textContent = m.name || m.nom || ('Module ' + m.id);
        sel.appendChild(o);
      });
      sel.disabled = false;
    } catch (e) { /* silent */ }
  },

  async _loadAcademicYears() {
    try {
      var data = await API.apiFetch('/classes/');
      var classes = Array.isArray(data) ? data : (data.results || []);
      var years = new Set();
      classes.forEach(function (c) { if (c.academic_year) years.add(c.academic_year); });
      var sorted = Array.from(years).sort();
      var sel = document.getElementById('wldYear');
      sorted.forEach(function (y) {
        var o = document.createElement('option');
        o.value = y;
        o.textContent = y;
        sel.appendChild(o);
      });
    } catch (e) { /* silent */ }
  },

  async _loadTeachers() {
    try {
      var data = await API.apiFetch('/users/?role=teacher');
      var users = Array.isArray(data) ? data : (data.results || []);
      var sel = document.getElementById('wldTeacher');
      sel.innerHTML = '<option value="">Tous</option>';
      users.forEach(function (u) {
        var o = document.createElement('option');
        o.value = u.id;
        o.textContent = (u.first_name || '') + ' ' + (u.last_name || '') + ' (' + (u.email || '') + ')';
        sel.appendChild(o);
      });
    } catch (e) { /* silent */ }
  },

  _initPeriod() {
    var now = new Date();
    document.getElementById('wldMonth').value = String(now.getMonth() + 1);
    document.getElementById('wldDateStart').value = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
    document.getElementById('wldDateEnd').value = now.toISOString().split('T')[0];
  },

  onPeriodChange() {
    var val = document.getElementById('wldPeriod').value;
    document.getElementById('wldMonthGroup').style.display = val === 'month' ? 'block' : 'none';
    document.getElementById('wldDateStartGroup').style.display = val === 'range' ? 'block' : 'none';
    document.getElementById('wldDateEndGroup').style.display = val === 'range' ? 'block' : 'none';
    this.onFilterChange();
  },

  onFilterChange() {
    this.page = 0;
    this.loadData();
  },

  /* ── Cascade handlers ── */

  _resetDownstream(from) {
    var ids = { niveau: 'wldNiveau', semestre: 'wldSemestre', filiere: 'wldFiliere', module: 'wldModule' };
    var levels = ['niveau', 'semestre', 'filiere', 'module'];
    var start = levels.indexOf(from);
    if (start === -1) return;
    for (var i = start; i < levels.length; i++) {
      var sel = document.getElementById(ids[levels[i]]);
      if (sel) {
        sel.innerHTML = '<option value="">— Sélectionner —</option>';
        sel.disabled = true;
      }
    }
  },

  async onDeptChange() {
    this._resetDownstream('niveau');
    await this._loadNiveaux(document.getElementById('wldDept').value);
    this.page = 0;
    this.loadData();
  },

  async onNiveauChange() {
    this._resetDownstream('semestre');
    var niveau = document.getElementById('wldNiveau').value;
    if (niveau) {
      await this._loadSemestres(niveau);
    } else {
      await this._loadSemestresAll();
    }
    this.page = 0;
    this.loadData();
  },

  async onSemestreChange() {
    this._resetDownstream('filiere');
    var semestreId = document.getElementById('wldSemestre').value;
    if (semestreId) {
      await this._loadFilieres(
        document.getElementById('wldDept').value,
        semestreId
      );
    }
    this.page = 0;
    this.loadData();
  },

  async onFiliereChange() {
    this._resetDownstream('module');
    var filiereId = document.getElementById('wldFiliere').value;
    if (filiereId) await this._loadModules(filiereId);
    this.page = 0;
    this.loadData();
  },

  _buildParams() {
    var params = {};
    var dept = document.getElementById('wldDept').value;
    var filiere = document.getElementById('wldFiliere').value;
    var semestre = document.getElementById('wldSemestre').value;
    var module = document.getElementById('wldModule').value;
    var niveau = document.getElementById('wldNiveau').value;
    var teacher = document.getElementById('wldTeacher').value;
    var year = document.getElementById('wldYear').value;
    var period = document.getElementById('wldPeriod').value;

    if (dept) params.department_id = dept;
    if (filiere) params.filiere_id = filiere;
    if (semestre) params.semestre_id = semestre;
    if (module) params.module_id = module;
    if (niveau) params.niveau = niveau;
    if (teacher) params.teacher_id = teacher;
    if (year) params.academic_year = year;

    if (period === 'month') {
      var m = document.getElementById('wldMonth').value;
      var y = document.getElementById('wldYear').value || new Date().getFullYear();
      if (m) { params.month = m; params.year = String(y); }
    } else if (period === 'range') {
      var ds = document.getElementById('wldDateStart').value;
      var de = document.getElementById('wldDateEnd').value;
      if (ds) params.start_date = ds;
      if (de) params.end_date = de;
    }
    return params;
  },

  async loadData() {
    try {
      var params = this._buildParams();
      var qs = Object.keys(params).map(function (k) { return k + '=' + encodeURIComponent(params[k]); }).join('&');
      var url = '/teacher-workload-dashboard/' + (qs ? '?' + qs : '');
      var resp = await API.apiFetch(url);
      this.teachers = resp.teachers || [];
      this.totals = resp.totals || {};
      this.chartData = resp.chart_data || {};
    } catch (e) {
      this.teachers = [];
      this.totals = {};
      this.chartData = {};
      var tbody = document.getElementById('wldBody');
      if (tbody) tbody.innerHTML = '<tr class="empty-row"><td colspan="9">Erreur: ' + API.esc(e.message) + '</td></tr>';
    }
    this._applyFilters();
    this._renderRanking();
    this._renderTable();
    this._updateStats();
  },

  /* ── Ranking table ── */

  _renderRanking() {
    var tbody = document.getElementById('wldRankingBody');
    if (!tbody) return;
    var data = this.filtered;
    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:1rem">Aucune donnée</td></tr>';
      return;
    }
    var medals = ['&#x1F947;', '&#x1F948;', '&#x1F949;'];
    tbody.innerHTML = data.map(function (t, i) {
      var rank = i < 3 ? medals[i] : ('#' + (i + 1));
      return '<tr>' +
        '<td style="text-align:center;font-size:1.1rem">' + rank + '</td>' +
        '<td><strong>' + API.esc(t.first_name) + ' ' + API.esc(t.last_name) + '</strong></td>' +
        '<td style="text-align:right;font-weight:700;color:var(--accent)">' + t.equivalent_hours.toFixed(1) + 'h</td>' +
        '<td style="text-align:right;color:var(--primary)">' + t.cm_hours.toFixed(1) + 'h</td>' +
        '<td style="text-align:right;color:#0ea5e9">' + t.td_hours.toFixed(1) + 'h</td>' +
        '<td style="text-align:right;color:#f59e0b">' + t.tp_hours.toFixed(1) + 'h</td>' +
        '<td style="text-align:right">' + t.total_sessions + '</td>' +
      '</tr>';
    }).join('');
  },

  /* ── Table ── */

  _applyFilters() {
    this.filtered = this.teachers.slice();
    this._sort();
  },

  _sort() {
    var key = this.sortKey;
    var dir = this.sortDir;
    this.filtered.sort(function (a, b) {
      var va, vb;
      if (key === 'name') { va = (a.last_name + a.first_name).toLowerCase(); vb = (b.last_name + b.first_name).toLowerCase(); return va < vb ? -dir : va > vb ? dir : 0; }
      if (key === 'department') { va = (a.department || '').toLowerCase(); vb = (b.department || '').toLowerCase(); return va < vb ? -dir : va > vb ? dir : 0; }
      if (key === 'filieres') { va = (a.filieres || '').toLowerCase(); vb = (b.filieres || '').toLowerCase(); return va < vb ? -dir : va > vb ? dir : 0; }
      if (key === 'rank') return dir * (a.rank || a.id - b.id);
      if (key === 'cm') return dir * (a.cm_hours - b.cm_hours);
      if (key === 'td') return dir * (a.td_hours - b.td_hours);
      if (key === 'tp') return dir * (a.tp_hours - b.tp_hours);
      if (key === 'sessions') return dir * (a.total_sessions - b.total_sessions);
      return dir * (a.equivalent_hours - b.equivalent_hours);
    });
  },

  setSort(key) {
    if (this.sortKey === key) {
      this.sortDir *= -1;
    } else {
      this.sortKey = key;
      this.sortDir = -1;
    }
    this._sort();
    this.page = 0;
    this._renderTable();
  },

  _goToPage(delta) {
    var total = this.filtered.length;
    var maxPage = Math.max(0, Math.ceil(total / this.pageSize) - 1);
    this.page = Math.max(0, Math.min(maxPage, this.page + delta));
    this._renderTable();
  },

  _renderTable() {
    var tbody = document.getElementById('wldBody');
    var info = document.getElementById('wldPaginationInfo');

    if (!this.filtered.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="9">Aucune donnée pour les filtres sélectionnés.</td></tr>';
      if (info) info.textContent = '—';
      return;
    }

    var start = this.page * this.pageSize;
    var end = Math.min(start + this.pageSize, this.filtered.length);
    var pageItems = this.filtered.slice(start, end);

    tbody.innerHTML = pageItems.map(function (t, i) {
      return '<tr>' +
        '<td style="color:var(--muted)">' + (start + i + 1) + '</td>' +
        '<td><strong>' + API.esc(t.first_name) + ' ' + API.esc(t.last_name) + '</strong></td>' +
        '<td>' + API.esc(t.department || '—') + '</td>' +
        '<td>' + API.esc(t.filieres || '—') + '</td>' +
        '<td style="text-align:right">' + t.cm_hours.toFixed(2) + '</td>' +
        '<td style="text-align:right">' + t.td_hours.toFixed(2) + '</td>' +
        '<td style="text-align:right">' + t.tp_hours.toFixed(2) + '</td>' +
        '<td style="text-align:right">' + t.total_sessions + '</td>' +
        '<td style="text-align:right;font-weight:700;color:var(--accent)">' + t.equivalent_hours.toFixed(2) + '</td>' +
      '</tr>';
    }).join('');

    document.querySelectorAll('.sortable').forEach(function (th) {
      th.classList.remove('sorted-asc', 'sorted-desc');
      if (th.dataset.sort === wld.sortKey) {
        th.classList.add(wld.sortDir === -1 ? 'sorted-desc' : 'sorted-asc');
      }
    });

    if (info) {
      info.textContent = 'Affichage ' + (start + 1) + '–' + end + ' sur ' + this.filtered.length + ' enseignant(s)';
    }
  },

  _updateStats() {
    var filtered = this.filtered;
    var cm = 0, td = 0, tp = 0, eq = 0, sess = 0;
    filtered.forEach(function (t) { cm += t.cm_hours; td += t.td_hours; tp += t.tp_hours; eq += t.equivalent_hours; sess += t.total_sessions; });
    var avg = filtered.length > 0 ? eq / filtered.length : 0;
    document.getElementById('statTeacherCount').textContent = filtered.length;
    document.getElementById('statCM').textContent = cm.toFixed(1);
    document.getElementById('statTD').textContent = td.toFixed(1);
    document.getElementById('statTP').textContent = tp.toFixed(1);
    document.getElementById('statEquivalent').textContent = eq.toFixed(1);
    document.getElementById('statAvgEquivalent').textContent = avg.toFixed(1);
    document.getElementById('statSessions').textContent = sess;

    var te = document.getElementById('statTopTeacher');
    if (te) {
      var top = this.totals.top_teacher;
      te.textContent = top ? API.esc(top.name) + ' — ' + top.equivalent_hours.toFixed(1) + 'h' : '—';
    }
  },

  /* ── Export Excel ── */

  async exportExcel() {
    try {
      var params = this._buildParams();
      var qs = Object.keys(params).map(function (k) { return k + '=' + encodeURIComponent(params[k]); }).join('&');
      var url = '/teacher-monthly-report/' + (qs ? '?' + qs : '');
      var blob = await API.apiFetch(url);
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      var now = new Date();
      a.download = 'Charge_Horaire_Enseignants_' + String(now.getMonth() + 1).padStart(2, '0') + '_' + now.getFullYear() + '.xlsx';
      a.click();
      URL.revokeObjectURL(a.href);
      showToast('Rapport Excel téléchargé.', 'success');
    } catch (e) {
      showToast('Erreur export: ' + e.message, 'error');
    }
  }
};

/* ── Bind events ── */
wld.bindEvents = function () {
  document.addEventListener('click', function (e) {
    var th = e.target.closest('.sortable');
    if (th) wld.setSort(th.dataset.sort);
  });

  document.getElementById('btnExportExcel')?.addEventListener('click', function () { wld.exportExcel(); });

  document.getElementById('wldPagePrev')?.addEventListener('click', function () { wld._goToPage(-1); });
  document.getElementById('wldPageNext')?.addEventListener('click', function () { wld._goToPage(1); });

  document.getElementById('wldDept')?.addEventListener('change', function () { wld.onDeptChange(); });
  document.getElementById('wldNiveau')?.addEventListener('change', function () { wld.onNiveauChange(); });
  document.getElementById('wldSemestre')?.addEventListener('change', function () { wld.onSemestreChange(); });
  document.getElementById('wldFiliere')?.addEventListener('change', function () { wld.onFiliereChange(); });
  document.getElementById('wldModule')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldTeacher')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldYear')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldPeriod')?.addEventListener('change', function () { wld.onPeriodChange(); });
  document.getElementById('wldMonth')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldDateStart')?.addEventListener('change', function () { wld.onFilterChange(); });
  document.getElementById('wldDateEnd')?.addEventListener('change', function () { wld.onFilterChange(); });
};
