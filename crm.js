/**
 * Qurrah CRM — localStorage-based call tracking
 * Data key: 'qurrah_crm' → { [branchId]: CRMRecord }
 */

const PITCHES = [
  { id: "p1", name: "تحويل رسمة الطفل" },
  { id: "p2", name: "حركة الطفل" },
  { id: "p3", name: "جهاز ال mini-booth" },
  { id: "p6", name: "أخرى" },
];

const STATUS_CONFIG = {
  not_called:  { label: "لم يتم الاتصال", color: "#50507a", emoji: "⬜" },
  no_answer:   { label: "لا يرد",          color: "#f59e0b", emoji: "🟡" },
  interested:  { label: "مهتم",            color: "#22c55e", emoji: "🟢" },
  follow_up:   { label: "متابعة",          color: "#60a5fa", emoji: "🔵" },
  rejected:    { label: "رفض",             color: "#ef4444", emoji: "🔴" },
  closed:      { label: "تم الإغلاق",      color: "#a78bfa", emoji: "🟣" },
};

const CRM = {
  _key: "qurrah_crm",

  _load() {
    try { return JSON.parse(localStorage.getItem(this._key) || "{}"); }
    catch { return {}; }
  },

  _save(data) {
    localStorage.setItem(this._key, JSON.stringify(data));
  },

  get(branchId) {
    return this._load()[branchId] || null;
  },

  getAll() {
    return this._load();
  },

  save(branchId, record) {
    const all = this._load();
    all[branchId] = { ...all[branchId], ...record, updated_at: new Date().toISOString() };
    this._save(all);
  },

  delete(branchId) {
    const all = this._load();
    delete all[branchId];
    this._save(all);
  },

  stats() {
    const all = this._load();
    const records = Object.values(all);
    const total = records.length;
    const called = records.filter(r => r.status && r.status !== "not_called").length;
    const interested = records.filter(r => r.status === "interested" || r.status === "closed").length;
    const follow_up = records.filter(r => r.status === "follow_up").length;

    // Best pitch by interested responses
    const pitchCounts = {};
    records.filter(r => r.pitch_id && (r.status === "interested" || r.status === "closed")).forEach(r => {
      pitchCounts[r.pitch_id] = (pitchCounts[r.pitch_id] || 0) + 1;
    });
    const bestPitchId = Object.entries(pitchCounts).sort((a,b)=>b[1]-a[1])[0]?.[0];
    const bestPitch = PITCHES.find(p => p.id === bestPitchId);

    return { total, called, interested, follow_up, bestPitch, pitchCounts };
  },

  exportCSV() {
    const all = this._load();
    const rows = [["المعرف","الاسم","المدينة","حالة المكالمة","تاريخ الاتصال","الفكرة المقدمة","ملاحظات","موعد المتابعة","آخر تحديث"]];
    Object.entries(all).forEach(([id, r]) => {
      const card = (window.ALL||[]).find(c => c.id === id) || {};
      const pitch = PITCHES.find(p => p.id === r.pitch_id);
      rows.push([
        id,
        card.name_ar || "",
        card.city_ar || "",
        STATUS_CONFIG[r.status]?.label || r.status || "",
        r.call_date || "",
        pitch?.name || "",
        (r.notes || "").replace(/\n/g, " "),
        r.follow_up_date || "",
        r.updated_at || "",
      ]);
    });
    const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g,'""')}"`).join(",")).join("\n");
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "qurrah-crm.csv";
    a.click();
  },
};

