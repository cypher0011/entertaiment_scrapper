/**
 * Qurrah CRM — localStorage-based call tracking
 * Data key: 'qurrah_crm'        → { [branchId]: CRMRecord }
 * Data key: 'qurrah_crm_pitches' → PitchRecord[]
 */

// ── Default pitches (user can add/edit/delete via UI) ──
const DEFAULT_PITCHES = [
  { id: "p1", name: "تحويل رسمة الطفل" },
  { id: "p2", name: "حركة الطفل" },
  { id: "p3", name: "جهاز الـ Mini-Booth" },
];

const STATUS_CONFIG = {
  not_called: { label: "لم يتم الاتصال", color: "#484F58",  emoji: "⬜" },
  no_answer:  { label: "لا يرد",          color: "#D29922",  emoji: "🟡" },
  interested: { label: "مهتم",            color: "#3FB950",  emoji: "🟢" },
  follow_up:  { label: "متابعة",          color: "#58A6FF",  emoji: "🔵" },
  rejected:   { label: "رفض",             color: "#DA3633",  emoji: "🔴" },
  closed:     { label: "تم الإغلاق",      color: "#A371F7",  emoji: "🟣" },
};

const CRM = {
  _key:        "qurrah_crm",
  _pitchesKey: "qurrah_crm_pitches",

  // ── CRM records ──
  _load() {
    try { return JSON.parse(localStorage.getItem(this._key) || "{}"); }
    catch { return {}; }
  },
  _save(data) { localStorage.setItem(this._key, JSON.stringify(data)); },

  get(branchId)        { return this._load()[branchId] || null; },
  getAll()             { return this._load(); },
  save(branchId, rec)  {
    const all = this._load();
    all[branchId] = { ...all[branchId], ...rec, updated_at: new Date().toISOString() };
    this._save(all);
  },
  delete(branchId)     { const all = this._load(); delete all[branchId]; this._save(all); },

  // ── Pitches ──
  getPitches() {
    try {
      const stored = JSON.parse(localStorage.getItem(this._pitchesKey));
      return Array.isArray(stored) && stored.length ? stored : [...DEFAULT_PITCHES];
    } catch { return [...DEFAULT_PITCHES]; }
  },
  savePitches(pitches) { localStorage.setItem(this._pitchesKey, JSON.stringify(pitches)); },
  addPitch(name) {
    const pitches = this.getPitches();
    const id = "p" + Date.now();
    pitches.push({ id, name });
    this.savePitches(pitches);
    return id;
  },
  deletePitch(id) {
    this.savePitches(this.getPitches().filter(p => p.id !== id));
  },
  renamePitch(id, name) {
    this.savePitches(this.getPitches().map(p => p.id === id ? { ...p, name } : p));
  },

  // ── Stats ──
  stats() {
    const all = this._load();
    const records = Object.values(all);
    const pitches = this.getPitches();
    const called     = records.filter(r => r.status && r.status !== "not_called").length;
    const interested = records.filter(r => r.status === "interested").length;
    const follow_up  = records.filter(r => r.status === "follow_up").length;
    const closed     = records.filter(r => r.status === "closed").length;
    const rejected   = records.filter(r => r.status === "rejected").length;
    const no_answer  = records.filter(r => r.status === "no_answer").length;

    // Best pitch: most "interested" or "closed" responses
    // Support both old pitch_id (string) and new pitch_ids (array)
    const pitchWins = {};
    records
      .filter(r => r.status === "interested" || r.status === "closed")
      .forEach(r => {
        const ids = r.pitch_ids || (r.pitch_id ? [r.pitch_id] : []);
        ids.forEach(id => { pitchWins[id] = (pitchWins[id] || 0) + 1; });
      });
    const bestPitchId = Object.entries(pitchWins).sort((a,b)=>b[1]-a[1])[0]?.[0];
    const bestPitch   = pitches.find(p => p.id === bestPitchId);

    return {
      total: records.length, called, interested, follow_up,
      closed, rejected, no_answer,
      bestPitch, pitchWins,
      conversionRate: called ? Math.round((interested + closed) * 100 / called) : 0,
    };
  },

  // ── Export CRM CSV ──
  exportCSV() {
    const all = this._load();
    const pitches = this.getPitches();
    const rows = [[
      "المعرف","الاسم","المدينة","المنطقة","الهاتف",
      "حالة المكالمة","تاريخ الاتصال","الفكرة المقدمة",
      "ملاحظات","موعد المتابعة","آخر تحديث"
    ]];
    Object.entries(all).forEach(([id, r]) => {
      const card  = (window.ALL || []).find(c => c.id === id) || {};
      // Support both old pitch_id and new pitch_ids
      const ids   = r.pitch_ids || (r.pitch_id ? [r.pitch_id] : []);
      const pitchNames = ids.map(pid => pitches.find(p => p.id === pid)?.name || pid).join(" + ");
      rows.push([
        id, card.name_ar||"", card.city_ar||"", card.region_ar||"", card.phone||"",
        STATUS_CONFIG[r.status]?.label || r.status || "",
        r.call_date||"", pitchNames,
        (r.notes||"").replace(/\n/g," "),
        r.follow_up_date||"", r.updated_at||"",
      ]);
    });
    const csv  = rows.map(r => r.map(c=>`"${String(c).replace(/"/g,'""')}"`).join(",")).join("\n");
    const blob = new Blob(["\ufeff"+csv], { type:"text/csv;charset=utf-8" });
    const a    = document.createElement("a");
    a.href     = URL.createObjectURL(blob);
    a.download = `qurrah-crm-${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  },
};

// ── CRM Panel (rendered inside drawer) ──
function renderCRMPanel(branchId) {
  const rec      = CRM.get(branchId) || {};
  const pitches  = CRM.getPitches();
  // Support both old pitch_id (string) and new pitch_ids (array)
  const selected = rec.pitch_ids || (rec.pitch_id ? [rec.pitch_id] : []);

  const statusOpts = Object.entries(STATUS_CONFIG).map(([k,v]) =>
    `<option value="${k}" ${(rec.status||"not_called")===k?"selected":""}>${v.emoji} ${v.label}</option>`
  ).join("");

  // Multi-select pitch toggle buttons
  const pitchBtns = pitches.map(p => {
    const isOn = selected.includes(p.id);
    return `<button type="button"
      class="pitch-toggle-btn${isOn ? " active" : ""}"
      data-pitch-id="${p.id}"
      onclick="togglePitchBtn(this)">${p.name}</button>`;
  }).join("");

  const lastUpdate = rec.updated_at
    ? `<span class="crm-updated">آخر تحديث: ${new Date(rec.updated_at).toLocaleString("ar-SA",{dateStyle:"short",timeStyle:"short"})}</span>`
    : "";

  return `<div class="crm-panel" id="crm-panel-${branchId}">
  <div class="crm-row">
    <div class="crm-field">
      <label class="crm-label">الحالة</label>
      <select class="crm-select" id="crm-status-${branchId}">${statusOpts}</select>
    </div>
    <div class="crm-field">
      <label class="crm-label">تاريخ الاتصال</label>
      <input class="crm-input" type="date" id="crm-date-${branchId}"
        value="${rec.call_date || new Date().toISOString().slice(0,10)}">
    </div>
  </div>
  <div class="crm-field">
    <label class="crm-label" style="display:flex;align-items:center;justify-content:space-between">
      <span>الأفكار / العروض المقدمة <span style="font-size:.72rem;color:var(--text3);font-weight:400">(اختر واحدة أو أكثر)</span></span>
      <button class="crm-pitch-manage-btn" onclick="openPitchManager()" title="إدارة الأفكار">⚙ إدارة</button>
    </label>
    <div class="pitch-toggle-group" id="crm-pitches-${branchId}">
      ${pitchBtns}
    </div>
  </div>
  <div class="crm-field">
    <label class="crm-label">موعد المتابعة</label>
    <input class="crm-input" type="date" id="crm-followup-${branchId}"
      value="${rec.follow_up_date || ""}">
  </div>
  <div class="crm-field">
    <label class="crm-label">ماذا قالوا / ملاحظات</label>
    <textarea class="crm-textarea" id="crm-notes-${branchId}"
      placeholder="سجّل ردّهم بالضبط...">${rec.notes || ""}</textarea>
  </div>
  <div class="crm-actions">
    <button class="crm-save-btn" onclick="saveCRM('${branchId}')">💾 حفظ</button>
    <button class="crm-clear-btn" onclick="clearCRM('${branchId}')">🗑 مسح</button>
    ${lastUpdate}
  </div>
</div>`;
}

function togglePitchBtn(btn) {
  btn.classList.toggle("active");
}

function saveCRM(branchId) {
  const status         = document.getElementById(`crm-status-${branchId}`)?.value   || "not_called";
  const call_date      = document.getElementById(`crm-date-${branchId}`)?.value     || "";
  const follow_up_date = document.getElementById(`crm-followup-${branchId}`)?.value || "";
  const notes          = document.getElementById(`crm-notes-${branchId}`)?.value    || "";

  // Collect all active pitch toggle buttons
  const pitchGroup = document.getElementById(`crm-pitches-${branchId}`);
  const pitch_ids  = pitchGroup
    ? [...pitchGroup.querySelectorAll(".pitch-toggle-btn.active")].map(b => b.dataset.pitchId)
    : [];

  CRM.save(branchId, { status, call_date, pitch_ids, follow_up_date, notes });

  // Feedback
  const btn = document.querySelector(`#crm-panel-${branchId} .crm-save-btn`);
  if (btn) {
    btn.textContent = "✅ تم الحفظ";
    btn.style.background = "rgba(63,185,80,.25)";
    btn.style.borderColor = "rgba(63,185,80,.5)";
    btn.style.color = "#3FB950";
    setTimeout(() => {
      btn.textContent = "💾 حفظ";
      btn.style.cssText = "";
    }, 1800);
  }

  updateCardDot(branchId, status);
  updateCRMHeaderStats();
}

function clearCRM(branchId) {
  if (!confirm("حذف سجل هذا المركز من CRM؟")) return;
  CRM.delete(branchId);
  updateCardDot(branchId, null);
  const panel = document.getElementById(`crm-panel-${branchId}`);
  if (panel) panel.outerHTML = renderCRMPanel(branchId);
  updateCRMHeaderStats();
}

function updateCardDot(branchId, status) {
  const dot   = document.querySelector(`.card[data-id="${branchId}"] .crm-dot`);
  const label = document.querySelector(`.card[data-id="${branchId}"] .crm-badge-label`);
  const st    = status || "not_called";
  const cfg   = STATUS_CONFIG[st] || {};
  if (dot)   { dot.className = `crm-dot crm-${st}`; dot.title = cfg.label||""; }
  if (label) { label.textContent = cfg.label || "لم يتم الاتصال"; }
}

function updateCRMHeaderStats() {
  const s  = CRM.stats();
  const el = document.getElementById("crm-header-stats");
  if (!el) return;
  el.innerHTML = [
    `<span class="crm-stat-chip">📞 ${s.called} اتصال</span>`,
    s.interested  ? `<span class="crm-stat-chip crm-chip-green">🟢 ${s.interested} مهتم</span>`       : "",
    s.follow_up   ? `<span class="crm-stat-chip crm-chip-blue">🔵 ${s.follow_up} متابعة</span>`       : "",
    s.closed      ? `<span class="crm-stat-chip crm-chip-purple">🟣 ${s.closed} مُغلق</span>`          : "",
    s.conversionRate ? `<span class="crm-stat-chip crm-chip-gold">📈 ${s.conversionRate}% تحويل</span>` : "",
    s.bestPitch   ? `<span class="crm-stat-chip crm-chip-purple">🏆 الأفضل: ${s.bestPitch.name}</span>` : "",
  ].join("");
}

// ── Pitch Manager Modal ──
function openPitchManager() {
  // Remove existing if any
  document.getElementById("pitch-manager-overlay")?.remove();

  const pitches = CRM.getPitches();
  const rows = pitches.map(p => `
    <div class="pm-row" id="pm-row-${p.id}">
      <input class="pm-input" type="text" value="${p.name.replace(/"/g,'&quot;')}"
        onchange="CRM.renamePitch('${p.id}', this.value); renderPitchStats()">
      <button class="pm-del-btn" onclick="CRM.deletePitch('${p.id}'); document.getElementById('pm-row-${p.id}').remove(); renderPitchStats()">✕</button>
    </div>`).join("");

  const stats = CRM.stats();
  const pitchStatsRows = pitches.map(p => {
    const wins = stats.pitchWins[p.id] || 0;
    const total = Object.values(CRM.getAll()).filter(r => {
      const ids = r.pitch_ids || (r.pitch_id ? [r.pitch_id] : []);
      return ids.includes(p.id);
    }).length;
    return `<div class="pm-stat-row">
      <span>${p.name}</span>
      <span>${total} عرض · <strong style="color:#3FB950">${wins} مهتم</strong></span>
    </div>`;
  }).join("") || '<p style="color:var(--text3);font-size:.85rem">لا توجد بيانات بعد</p>';

  const overlay = document.createElement("div");
  overlay.id = "pitch-manager-overlay";
  overlay.style.cssText = "position:fixed;inset:0;z-index:400;background:rgba(0,0,0,.7);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;padding:1.5rem";
  overlay.innerHTML = `
    <div style="background:#0D1117;border:1px solid #30363D;border-radius:16px;width:100%;max-width:480px;overflow:hidden;animation:fadeInUp .2s ease">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:1rem 1.25rem;border-bottom:1px solid #30363D">
        <div style="font-size:1rem;font-weight:700;direction:rtl">إدارة الأفكار والعروض</div>
        <button onclick="document.getElementById('pitch-manager-overlay').remove()"
          style="background:none;border:1px solid #30363D;color:#8B949E;width:30px;height:30px;border-radius:8px;cursor:pointer;font-size:.9rem">✕</button>
      </div>
      <div style="padding:1.1rem 1.25rem;display:flex;flex-direction:column;gap:1rem;direction:rtl;max-height:70vh;overflow-y:auto">
        <div>
          <div style="font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#484F58;margin-bottom:.65rem">الأفكار الحالية</div>
          <div id="pm-list" style="display:flex;flex-direction:column;gap:.4rem">${rows}</div>
          <div style="display:flex;gap:.5rem;margin-top:.65rem">
            <input id="pm-new-input" class="pm-input" type="text" placeholder="اسم الفكرة الجديدة..."
              style="flex:1" onkeydown="if(event.key==='Enter')addNewPitch()">
            <button onclick="addNewPitch()"
              style="padding:.45rem .9rem;background:rgba(124,58,237,.2);border:1px solid rgba(124,58,237,.4);color:#C4B5FD;border-radius:8px;cursor:pointer;font-size:.82rem;font-family:inherit;font-weight:600">+ إضافة</button>
          </div>
        </div>
        <div style="border-top:1px solid #30363D;padding-top:.85rem">
          <div style="font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#484F58;margin-bottom:.65rem">أداء كل فكرة</div>
          <div id="pm-stats" style="display:flex;flex-direction:column;gap:.4rem">${pitchStatsRows}</div>
        </div>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", e => { if (e.target === overlay) overlay.remove(); });
}

function addNewPitch() {
  const input = document.getElementById("pm-new-input");
  const name  = input?.value.trim();
  if (!name) return;
  CRM.addPitch(name);
  // Refresh list
  const pitches = CRM.getPitches();
  const p = pitches[pitches.length - 1];
  const list = document.getElementById("pm-list");
  if (list) {
    const div = document.createElement("div");
    div.className = "pm-row";
    div.id = `pm-row-${p.id}`;
    div.innerHTML = `
      <input class="pm-input" type="text" value="${p.name}"
        onchange="CRM.renamePitch('${p.id}', this.value)">
      <button class="pm-del-btn" onclick="CRM.deletePitch('${p.id}'); document.getElementById('pm-row-${p.id}').remove()">✕</button>`;
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
      const ids = r.pitch_ids || (r.pitch_id ? [r.pitch_id] : []);
      return ids.includes(p.id);
    }).length;
    return `<div class="pm-stat-row">
      <span>${p.name}</span>
      <span>${total} عرض · <strong style="color:#3FB950">${wins} مهتم</strong></span>
    </div>`;
  }).join("") || '<p style="color:var(--text3);font-size:.85rem">لا توجد بيانات بعد</p>';
}

// Called on page load
document.addEventListener("DOMContentLoaded", updateCRMHeaderStats);
