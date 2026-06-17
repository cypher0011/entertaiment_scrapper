/**
 * Dream CRM — Professional B2B Sales Pipeline
 * Based on: MEDDICC + SPIN + Challenger Sale + Fanatical Prospecting
 *
 * Storage keys:
 *   qurrah_crm         → { [branchId]: DealRecord }
 *   qurrah_crm_pitches → PitchRecord[]
 */

// ─────────────────────────────────────────────
// PIPELINE STAGES (outcome-based, not activity)
// ─────────────────────────────────────────────
const PIPELINE_STAGES = [
  { id: "target",      label: "🎯 محددة",             label_en: "Target",          color: "#484F58", prob: 5  },
  { id: "contacted",   label: "📞 تم التواصل",          label_en: "Contacted",       color: "#D29922", prob: 10 },
  { id: "no_answer",   label: "🔇 ما رد",              label_en: "No Answer",       color: "#6E40C9", prob: 10 },
  { id: "qualified",   label: "✅ مؤهلة (BANT)",        label_en: "Qualified",       color: "#58A6FF", prob: 20 },
  { id: "discovery",   label: "🔍 اكتشاف مكتمل",        label_en: "Discovery Done",  color: "#A371F7", prob: 35 },
  { id: "proposal",    label: "📋 عرض مقدم",            label_en: "Proposal Sent",   color: "#F78166", prob: 50 },
  { id: "owner_in",    label: "👤 المالك موافق مبدئياً", label_en: "Owner Buy-in",    color: "#3FB950", prob: 65 },
  { id: "contract",    label: "📄 عقد/فاتورة مرسلة",    label_en: "Contract Out",    color: "#3FB950", prob: 80 },
  { id: "won",       label: "🏆 مغلق — دفعوا",        label_en: "Closed Won",      color: "#3FB950", prob: 100 },
  { id: "lost",      label: "❌ خسرنا",               label_en: "Closed Lost",     color: "#DA3633", prob: 0  },
];

const STAGE_MAP = Object.fromEntries(PIPELINE_STAGES.map(s => [s.id, s]));

// Legacy status → stage mapping (backward compat)
const LEGACY_STATUS_MAP = {
  not_called: "target", no_answer: "contacted", interested: "qualified",
  follow_up: "discovery", rejected: "lost", closed: "won",
};

// ─────────────────────
// OBJECTION TYPES
// ─────────────────────
const OBJECTION_TYPES = [
  { id: "price",      label: "السعر غالي" },
  { id: "budget",     label: "ما عندنا ميزانية الحين" },
  { id: "timing",     label: "مو وقتها / بعدين" },
  { id: "need",       label: "ما نحتاجها" },
  { id: "authority",  label: "لازم أتكلم مع شخص ثاني" },
  { id: "trust",      label: "ما نعرف الشركة" },
  { id: "competitor", label: "عندنا عرض ثاني" },
  { id: "nodecision", label: "لا زلنا نفكر" },
];

// ─────────────────────
// LOST REASONS
// ─────────────────────
const LOST_REASONS = [
  { id: "price",       label: "السعر غالي" },
  { id: "no_budget",   label: "ما فيه ميزانية هالسنة" },
  { id: "not_priority",label: "مو أولوية الحين" },
  { id: "competitor",  label: "اختاروا منافس" },
  { id: "no_fit",      label: "المنتج ما يناسبهم" },
  { id: "no_dm",       label: "ما وصلنا لصاحب القرار" },
  { id: "timing",      label: "توقيت سيء (رمضان/صيف/إجازة)" },
  { id: "ghosted",     label: "انقطع التواصل" },
  { id: "internal",    label: "مشكلة داخلية في الروضة" },
];

// ─────────────────────
// CONTACT CHANNELS
// ─────────────────────
const CHANNELS = [
  { id: "whatsapp", label: "واتساب" },
  { id: "call",     label: "اتصال هاتفي" },
  { id: "visit",    label: "زيارة شخصية" },
  { id: "email",    label: "إيميل" },
  { id: "other",    label: "أخرى" },
];

// ─────────────────────
// DEFAULT PITCHES
// ─────────────────────
const DEFAULT_PITCHES = [
  { id: "p1", name: "تحويل رسمة الطفل" },
  { id: "p2", name: "حركة الطفل" },
  { id: "p3", name: "جهاز الـ Mini-Booth" },
];

