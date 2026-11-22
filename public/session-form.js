(function () {
  'use strict';

  const ACADEMIC_ORDER = ['niveau', 'semestre', 'filiere', 'module'];

  window.SessionForm = {
    isAdmin: false,
    userRole: null,
    classeId: null,
    blocksData: [],
    amphiData: [],
    teachersData: [],
    _availableRooms: null,
    _availableBlocks: null,
    _availableAmphis: null,
    _editingId: null,
    _editingData: null,
    _teacherClasses: [],
    _allClasses: [],
    _niveauCache: null,
    // Sélections académiques uniques (chaînes) + classes (multi, champ non concerné)
    _sel: { niveau: '', semestre: '', filiere: '', module: '', classe: [] },
    _enabled: { semestre: false, filiere: false, module: false, classe: false },
    _refreshToken: 0,
    // Champs académiques : menus déroulants natifs identiques à « Ajouter une classe ».
    // Seul le champ classe conserve le composant multiselect existant.
    _fields: {
      niveau:   { select: 'sfNiveau',   placeholder: '— Sélectionner —' },
      semestre: { select: 'sfSemestre', placeholder: "— Sélectionnez d'abord le niveau —" },
      filiere:  { select: 'sfFiliere',  placeholder: "— Sélectionnez d'abord le semestre —" },
      module:   { select: 'sfModule',   placeholder: "— Sélectionnez d'abord la filière —" },
      classe:   { radios: 'sfClasseOptions', summary: 'sfClasseSelected', placeholder: '— Sélectionner une classe —' },
    },

    /* ── PUBLIC API ── */

    async init(options) {
      this.isAdmin = options && options.isAdmin === true;
      this.userRole = (options && options.userRole) || null;
      this._ensureModal();
      this._bindEvents();
      var needsTeacher = this.userRole !== 'teacher';
      await Promise.all([
        needsTeacher ? Promise.all([this._loadNiveauOptions(), this._loadTeachers()]) : Promise.resolve(),
      ]);
      if (!needsTeacher) await this._loadNiveauOptions();
      this._renderNiveauSelect();
    },

    async open(classeId) {
      var requested = classeId || null;
      this._reset();
      this.classeId = requested;

      if (this.userRole === 'teacher') {
        await this._openForTeacher();
      } else {
        await this._loadNiveauOptions();
        await this._loadAllClasses();
        await this._refreshFromOptions();
      }
      openModal('modalSessionForm');
    },

    async edit(id) {
      var _this = this;
      this._editingId = id;
      try {
        var session = await API.apiFetch('/sessions/' + id + '/');
        this._editingData = session;
        this._reset();
        // `_reset()` efface l'état d'édition : on le rétablit ensuite pour que
        // `_submit()` envoie bien un PATCH et non un POST.
        this._editingId = id;
        this._editingData = session;

        this.classeId = session.classe || null;

        document.getElementById('sfDate').value = session.date || '';
        if (session.start_time) document.getElementById('sfStartTime').value = String(session.start_time).slice(0, 5);
        if (session.end_time) document.getElementById('sfEndTime').value = String(session.end_time).slice(0, 5);
        if (session.session_type) document.getElementById('sfSessionType').value = session.session_type;
        if (session.teacher) document.getElementById('sfTeacher').value = session.teacher;

        var titleEl = document.querySelector('#modalSessionForm .modal-header h3');
        if (titleEl) titleEl.textContent = 'Modifier la séance';
        document.getElementById('sfSubmit').textContent = 'Enregistrer';
        openModal('modalSessionForm');

        if (this.userRole === 'teacher') {
          var cFields = document.getElementById('sfCascadeFields');
          var tcField = document.getElementById('sfTeacherClassField');
          if (cFields) cFields.style.display = 'block';
          if (tcField) tcField.style.display = 'block';
          await this._loadTeacherClasses();
          await this._loadNiveauOptions();
          if (session.classe) {
            var cls = this._teacherClasses.find(function (c) { return c.id === session.classe; });
            if (cls) {
              await _this._preselectClassCombo(cls);
            }
          } else {
            this._refreshTeacherCascade();
          }
        } else if (session.classe) {
          try {
            var classe = await API.apiFetch('/classes/' + session.classe + '/');
            await _this._loadNiveauOptions();
            await _this._loadAllClasses();
            var moduleId = session.module_id || classe.module_id;
            _this._sel.niveau = classe.niveau_id ? String(classe.niveau_id) : '';
            _this._sel.semestre = classe.semestre_id != null ? String(classe.semestre_id) : '';
            _this._sel.filiere = classe.filiere_id != null ? String(classe.filiere_id) : '';
            _this._sel.module = moduleId != null ? String(moduleId) : '';
            _this._sel.classe = [String(classe.id)];
            await _this._refreshNonTeacherLevel();
          } catch (e) {
            // cascade pre-fill failed, user can select manually
          }
        }

      } catch (e) {
        this._editingId = null;
        this._editingData = null;
        showToast('Erreur lors du chargement de la séance: ' + e.message, 'error');
      }
    },

    /* ── MODAL HTML ── */

    _ensureModal() {
      if (document.getElementById('modalSessionForm')) return;
      const isTeacher = this.userRole === 'teacher';
      const html = `
<div class="modal-backdrop" id="modalSessionForm">
  <div class="modal">
    <div class="modal-header">
      <h3>Nouvelle séance</h3>
      <button class="modal-close" data-close="modalSessionForm">✕</button>
    </div>
    <div class="modal-body">
      <div id="sfCascadeFields">
        <div class="field">
          <label>Niveau <span class="req">*</span></label>
          <select id="sfNiveau">
            <option value="">— Sélectionner —</option>
          </select>
        </div>
        <div class="field">
          <label>Semestre <span class="req">*</span></label>
          <select id="sfSemestre" disabled>
            <option value="">— Sélectionnez d'abord le niveau —</option>
          </select>
        </div>
        <div class="field">
          <label>Filière <span class="req">*</span></label>
          <select id="sfFiliere" disabled>
            <option value="">— Sélectionnez d'abord le semestre —</option>
          </select>
        </div>
        <div class="field">
          <label>Module <span class="req">*</span></label>
          <select id="sfModule" disabled>
            <option value="">— Sélectionnez d'abord la filière —</option>
          </select>
        </div>
      </div>
      <div id="sfTeacherField"${isTeacher ? ' style="display:none"' : ''}>
        <label>Enseignant</label>
        <select id="sfTeacher"><option value="">— Sélectionner —</option></select>
      </div>
      <div class="field">
        <label>Type de séance</label>
        <select id="sfSessionType">
          <option value="Cours">Cours</option>
          <option value="TD">TD</option>
          <option value="TP">TP</option>
          <option value="Exam">Examen</option>
          <option value="Other">Autre</option>
        </select>
      </div>
      <div class="field" id="sfTeacherClassField" style="display:none">
        <label>Classe</label>
        <div class="multiselect">
          <div class="multiselect-selected placeholder" id="sfClasseSelected" data-ml-sel="classe">— Sélectionner une classe —</div>
          <div class="multiselect-options" id="sfClasseOptions" style="display:none"></div>
        </div>
      </div>
      <div class="field">
        <label>Heure de fin <span class="req">*</span></label>
        <input type="time" id="sfEndTime" value="16:00" />
      </div>
      <p style="font-size:.78rem;color:var(--muted);margin:0 0 .25rem">
        🕒 Démarrage immédiat : la date et l'heure de début sont enregistrées
        automatiquement par le serveur au moment de la création.
      </p>
      <p style="font-size:.78rem;color:var(--muted);margin:0">
        Le QR ne peut être généré que pendant ce créneau. Après la fin, seules les statistiques et l'export restent disponibles.
      </p>
      <!-- Valeurs internes (non modifiables) : démarrage réel / édition -->
      <input type="hidden" id="sfDate" />
      <input type="hidden" id="sfStartTime" />
    </div>
    <div class="modal-footer">
      <button class="btn outline" data-close="modalSessionForm">Annuler</button>
      <button class="btn" id="sfSubmit">Créer la séance</button>
    </div>
  </div>
</div>`;
      document.body.insertAdjacentHTML('beforeend', html);
      var modal = document.getElementById('modalSessionForm');
      modal.querySelectorAll('[data-close="modalSessionForm"]').forEach(function (el) {
        el.addEventListener('click', function () { closeModal('modalSessionForm'); });
      });
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeModal('modalSessionForm');
      });
    },

    /* ── HELPERS ── */

    _esc(str) {
      return String(str == null ? '' : str).replace(/[&<>"']/g, function (ch) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
      });
    },

    _el(id) {
      return document.getElementById(id);
    },

    _toggleOptions(level) {
      var f = this._fields[level];
      if (!f) return;
      var box = this._el(f.radios);
      if (box) box.style.display = box.style.display === 'none' ? 'block' : 'none';
    },

    _setEnabled(level, enabled) {
      var f = this._fields[level];
      if (!f) return;
      if (f.select) {
        var sel = this._el(f.select);
        if (sel) {
          sel.disabled = !enabled;
          if (!enabled) sel.value = '';
        }
        this._enabled[level] = !!enabled;
        return;
      }
      // Composant multiselect (classe) : comportement existant conservé.
      var box = this._el(f.radios);
      var summary = f.summary ? this._el(f.summary) : null;
      var wrap = summary ? summary.closest('.multiselect') : (box ? box.closest('.multiselect') : null);
      if (wrap) {
        wrap.style.opacity = enabled ? '' : '0.55';
        wrap.style.pointerEvents = enabled ? '' : 'none';
      }
      if (summary) summary.classList.toggle('disabled', !enabled);
      this._enabled[level] = !!enabled;
    },

    _placeholderOption(level) {
      var f = this._fields[level];
      return '<option value="">' + this._esc(f ? f.placeholder : '') + '</option>';
    },

    /**
     * Remplit un menu déroulant académique avec les libellés réels de la base.
     * Le premier choix est toujours le texte d'attente (valeur vide) ; une
     * sélection devenue incompatible est effacée. Aucun "#undefined" possible.
     */
    _renderSelect(level, options) {
      var f = this._fields[level];
      if (!f || !f.select) return;
      var sel = this._el(f.select);
      if (!sel) return;

      var opts = options || [];
      var ids = new Set(opts.map(function (o) { return String(o.id); }));
      if (this._sel[level] && !ids.has(String(this._sel[level]))) {
        this._sel[level] = '';
      }

      var self = this;
      var html = this._placeholderOption(level);
      html += opts.map(function (o) {
        var selected = String(self._sel[level]) === String(o.id) ? ' selected' : '';
        var label = o.label != null ? o.label : (o.name != null ? o.name : '');
        return '<option value="' + self._esc(o.id) + '"' + selected + '>' +
          self._esc(label) + '</option>';
      }).join('');
      sel.innerHTML = html;
      sel.value = this._sel[level] ? String(this._sel[level]) : '';
    },

    _renderNiveauSelect(options) {
      var opts = (options || this._niveauCache || []).map(function (n) {
        return { id: String(n.id), label: n.label || n.name || String(n.id) };
      });
      this._renderSelect('niveau', opts);
      var sel = this._el('sfNiveau');
      if (sel) sel.disabled = false;
    },

    _resetLevel(level) {
      this._sel[level] = '';
      var f = this._fields[level];
      if (!f) return;
      if (f.select) {
        var sel = this._el(f.select);
        if (sel) {
          sel.innerHTML = this._placeholderOption(level);
          sel.value = '';
          sel.disabled = true;
        }
        this._enabled[level] = false;
        return;
      }
      var box = this._el(f.radios);
      if (box) { box.innerHTML = ''; box.style.display = 'none'; }
      var summary = f.summary ? this._el(f.summary) : null;
      if (summary) {
        summary.textContent = f.placeholder;
        summary.classList.add('placeholder');
      }
      this._setEnabled(level, false);
    },

    _resetClasse() {
      this._sel.classe = [];
      this.classeId = null;
      var f = this._fields.classe;
      var box = this._el(f.radios);
      if (box) { box.innerHTML = ''; box.style.display = 'none'; }
      var summary = this._el(f.summary);
      if (summary) {
        summary.textContent = f.placeholder;
        summary.classList.add('placeholder');
      }
      this._enabled.classe = false;
    },

    _syncClasseFromControls(list) {
      var box = this._el(this._fields.classe.radios);
      var vals = [];
      if (box) {
        box.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
          if (cb.checked) vals.push(cb.value);
        });
      }
      this._sel.classe = vals;
      this.classeId = vals.length ? Number(vals[0]) : null;
      var summary = this._el(this._fields.classe.summary);
      if (!summary) return;
      if (!vals.length) {
        summary.textContent = this._fields.classe.placeholder;
        summary.classList.add('placeholder');
        return;
      }
      var names = vals.map(function (v) {
        var c = (list || []).find(function (x) { return String(x.id) === String(v); });
        return c && c.name ? String(c.name) : '';
      }).filter(function (n) { return n; });
      if (!names.length) {
        summary.textContent = this._fields.classe.placeholder;
        summary.classList.add('placeholder');
        return;
      }
      summary.textContent = names.join(', ');
      summary.classList.remove('placeholder');
    },

    _renderClasseList(list) {
      var self = this;
      var box = this._el(this._fields.classe.radios);
      if (!box) return;
      var ids = new Set((list || []).map(function (c) { return String(c.id); }));
      this._sel.classe = (this._sel.classe || []).filter(function (id) { return ids.has(String(id)); });
      if (!list || !list.length) {
        box.innerHTML = '<div class="multiselect-loading">Aucune classe disponible pour cette combinaison</div>';
      } else {
        box.innerHTML = list.map(function (c) {
          var checked = self._sel.classe.indexOf(String(c.id)) !== -1 ? ' checked' : '';
          return '<label class="multiselect-option">' +
            '<input type="checkbox" value="' + self._esc(c.id) + '"' + checked + '>' +
            '<span>' + self._esc(c.name || ('Classe #' + c.id)) + '</span></label>';
        }).join('');
        box.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
          cb.addEventListener('change', function () {
            self._syncClasseFromControls(list);
          });
        });
      }
      this._enabled.classe = true;
      this._syncClasseFromControls(list);
    },

    _onLevelChange(level, value) {
      this._sel[level] = value || '';
      var idx = ACADEMIC_ORDER.indexOf(level);
      if (idx >= 0) {
        var self = this;
        ACADEMIC_ORDER.slice(idx + 1).forEach(function (lv) {
          self._resetLevel(lv);
        });
      }
      this._resetClasse();
      this._refreshFromOptions();
    },

    /* ── DATA LOADING ── */

    async _loadNiveauOptions() {
      if (this._niveauCache) return this._niveauCache;
      try {
        var data = await API.apiFetch('/curriculum/niveaux/');
        this._niveauCache = Array.isArray(data) ? data : [];
      } catch (e) {
        this._niveauCache = [];
        showToast('Erreur chargement niveaux: ' + e.message, 'error');
      }
      return this._niveauCache;
    },

    async _fetchSemestres(niveau) {
      try {
        var data = await API.apiFetch('/curriculum/semestres-par-niveau/?niveau=' + encodeURIComponent(niveau));
        return (Array.isArray(data) ? data : []).map(function (s) {
          return { id: String(s.id), label: s.name };
        });
      } catch (e) {
        showToast('Erreur chargement semestres: ' + e.message, 'error');
        return [];
      }
    },

    async _fetchFilieres(niveau, semestreId) {
      try {
        var params = new URLSearchParams({ semestre_id: semestreId, niveau: niveau });
        var data = await API.apiFetch('/curriculum/filieres/?' + params.toString());
        return (Array.isArray(data) ? data : []).map(function (f) {
          return { id: String(f.id), label: f.name };
        });
      } catch (e) {
        showToast('Erreur chargement filières: ' + e.message, 'error');
        return [];
      }
    },

    async _fetchModules(filiereId, semestreId) {
      try {
        var params = new URLSearchParams({ filiere_id: filiereId });
        if (semestreId) params.set('semestre_id', semestreId);
        var data = await API.apiFetch('/curriculum/modules/?' + params.toString());
        return (Array.isArray(data) ? data : []).map(function (m) {
          return { id: String(m.id), label: m.name };
        });
      } catch (e) {
        showToast('Erreur chargement modules: ' + e.message, 'error');
        return [];
      }
    },

    _distinct(list, keyFn, labelFn) {
      var map = new Map();
      list.forEach(function (x) {
        var k = keyFn(x);
        if (k === null || k === undefined || k === '') return;
        var kk = String(k);
        if (!map.has(kk)) map.set(kk, labelFn(x) || kk);
      });
      return Array.from(map, function (entry) { return { id: entry[0], label: entry[1] }; });
    },

    _distinctNiveau(all) {
      var seen = new Set();
      var out = [];
      var cache = this._niveauCache || [];
      var byId = {};
      cache.forEach(function (n) { byId[String(n.id)] = n.label || n.name; });
      all.forEach(function (c) {
        if (!c.niveau_id) return;
        var k = String(c.niveau_id);
        if (seen.has(k)) return;
        seen.add(k);
        out.push({ id: k, label: byId[k] || c.niveau_id });
      });
      return out;
    },

    _refreshFromOptions() {
      if (this.userRole === 'teacher') return this._refreshTeacherCascade();
      return this._refreshNonTeacherLevel();
    },

    async _refreshNonTeacherLevel() {
      var token = ++this._refreshToken;
      this._renderNiveauSelect();
      var niveau = this._sel.niveau;
      if (!niveau) {
        this._resetLevel('semestre');
        this._resetLevel('filiere');
        this._resetLevel('module');
        this._resetClasse();
        return;
      }

      var sems = await this._fetchSemestres(niveau);
      if (token !== this._refreshToken) return;
      this._renderSelect('semestre', sems);
      this._setEnabled('semestre', true);
      if (!this._sel.semestre) {
        this._resetLevel('filiere');
        this._resetLevel('module');
        this._resetClasse();
        return;
      }

      var filieres = await this._fetchFilieres(niveau, this._sel.semestre);
      if (token !== this._refreshToken) return;
      this._renderSelect('filiere', filieres);
      this._setEnabled('filiere', true);
      if (!this._sel.filiere) {
        this._resetLevel('module');
        this._resetClasse();
        return;
      }

      var modules = await this._fetchModules(this._sel.filiere, this._sel.semestre);
      if (token !== this._refreshToken) return;
      this._renderSelect('module', modules);
      this._setEnabled('module', true);
      if (!this._sel.module) {
        this._resetClasse();
        return;
      }

      this._renderClasseList(this._filterClasses());
    },

    _filterClasses() {
      var s = this._sel;
      return (this._allClasses || []).filter(function (c) {
        return (!s.niveau || String(c.niveau_id) === String(s.niveau)) &&
          (!s.semestre || String(c.semestre_id) === String(s.semestre)) &&
          (!s.filiere || String(c.filiere_id) === String(s.filiere)) &&
          (!s.module || String(c.module_id) === String(s.module));
      });
    },

    _refreshTeacherCascade() {
      var all = this._teacherClasses || [];
      this._renderNiveauSelect(this._distinctNiveau(all));
      var niveau = this._sel.niveau;
      if (!niveau) {
        this._resetLevel('semestre');
        this._resetLevel('filiere');
        this._resetLevel('module');
        this._resetClasse();
        return;
      }

      var self = this;
      var semList = all.filter(function (c) { return String(c.niveau_id) === String(niveau); });
      this._renderSelect('semestre', this._distinct(semList, function (c) { return c.semestre_id; }, function (c) { return c.semestre_name; }));
      this._setEnabled('semestre', true);
      if (!this._sel.semestre) {
        this._resetLevel('filiere');
        this._resetLevel('module');
        this._resetClasse();
        return;
      }

      var filList = all.filter(function (c) {
        return String(c.niveau_id) === String(niveau) && String(c.semestre_id) === String(self._sel.semestre);
      });
      this._renderSelect('filiere', this._distinct(filList, function (c) { return c.filiere_id; }, function (c) { return c.filiere_name; }));
      this._setEnabled('filiere', true);
      if (!this._sel.filiere) {
        this._resetLevel('module');
        this._resetClasse();
        return;
      }

      var modList = all.filter(function (c) {
        return String(c.niveau_id) === String(niveau) &&
          String(c.semestre_id) === String(self._sel.semestre) &&
          String(c.filiere_id) === String(self._sel.filiere);
      });
      this._renderSelect('module', this._distinct(modList, function (c) { return c.module_id; }, function (c) { return c.module_name; }));
      this._setEnabled('module', true);
      if (!this._sel.module) {
        this._resetClasse();
        return;
      }

      var clsList = all.filter(function (c) {
        return String(c.niveau_id) === String(niveau) &&
          String(c.semestre_id) === String(self._sel.semestre) &&
          String(c.filiere_id) === String(self._sel.filiere) &&
          String(c.module_id) === String(self._sel.module);
      });
      this._renderClasseList(clsList.map(function (c) {
        return { id: c.id, name: c.name || ('Classe #' + c.id) };
      }));
    },

    async _loadBlocksAmphis() {
      try {
        var res = await Promise.all([
          API.apiFetch('/blocks/'),
          API.apiFetch('/amphitheaters/'),
        ]);
        this.blocksData = Array.isArray(res[0]) ? res[0] : [];
        this.amphiData = Array.isArray(res[1]) ? res[1] : [];
        this._populateLocationSelects();
      } catch (e) {
        this.blocksData = [];
        this.amphiData = [];
      }
    },

    /* ── AVAILABILITY ── */

    // Démarrage immédiat : valeurs locales indicatives. Le serveur reste
    // l'autorité et enregistre sa propre date/heure au moment de la création.
    _nowDateValue() {
      var now = new Date();
      return now.getFullYear() + '-' +
        String(now.getMonth() + 1).padStart(2, '0') + '-' +
        String(now.getDate()).padStart(2, '0');
    },

    _nowTimeValue() {
      var now = new Date();
      return String(now.getHours()).padStart(2, '0') + ':' +
        String(now.getMinutes()).padStart(2, '0');
    },

    _defaultEndTimeValue() {
      var now = new Date();
      var end = new Date(now.getTime() + 2 * 60 * 60 * 1000);
      if (end.getFullYear() !== now.getFullYear() ||
          end.getMonth() !== now.getMonth() ||
          end.getDate() !== now.getDate()) {
        return '23:59';
      }
      return String(end.getHours()).padStart(2, '0') + ':' +
        String(end.getMinutes()).padStart(2, '0');
    },

    _setImmediateStartFields() {
      document.getElementById('sfDate').value = this._nowDateValue();
      document.getElementById('sfStartTime').value = this._nowTimeValue();
    },

    async _fetchAvailableLocations() {
      if (!this._editingId) this._setImmediateStartFields();
      var date = document.getElementById('sfDate').value;
      var startTime = document.getElementById('sfStartTime').value;
      var endTime = document.getElementById('sfEndTime').value;
      if (!date || !startTime || !endTime) return;

      try {
        var params = new URLSearchParams({
          date: date,
          start_time: startTime,
          end_time: endTime,
        });
        var data = await API.apiFetch('/sessions/available-locations/?' + params.toString());
        if (!data) return;

        this._availableRooms = data.rooms || [];
        this._availableBlocks = data.blocks || [];
        this._availableAmphis = data.amphitheaters || [];

        var locType = document.getElementById('sfLocationType').value;
        if (locType === 'block' || locType === 'amphitheater') {
          this._populateLocationSelects();
          this._validateCurrentSelection();
        }
      } catch (e) {
        this._availableRooms = null;
        this._availableBlocks = null;
        this._availableAmphis = null;
        this._populateLocationSelects();
      }
    },

    _validateCurrentSelection() {
      var locType = document.getElementById('sfLocationType').value;
      if (locType === 'block') {
        var blockSel = document.getElementById('sfBlock');
        var roomSel = document.getElementById('sfRoom');
        if (blockSel.value && this._availableBlocks) {
          var block = this._availableBlocks.find(function (b) { return String(b.id) === blockSel.value; });
          if (block && roomSel.value && !block.rooms.some(function (r) { return String(r.id) === roomSel.value; })) {
            roomSel.value = '';
          }
        }
      } else if (locType === 'amphitheater') {
        var sel = document.getElementById('sfAmphi');
        if (sel.value && this._availableAmphis && !this._availableAmphis.some(function (a) { return String(a.id) === sel.value; })) {
          sel.value = '';
        }
      }
    },

    async _loadTeachers() {
      var sel = document.getElementById('sfTeacher');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      try {
        var data = await API.apiFetch('/teachers/');
        this.teachersData = Array.isArray(data) ? data : [];
        this.teachersData.forEach(function (t) {
          var opt = document.createElement('option');
          opt.value = t.id;
          opt.textContent = t.full_name + (t.email ? ' (' + t.email + ')' : '');
          sel.appendChild(opt);
        });
      } catch (e) { showToast(e.message, 'error'); }
    },

    /* ── TEACHER MODE HELPERS ── */

    async _openForTeacher() {
      var _this = this;
      var cFields = document.getElementById('sfCascadeFields');
      if (cFields) cFields.style.display = 'block';

      await this._loadTeacherClasses();

      if (!this._teacherClasses.length) {
        showToast("Aucune classe assignée. Contactez l'administration.", 'error');
        return;
      }

      var tcField = document.getElementById('sfTeacherClassField');
      if (tcField) tcField.style.display = 'block';

      await this._loadNiveauOptions();

      if (this.classeId != null && this.classeId) {
        var cls = this._teacherClasses.find(function (c) { return c.id === _this.classeId; });
        if (cls) {
          await this._preselectClassCombo(cls);
          return;
        }
        this.classeId = null;
      }

      if (this._teacherClasses.length === 1) {
        await this._preselectClassCombo(this._teacherClasses[0]);
        return;
      }

      this._refreshTeacherCascade();
    },

    async _loadAllClasses() {
      if (this._allClasses.length > 0) return;
      try {
        var data = await API.apiFetch('/classes/');
        this._allClasses = Array.isArray(data) ? data : (data.results || []);
      } catch (e) {
        this._allClasses = [];
        showToast('Erreur chargement classes: ' + e.message, 'error');
      }
    },

    async _loadTeacherClasses() {
      if (this._teacherClasses.length > 0) return;
      try {
        var data = await API.apiFetch('/classes/');
        this._teacherClasses = Array.isArray(data) ? data : (data.results || []);
      } catch (e) {
        this._teacherClasses = [];
        showToast('Erreur chargement classes: ' + e.message, 'error');
      }
    },

    async _preselectClassCombo(cls) {
      await this._loadNiveauOptions();
      this._sel.niveau = cls.niveau_id ? String(cls.niveau_id) : '';
      this._sel.semestre = cls.semestre_id != null ? String(cls.semestre_id) : '';
      this._sel.filiere = cls.filiere_id != null ? String(cls.filiere_id) : '';
      this._sel.module = cls.module_id != null ? String(cls.module_id) : '';
      this._sel.classe = [String(cls.id)];
      this.classeId = cls.id;
      this._refreshTeacherCascade();
      this._applyClassLocation(cls);
    },

    /**
     * Charge le lieu par défaut de la classe (défini par l'administrateur)
     * dans le formulaire. L'enseignant peut le modifier si nécessaire.
     */
    _applyClassLocation(cls) {
      if (this._editingId) return; // édition : le lieu de la séance est appliqué séparément
      var locTypeEl = document.getElementById('sfLocationType');
      var blockGroup = document.getElementById('sfBlockGroup');
      var amphiGroup = document.getElementById('sfAmphiGroup');
      if (!locTypeEl || !blockGroup || !amphiGroup) return;

      var type = cls.location_type || '';
      var mapped = null;
      if ((type === 'BLOC' || type === 'BOTH_ALLOWED') && cls.block_id && cls.room_id) {
        mapped = 'block';
      } else if ((type === 'AMPHI' || type === 'BOTH_ALLOWED') && cls.amphitheater_id) {
        mapped = 'amphitheater';
      } else if (type === 'BLOC' || type === 'BOTH_ALLOWED') {
        mapped = 'block';
      } else if (type === 'AMPHI') {
        mapped = 'amphitheater';
      }

      if (!mapped) {
        locTypeEl.value = '';
        blockGroup.style.display = 'none';
        amphiGroup.style.display = 'none';
        this._resetLocationFields();
        return;
      }

      locTypeEl.value = mapped;
      blockGroup.style.display = mapped === 'block' ? 'block' : 'none';
      amphiGroup.style.display = mapped === 'amphitheater' ? 'block' : 'none';

      var blockSel = document.getElementById('sfBlock');
      var roomSel = document.getElementById('sfRoom');
      var amphiSel = document.getElementById('sfAmphi');

      if (mapped === 'block') {
        blockSel.value = cls.block_id ? String(cls.block_id) : '';
        roomSel.value = '';
      } else {
        amphiSel.value = cls.amphitheater_id ? String(cls.amphitheater_id) : '';
      }

      this._populateLocationSelects();
      if (mapped === 'block' && cls.room_id) {
        roomSel.value = String(cls.room_id);
      }
      this._fetchAvailableLocations();
    },

    _resetLocationFields() {
      document.getElementById('sfBlock').innerHTML = '<option value="">— Sélectionner un bloc —</option>';
      document.getElementById('sfRoom').innerHTML = "<option value=\"\">— Sélectionner d'abord le bloc —</option>";
      document.getElementById('sfRoom').disabled = true;
      document.getElementById('sfAmphi').innerHTML = '<option value="">— Sélectionner un amphithéâtre —</option>';
    },

    /* ── UI HELPERS ── */

    _populateLocationSelects() {
      var locType = document.getElementById('sfLocationType').value;
      var blockSel = document.getElementById('sfBlock');
      var currentBlock = blockSel.value;
      blockSel.innerHTML = '<option value="">— Sélectionner un bloc —</option>';

      var blocks = this._availableBlocks;
      if (!blocks) {
        blocks = this.blocksData.map(function (b) {
          return { id: b.id, name: b.name, rooms: (b.rooms || []) };
        });
      }
      var hasRooms = false;
      blocks.forEach(function (b) {
        if (b.rooms && b.rooms.length) {
          hasRooms = true;
          var opt = document.createElement('option');
          opt.value = b.id;
          opt.textContent = b.name + ' (' + b.rooms.length + ' salle' + (b.rooms.length > 1 ? 's' : '') + ' disponible' + (b.rooms.length > 1 ? 's' : '') + ')';
          blockSel.appendChild(opt);
        }
      });
      if (!hasRooms) {
        blockSel.innerHTML = '<option value="">— Aucune salle disponible —</option>';
        blockSel.querySelector('option').disabled = true;
      }
      if (currentBlock && blocks.some(function (b) { return String(b.id) === currentBlock; })) {
        blockSel.value = currentBlock;
      }
      blockSel.dispatchEvent(new Event('change'));

      var amphiSel = document.getElementById('sfAmphi');
      var currentAmphi = amphiSel.value;
      amphiSel.innerHTML = '<option value="">— Sélectionner un amphithéâtre —</option>';
      var amphis = this._availableAmphis || this.amphiData;
      (amphis || []).forEach(function (a) {
        var opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.name;
        amphiSel.appendChild(opt);
      });
      if (!amphis || !amphis.length) {
        amphiSel.innerHTML = '<option value="">— Aucun amphithéâtre disponible —</option>';
        amphiSel.querySelector('option').disabled = true;
      }
      if (currentAmphi && amphis.some(function (a) { return String(a.id) === currentAmphi; })) {
        amphiSel.value = currentAmphi;
      }
    },

    _reset() {
      this._setImmediateStartFields();
      document.getElementById('sfEndTime').value = this._defaultEndTimeValue();
      document.getElementById('sfSessionType').value = 'Cours';
      this._editingId = null;
      this._editingData = null;

      // Réinitialisation complète de la cascade académique
      this._sel = { niveau: '', semestre: '', filiere: '', module: '', classe: [] };
      this._resetLevel('semestre');
      this._resetLevel('filiere');
      this._resetLevel('module');
      this._resetClasse();
      this._renderNiveauSelect();

      var tcField = document.getElementById('sfTeacherClassField');
      if (tcField) tcField.style.display = 'block';
      var tEl = document.querySelector('#modalSessionForm .modal-header h3');
      if (tEl) tEl.textContent = 'Nouvelle séance';
      var sBtn = document.getElementById('sfSubmit');
      if (sBtn) sBtn.textContent = 'Créer la séance';
    },

    /* ── EVENT BINDING ── */

    _bindEvents() {
      var self = this;

      // Menus déroulants académiques : Niveau → Semestre → Filière → Module
      ['niveau', 'semestre', 'filiere', 'module'].forEach(function (level) {
        var f = self._fields[level];
        var selEl = f && f.select ? document.getElementById(f.select) : null;
        if (selEl) {
          selEl.addEventListener('change', function () {
            self._onLevelChange(level, selEl.value);
          });
        }
      });

      var modal = document.getElementById('modalSessionForm');
      if (modal) {
        modal.addEventListener('click', function (e) {
          var openEl = e.target.closest('[data-ml-sel]');
          if (openEl) {
            var lv = openEl.getAttribute('data-ml-sel');
            if (self._enabled[lv]) self._toggleOptions(lv);
          }
        });
      }

      document.getElementById('sfSubmit').addEventListener('click', function () { self._submit(); });
    },

    /* ── SUBMIT ── */

    async _submit() {
      var _this = this;
      var s = this._sel;
      var isEditing = !!this._editingId;
      if (!isEditing) this._setImmediateStartFields();
      var date = document.getElementById('sfDate').value;
      var startTime = document.getElementById('sfStartTime').value;
      var endTime = document.getElementById('sfEndTime').value;

      // Cascade académique obligatoire et unique
      if (!s.niveau) { showToast('Veuillez sélectionner un niveau.', 'error'); return; }
      if (!s.semestre) { showToast('Veuillez sélectionner un semestre.', 'error'); return; }
      if (!s.filiere) { showToast('Veuillez sélectionner une filière.', 'error'); return; }
      if (!s.module) { showToast('Veuillez sélectionner un module.', 'error'); return; }

      if (this.userRole === 'teacher' && !(s.classe && s.classe.length)) {
        showToast('Veuillez sélectionner au moins une classe.', 'error');
        return;
      }
      if (this.userRole !== 'teacher' && !this._editingId && !(s.classe && s.classe.length)) {
        showToast('Veuillez sélectionner au moins une classe.', 'error');
        return;
      }
      if (!endTime) { showToast("L'heure de fin est obligatoire.", 'error'); return; }
      var referenceStart = isEditing ? startTime : this._nowTimeValue();
      if (endTime <= referenceStart) {
        showToast("L'heure de fin doit être après l'heure de début (démarrage immédiat).", 'error');
        return;
      }

      var bodyCore = {
        end_time: endTime,
        session_type: document.getElementById('sfSessionType').value,
      };
      if (isEditing) {
        // Édition : conserver la date et l'heure de début existantes.
        bodyCore.date = date;
        bodyCore.start_time = startTime;
      }

      if (this.userRole !== 'teacher') {
        var teacherVal = document.getElementById('sfTeacher').value;
        if (!teacherVal) { showToast('Veuillez sélectionner un enseignant.', 'error'); return; }
        bodyCore.teacher = Number(teacherVal);
      }

      // Combinaison académique réellement sélectionnée (validée aussi côté serveur)
      var academic = {
        niveau: s.niveau,
        semestre_id: Number(s.semestre),
        filiere_id: Number(s.filiere),
      };

      // Un payload (POST ou PATCH) par classe cible
      var payloads = [];
      if (this.userRole === 'teacher') {
        payloads = (s.classe || []).map(function (id) {
          var cls = _this._teacherClasses.find(function (c) { return String(c.id) === String(id); });
          if (!cls) return null;
          var body = Object.assign({}, bodyCore, academic, { module_id: Number(cls.module_id || s.module) });
          body.classe = cls.id;
          return { body: body, label: cls.name || ('Classe #' + cls.id) };
        }).filter(Boolean);
      } else {
        if (this._editingId) {
          var bodyEdit = Object.assign({}, bodyCore, academic, { module_id: Number(s.module) });
          if (this.classeId) bodyEdit.classe = this.classeId;
          payloads = [{ body: bodyEdit, label: '' }];
        } else {
          payloads = (s.classe || []).map(function (id) {
            var cls = _this._allClasses.find(function (c) { return String(c.id) === String(id); });
            if (!cls) return null;
            var body = Object.assign({}, bodyCore, academic, { module_id: Number(cls.module_id || s.module) });
            body.classe = cls.id;
            return { body: body, label: cls.name || ('Classe #' + cls.id) };
          }).filter(Boolean);
        }
      }

      if (!payloads.length) { showToast('Aucune classe valide sélectionnée.', 'error'); return; }

      await this._executePayloads(payloads, isEditing);
    },

    async _executePayloads(payloads, isEditing) {
      var btn = document.getElementById('sfSubmit');
      var multi = payloads.length > 1 && !isEditing;
      btn.disabled = true;
      try {
        if (multi) {
          var ok = 0;
          var fails = [];
          var lotIds = [];
          for (var i = 0; i < payloads.length; i++) {
            btn.textContent = 'Création… (' + (i + 1) + '/' + payloads.length + ')';
            try {
              if (lotIds.length) payloads[i].body.exclude_session_ids = lotIds.slice();
              var data = await API.apiFetch('/sessions/', { method: 'POST', body: JSON.stringify(payloads[i].body) });
              ok++;
              if (data && data.id) lotIds.push(Number(data.id));
              document.dispatchEvent(new CustomEvent('session-created', { detail: data }));
            } catch (e) {
              fails.push((payloads[i].label || 'Classe') + ' : ' + (e.message || 'erreur'));
            }
          }
          if (!fails.length) {
            closeModal('modalSessionForm');
            showToast(ok + ' séance(s) créée(s) avec succès.', 'success');
          } else {
            showToast(ok + ' créée(s), ' + fails.length + ' échec(s). ' + fails.slice(0, 3).join(' — '), 'error');
          }
          return;
        }

        var p = payloads[0];
        if (isEditing) {
          await API.apiFetch('/sessions/' + this._editingId + '/', { method: 'PATCH', body: JSON.stringify(p.body) });
          closeModal('modalSessionForm');
          showToast('Séance modifiée avec succès.', 'success');
          document.dispatchEvent(new CustomEvent('session-created', {}));
        } else {
          var created = await API.apiFetch('/sessions/', { method: 'POST', body: JSON.stringify(p.body) });
          closeModal('modalSessionForm');
          showToast('Séance créée avec succès.', 'success');
          document.dispatchEvent(new CustomEvent('session-created', { detail: created }));
        }
      } catch (e) {
        showToast('Erreur : ' + (e.message || 'Échec de la création de la séance.'), 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = isEditing ? 'Enregistrer' : 'Créer la séance';
      }
    },
  };
})();