// ── Render CRM panel inside modal ──
function renderCRMPanel(branchId) {
  const rec = CRM.get(branchId) || {};
  const pitchOpts = PITCHES.map(p =>
    `<option value="${p.id}" ${rec.pitch_id === p.id ? "selected" : ""}>${p.name}</option>`
  ).join("");
  const statusOpts = Object.entries(STATUS_CONFIG).map(([k, v]) =>
    `<option value="${k}" ${(rec.status || "not_called") === k ? "selected" : ""}>${v.emoji} ${v.label}</option>`
  ).join("");

  return `<div class="crm-panel" id="crm-panel-${branchId}">
  <div class="crm-row">
    <div class="crm-field">
      <label class="crm-label">حالة المكالمة</label>
      <select class="crm-select" id="crm-status-${branchId}">${statusOpts}</select>
    </div>
    <div class="crm-field">
      <label class="crm-label">تاريخ الاتصال</label>
      <input class="crm-input" type="date" id="crm-date-${branchId}" value="${rec.call_date || new Date().toISOString().slice(0,10)}">
    </div>
  </div>
  <div class="crm-row">
    <div class="crm-field">
      <label class="crm-label">الفكرة / العرض</label>
      <select class="crm-select" id="crm-pitch-${branchId}">
        <option value="">-- اختر --</option>${pitchOpts}
      </select>
    </div>
    <div class="crm-field">
      <label class="crm-label">موعد المتابعة</label>
      <input class="crm-input" type="date" id="crm-followup-${branchId}" value="${rec.follow_up_date || ""}">
    </div>
  </div>
  <div class="crm-field" style="margin-top:.5rem">
    <label class="crm-label">ماذا قالوا / ملاحظات</label>
    <textarea class="crm-textarea" id="crm-notes-${branchId}" placeholder="سجل ما قالوه بالضبط...">${rec.notes || ""}</textarea>
  </div>
  <div class="crm-actions">
    <button class="crm-save-btn" onclick="saveCRM('${branchId}')">💾 حفظ</button>
    <button class="crm-clear-btn" onclick="clearCRM('${branchId}')">🗑 مسح</button>
    ${rec.updated_at ? `<span class="crm-updated">آخر تحديث: ${new Date(rec.updated_at).toLocaleString('ar-SA')}</span>` : ""}
  </div>
</div>`;
}

function saveCRM(branchId) {
  const status      = document.getElementById(`crm-status-${branchId}`)?.value || "not_called";
  const call_date   = document.getElementById(`crm-date-${branchId}`)?.value || "";
  const pitch_id    = document.getElementById(`crm-pitch-${branchId}`)?.value || "";
  const follow_up_date = document.getElementById(`crm-followup-${branchId}`)?.value || "";
  const notes       = document.getElementById(`crm-notes-${branchId}`)?.value || "";

  CRM.save(branchId, { status, call_date, pitch_id, follow_up_date, notes });

  // Animate save btn
  const btn = document.querySelector(`#crm-panel-${branchId} .crm-save-btn`);
  if (btn) { btn.textContent = "✅ تم الحفظ"; setTimeout(() => { btn.textContent = "💾 حفظ"; }, 1500); }

  // Update card dot in grid
  updateCardDot(branchId, status);
  updateCRMHeaderStats();
}

function clearCRM(branchId) {
  if (!confirm("حذف سجل هذا المركز؟")) return;
  CRM.delete(branchId);
  updateCardDot(branchId, null);
  // Re-render panel
  const panel = document.getElementById(`crm-panel-${branchId}`);
  if (panel) panel.outerHTML = renderCRMPanel(branchId);
  updateCRMHeaderStats();
}

function updateCardDot(branchId, status) {
  const dot = document.querySelector(`.card[data-id="${branchId}"] .crm-dot`);
  if (!dot) return;
  if (!status || status === "not_called") {
    dot.className = "crm-dot crm-not_called";
    dot.title = "لم يتم الاتصال";
  } else {
    const cfg = STATUS_CONFIG[status] || {};
    dot.className = `crm-dot crm-${status}`;
    dot.title = cfg.label || status;
  }
}

function updateCRMHeaderStats() {
  const s = CRM.stats();
  const el = document.getElementById("crm-header-stats");
  if (!el) return;
  el.innerHTML = `
    <span class="crm-stat-chip">📞 ${s.called} تم الاتصال</span>
    <span class="crm-stat-chip crm-chip-green">🟢 ${s.interested} مهتم</span>
    <span class="crm-stat-chip crm-chip-blue">🔵 ${s.follow_up} متابعة</span>
    ${s.bestPitch ? `<span class="crm-stat-chip crm-chip-purple">🏆 الأفضل: ${s.bestPitch.name}</span>` : ""}
  `;
}

// Call on page load
document.addEventListener("DOMContentLoaded", updateCRMHeaderStats);
