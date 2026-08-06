(function () {
  'use strict';

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
    _ml: null,
    _sel: { niveau: [], semestre: [], filiere: [], module: [], classe: [] },

    /* ── PUBLIC API ── */

    async init(options) {
      this.isAdmin = options && options.isAdmin === true;
      this.userRole = (options && options.userRole) || null;
      this._ensureModal();
      this._initMl();
      var needsTeacher = this.userRole !== 'teacher';
      await Promise.all([
        this._loadBlocksAmphis(),
        needsTeacher ? Promise.all([this._loadNiveauOptions(), this._loadTeachers()]) : Promise.resolve(),
      ]);
      this._bindEvents();
    },

    async open(classeId) {
      this.classeId = classeId || null;
      this._reset();
      document.getElementById('sfDate').value = new Date().toISOString().split('T')[0];

      if (this.userRole === 'teacher') {
        await this._openForTeacher();
      } else {
        await this._loadNiveauOptions();
        await this._loadAllClasses();
        await this._refreshFromOptions();
        if (!this.blocksData.length || !this.amphiData.length) {
          await this._loadBlocksAmphis();
          this._populateLocationSelects();
        }
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

        this.classeId = session.classe || null;

        document.getElementById('sfDate').value = session.date || '';
        if (session.start_time) document.getElementById('sfStartTime').value = session.start_time;
        if (session.end_time) document.getElementById('sfEndTime').value = session.end_time;
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
            _this._sel.niveau = classe.niveau_id ? [String(classe.niveau_id)] : [];
            _this._sel.semestre = classe.semestre_id != null ? [String(classe.semestre_id)] : [];
            _this._sel.filiere = classe.filiere_id != null ? [String(classe.filiere_id)] : [];
            _this._sel.module = moduleId != null ? [String(moduleId)] : [];
            _this._sel.classe = [String(classe.id)];
            await _this._refreshNonTeacherLevel();
          } catch (e) {
            // cascade pre-fill failed, user can select manually
          }
        }

        if (session.location_type) {
          document.getElementById('sfLocationType').value = session.location_type;
          document.getElementById('sfLocationType').dispatchEvent(new Event('change'));
          setTimeout(function () {
            if (session.location_type === 'block') {
              document.getElementById('sfBlock').value = session.block || '';
              document.getElementById('sfBlock').dispatchEvent(new Event('change'));
              setTimeout(function () {
                document.getElementById('sfRoom').value = session.room || '';
              }, 100);
            } else if (session.location_type === 'amphitheater') {
              document.getElementById('sfAmphi').value = session.amphitheater || '';
            }
          }, 200);
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
          <label>Niveau</label>
          <div class="multiselect">
            <div class="multiselect-selected placeholder" id="sfNiveauSelected" data-ml-sel="niveau">— Sélectionner —</div>
            <div class="multiselect-options" id="sfNiveauOptions" style="display:none"></div>
          </div>
        </div>
        <div class="field">
          <label>Semestre</label>
          <div class="multiselect">
            <div class="multiselect-selected placeholder" id="sfSemestreSelected" data-ml-sel="semestre">— Sélectionnez d'abord un niveau —</div>
            <div class="multiselect-options" id="sfSemestreOptions" style="display:none"></div>
          </div>
        </div>
        <div class="field">
          <label>Filière</label>
          <div class="multiselect">
            <div class="multiselect-selected placeholder" id="sfFiliereSelected" data-ml-sel="filiere">— Sélectionnez d'abord un semestre —</div>
            <div class="multiselect-options" id="sfFiliereOptions" style="display:none"></div>
          </div>
        </div>
        <div class="field">
          <label>Module</label>
          <div class="multiselect">
            <div class="multiselect-selected placeholder" id="sfModuleSelected" data-ml-sel="module">— Sélectionnez d'abord une filière —</div>
            <div class="multiselect-options" id="sfModuleOptions" style="display:none"></div>
          </div>
        </div>
      </div>
      <div class="field">
        <label>Type de lieu</label>
        <select id="sfLocationType">
          <option value="">— Sélectionner —</option>
          <option value="block">Bloc / Salle</option>
          <option value="amphitheater">Amphithéâtre</option>
        </select>
        <p style="font-size:.75rem;color:var(--muted);margin:.25rem 0 0">
          Lieu par défaut de la classe, modifiable en cas de changement exceptionnel.
        </p>
      </div>
      <div id="sfBlockGroup" style="display:none">
        <div class="field">
          <label>Bloc</label>
          <select id="sfBlock"><option value="">— Sélectionner un bloc —</option></select>
        </div>
        <div class="field">
          <label>Salle</label>
          <select id="sfRoom" disabled><option value="">— Sélectionner d'abord le bloc —</option></select>
        </div>
      </div>
      <div id="sfAmphiGroup" style="display:none">
        <div class="field">
          <label>Amphithéâtre</label>
          <select id="sfAmphi"><option value="">— Sélectionner un amphithéâtre —</option></select>
        </div>
      </div>
      <div class="field" id="sfTeacherField"${isTeacher ? ' style="display:none"' : ''}>
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
        <label>Date</label>
        <input type="date" id="sfDate" />
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
        <div class="field">
          <label>Heure de début</label>
          <input type="time" id="sfStartTime" value="14:00" />
        </div>
        <div class="field">
          <label>Heure de fin</label>
          <input type="time" id="sfEndTime" value="16:00" />
        </div>
      </div>
      <p style="font-size:.78rem;color:var(--muted);margin:0">
        Le QR ne peut être généré que pendant ce créneau. Après la fin, seules les statistiques et l'export restent disponibles.
      </p>
    </div>
    <div class="modal-footer">
      <button class="btn outline" data-close="modalSessionForm">Annuler</button>
      <button class="btn" id="sfSubmit">Créer la séance</button>
    </div>
  </div>
</div>`;
      document.body.insertAdjacentHTML('beforeend', html);
      // Bind close handlers for this dynamically created modal
      var modal = document.getElementById('modalSessionForm');
      modal.querySelectorAll('[data-close="modalSessionForm"]').forEach(function (el) {
        el.addEventListener('click', function () { closeModal('modalSessionForm'); });
      });
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeModal('modalSessionForm');
      });
    },

    /* ── MULTISELECT ── */

    _initMl() {
      if (this._ml) return;
      this._ml = {
        niveau:   { selId: 'sfNiveauSelected',   optId: 'sfNiveauOptions',   placeholder: '— Sélectionner —' },
        semestre: { selId: 'sfSemestreSelected', optId: 'sfSemestreOptions', placeholder: "— Sélectionnez d'abord un niveau —" },
        filiere:  { selId: 'sfFiliereSelected',  optId: 'sfFiliereOptions',  placeholder: "— Sélectionnez d'abord un semestre —" },
        module:   { selId: 'sfModuleSelected',   optId: 'sfModuleOptions',   placeholder: "— Sélectionnez d'abord une filière —" },
        classe:   { selId: 'sfClasseSelected',   optId: 'sfClasseOptions',   placeholder: '— Sélectionner une classe —' },
      };
    },

    _esc(str) {
      return String(str == null ? '' : str).replace(/[&<>"']/g, function (ch) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
      });
    },

    _toggleMlOptions(level) {
      const f = this._ml[level];
      if (!f) return;
      const box = document.getElementById(f.optId);
      if (box) box.style.display = box.style.display === 'none' ? 'block' : 'none';
    },

    _renderMlSummary(level) {
      const f = this._ml[level];
      if (!f) return;
      const el = document.getElementById(f.selId);
      if (!el) return;
      const vals = this._sel[level] || [];
      if (!vals.length) {
        el.textContent = f.placeholder;
        el.classList.add('placeholder');
        return;
      }
      el.classList.remove('placeholder');
      const self = this;
      el.innerHTML = vals.map(function (v) {
        const o = (f.data || {})[String(v)];
        const label = o ? o.label : ('#' + v);
        return '<span class="multiselect-chip">' + self._esc(label) +
          ' <span class="chip-x" data-ml-remove="' + level + '" data-ml-value="' + self._esc(v) + '">✕</span></span>';
      }).join('');
    },

    _setLevelOptions(level, opts) {
      const f = this._ml[level];
      if (!f) return;
      const self = this;
      f.data = {};
      opts.forEach(function (o) { f.data[String(o.id)] = o; });
      const valid = new Set(opts.map(function (o) { return String(o.id); }));
      this._sel[level] = (this._sel[level] || []).filter(function (v) { return valid.has(v); });
      const box = document.getElementById(f.optId);
      if (box) {
        if (!opts.length) {
          box.innerHTML = '<div class="multiselect-loading">Aucune option</div>';
        } else {
          box.innerHTML = opts.map(function (o) {
            const checked = (self._sel[level] || []).indexOf(String(o.id)) !== -1 ? 'checked' : '';
            return '<label class="multiselect-option"><input type="checkbox" value="' + self._esc(o.id) + '" ' + checked + '><span>' + self._esc(o.label) + '</span></label>';
          }).join('');
        }
      }
      this._renderMlSummary(level);
    },

    _syncSelectionsFromControls() {
      const self = this;
      ['niveau', 'semestre', 'filiere', 'module', 'classe'].forEach(function (lv) {
        const box = document.getElementById(self._ml[lv].optId);
        const vals = [];
        if (box) {
          box.querySelectorAll('input[type=checkbox]').forEach(function (inp) {
            if (inp.checked) vals.push(inp.value);
          });
        }
        self._sel[lv] = vals;
      });
    },

    _removeMlValue(level, value) {
      this._sel[level] = (this._sel[level] || []).filter(function (v) { return v !== value; });
      const f = this._ml[level];
      if (f) {
        const box = document.getElementById(f.optId);
        if (box) {
          box.querySelectorAll('input[type=checkbox]').forEach(function (inp) {
            if (inp.value === value) inp.checked = false;
          });
        }
      }
      this._renderMlSummary(level);
      this._refreshFromOptions();
      this._syncClasseId();
    },

    _syncClasseId() {
      const c = this._sel.classe || [];
      this.classeId = c.length ? Number(c[0]) : null;
    },

    _clearAllMl() {
      const self = this;
      if (!this._ml) return;
      Object.keys(this._ml).forEach(function (lv) {
        self._sel[lv] = [];
        const box = document.getElementById(self._ml[lv].optId);
        if (box) { box.innerHTML = ''; box.style.display = 'none'; }
        self._renderMlSummary(lv);
      });
      this.classeId = null;
    },

    /* ── DATA LOADING ── */

    async _loadNiveauOptions() {
      if (this._niveauCache) return this._niveauCache;
      try {
        const data = await API.apiFetch('/curriculum/niveaux/');
        this._niveauCache = Array.isArray(data) ? data : [];
      } catch (e) {
        this._niveauCache = [];
        showToast('Erreur chargement niveaux: ' + e.message, 'error');
      }
      return this._niveauCache;
    },

    _distinct(list, keyFn, labelFn) {
      const map = new Map();
      list.forEach(function (x) {
        const k = keyFn(x);
        if (k === null || k === undefined || k === '') return;
        const kk = String(k);
        if (!map.has(kk)) map.set(kk, labelFn(x) || kk);
      });
      return Array.from(map, function (entry) { return { id: entry[0], label: entry[1] }; });
    },

    _distinctNiveau(all) {
      const seen = new Set();
      const out = [];
      const cache = this._niveauCache || [];
      const byId = {};
      cache.forEach(function (n) { byId[String(n.id)] = n.label; });
      all.forEach(function (c) {
        if (!c.niveau_id) return;
        const k = String(c.niveau_id);
        if (seen.has(k)) return;
        seen.add(k);
        out.push({ id: k, label: byId[k] || c.niveau_id });
      });
      return out;
    },

    _refreshFromOptions() {
      if (this.userRole === 'teacher') this._refreshTeacherCascade();
      else this._refreshNonTeacherLevel();
    },

    _refreshTeacherCascade() {
      const all = this._teacherClasses || [];
      const s = this._sel;
      const hitN = function (v) { return s.niveau.indexOf(String(v)) !== -1; };
      const hitS = function (v) { return s.semestre.indexOf(String(v)) !== -1; };
      const hitF = function (v) { return s.filiere.indexOf(String(v)) !== -1; };
      const hitM = function (v) { return s.module.indexOf(String(v)) !== -1; };

      // Niveau : toujours la liste des niveaux affectés (premier niveau, rien ne le filtre)
      this._setLevelOptions('niveau', this._distinctNiveau(all));

      // Semestre : uniquement si au moins un niveau est coché
      if (!s.niveau.length) {
        this._setLevelOptions('semestre', []);
        this._setLevelOptions('filiere', []);
        this._setLevelOptions('module', []);
        this._setLevelOptions('classe', []);
        return;
      }
      const semList = all.filter(function (c) { return hitN(c.niveau_id); });
      this._setLevelOptions('semestre', this._distinct(semList, function (c) { return c.semestre_id; }, function (c) { return c.semestre_name; }));

      // Filière : uniquement si au moins un semestre est coché
      if (!s.semestre.length) {
        this._setLevelOptions('filiere', []);
        this._setLevelOptions('module', []);
        this._setLevelOptions('classe', []);
        return;
      }
      const filList = all.filter(function (c) { return hitN(c.niveau_id) && hitS(c.semestre_id); });
      this._setLevelOptions('filiere', this._distinct(filList, function (c) { return c.filiere_id; }, function (c) { return c.filiere_name; }));

      // Module : uniquement si au moins une filière est cochée
      if (!s.filiere.length) {
        this._setLevelOptions('module', []);
        this._setLevelOptions('classe', []);
        return;
      }
      const modList = all.filter(function (c) { return hitN(c.niveau_id) && hitS(c.semestre_id) && hitF(c.filiere_id); });
      this._setLevelOptions('module', this._distinct(modList, function (c) { return c.module_id; }, function (c) { return c.module_name; }));

      // Classe : uniquement si au moins un module est coché
      if (!s.module.length) {
        this._setLevelOptions('classe', []);
        return;
      }
      const clsList = all.filter(function (c) { return hitN(c.niveau_id) && hitS(c.semestre_id) && hitF(c.filiere_id) && hitM(c.module_id); });
      this._setLevelOptions('classe', clsList.map(function (c) { return { id: c.id, label: c.name || ('Classe #' + c.id) }; }));
    },

    async _refreshNonTeacherLevel() {
      const s = this._sel;
      this._setLevelOptions('niveau', (this._niveauCache || []).map(function (n) { return { id: String(n.id), label: n.label }; }));
      if (!s.niveau.length) {
        this._setLevelOptions('semestre', []);
        this._setLevelOptions('filiere', []);
        this._setLevelOptions('module', []);
        return;
      }
      const semMap = new Map();
      for (let i = 0; i < s.niveau.length; i++) {
        const nId = s.niveau[i];
        try {
          const data = await API.apiFetch('/curriculum/semestres-par-niveau/?niveau=' + encodeURIComponent(nId));
          (Array.isArray(data) ? data : []).forEach(function (x) { semMap.set(String(x.id), x.name); });
        } catch (e) { /* ignore nested errors */ }
      }
      this._setLevelOptions('semestre', Array.from(semMap, function (e) { return { id: e[0], label: e[1] }; }));
      if (!s.semestre.length) {
        this._setLevelOptions('filiere', []);
        this._setLevelOptions('module', []);
        return;
      }
      const filMap = new Map();
      for (let nIdx = 0; nIdx < s.niveau.length; nIdx++) {
        const nId = s.niveau[nIdx];
        for (let sIdx = 0; sIdx < s.semestre.length; sIdx++) {
          const params = new URLSearchParams({ semestre_id: s.semestre[sIdx], niveau: nId });
          try {
            const data = await API.apiFetch('/curriculum/filieres/?' + params.toString());
            (Array.isArray(data) ? data : []).forEach(function (f) { filMap.set(String(f.id), f.name); });
          } catch (e) { /* ignore nested errors */ }
        }
      }
      this._setLevelOptions('filiere', Array.from(filMap, function (e) { return { id: e[0], label: e[1] }; }));
      if (!s.filiere.length) {
        this._setLevelOptions('module', []);
        return;
      }
      const modMap = new Map();
      for (let i = 0; i < s.filiere.length; i++) {
        try {
          const data = await API.apiFetch('/curriculum/modules/?filiere_id=' + encodeURIComponent(s.filiere[i]));
          (Array.isArray(data) ? data : []).forEach(function (m) { modMap.set(String(m.id), m.name); });
        } catch (e) { /* ignore nested errors */ }
      }
      this._setLevelOptions('module', Array.from(modMap, function (e) { return { id: e[0], label: e[1] }; }));

      // Classe : uniquement si au moins un module est coché — filtrage strict sur
      // les classes réelles conformes à la combinaison (AND inter-niveaux).
      if (!s.module.length) {
        this._setLevelOptions('classe', []);
        return;
      }
      const all = this._allClasses || [];
      const hitN2 = function (v) { return s.niveau.indexOf(String(v)) !== -1; };
      const hitS2 = function (v) { return s.semestre.indexOf(String(v)) !== -1; };
      const hitF2 = function (v) { return s.filiere.indexOf(String(v)) !== -1; };
      const hitM2 = function (v) { return s.module.indexOf(String(v)) !== -1; };
      const clsList = all.filter(function (c) {
        return hitN2(c.niveau_id) && hitS2(c.semestre_id) && hitF2(c.filiere_id) && hitM2(c.module_id);
      });
      this._setLevelOptions('classe', clsList.map(function (c) { return { id: c.id, label: c.name || ('Classe #' + c.id) }; }));
    },

    async _loadBlocksAmphis() {
      try {
        const [blocks, amphis] = await Promise.all([
          API.apiFetch('/blocks/'),
          API.apiFetch('/amphitheaters/'),
        ]);
        this.blocksData = Array.isArray(blocks) ? blocks : [];
        this.amphiData = Array.isArray(amphis) ? amphis : [];
        this._populateLocationSelects();
      } catch (e) {
        this.blocksData = [];
        this.amphiData = [];
      }
    },

    /* ── AVAILABILITY ── */

    async _fetchAvailableLocations() {
      const date = document.getElementById('sfDate').value;
      const startTime = document.getElementById('sfStartTime').value;
      const endTime = document.getElementById('sfEndTime').value;
      if (!date || !startTime || !endTime) return;

      try {
        const params = new URLSearchParams({
          date: date,
          start_time: startTime,
          end_time: endTime,
        });
        const data = await API.apiFetch('/sessions/available-locations/?' + params.toString());
        if (!data) return;

        this._availableRooms = data.rooms || [];
        this._availableBlocks = data.blocks || [];
        this._availableAmphis = data.amphitheaters || [];

        const locType = document.getElementById('sfLocationType').value;
        if (locType === 'block') {
          this._populateLocationSelects();
          this._validateCurrentSelection();
        } else if (locType === 'amphitheater') {
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
      const locType = document.getElementById('sfLocationType').value;
      if (locType === 'block') {
        const blockSel = document.getElementById('sfBlock');
        const roomSel = document.getElementById('sfRoom');
        if (blockSel.value && this._availableBlocks) {
          const block = this._availableBlocks.find(function (b) { return String(b.id) === blockSel.value; });
          if (block && roomSel.value && !block.rooms.some(function (r) { return String(r.id) === roomSel.value; })) {
            roomSel.value = '';
          }
        }
      } else if (locType === 'amphitheater') {
        const sel = document.getElementById('sfAmphi');
        if (sel.value && this._availableAmphis && !this._availableAmphis.some(function (a) { return String(a.id) === sel.value; })) {
          sel.value = '';
        }
      }
    },

    async _loadTeachers() {
      const sel = document.getElementById('sfTeacher');
      sel.innerHTML = '<option value="">— Sélectionner —</option>';
      try {
        const data = await API.apiFetch('/teachers/');
        this.teachersData = Array.isArray(data) ? data : [];
        this.teachersData.forEach(function (t) {
          const opt = document.createElement('option');
          opt.value = t.id;
          opt.textContent = t.full_name + (t.email ? ' (' + t.email + ')' : '');
          sel.appendChild(opt);
        });
      } catch (e) { showToast(e.message, 'error'); }
    },

    /* ── TEACHER MODE HELPERS ── */

    async _openForTeacher() {
      var _this = this;
      const cFields = document.getElementById('sfCascadeFields');
      if (cFields) cFields.style.display = 'block';

      if (!this.blocksData.length || !this.amphiData.length) {
        await this._loadBlocksAmphis();
        this._populateLocationSelects();
      }

      await this._loadTeacherClasses();

      if (!this._teacherClasses.length) {
        showToast("Aucune classe assignée. Contactez l'administration.", 'error');
        return;
      }

      const tcField = document.getElementById('sfTeacherClassField');
      if (tcField) tcField.style.display = 'block';

      await this._loadNiveauOptions();

      if (this.classeId != null && this.classeId) {
        const cls = this._teacherClasses.find(function (c) { return c.id === _this.classeId; });
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

      // Plusieurs classes : l'enseignant coche
      // niveau → semestre → filière → module → type de séance → classe(s).
      this._refreshTeacherCascade();
      this._syncClasseId();
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
      this._sel.niveau = cls.niveau_id ? [String(cls.niveau_id)] : [];
      this._sel.semestre = cls.semestre_id != null ? [String(cls.semestre_id)] : [];
      this._sel.filiere = cls.filiere_id != null ? [String(cls.filiere_id)] : [];
      this._sel.module = cls.module_id != null ? [String(cls.module_id)] : [];
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
      const locType = document.getElementById('sfLocationType').value;
      const blockSel = document.getElementById('sfBlock');
      const currentBlock = blockSel.value;
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
          const opt = document.createElement('option');
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

      const amphiSel = document.getElementById('sfAmphi');
      const currentAmphi = amphiSel.value;
      amphiSel.innerHTML = '<option value="">— Sélectionner un amphithéâtre —</option>';
      var amphis = this._availableAmphis || this.amphiData;
      (amphis || []).forEach(function (a) {
        const opt = document.createElement('option');
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
      const now = new Date();
      const y = now.getFullYear();
      const m = now.getMonth() + 1;
      const d = now.getDate();
      document.getElementById('sfDate').value = y + '-' + String(m).padStart(2, '0') + '-' + String(d).padStart(2, '0');
      document.getElementById('sfStartTime').value = '14:00';
      document.getElementById('sfEndTime').value = '16:00';
      document.getElementById('sfLocationType').value = '';
      document.getElementById('sfBlockGroup').style.display = 'none';
      document.getElementById('sfAmphiGroup').style.display = 'none';
      this._resetLocationFields();
      document.getElementById('sfSessionType').value = 'Cours';
      this._availableRooms = null;
      this._availableBlocks = null;
      this._availableAmphis = null;
      this._populateLocationSelects();
      this._editingId = null;
      this._editingData = null;
      this._clearAllMl();
      var tcField = document.getElementById('sfTeacherClassField');
      if (tcField) tcField.style.display = 'block';
      var tEl = document.querySelector('#modalSessionForm .modal-header h3');
      if (tEl) tEl.textContent = 'Nouvelle séance';
      var sBtn = document.getElementById('sfSubmit');
      if (sBtn) sBtn.textContent = 'Créer la séance';
    },

    /* ── EVENT BINDING ── */

    _bindEvents() {
      const self = this;

      ['niveau', 'semestre', 'filiere', 'module', 'classe'].forEach(function (lv) {
        const box = document.getElementById(self._ml[lv].optId);
        if (box) {
          box.addEventListener('change', function () {
            self._syncSelectionsFromControls();
            self._refreshFromOptions();
            self._syncClasseId();
          });
        }
      });

      const modal = document.getElementById('modalSessionForm');
      if (modal) {
        modal.addEventListener('click', function (e) {
          const chip = e.target.closest('.chip-x');
          if (chip) {
            e.stopPropagation();
            const lv = chip.getAttribute('data-ml-remove');
            const val = chip.getAttribute('data-ml-value');
            if (lv && val) self._removeMlValue(lv, val);
            return;
          }
          const openEl = e.target.closest('[data-ml-sel]');
          if (openEl) self._toggleMlOptions(openEl.getAttribute('data-ml-sel'));
        });
      }

      document.getElementById('sfLocationType').addEventListener('change', function () {
        const val = this.value;
        document.getElementById('sfBlockGroup').style.display = val === 'block' ? 'block' : 'none';
        document.getElementById('sfAmphiGroup').style.display = val === 'amphitheater' ? 'block' : 'none';
        self._populateLocationSelects();
        self._fetchAvailableLocations();
      });

      // Re-check availability when date or time changes
      ['sfDate', 'sfStartTime', 'sfEndTime'].forEach(function (id) {
        document.getElementById(id).addEventListener('change', function () {
          const locType = document.getElementById('sfLocationType').value;
          if (locType) {
            self._populateLocationSelects();
            self._fetchAvailableLocations();
          }
        });
      });

      document.getElementById('sfBlock').addEventListener('change', function () {
        const blockId = parseInt(this.value);
        const roomSel = document.getElementById('sfRoom');
        roomSel.innerHTML = '<option value="">— Sélectionner —</option>';
        roomSel.disabled = !blockId;
        if (blockId) {
          var rooms = null;
          if (self._availableBlocks) {
            var ab = self._availableBlocks.find(function (b) { return b.id === blockId; });
            if (ab) rooms = ab.rooms;
          } else {
            var fb = self.blocksData.find(function (b) { return b.id === blockId; });
            if (fb) rooms = fb.rooms;
          }
          if (rooms && rooms.length) {
            rooms.forEach(function (r) {
              const opt = document.createElement('option');
              opt.value = r.id;
              opt.textContent = r.name;
              roomSel.appendChild(opt);
            });
          } else if (self._availableBlocks) {
            roomSel.innerHTML = '<option value="">— Aucune salle disponible —</option>';
            roomSel.querySelector('option').disabled = true;
          }
        }
      });

      document.getElementById('sfSubmit').addEventListener('click', function () { self._submit(); });
    },

    /* ── SUBMIT ── */

    async _submit() {
      var _this = this;
      const s = this._sel;
      const moduleIds = s.module || [];
      const locType = document.getElementById('sfLocationType').value;
      const date = document.getElementById('sfDate').value;
      const startTime = document.getElementById('sfStartTime').value;
      const endTime = document.getElementById('sfEndTime').value;

      if (!moduleIds.length) {
        showToast('Veuillez sélectionner au moins un module.', 'error');
        return;
      }
      if (this.userRole === 'teacher' && !(s.classe && s.classe.length)) {
        showToast('Veuillez sélectionner au moins une classe.', 'error');
        return;
      }
      if (this.userRole !== 'teacher' && !this._editingId && !(s.classe && s.classe.length)) {
        showToast('Veuillez sélectionner au moins une classe.', 'error');
        return;
      }
      if (!date || !startTime || !endTime) { showToast('Date et horaires obligatoires.', 'error'); return; }
      if (endTime <= startTime) { showToast("L'heure de fin doit être après l'heure de début.", 'error'); return; }
      if (!locType) { showToast('Veuillez sélectionner un type de lieu.', 'error'); return; }

      const bodyCore = {
        date: date,
        start_time: startTime,
        end_time: endTime,
        location_type: locType,
        session_type: document.getElementById('sfSessionType').value,
      };

      if (locType === 'block') {
        const blockId = document.getElementById('sfBlock').value;
        const roomId = document.getElementById('sfRoom').value;
        if (!blockId) { showToast('Veuillez sélectionner un bloc.', 'error'); return; }
        if (!roomId) { showToast('Veuillez sélectionner une salle.', 'error'); return; }
        if (this._availableBlocks) {
          const ab = this._availableBlocks.find(function (b) { return String(b.id) === blockId; });
          if (!ab || !ab.rooms.some(function (r) { return String(r.id) === roomId; })) {
            showToast("Cette salle n'est plus disponible pour ce créneau.", 'error');
            return;
          }
        }
        bodyCore.block = Number(blockId);
        bodyCore.room = Number(roomId);
      } else if (locType === 'amphitheater') {
        const amphiId = document.getElementById('sfAmphi').value;
        if (!amphiId) { showToast('Veuillez sélectionner un amphithéâtre.', 'error'); return; }
        if (this._availableAmphis && !this._availableAmphis.some(function (a) { return String(a.id) === amphiId; })) {
          showToast("Cet amphithéâtre n'est plus disponible pour ce créneau.", 'error');
          return;
        }
        bodyCore.amphitheater = Number(amphiId);
      }

      if (this.userRole !== 'teacher') {
        const teacherVal = document.getElementById('sfTeacher').value;
        if (!teacherVal) { showToast('Veuillez sélectionner un enseignant.', 'error'); return; }
        bodyCore.teacher = Number(teacherVal);
      }

      const isEditing = !!this._editingId;

      // Un payload (POST ou PATCH) par classe cible
      let payloads = [];
      if (this.userRole === 'teacher') {
        payloads = (s.classe || []).map(function (id) {
          const cls = _this._teacherClasses.find(function (c) { return String(c.id) === String(id); });
          if (!cls) return null;
          const body = Object.assign({}, bodyCore, { module_id: Number(cls.module_id) });
          body.classe = cls.id;
          return { body: body, label: cls.name || ('Classe #' + cls.id) };
        }).filter(Boolean);
      } else {
        if (this._editingId) {
          const body = Object.assign({}, bodyCore, { module_id: Number(moduleIds[0]) });
          if (this.classeId) body.classe = this.classeId;
          payloads = [{ body: body, label: '' }];
        } else {
          payloads = (s.classe || []).map(function (id) {
            const cls = _this._allClasses.find(function (c) { return String(c.id) === String(id); });
            if (!cls) return null;
            const body = Object.assign({}, bodyCore, { module_id: Number(cls.module_id) });
            body.classe = cls.id;
            return { body: body, label: cls.name || ('Classe #' + cls.id) };
          }).filter(Boolean);
        }
      }

      if (!payloads.length) { showToast('Aucune classe valide sélectionnée.', 'error'); return; }

      await this._executePayloads(payloads, isEditing);
    },

    async _executePayloads(payloads, isEditing) {
      const btn = document.getElementById('sfSubmit');
      const multi = payloads.length > 1 && !isEditing;
      btn.disabled = true;
      try {
        if (multi) {
          let ok = 0;
          const fails = [];
          const lotIds = [];
          for (let i = 0; i < payloads.length; i++) {
            btn.textContent = 'Création… (' + (i + 1) + '/' + payloads.length + ')';
            try {
              if (lotIds.length) payloads[i].body.exclude_session_ids = lotIds.slice();
              const data = await API.apiFetch('/sessions/', { method: 'POST', body: JSON.stringify(payloads[i].body) });
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

        const p = payloads[0];
        if (isEditing) {
          await API.apiFetch('/sessions/' + this._editingId + '/', { method: 'PATCH', body: JSON.stringify(p.body) });
          closeModal('modalSessionForm');
          showToast('Séance modifiée avec succès.', 'success');
          document.dispatchEvent(new CustomEvent('session-created', {}));
        } else {
          const data = await API.apiFetch('/sessions/', { method: 'POST', body: JSON.stringify(p.body) });
          closeModal('modalSessionForm');
          showToast('Séance créée avec succès.', 'success');
          document.dispatchEvent(new CustomEvent('session-created', { detail: data }));
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