// ─────────────────────────────────────────────
// CRM ENGINE
// ─────────────────────────────────────────────
const CRM = {
  _key:        "qurrah_crm",
  _pitchesKey: "qurrah_crm_pitches",

  _load() {
    try { return JSON.parse(localStorage.getItem(this._key) || "{}"); }
    catch { return {}; }
  },
  _save(data) {
    localStorage.setItem(this._key, JSON.stringify(data));
    // Auto-backup to file via server (silent, non-blocking)
    fetch("/save-crm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).catch(() => {}); // silent if server not running
  },

  get(branchId) {
    const rec = this._load()[branchId];
    if (!rec) return null;
    // Migrate legacy status → stage
    if (rec.status && !rec.stage) {
      rec.stage = LEGACY_STATUS_MAP[rec.status] || "target";
    }
    return rec;
  },

  getAll() {
    const all = this._load();
    // Migrate all legacy records
    Object.keys(all).forEach(id => {
      if (all[id].status && !all[id].stage) {
        all[id].stage = LEGACY_STATUS_MAP[all[id].status] || "target";
      }
    });
    return all;
  },

  save(branchId, patch) {
    const all = this._load();
    const prev = all[branchId] || {};
    const now  = new Date().toISOString();

    // Auto-log stage change in activity history
    const history = prev.history || [];
    if (patch.stage && patch.stage !== prev.stage) {
      history.push({
        type:  "stage",
        from:  prev.stage || "target",
        to:    patch.stage,
        note:  patch._stage_note || "",
        at:    now,
      });
    }
    if (patch._activity) {
      history.push({ ...patch._activity, at: now });
    }

    const { _stage_note, _activity, ...cleanPatch } = patch;
    all[branchId] = { ...prev, ...cleanPatch, history, updated_at: now };
    this._save(all);
  },

  logActivity(branchId, { type, channel, note, next_action, next_date }) {
    this.save(branchId, {
      last_contact_date: new Date().toISOString().slice(0, 10),
      next_action, next_date,
      _activity: { type, channel, note },
    });
  },

  addObjection(branchId, { obj_type, quote, how_handled }) {
    const rec = this.get(branchId) || {};
    const objections = rec.objections || [];
    objections.push({ obj_type, quote, how_handled, at: new Date().toISOString() });
    this.save(branchId, { objections });
  },

  delete(branchId) {
    const all = this._load();
    delete all[branchId];
    this._save(all);
  },

  // ── Pitches ──
  getPitches() {
    try {
      const stored = JSON.parse(localStorage.getItem(this._pitchesKey));
      return Array.isArray(stored) && stored.length ? stored : [...DEFAULT_PITCHES];
    } catch { return [...DEFAULT_PITCHES]; }
  },
  savePitches(p) {
    localStorage.setItem(this._pitchesKey, JSON.stringify(p));
    fetch("/save-pitches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    }).catch(() => {});
  },
  addPitch(name) {
    const p = this.getPitches();
    const id = "p" + Date.now();
    p.push({ id, name });
    this.savePitches(p);
    return id;
  },
  deletePitch(id)        { this.savePitches(this.getPitches().filter(p => p.id !== id)); },
  renamePitch(id, name)  { this.savePitches(this.getPitches().map(p => p.id === id ? {...p, name} : p)); },

  // ── Stats ──
  stats() {
    const all     = this.getAll();
    const records = Object.values(all);
    const pitches = this.getPitches();

    const byStage = {};
    PIPELINE_STAGES.forEach(s => byStage[s.id] = 0);
    records.forEach(r => { const st = r.stage || "target"; byStage[st] = (byStage[st]||0) + 1; });

    const active  = records.filter(r => r.stage && !["target","lost"].includes(r.stage)).length;
    const won     = byStage["won"]  || 0;
    const lost    = byStage["lost"] || 0;
    const winRate = (won + lost) ? Math.round(won * 100 / (won + lost)) : 0;

    // Pipeline value (deals not yet won/lost)
    const pipelineDeals = records.filter(r => r.stage && !["won","lost","target"].includes(r.stage));
    const totalPipelineValue = pipelineDeals.reduce((s, r) => s + (parseFloat(r.deal_value) || 0), 0);

    // Best pitch
    const pitchWins = {};
    records.filter(r => r.stage === "won" || r.stage === "owner_in").forEach(r => {
      const ids = r.pitch_ids || (r.pitch_id ? [r.pitch_id] : []);
      ids.forEach(id => { pitchWins[id] = (pitchWins[id]||0) + 1; });
    });
    const bestPitchId = Object.entries(pitchWins).sort((a,b)=>b[1]-a[1])[0]?.[0];
    const bestPitch   = pitches.find(p => p.id === bestPitchId);

    // Overdue follow-ups
    const today    = new Date().toISOString().slice(0, 10);
    const overdue  = records.filter(r => r.next_date && r.next_date < today && !["won","lost"].includes(r.stage)).length;

    // Objection breakdown
    const objectionCounts = {};
    records.forEach(r => (r.objections||[]).forEach(o => {
      objectionCounts[o.obj_type] = (objectionCounts[o.obj_type]||0) + 1;
    }));

    return {
      total: records.length, active, won, lost, winRate,
      byStage, totalPipelineValue, overdue,
      bestPitch, pitchWins, objectionCounts,
      conversionRate: active ? Math.round(won * 100 / Math.max(active + won + lost, 1)) : 0,
    };
  },

  // ── Export CSV ──
  exportCSV() {
    const all     = this.getAll();
    const pitches = this.getPitches();
    const rows    = [[
      "الاسم","المدينة","الهاتف","المرحلة","قيمة الصفقة (ر.س)",
      "الأفكار المقدمة","صاحب القرار","المؤيد الداخلي","الألم الرئيسي",
      "الاعتراضات","تاريخ آخر تواصل","الخطوة التالية","موعدها",
      "ملاحظات","سبب الخسارة","آخر تحديث",
    ]];
    Object.entries(all).forEach(([id, r]) => {
      const card       = (window.ALL||[]).find(c=>c.id===id) || {};
      const stage      = STAGE_MAP[r.stage]?.label || r.stage || "";
      const ids        = r.pitch_ids || (r.pitch_id ? [r.pitch_id] : []);
      const pitchNames = ids.map(pid => pitches.find(p=>p.id===pid)?.name||pid).join(" + ");
      const objStr     = (r.objections||[]).map(o=>`${o.obj_type}: ${o.quote}`).join(" | ");
      const lostLabel  = LOST_REASONS.find(l=>l.id===r.lost_reason)?.label || r.lost_reason || "";
      rows.push([
        card.name_ar||"", card.city_ar||"", card.phone||"",
        stage, r.deal_value||"", pitchNames,
        r.economic_buyer||"", r.champion||"", r.identified_pain||"",
        objStr, r.last_contact_date||"", r.next_action||"", r.next_date||"",
        (r.notes||"").replace(/\n/g," "), lostLabel, r.updated_at||"",
      ]);
    });
    const csv  = rows.map(r=>r.map(c=>`"${String(c||"").replace(/"/g,'""')}"`).join(",")).join("\n");
    const blob = new Blob(["\ufeff"+csv], {type:"text/csv;charset=utf-8"});
    const a    = document.createElement("a");
    a.href     = URL.createObjectURL(blob);
    a.download = `dream-crm-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  },
};

// ─────────────────────────────────────────────
// RENDER CRM PANEL (inside drawer)
// ─────────────────────────────────────────────
function renderCRMPanel(branchId) {
  const rec     = CRM.get(branchId) || {};
  const pitches = CRM.getPitches();
  const stage   = rec.stage || "target";
  const selected = rec.pitch_ids || (rec.pitch_id ? [rec.pitch_id] : []);

  const stageOpts = PIPELINE_STAGES.map(s =>
    `<option value="${s.id}" ${stage===s.id?"selected":""}>${s.label} (${s.prob}%)</option>`
  ).join("");

  const pitchBtns = pitches.map(p => {
    const on = selected.includes(p.id);
    return `<button type="button" class="pitch-toggle-btn${on?" active":""}"
      data-pitch-id="${p.id}" onclick="togglePitchBtn(this)">${p.name}</button>`;
  }).join("");

  const objRows = (rec.objections||[]).map((o,i) => {
    const typeLabel = OBJECTION_TYPES.find(t=>t.id===o.obj_type)?.label || o.obj_type;
    return `<div class="obj-row">
      <span class="obj-type-badge">${typeLabel}</span>
      <span class="obj-quote">"${o.quote||""}"</span>
      ${o.how_handled ? `<span class="obj-handled">↳ ${o.how_handled}</span>` : ""}
      <button class="obj-del-btn" onclick="deleteObjection('${branchId}',${i})">✕</button>
    </div>`;
  }).join("") || `<p class="empty-hint">لا توجد اعتراضات مسجّلة بعد</p>`;

  const histRows = (rec.history||[]).slice(-8).reverse().map(h => {
    if (h.type === "stage") {
      const from = STAGE_MAP[h.from]?.label || h.from;
      const to   = STAGE_MAP[h.to]?.label   || h.to;
      return `<div class="hist-row hist-stage">
        <span class="hist-icon">→</span>
        <span>${from} <strong>→</strong> ${to}</span>
        ${h.note ? `<span class="hist-note">${h.note}</span>` : ""}
        <span class="hist-date">${h.at?.slice(0,10)||""}</span>
      </div>`;
    }
    const chLabel = CHANNELS.find(c=>c.id===h.channel)?.label || h.channel || "";
    return `<div class="hist-row">
      <span class="hist-icon">◈</span>
      <span>${chLabel}${h.note ? ` — ${h.note}` : ""}</span>
      <span class="hist-date">${h.at?.slice(0,10)||""}</span>
    </div>`;
  }).join("") || `<p class="empty-hint">لا يوجد نشاط مسجّل بعد</p>`;

  const lostSection = stage === "lost" ? `
    <div class="crm-field">
      <label class="crm-label">سبب الخسارة</label>
      <select class="crm-select" id="crm-lost-reason-${branchId}">
        <option value="">-- اختر السبب --</option>
        ${LOST_REASONS.map(l=>`<option value="${l.id}" ${rec.lost_reason===l.id?"selected":""}>${l.label}</option>`).join("")}
      </select>
    </div>` : "";

  const lastUpdate = rec.updated_at
    ? `<span class="crm-updated">آخر تحديث: ${new Date(rec.updated_at).toLocaleString("ar-SA",{dateStyle:"short",timeStyle:"short"})}</span>`
    : "";

  return `<div class="crm-panel" id="crm-panel-${branchId}">

  <!-- ① PIPELINE STAGE -->
  <div class="crm-section">
    <div class="crm-section-title">مرحلة الصفقة</div>
    <div class="stage-selector" id="stage-selector-${branchId}">
      ${PIPELINE_STAGES.map(s => `
        <button type="button"
          class="stage-btn${s.id===stage?" active":""} stage-${s.id}"
          data-stage="${s.id}"
          onclick="selectStage('${branchId}','${s.id}',this)"
          title="${s.prob}% احتمال إغلاق">${s.label}</button>`).join("")}
    </div>
    <div class="stage-note-wrap" id="stage-note-${branchId}" style="${stage==="lost"?"":""}">
      <input class="crm-input" type="text" id="crm-stage-note-${branchId}"
        placeholder="ملاحظة تحول المرحلة (اختياري)...">
    </div>
    ${lostSection}
  </div>

  <!-- ② DEAL INFO -->
  <div class="crm-section">
    <div class="crm-section-title">بيانات الصفقة</div>
    <div class="crm-row">
      <div class="crm-field">
        <label class="crm-label">قيمة الصفقة (ر.س)</label>
        <input class="crm-input" type="number" id="crm-value-${branchId}"
          placeholder="0" value="${rec.deal_value||""}">
      </div>
      <div class="crm-field">
        <label class="crm-label">تاريخ الاتصال الأول</label>
        <input class="crm-input" type="date" id="crm-date-${branchId}"
          value="${rec.call_date||new Date().toISOString().slice(0,10)}">
      </div>
    </div>
    <div class="crm-row">
      <div class="crm-field">
        <label class="crm-label">صاحب القرار الفعلي (المالك)</label>
        <input class="crm-input" type="text" id="crm-buyer-${branchId}"
          placeholder="الاسم والمسمى..." value="${rec.economic_buyer||""}">
      </div>
      <div class="crm-field">
        <label class="crm-label">المؤيد الداخلي (Champion)</label>
        <input class="crm-input" type="text" id="crm-champion-${branchId}"
          placeholder="مين يريدنا نفوز؟" value="${rec.champion||""}">
      </div>
    </div>
    <div class="crm-field">
      <label class="crm-label">الألم المحدد (بكلامهم هم)</label>
      <textarea class="crm-textarea crm-textarea-sm" id="crm-pain-${branchId}"
        placeholder="اكتب اقتباساً حرفياً من كلام المالك...">${rec.identified_pain||""}</textarea>
    </div>
    <div class="crm-field">
      <label class="crm-label">معيار اتخاذ القرار</label>
      <input class="crm-input" type="text" id="crm-criteria-${branchId}"
        placeholder="ايش يحتاج يكون صح عشان يقولون نعم؟" value="${rec.decision_criteria||""}">
    </div>
    <div class="crm-field">
      <label class="crm-label">المنافس / البديل</label>
      <input class="crm-input" type="text" id="crm-competitor-${branchId}"
        placeholder="شو يفكرون فيه كبديل؟" value="${rec.competitor||""}">
    </div>
  </div>

  <!-- ③ PITCHES -->
  <div class="crm-section">
    <div class="crm-section-title" style="display:flex;justify-content:space-between;align-items:center">
      <span>الأفكار / العروض المقدمة</span>
      <button class="crm-pitch-manage-btn" onclick="openPitchManager()">⚙ إدارة</button>
    </div>
    <div class="pitch-toggle-group" id="crm-pitches-${branchId}">${pitchBtns}</div>
  </div>

  <!-- ④ NEXT ACTION -->
  <div class="crm-section">
    <div class="crm-section-title">الخطوة التالية</div>
    <div class="crm-row">
      <div class="crm-field">
        <label class="crm-label">الإجراء المحدد</label>
        <input class="crm-input" type="text" id="crm-next-action-${branchId}"
          placeholder="مثال: اتصل بأم خالد الثلاثاء وناقش العقد"
          value="${rec.next_action||""}">
      </div>
      <div class="crm-field">
        <label class="crm-label">الموعد</label>
        <input class="crm-input" type="date" id="crm-next-date-${branchId}"
          value="${rec.next_date||""}">
      </div>
    </div>
  </div>

  <!-- ⑤ NOTES -->
  <div class="crm-section">
    <div class="crm-section-title">ملاحظات المكالمة</div>
    <textarea class="crm-textarea" id="crm-notes-${branchId}"
      placeholder="ماذا قالوا بالضبط؟ ما الذي أثار اهتمامهم؟ ما الذي قلقهم؟">${rec.notes||""}</textarea>
  </div>

  <!-- SAVE -->
  <div class="crm-actions">
    <button class="crm-save-btn" onclick="saveCRM('${branchId}')">💾 حفظ السجل</button>
    <button class="crm-log-btn" onclick="openActivityLog('${branchId}')">📝 سجّل نشاط</button>
    <button class="crm-obj-btn" onclick="openObjectionForm('${branchId}')">⚠ سجّل اعتراض</button>
    <button class="crm-clear-btn" onclick="clearCRM('${branchId}')">🗑</button>
    ${lastUpdate}
  </div>

  <!-- ⑥ OBJECTIONS LOG -->
  <div class="crm-section" id="obj-section-${branchId}">
    <div class="crm-section-title">سجل الاعتراضات</div>
    <div id="obj-list-${branchId}">${objRows}</div>
  </div>

  <!-- ⑦ ACTIVITY HISTORY -->
  <div class="crm-section">
    <div class="crm-section-title">سجل النشاط</div>
    <div class="history-list" id="history-list-${branchId}">${histRows}</div>
  </div>

</div>`;
}

// ─────────────────────────────────────────────
// STAGE SELECTOR
// ─────────────────────────────────────────────
function selectStage(branchId, stageId, btn) {
  const selector = document.getElementById(`stage-selector-${branchId}`);
  selector?.querySelectorAll(".stage-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");

  // Show/hide lost reason
  const lostSel = document.querySelector(`#crm-panel-${branchId} [id^="crm-lost-reason"]`);
  if (stageId === "lost") {
    if (!lostSel) {
      // Inject lost reason if not present
      const noteWrap = document.getElementById(`stage-note-${branchId}`);
      if (noteWrap) {
        const div = document.createElement("div");
        div.className = "crm-field";
        div.style.marginTop = ".5rem";
        div.innerHTML = `<label class="crm-label">سبب الخسارة</label>
          <select class="crm-select" id="crm-lost-reason-${branchId}">
            <option value="">-- اختر السبب --</option>
            ${LOST_REASONS.map(l=>`<option value="${l.id}">${l.label}</option>`).join("")}
          </select>`;
        noteWrap.after(div);
      }
    }
  }
}

// ─────────────────────────────────────────────
// SAVE
// ─────────────────────────────────────────────
function saveCRM(branchId) {
  const g = id => document.getElementById(`${id}-${branchId}`)?.value || "";

  const stageBtn = document.querySelector(`#stage-selector-${branchId} .stage-btn.active`);
  const stage    = stageBtn?.dataset.stage || CRM.get(branchId)?.stage || "target";

  const pitch_ids = [...(document.getElementById(`crm-pitches-${branchId}`)?.
    querySelectorAll(".pitch-toggle-btn.active") || [])].map(b => b.dataset.pitchId);

  CRM.save(branchId, {
    stage,
    call_date:          g("crm-date"),
    deal_value:         g("crm-value"),
    economic_buyer:     g("crm-buyer"),
    champion:           g("crm-champion"),
    identified_pain:    g("crm-pain"),
    decision_criteria:  g("crm-criteria"),
    competitor:         g("crm-competitor"),
    next_action:        g("crm-next-action"),
    next_date:          g("crm-next-date"),
    notes:              g("crm-notes"),
    lost_reason:        g("crm-lost-reason"),
    pitch_ids,
    _stage_note:        g("crm-stage-note"),
  });

  // Visual feedback
  const btn = document.querySelector(`#crm-panel-${branchId} .crm-save-btn`);
  if (btn) {
    const orig = btn.textContent;
    btn.textContent = "✅ تم الحفظ";
    btn.style.cssText = "background:rgba(63,185,80,.2);border-color:rgba(63,185,80,.5);color:#3FB950";
    setTimeout(() => { btn.textContent = orig; btn.style.cssText = ""; }, 1800);
  }

  updateCardStage(branchId, stage);
  updateCRMHeaderStats();
  // Refresh pipeline if open
  if (document.getElementById("pipeline-page")?.style.display !== "none") buildPipeline();
}

function togglePitchBtn(btn) { btn.classList.toggle("active"); }

function clearCRM(branchId) {
  if (!confirm("حذف سجل CRM لهذا المركز كاملاً؟")) return;
  CRM.delete(branchId);
  updateCardStage(branchId, "target");
  const panel = document.getElementById(`crm-panel-${branchId}`);
  if (panel) panel.outerHTML = renderCRMPanel(branchId);
  updateCRMHeaderStats();
}

// ─────────────────────────────────────────────
// ACTIVITY LOG MODAL
// ─────────────────────────────────────────────
function openActivityLog(branchId) {
  _removeOverlay("act-overlay");
  const channelOpts = CHANNELS.map(c =>
    `<option value="${c.id}">${c.label}</option>`).join("");

  const ov = _makeOverlay("act-overlay", `
    <div class="crm-modal">
      <div class="crm-modal-header">
        <span>📝 سجّل نشاط جديد</span>
        <button onclick="_removeOverlay('act-overlay')">✕</button>
      </div>
      <div class="crm-modal-body">
        <div class="crm-field">
          <label class="crm-label">نوع النشاط</label>
          <select class="crm-select" id="act-channel">${channelOpts}</select>
        </div>
        <div class="crm-field">
          <label class="crm-label">ماذا حدث / ماذا قالوا</label>
          <textarea class="crm-textarea" id="act-note" placeholder="سجّل بالضبط..."></textarea>
        </div>
        <div class="crm-row">
          <div class="crm-field">
            <label class="crm-label">الخطوة التالية</label>
            <input class="crm-input" type="text" id="act-next" placeholder="ايش بعدها؟">
          </div>
          <div class="crm-field">
            <label class="crm-label">موعدها</label>
            <input class="crm-input" type="date" id="act-date">
          </div>
        </div>
        <button class="crm-save-btn" style="width:100%;margin-top:.5rem"
          onclick="saveActivity('${branchId}')">💾 حفظ النشاط</button>
      </div>
    </div>`);
  document.body.appendChild(ov);
}

function saveActivity(branchId) {
  const channel     = document.getElementById("act-channel")?.value || "";
  const note        = document.getElementById("act-note")?.value    || "";
  const next_action = document.getElementById("act-next")?.value    || "";
  const next_date   = document.getElementById("act-date")?.value    || "";
  CRM.logActivity(branchId, { type: "activity", channel, note, next_action, next_date });
  _removeOverlay("act-overlay");
  // Refresh history in panel
  const histEl = document.getElementById(`history-list-${branchId}`);
  if (histEl) {
    const rec = CRM.get(branchId) || {};
    histEl.innerHTML = (rec.history||[]).slice(-8).reverse().map(h => {
      if (h.type === "stage") {
        return `<div class="hist-row hist-stage"><span class="hist-icon">→</span>
          <span>${STAGE_MAP[h.from]?.label||h.from} → ${STAGE_MAP[h.to]?.label||h.to}</span>
          <span class="hist-date">${h.at?.slice(0,10)||""}</span></div>`;
      }
      const chLabel = CHANNELS.find(c=>c.id===h.channel)?.label || h.channel || "";
      return `<div class="hist-row"><span class="hist-icon">◈</span>
        <span>${chLabel}${h.note?` — ${h.note}`:""}</span>
        <span class="hist-date">${h.at?.slice(0,10)||""}</span></div>`;
    }).join("") || `<p class="empty-hint">لا يوجد نشاط</p>`;
  }
  updateCRMHeaderStats();
}

// ─────────────────────────────────────────────
// OBJECTION FORM
// ─────────────────────────────────────────────
function openObjectionForm(branchId) {
  _removeOverlay("obj-overlay");
  const typeOpts = OBJECTION_TYPES.map(t =>
    `<option value="${t.id}">${t.label}</option>`).join("");

  const ov = _makeOverlay("obj-overlay", `
    <div class="crm-modal">
      <div class="crm-modal-header">
        <span>⚠ سجّل اعتراض</span>
        <button onclick="_removeOverlay('obj-overlay')">✕</button>
      </div>
      <div class="crm-modal-body">
        <div class="crm-field">
          <label class="crm-label">نوع الاعتراض</label>
          <select class="crm-select" id="obj-type">${typeOpts}</select>
        </div>
        <div class="crm-field">
          <label class="crm-label">ماذا قالوا بالضبط (اقتباس حرفي)</label>
          <textarea class="crm-textarea" id="obj-quote"
            placeholder='"ما عندنا ميزانية هالسنة"'></textarea>
        </div>
        <div class="crm-field">
          <label class="crm-label">كيف تعاملت معه</label>
          <textarea class="crm-textarea crm-textarea-sm" id="obj-handled"
            placeholder="قلت لهم..."></textarea>
        </div>
        <button class="crm-save-btn" style="width:100%;margin-top:.5rem"
          onclick="saveObjection('${branchId}')">💾 حفظ الاعتراض</button>
      </div>
    </div>`);
  document.body.appendChild(ov);
}

function saveObjection(branchId) {
  const obj_type    = document.getElementById("obj-type")?.value    || "";
  const quote       = document.getElementById("obj-quote")?.value   || "";
  const how_handled = document.getElementById("obj-handled")?.value || "";
  CRM.addObjection(branchId, { obj_type, quote, how_handled });
  _removeOverlay("obj-overlay");
  // Refresh objection list
  const listEl = document.getElementById(`obj-list-${branchId}`);
  if (listEl) {
    const rec = CRM.get(branchId) || {};
    listEl.innerHTML = (rec.objections||[]).map((o,i) => {
      const typeLabel = OBJECTION_TYPES.find(t=>t.id===o.obj_type)?.label || o.obj_type;
      return `<div class="obj-row">
        <span class="obj-type-badge">${typeLabel}</span>
        <span class="obj-quote">"${o.quote||""}"</span>
        ${o.how_handled?`<span class="obj-handled">↳ ${o.how_handled}</span>`:""}
        <button class="obj-del-btn" onclick="deleteObjection('${branchId}',${i})">✕</button>
      </div>`;
    }).join("") || `<p class="empty-hint">لا توجد اعتراضات</p>`;
  }
}

function deleteObjection(branchId, idx) {
  const rec = CRM.get(branchId) || {};
  const objs = rec.objections || [];
  objs.splice(idx, 1);
  CRM.save(branchId, { objections: objs });
  const listEl = document.getElementById(`obj-list-${branchId}`);
  if (listEl) {
    listEl.innerHTML = objs.map((o,i) => {
      const typeLabel = OBJECTION_TYPES.find(t=>t.id===o.obj_type)?.label || o.obj_type;
      return `<div class="obj-row">
        <span class="obj-type-badge">${typeLabel}</span>
        <span class="obj-quote">"${o.quote||""}"</span>
        ${o.how_handled?`<span class="obj-handled">↳ ${o.how_handled}</span>`:""}
        <button class="obj-del-btn" onclick="deleteObjection('${branchId}',${i})">✕</button>
      </div>`;
    }).join("") || `<p class="empty-hint">لا توجد اعتراضات</p>`;
  }
}

// ─────────────────────────────────────────────
// PITCH MANAGER
// ─────────────────────────────────────────────
function openPitchManager() {
  _removeOverlay("pitch-manager-overlay");
  const pitches = CRM.getPitches();
  const stats   = CRM.stats();

  const rows = pitches.map(p => `
    <div class="pm-row" id="pm-row-${p.id}">
      <input class="pm-input" type="text" value="${p.name.replace(/"/g,"&quot;")}"
        onchange="CRM.renamePitch('${p.id}',this.value);renderPitchStats()">
      <button class="pm-del-btn"
        onclick="CRM.deletePitch('${p.id}');document.getElementById('pm-row-${p.id}').remove();renderPitchStats()">✕</button>
    </div>`).join("");

  const statsRows = pitches.map(p => {
    const wins  = stats.pitchWins[p.id] || 0;
    const total = Object.values(CRM.getAll()).filter(r => {
      const ids = r.pitch_ids||(r.pitch_id?[r.pitch_id]:[]);
      return ids.includes(p.id);
    }).length;
    return `<div class="pm-stat-row">
      <span>${p.name}</span>
      <span>${total} عرض · <strong style="color:#3FB950">${wins} ربح</strong></span>
    </div>`;
  }).join("") || `<p class="empty-hint">لا توجد بيانات</p>`;

  const ov = _makeOverlay("pitch-manager-overlay", `
    <div class="crm-modal" style="max-width:480px">
      <div class="crm-modal-header">
        <span>⚙ إدارة الأفكار والعروض</span>
        <button onclick="_removeOverlay('pitch-manager-overlay')">✕</button>
      </div>
      <div class="crm-modal-body">
        <div class="crm-section-title">الأفكار الحالية</div>
        <div id="pm-list" style="display:flex;flex-direction:column;gap:.4rem">${rows}</div>
        <div style="display:flex;gap:.5rem;margin-top:.65rem">
          <input id="pm-new-input" class="pm-input crm-input" type="text"
            placeholder="اسم الفكرة الجديدة..." style="flex:1"
            onkeydown="if(event.key==='Enter')addNewPitch()">
          <button onclick="addNewPitch()" class="crm-save-btn">+ إضافة</button>
        </div>
        <div style="border-top:1px solid var(--border);margin-top:1rem;padding-top:.85rem">
          <div class="crm-section-title">أداء كل فكرة</div>
          <div id="pm-stats" style="display:flex;flex-direction:column;gap:.4rem">${statsRows}</div>
        </div>
      </div>
    </div>`);
  document.body.appendChild(ov);
}

function addNewPitch() {
  const input = document.getElementById("pm-new-input");
  const name  = input?.value.trim();
  if (!name) return;
  CRM.addPitch(name);
  const p    = CRM.getPitches().at(-1);
  const list = document.getElementById("pm-list");
  if (list) {
    const div = document.createElement("div");
    div.className = "pm-row";
    div.id = `pm-row-${p.id}`;
    div.innerHTML = `
      <input class="pm-input" type="text" value="${p.name}"
        onchange="CRM.renamePitch('${p.id}',this.value)">
      <button class="pm-del-btn"
        onclick="CRM.deletePitch('${p.id}');document.getElementById('pm-row-${p.id}').remove()">✕</button>`;
    list.appendChild(div);
  }
  if (input) input.value = "";
}

function renderPitchStats() {
  const el = document.getElementById("pm-stats");
  if (!el) return;
  const pitches = CRM.getPitches();
  const stats   = CRM.stats();
  el.innerHTML = pitches.map(p => {
    const wins  = stats.pitchWins[p.id] || 0;
    const total = Object.values(CRM.getAll()).filter(r => {
      const ids = r.pitch_ids||(r.pitch_id?[r.pitch_id]:[]);
      return ids.includes(p.id);
    }).length;
    return `<div class="pm-stat-row">
      <span>${p.name}</span>
      <span>${total} عرض · <strong style="color:#3FB950">${wins} ربح</strong></span>
    </div>`;
  }).join("") || `<p class="empty-hint">لا توجد بيانات</p>`;
}

// ─────────────────────────────────────────────
// PIPELINE PAGE (Kanban)
// ─────────────────────────────────────────────
function buildPipeline() {
  const page = document.getElementById("pipeline-page");
  if (!page) return;
  const all   = CRM.getAll();
  const stats = CRM.stats();

  // Active stages only (exclude target + won + lost for kanban, show them separately)
  const activeStages = PIPELINE_STAGES.filter(s => s.id !== "target");

  const columns = activeStages.map(s => {
    const deals = Object.entries(all)
      .filter(([,r]) => (r.stage || "target") === s.id)
      .map(([id, r]) => {
        const card = (window.ALL||[]).find(c => c.id === id) || {};
        const overdue = r.next_date && r.next_date < new Date().toISOString().slice(0,10);
        return `<div class="pipeline-card${overdue?" pipeline-overdue":""}"
          onclick="openDrawer(${(window.ALL||[]).findIndex(c=>c.id===id)})">
          <div class="pipeline-card-name">${card.name_ar||id}</div>
          <div class="pipeline-card-city">${card.city_ar||""}</div>
          ${r.deal_value?`<div class="pipeline-card-value">${Number(r.deal_value).toLocaleString("ar-SA")} ر.س</div>`:""}
          ${r.next_action?`<div class="pipeline-card-next${overdue?" overdue-text":""}">⏭ ${r.next_action}</div>`:""}
          ${r.next_date?`<div class="pipeline-card-date${overdue?" overdue-text":""}">${r.next_date}</div>`:""}
        </div>`;
      }).join("") || `<div class="pipeline-empty-col">لا يوجد</div>`;

    const colValue = Object.entries(all)
      .filter(([,r]) => r.stage === s.id && r.deal_value)
      .reduce((sum,[,r]) => sum + parseFloat(r.deal_value||0), 0);

    return `<div class="pipeline-col">
      <div class="pipeline-col-header" style="border-top:3px solid ${s.color}">
        <span class="pipeline-col-title">${s.label}</span>
        <span class="pipeline-col-count">${stats.byStage[s.id]||0}</span>
        ${colValue?`<span class="pipeline-col-value">${colValue.toLocaleString("ar-SA")} ر.س</span>`:""}
      </div>
      <div class="pipeline-col-body">${deals}</div>
    </div>`;
  }).join("");

  // Summary bar
  const totalVal = Object.values(all)
    .filter(r => !["won","lost","target"].includes(r.stage||"target"))
    .reduce((s,r) => s + parseFloat(r.deal_value||0), 0);

  const overdueList = Object.entries(all)
    .filter(([,r]) => r.next_date && r.next_date < new Date().toISOString().slice(0,10) && !["won","lost"].includes(r.stage||""))
    .map(([id,r]) => {
      const card = (window.ALL||[]).find(c=>c.id===id) || {};
      return `<div class="overdue-item" onclick="openDrawer(${(window.ALL||[]).findIndex(c=>c.id===id)})">
        <span>${card.name_ar||id}</span>
        <span class="overdue-date">${r.next_date}</span>
        <span class="overdue-action">${r.next_action||""}</span>
      </div>`;
    }).join("");

  // Objection analysis
  const objData = stats.objectionCounts;
  const totalObj = Object.values(objData).reduce((s,v)=>s+v,0);
  const objChart = Object.entries(objData).sort((a,b)=>b[1]-a[1]).map(([id,count]) => {
    const label = OBJECTION_TYPES.find(t=>t.id===id)?.label || id;
    const pct   = totalObj ? Math.round(count*100/totalObj) : 0;
    return `<div class="obj-bar-row">
      <span class="obj-bar-label">${label}</span>
      <div class="obj-bar-track"><div class="obj-bar-fill" style="width:${pct}%"></div></div>
      <span class="obj-bar-count">${count}</span>
    </div>`;
  }).join("") || `<p class="empty-hint">لا توجد اعتراضات مسجّلة بعد</p>`;

  page.innerHTML = `
    <div class="pipeline-header">
      <h2 class="pipeline-title">Pipeline — لوحة الصفقات</h2>
      <div class="pipeline-summary">
        <div class="pip-stat"><span class="pip-num">${stats.active}</span><span class="pip-label">صفقة نشطة</span></div>
        <div class="pip-stat"><span class="pip-num green">${stats.won}</span><span class="pip-label">مغلق — دفعوا</span></div>
        <div class="pip-stat"><span class="pip-num red">${stats.lost}</span><span class="pip-label">خسرنا</span></div>
        <div class="pip-stat"><span class="pip-num accent">${stats.winRate}%</span><span class="pip-label">Win Rate</span></div>
        <div class="pip-stat"><span class="pip-num gold">${totalVal?totalVal.toLocaleString("ar-SA")+" ر.س":"—"}</span><span class="pip-label">قيمة الـ Pipeline</span></div>
        ${stats.overdue?`<div class="pip-stat"><span class="pip-num red">${stats.overdue}</span><span class="pip-label">متأخر</span></div>`:""}
      </div>
    </div>

    ${overdueList ? `<div class="overdue-section">
      <div class="overdue-title">🔴 متأخر — يحتاج اتصال اليوم</div>
      <div class="overdue-list">${overdueList}</div>
    </div>` : ""}

    <div class="pipeline-board">${columns}</div>

    <div class="pipeline-analytics">
      <div class="analytics-card">
        <div class="analytics-title">أكثر الاعتراضات</div>
        <div class="obj-bars">${objChart}</div>
      </div>
      ${stats.bestPitch ? `<div class="analytics-card">
        <div class="analytics-title">أفضل فكرة</div>
        <div class="best-pitch-display">
          <div class="best-pitch-name">${stats.bestPitch.name}</div>
          <div class="best-pitch-stat">${stats.pitchWins[stats.bestPitch.id]||0} صفقة مغلقة / مهتمة</div>
        </div>
      </div>` : ""}
    </div>`;
}

// ─────────────────────────────────────────────
// CARD DOT UPDATE
// ─────────────────────────────────────────────
function updateCardStage(branchId, stageId) {
  const stage = STAGE_MAP[stageId];
  const dot   = document.querySelector(`.card[data-id="${branchId}"] .crm-dot`);
  const label = document.querySelector(`.card[data-id="${branchId}"] .crm-badge-label`);
  if (dot)   { dot.className = `crm-dot crm-${stageId}`; dot.title = stage?.label||""; }
  if (label) { label.textContent = stage?.label || ""; }
}

// Legacy alias
function updateCardDot(branchId, status) {
  const stage = LEGACY_STATUS_MAP[status] || status || "target";
  updateCardStage(branchId, stage);
}

// ─────────────────────────────────────────────
// HEADER STATS
// ─────────────────────────────────────────────
function updateCRMHeaderStats() {
  const s  = CRM.stats();
  const el = document.getElementById("crm-header-stats");
  if (!el) return;
  el.innerHTML = [
    `<span class="crm-stat-chip">🎯 ${s.total} في CRM</span>`,
    s.active       ? `<span class="crm-stat-chip crm-chip-blue">⚡ ${s.active} نشطة</span>` : "",
    s.won          ? `<span class="crm-stat-chip crm-chip-green">✅ ${s.won} دفعوا</span>` : "",
    s.overdue      ? `<span class="crm-stat-chip crm-chip-red">🔴 ${s.overdue} متأخر</span>` : "",
    s.winRate      ? `<span class="crm-stat-chip crm-chip-gold">📈 ${s.winRate}% Win Rate</span>` : "",
    s.bestPitch    ? `<span class="crm-stat-chip crm-chip-purple">🏆 ${s.bestPitch.name}</span>` : "",
  ].join("");
}

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────
function _makeOverlay(id, html) {
  const ov = document.createElement("div");
  ov.id = id;
  ov.className = "crm-overlay";
  ov.innerHTML = html;
  ov.addEventListener("click", e => { if (e.target === ov) _removeOverlay(id); });
  return ov;
}
function _removeOverlay(id) {
  document.getElementById(id)?.remove();
}

// ── Auto-restore from file backup if localStorage is empty ──
async function restoreFromBackup() {
  try {
    const existing = localStorage.getItem("qurrah_crm");
    if (!existing || existing === "{}") {
      const r = await fetch("/load-crm", { method: "POST", body: "" });
      if (r.ok) {
        const text = await r.text();
        if (text && text !== "{}") {
          localStorage.setItem("qurrah_crm", text);
          console.log("✅ CRM restored from backup");
        }
      }
    }
    const existingP = localStorage.getItem("qurrah_crm_pitches");
    if (!existingP) {
      const r2 = await fetch("/load-pitches", { method: "POST", body: "" });
      if (r2.ok) {
        const text2 = await r2.text();
        if (text2) localStorage.setItem("qurrah_crm_pitches", text2);
      }
    }
  } catch (e) {} // silent — server not running
  updateCRMHeaderStats();
}

document.addEventListener("DOMContentLoaded", restoreFromBackup);
