#!/usr/bin/env python3
"""
build_html.py — Generate modern SaaS-style Arabic RTL HTML directory for Qurrah (قرة).
Outputs: index.html + data/modal.json
Usage:
    python3 build_html.py           # full build
    python3 build_html.py rebuild   # rebuild HTML from existing branches.json
"""
import json
import os
import sys
from datetime import datetime
from collections import Counter

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "data", "branches.json")
MODAL_FILE = os.path.join(BASE_DIR, "data", "modal.json")
HTML_FILE = os.path.join(BASE_DIR, "index.html")

# ── Lookup maps ──
ACCRED_AR = {
    "ACCREDITED": "معتمد",
    "PENDING_APPROVAL": "قيد المراجعة",
    "REJECTED": "مرفوض",
}
ACCRED_CLS = {
    "ACCREDITED": "badge-green",
    "PENDING_APPROVAL": "badge-yellow",
    "REJECTED": "badge-red",
}
LICENSE_ISSUER_AR = {
    "MOE": "وزارة التعليم",
    "MOH": "وزارة الصحة",
    "MOS": "وزارة الشؤون الاجتماعية",
}


# ── Python helpers ──

def get_min_price(branch):
    """Return lowest monthly price across all services, or None."""
    prices = []
    for svc in (branch.get("services") or []):
        for t in (svc.get("booking_terms") or []):
            try:
                p = float(t.get("total_price") or 0)
                if p > 0:
                    prices.append(p)
            except Exception:
                pass
    return min(prices) if prices else None


def service_cards_html(services):
    """Build HTML string for service cards grid."""
    if not services:
        return ""
    items = []
    for svc in services:
        st = svc.get("service_type") or {}
        name_ar = st.get("name_ar", "")
        age_from = st.get("age_from", "")
        age_to = st.get("age_to", "")
        age_str = f"{age_from} – {age_to} سنوات" if age_from != "" else ""
        wh = svc.get("working_hours") or {}
        from_t = (wh.get("from_time") or "")[:5]
        to_t = (wh.get("to_time") or "")[:5]
        hours = f"{from_t} – {to_t}" if from_t else ""
        terms = svc.get("booking_terms") or []
        price_tags = []
        for t in terms:
            bt = t.get("booking_type") or {}
            try:
                price = float(t.get("total_price") or 0)
            except Exception:
                price = 0
            if price > 0:
                price_tags.append(
                    f'<span class="price-tag">{price:,.0f} ر.س'
                    f'<span class="price-period"> / {bt.get("name_ar", "")}</span></span>'
                )
        items.append(f"""<div class="svc-card">
  <div class="svc-name">{name_ar}</div>
  {f'<div class="svc-meta">👶 {age_str}</div>' if age_str else ""}
  {f'<div class="svc-meta">⏰ {hours}</div>' if hours else ""}
  {f'<div class="svc-prices">{"".join(price_tags)}</div>' if price_tags else ""}
</div>""")
    return '<div class="svc-grid">' + "".join(items) + "</div>"


def gallery_html(gallery, display_img):
    """Build HTML string for modal gallery section."""
    imgs = []
    if display_img:
        imgs.append(display_img)
    for g in (gallery or []):
        url = g.get("file", "")
        if url and url not in imgs:
            imgs.append(url)
    if not imgs:
        return '<div class="no-img-big">لا توجد صور</div>'
    hero = imgs[0]
    thumbs = imgs[1:]
    thumb_html = ""
    if thumbs:
        tlist = "".join(
            f'<img src="{u}" loading="lazy" onclick="setHero(this)" '
            f'onerror="this.style.display=\'none\'">'
            for u in thumbs
        )
        thumb_html = f'<div class="thumb-strip">{tlist}</div>'
    count_badge = f'<div class="img-count-badge">{len(imgs)} صورة</div>' if len(imgs) > 1 else ""
    return f"""<div class="gallery">
  <div class="hero-wrap">
    <img class="hero-img" id="modal-hero" src="{hero}" onerror="this.style.display='none'">
    {count_badge}
  </div>
  {thumb_html}
</div>"""


def build_card_data(b):
    """Extract lean card dict + full modal dict from a branch record."""
    bid = b.get("id", "")
    name_ar = b.get("name_ar") or "—"
    name_en = b.get("name_en") or ""
    desc = (b.get("description") or "").strip()
    if desc == ".":
        desc = ""

    addr = b.get("address") or {}
    city_ar = addr.get("city_name_ar") or addr.get("city_name_en") or ""
    city_en = addr.get("city_name_en") or ""
    region_ar = addr.get("region_name_ar") or ""
    street_ar = addr.get("street_name_ar") or addr.get("street_name_en") or ""
    zip_code = addr.get("zip_code") or ""
    lat = addr.get("lat", "")
    lng = addr.get("lng", "")

    rating = float(b.get("avg_branch_rating") or 0)
    rcount = int(b.get("total_ratings_count") or 0)
    accred = b.get("accreditation_status", "")

    phone = b.get("contact_phone_number") or ""
    email = b.get("contact_email") or ""

    sub = b.get("branch_subtype") or {}
    sub_ar = sub.get("name_ar") or "" if isinstance(sub, dict) else ""
    btype = (sub.get("branch_type") or {}).get("name_ar") or "" if isinstance(sub, dict) else ""

    # License rows
    lic_rows = []
    for lic in (b.get("branch_license") or []):
        if not isinstance(lic, dict):
            continue
        lic_no = lic.get("license_number") or ""
        lic_exp = lic.get("license_expiry_date") or ""
        issuer = LICENSE_ISSUER_AR.get(lic.get("license_issuer") or "", lic.get("license_issuer") or "")
        if lic_no:
            lic_rows.append({"label": "رقم الرخصة", "val": lic_no, "sub": f"تنتهي {lic_exp}" if lic_exp else ""})
        if issuer:
            lic_rows.append({"label": "جهة الترخيص", "val": issuer})

    cr = b.get("cr") or {}
    cr_no = cr.get("number") or ""
    cr_exp = cr.get("expiry_date") or ""

    services = b.get("services") or []
    gallery = b.get("gallery") or []
    disp_img = b.get("branch_display_image") or ""

    min_price = get_min_price(b)
    img_count = len(gallery) + (1 if disp_img else 0)
    thumb_url = disp_img or (gallery[0].get("file", "") if gallery else "")
    created = (b.get("created_at") or "")[:4]

    maps_url = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else ""
    branch_url = f"https://qurrah.sa/branch/{bid}"

    card = {
        "id": bid,
        "name_ar": name_ar,
        "name_en": name_en,
        "city_ar": city_ar,
        "city_en": city_en,
        "region_ar": region_ar,
        "rating": rating,
        "rcount": rcount,
        "accred": accred,
        "accred_label": ACCRED_AR.get(accred, accred),
        "accred_cls": ACCRED_CLS.get(accred, "badge-gray"),
        "sub_ar": sub_ar,
        "phone": phone,
        "min_price": min_price,
        "img_count": img_count,
        "thumb_url": thumb_url,
        "svc_count": len(services),
        "created": created,
    }
    modal = {
        "id": bid,
        "name_ar": name_ar,
        "name_en": name_en,
        "desc": desc,
        "city_ar": city_ar,
        "region_ar": region_ar,
        "street_ar": street_ar,
        "zip_code": zip_code,
        "lat": str(lat),
        "lng": str(lng),
        "rating": rating,
        "rcount": rcount,
        "accred_label": ACCRED_AR.get(accred, accred),
        "accred_cls": ACCRED_CLS.get(accred, "badge-gray"),
        "sub_ar": sub_ar,
        "btype": btype,
        "phone": phone,
        "email": email,
        "lic_rows": lic_rows,
        "cr_no": cr_no,
        "cr_exp": cr_exp,
        "min_price": min_price,
        "branch_url": branch_url,
        "maps_url": maps_url,
        "created": created,
        "svc_html": service_cards_html(services),
        "gal_html": gallery_html(gallery, disp_img),
    }
    return card, modal


def build_html(branches):
    """Return complete HTML string and write data/modal.json."""
    total = len(branches)
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    accred_count = sum(1 for b in branches if b.get("accreditation_status") == "ACCREDITED")

    # Build card + modal data
    cards = []
    modal_map = {}
    for b in branches:
        card, modal = build_card_data(b)
        cards.append(card)
        modal_map[card["id"]] = modal

    # Write modal data to separate file
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    with open(MODAL_FILE, "w", encoding="utf-8") as f:
        json.dump(modal_map, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  modal.json written ({os.path.getsize(MODAL_FILE) // 1024}KB)")

    # Stats for charts
    regions = Counter(c["region_ar"] for c in cards if c["region_ar"])
    subtypes = Counter(c["sub_ar"] for c in cards if c["sub_ar"])
    top_cities = Counter(c["city_ar"] for c in cards if c["city_ar"]).most_common(15)
    years = Counter(c["created"] for c in cards if c["created"])

    # Unique cities per region for cascading filter
    region_cities = {}
    for c in cards:
        r = c["region_ar"]
        ci = c["city_ar"]
        if r and ci:
            region_cities.setdefault(r, set()).add(ci)

    region_city_js = json.dumps(
        {r: sorted(list(cs)) for r, cs in sorted(region_cities.items())},
        ensure_ascii=False,
    )

    # All card data as JS array
    cards_js = json.dumps(cards, ensure_ascii=False)

    # Chart data
    chart_regions_labels = json.dumps([k for k, _ in regions.most_common(13)], ensure_ascii=False)
    chart_regions_data = json.dumps([v for _, v in regions.most_common(13)])
    chart_sub_labels = json.dumps([k for k, _ in subtypes.most_common()], ensure_ascii=False)
    chart_sub_data = json.dumps([v for _, v in subtypes.most_common()])
    chart_city_labels = json.dumps([k for k, _ in top_cities], ensure_ascii=False)
    chart_city_data = json.dumps([v for _, v in top_cities])
    chart_year_labels = json.dumps(sorted(years.keys()))
    chart_year_data = json.dumps([years[y] for y in sorted(years.keys())])

    rated = [c["rating"] for c in cards if c["rcount"] > 0]
    avg_rating = f"{sum(rated) / len(rated):.1f}" if rated else "—"
    with_img = sum(1 for c in cards if c["img_count"] > 0)

    return f"""<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>قرة — دليل مراكز رعاية الأطفال</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="crm.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#080B14;
  --surface:#0D1117;
  --surface2:#161B22;
  --surface3:#21262D;
  --border:#30363D;
  --border-active:#58A6FF;
  --accent:#7C3AED;
  --accent2:#2563EB;
  --success:#238636;
  --warning:#D29922;
  --danger:#DA3633;
  --text:#E6EDF3;
  --text2:#8B949E;
  --text3:#484F58;
  --r:12px;
  --r-sm:8px;
  --sidebar-w:240px;
}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important;animation:none!important}}}}
html{{scroll-behavior:smooth}}
body{{
  background:var(--bg);color:var(--text);
  font-family:'IBM Plex Sans Arabic','Inter',system-ui,sans-serif;
  min-height:100vh;overflow-x:hidden;
  display:flex;
}}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:var(--surface3);border-radius:3px}}
::-webkit-scrollbar-thumb:hover{{background:var(--text3)}}

/* ── KEYFRAMES ── */
@keyframes fadeInUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes shimmer{{0%{{background-position:-200% 0}}100%{{background-position:200% 0}}}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}

/* ── SIDEBAR ── */
.sidebar{{
  position:fixed;top:0;left:0;bottom:0;
  width:var(--sidebar-w);
  background:var(--surface);
  border-right:1px solid var(--border);
  display:flex;flex-direction:column;
  z-index:100;
  transition:transform .25s cubic-bezier(.4,0,.2,1);
}}
.sidebar-header{{
  padding:1.4rem 1.25rem 1rem;
  border-bottom:1px solid var(--border);
  display:flex;flex-direction:column;gap:.15rem;
}}
.sidebar-logo{{
  display:flex;align-items:center;gap:.5rem;
  direction:rtl;
}}
.sidebar-logo-mark{{
  width:32px;height:32px;border-radius:8px;flex-shrink:0;
  background:linear-gradient(135deg,#7C3AED,#2563EB);
  display:flex;align-items:center;justify-content:center;
  font-size:.95rem;font-weight:700;color:#fff;
  box-shadow:0 0 12px rgba(124,58,237,.4);
}}
.sidebar-logo-text{{
  font-size:1.15rem;font-weight:700;color:var(--text);
  letter-spacing:-.3px;
}}
.sidebar-sub{{
  font-size:.68rem;color:var(--text3);margin-top:.1rem;
  direction:rtl;text-align:right;padding-right:0;
}}
.sidebar-nav{{
  flex:1;padding:.5rem 0;overflow-y:auto;
}}
.nav-section-label{{
  padding:.65rem 1.25rem .3rem;
  font-size:.6rem;font-weight:700;text-transform:uppercase;
  letter-spacing:1px;color:var(--text3);direction:rtl;
}}
.nav-item{{
  display:flex;align-items:center;gap:.6rem;
  padding:.6rem 1rem .6rem 1.25rem;
  font-size:.83rem;color:var(--text2);
  cursor:pointer;transition:all .15s;
  direction:rtl;text-align:right;
  border:none;background:none;width:100%;
  font-family:inherit;border-radius:0;
  position:relative;
}}
.nav-item::before{{
  content:'';position:absolute;right:0;top:50%;transform:translateY(-50%);
  width:3px;height:0;border-radius:2px;
  background:var(--accent);transition:height .2s;
}}
.nav-item:hover{{background:var(--surface2);color:var(--text)}}
.nav-item.active{{color:var(--text);background:rgba(124,58,237,.1)}}
.nav-item.active::before{{height:60%}}
.nav-icon{{
  font-size:.95rem;width:20px;text-align:center;flex-shrink:0;
  opacity:.7;
}}
.nav-item.active .nav-icon,.nav-item:hover .nav-icon{{opacity:1}}
.sidebar-footer{{
  padding:.85rem 1.25rem;border-top:1px solid var(--border);
  font-size:.62rem;color:var(--text3);
  direction:rtl;text-align:right;line-height:1.5;
}}

/* hamburger */
.hamburger{{
  display:none;position:fixed;top:12px;left:12px;z-index:150;
  background:var(--surface2);border:1px solid var(--border);
  color:var(--text);width:38px;height:38px;border-radius:var(--r-sm);
  font-size:1.2rem;cursor:pointer;
  align-items:center;justify-content:center;
}}
.sidebar-overlay{{
  display:none;position:fixed;inset:0;z-index:90;
  background:rgba(0,0,0,.5);backdrop-filter:blur(2px);
}}

/* ── MAIN ── */
.main{{
  margin-left:var(--sidebar-w);flex:1;
  display:flex;flex-direction:column;min-height:100vh;
  direction:rtl;
}}

/* ── TOPBAR (sticky) ── */
.topbar{{
  position:sticky;top:0;z-index:50;
  background:rgba(8,11,20,.92);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);
  padding:0 1.5rem;
}}
.topbar-search{{padding:.8rem 0 .5rem}}
.search-wrap{{position:relative}}
.search-icon{{
  position:absolute;left:12px;top:50%;transform:translateY(-50%);
  color:var(--text3);pointer-events:none;font-size:.9rem;
}}
.search-input{{
  width:100%;padding:.65rem 1rem .65rem 2.5rem;
  background:var(--surface2);
  border:1px solid var(--border);
  border-radius:var(--r);color:var(--text);
  font-family:inherit;font-size:.9rem;outline:none;
  transition:border-color .2s,box-shadow .2s,background .2s;
}}
.search-input:focus{{
  border-color:var(--accent);
  background:var(--surface3);
  box-shadow:0 0 0 3px rgba(124,58,237,.12);
}}
.search-input::placeholder{{color:var(--text3)}}
.topbar-filters{{
  display:flex;gap:.4rem;flex-wrap:wrap;align-items:center;
  padding:.45rem 0;
}}
.filter-select{{
  padding:.4rem .7rem;background:var(--surface2);
  border:1px solid var(--border);border-radius:var(--r-sm);
  color:var(--text);font-family:inherit;font-size:.78rem;
  outline:none;cursor:pointer;
  transition:border-color .15s,background .15s;
  direction:rtl;
}}
.filter-select:hover{{border-color:var(--text3)}}
.filter-select:focus{{border-color:var(--accent)}}
.topbar-chips{{
  display:flex;gap:.3rem;flex-wrap:wrap;align-items:center;
  padding:0 0 .65rem;
}}
.chip{{
  padding:.28rem .7rem;border-radius:20px;font-size:.7rem;font-weight:600;
  background:transparent;border:1px solid var(--border);
  color:var(--text3);cursor:pointer;transition:all .15s;
  white-space:nowrap;user-select:none;letter-spacing:.2px;
}}
.chip:hover{{border-color:var(--text2);color:var(--text2)}}
.chip.active{{
  background:rgba(124,58,237,.15);
  border-color:rgba(124,58,237,.5);
  color:#C4B5FD;
  box-shadow:0 0 8px rgba(124,58,237,.15);
}}
.result-pill{{
  font-size:.72rem;color:var(--text3);
  padding:.22rem .6rem;background:var(--surface3);
  border-radius:20px;border:1px solid var(--border);
  white-space:nowrap;font-feature-settings:'tnum';
}}
.view-btns{{display:flex;gap:.2rem}}
.view-btn{{
  background:transparent;border:1px solid var(--border);
  color:var(--text3);width:30px;height:30px;border-radius:var(--r-sm);
  cursor:pointer;font-size:.9rem;transition:all .15s;
  display:flex;align-items:center;justify-content:center;
}}
.view-btn:hover{{border-color:var(--text2);color:var(--text2)}}
.view-btn.active{{background:rgba(124,58,237,.15);border-color:var(--accent);color:var(--accent)}}
.sort-select{{max-width:155px}}

/* ── STAT STRIP ── */
.stat-strip{{
  display:flex;gap:.6rem;padding:.85rem 1.5rem;
  overflow-x:auto;border-bottom:1px solid var(--border);
  background:var(--surface);
  scrollbar-width:none;
}}
.stat-strip::-webkit-scrollbar{{display:none}}
.stat-card{{
  flex-shrink:0;padding:.75rem 1.1rem;
  background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--r);min-width:120px;
  transition:border-color .2s,background .2s,transform .2s;
  cursor:default;
}}
.stat-card:hover{{
  border-color:rgba(124,58,237,.4);
  background:rgba(124,58,237,.05);
  transform:translateY(-1px);
}}
.stat-num{{
  font-size:1.6rem;font-weight:800;
  font-family:'Inter',system-ui,sans-serif;
  color:var(--text);line-height:1;letter-spacing:-.5px;
}}
.stat-num.accent{{color:#A78BFA}}
.stat-num.blue{{color:#60A5FA}}
.stat-num.green{{color:#34D399}}
.stat-num.gold{{color:#FBBF24}}
.stat-label{{font-size:.65rem;color:var(--text3);margin-top:.3rem;letter-spacing:.3px}}

/* CRM header stats */
#crm-header-stats{{
  display:flex;gap:.4rem;flex-wrap:wrap;align-items:center;
  padding:0 1.5rem .65rem;
}}
.crm-stat-chip{{
  padding:.25rem .6rem;border-radius:20px;font-size:.72rem;
  background:var(--surface2);border:1px solid var(--border);color:var(--text2);
}}
.crm-chip-green {{border-color:rgba(63,185,80,.3);color:#3FB950}}
.crm-chip-blue  {{border-color:rgba(88,166,255,.3);color:#58A6FF}}
.crm-chip-purple{{border-color:rgba(124,58,237,.3);color:#C4B5FD}}

/* ── CHARTS ── */
.charts-section{{
  padding:1rem 1.5rem 1.25rem;
  border-bottom:1px solid var(--border);
  display:none;
  background:rgba(13,17,23,.5);
}}
.charts-section.visible{{display:block;animation:fadeInUp .2s ease}}
.charts-toggle{{
  display:flex;align-items:center;gap:.5rem;
  padding:.5rem 1.5rem;
  border-bottom:1px solid var(--border);
  background:var(--surface);
}}
.toggle-btn{{
  padding:.35rem .8rem;border-radius:var(--r-sm);
  font-size:.75rem;font-weight:600;cursor:pointer;
  background:transparent;border:1px solid var(--border);
  color:var(--text3);font-family:inherit;
  transition:all .15s;
}}
.toggle-btn:hover{{border-color:var(--text2);color:var(--text2)}}
.toggle-btn.active{{background:rgba(124,58,237,.12);border-color:rgba(124,58,237,.4);color:#C4B5FD}}
.charts-grid{{
  display:grid;grid-template-columns:repeat(2,1fr);
  gap:.85rem;margin-top:.85rem;
}}
.chart-card{{
  background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--r);padding:.9rem;
}}
.chart-title{{
  font-size:.65rem;font-weight:700;color:var(--text3);
  text-transform:uppercase;letter-spacing:1px;margin-bottom:.7rem;
  direction:rtl;
}}
.chart-wrap{{position:relative;height:185px}}

/* ── CARDS GRID ── */
#grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(290px,1fr));
  gap:1rem;padding:1.25rem 1.5rem;flex:1;
  align-content:start;
}}
#grid.list-view{{grid-template-columns:1fr}}

/* ── CARD ── */
.card{{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--r);overflow:hidden;cursor:pointer;
  display:flex;flex-direction:column;
  transition:transform .2s cubic-bezier(.4,0,.2,1),border-color .2s,box-shadow .2s;
  animation:fadeInUp .3s ease both;
}}
.card:nth-child(1){{animation-delay:0s}}
.card:nth-child(2){{animation-delay:.03s}}
.card:nth-child(3){{animation-delay:.06s}}
.card:nth-child(4){{animation-delay:.09s}}
.card:nth-child(5){{animation-delay:.12s}}
.card:nth-child(6){{animation-delay:.15s}}
.card:hover{{
  transform:translateY(-4px);
  border-color:rgba(124,58,237,.45);
  box-shadow:0 12px 40px rgba(124,58,237,.15),0 4px 12px rgba(0,0,0,.3);
}}
/* List view */
#grid.list-view .card{{
  flex-direction:row;max-height:135px;
  animation:none;
}}
#grid.list-view .card-thumb{{width:150px;flex-shrink:0;height:auto}}
#grid.list-view .card-info{{flex:1;padding:.7rem .9rem}}
#grid.list-view .card:hover{{transform:none;box-shadow:0 0 0 1px rgba(124,58,237,.45),0 4px 20px rgba(124,58,237,.1)}}
#grid.list-view .card-name{{font-size:.88rem}}

.card-thumb{{
  position:relative;height:188px;background:var(--surface2);overflow:hidden;
}}
.card-thumb img{{
  width:100%;height:100%;object-fit:cover;
  transition:transform .4s cubic-bezier(.4,0,.2,1);
}}
.card:hover .card-thumb img{{transform:scale(1.06)}}
/* Gradient overlay at bottom of image */
.card-thumb::after{{
  content:'';position:absolute;bottom:0;left:0;right:0;height:60px;
  background:linear-gradient(to top,rgba(8,11,20,.7),transparent);
  pointer-events:none;
}}
.no-thumb{{
  width:100%;height:100%;display:flex;align-items:center;
  justify-content:center;flex-direction:column;gap:.5rem;
  background:linear-gradient(135deg,var(--surface),var(--surface3));
}}
.no-thumb-initials{{
  width:54px;height:54px;border-radius:14px;
  display:flex;align-items:center;justify-content:center;
  font-size:1.25rem;font-weight:800;color:#fff;
  box-shadow:0 4px 16px rgba(0,0,0,.3);
}}
.card-badges{{
  position:absolute;top:8px;right:8px;z-index:1;
  display:flex;gap:4px;flex-wrap:wrap;
}}
.img-badge{{
  position:absolute;bottom:8px;left:8px;z-index:1;
  background:rgba(0,0,0,.7);backdrop-filter:blur(8px);
  border-radius:20px;padding:2px 8px;
  font-size:.65rem;color:rgba(255,255,255,.85);
  border:1px solid rgba(255,255,255,.08);
}}
.rating-badge{{
  position:absolute;bottom:8px;right:8px;z-index:1;
  background:rgba(0,0,0,.7);backdrop-filter:blur(8px);
  border-radius:20px;padding:3px 9px;
  display:flex;align-items:center;gap:4px;
  font-size:.72rem;border:1px solid rgba(255,255,255,.08);
}}
.badge{{
  padding:2px 9px;border-radius:20px;font-size:.62rem;font-weight:700;
  backdrop-filter:blur(10px);letter-spacing:.3px;
}}
.badge-green {{background:rgba(35,134,54,.25);color:#3FB950;border:1px solid rgba(63,185,80,.35)}}
.badge-yellow{{background:rgba(210,153,34,.2);color:#FBBF24;border:1px solid rgba(210,153,34,.35)}}
.badge-red   {{background:rgba(218,54,51,.2);color:#F85149;border:1px solid rgba(218,54,51,.35)}}
.badge-gray  {{background:rgba(139,148,158,.1);color:#8B949E;border:1px solid rgba(139,148,158,.2)}}
.badge-blue  {{background:rgba(88,166,255,.18);color:#60A5FA;border:1px solid rgba(88,166,255,.3)}}
.badge-purple{{background:rgba(124,58,237,.18);color:#C4B5FD;border:1px solid rgba(124,58,237,.35)}}

.card-info{{
  padding:.9rem 1rem .85rem;display:flex;flex-direction:column;gap:.32rem;flex:1;
  direction:rtl;text-align:right;
}}
.card-name{{
  font-size:.93rem;font-weight:700;line-height:1.35;color:var(--text);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}}
.card-name-en{{font-size:.67rem;color:var(--text3);direction:ltr;text-align:left;margin-top:-2px}}
.card-row{{display:flex;align-items:center;gap:.35rem;font-size:.77rem;color:var(--text2)}}
.card-phone{{direction:ltr;display:inline;font-family:'Inter',monospace;font-size:.75rem}}
.card-price{{
  margin-top:auto;padding-top:.45rem;border-top:1px solid var(--border);
  font-size:.78rem;font-weight:700;
  background:linear-gradient(90deg,#A78BFA,#60A5FA);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}
.stars{{color:#FBBF24;letter-spacing:1px;font-size:.78rem}}
.rcount{{color:var(--text3);font-size:.67rem}}

/* CRM dot on card */
.crm-dot{{
  width:9px;height:9px;border-radius:50%;display:inline-block;
  flex-shrink:0;transition:background .2s;
}}
.crm-not_called {{background:var(--text3)}}
.crm-no_answer  {{background:#D29922}}
.crm-interested {{background:#3FB950}}
.crm-follow_up  {{background:#58A6FF}}
.crm-rejected   {{background:#DA3633}}
.crm-closed     {{background:#A371F7}}
.crm-badge-row{{
  display:flex;align-items:center;gap:5px;
  padding-top:.35rem;border-top:1px solid var(--border);
  margin-top:.25rem;font-size:.72rem;color:var(--text2);
}}
.crm-badge-label{{font-size:.7rem}}

/* ── EMPTY STATE ── */
.empty-state{{
  grid-column:1/-1;text-align:center;padding:5rem 2rem;color:var(--text2);
}}
.empty-state .e-icon{{font-size:3rem;display:block;margin-bottom:.75rem;opacity:.5}}
.empty-state h3{{font-size:1.3rem;color:var(--text);margin-bottom:.35rem}}

/* ── MODAL DRAWER ── */
.drawer-overlay{{
  display:none;position:fixed;inset:0;z-index:200;
  background:rgba(0,0,0,.55);backdrop-filter:blur(6px);
  transition:opacity .25s;
}}
.drawer-overlay.open{{display:block}}
.modal-drawer{{
  position:fixed;top:0;right:0;width:520px;height:100vh;
  background:var(--surface);
  border-left:1px solid var(--border);
  z-index:210;overflow-y:auto;overflow-x:hidden;
  transform:translateX(110%);
  transition:transform .3s cubic-bezier(.4,0,.2,1);
  box-shadow:-20px 0 60px rgba(0,0,0,.5);
}}
.modal-drawer.open{{transform:translateX(0)}}
.drawer-close{{
  position:sticky;top:0;z-index:10;
  display:flex;align-items:center;justify-content:space-between;
  padding:.6rem .85rem;
  background:rgba(13,17,23,.95);backdrop-filter:blur(16px);
  border-bottom:1px solid var(--border);
}}
.drawer-close-btn{{
  background:transparent;border:1px solid var(--border);
  color:var(--text2);width:30px;height:30px;border-radius:var(--r-sm);
  font-size:.85rem;display:flex;align-items:center;justify-content:center;
  cursor:pointer;transition:all .15s;
}}
.drawer-close-btn:hover{{background:rgba(218,54,51,.12);border-color:var(--danger);color:var(--danger)}}
.drawer-nav{{display:flex;gap:.25rem}}
.drawer-nav-btn{{
  background:transparent;border:1px solid var(--border);
  color:var(--text3);width:30px;height:30px;border-radius:var(--r-sm);
  font-size:.8rem;display:flex;align-items:center;justify-content:center;
  cursor:pointer;transition:all .15s;
}}
.drawer-nav-btn:hover{{border-color:var(--accent);color:var(--accent);background:rgba(124,58,237,.1)}}

/* Gallery inside drawer */
.gallery{{width:100%}}
.hero-wrap{{
  height:250px;overflow:hidden;background:var(--surface2);position:relative;
}}
.hero-img{{width:100%;height:100%;object-fit:cover;cursor:zoom-in}}
.img-count-badge{{
  position:absolute;bottom:10px;left:10px;
  background:rgba(0,0,0,.65);backdrop-filter:blur(6px);
  border-radius:20px;padding:3px 10px;font-size:.72rem;
  color:rgba(255,255,255,.75);direction:rtl;
}}
.thumb-strip{{
  display:flex;gap:4px;padding:5px 6px;
  overflow-x:auto;background:rgba(0,0,0,.3);
}}
.thumb-strip img{{
  height:56px;width:80px;object-fit:cover;border-radius:6px;
  cursor:pointer;border:2px solid transparent;
  transition:border-color .15s;flex-shrink:0;
}}
.thumb-strip img:hover{{border-color:var(--accent)}}
.no-img-big{{
  height:150px;display:flex;align-items:center;justify-content:center;
  color:var(--text3);background:var(--surface2);font-size:.85rem;
}}

.drawer-body{{padding:1.15rem;display:flex;flex-direction:column;gap:1.1rem;direction:rtl}}

/* Modal header */
.modal-header{{display:flex;flex-direction:column;gap:.3rem}}
.modal-name{{font-size:1.3rem;font-weight:800;line-height:1.3;letter-spacing:-.3px}}
.modal-name-en{{font-size:.77rem;color:var(--text3);direction:ltr;text-align:left}}
.modal-badges{{display:flex;gap:5px;flex-wrap:wrap;margin-top:.25rem}}
.modal-rating{{display:flex;align-items:center;gap:6px;margin-top:.15rem}}

.section-title{{
  font-size:.6rem;font-weight:700;letter-spacing:1.5px;
  text-transform:uppercase;
  color:transparent;
  background:linear-gradient(90deg,var(--accent),var(--border-active));
  -webkit-background-clip:text;background-clip:text;
  padding-bottom:.35rem;border-bottom:1px solid var(--border);margin-bottom:.65rem;
}}
.section-divider{{border:none;border-top:1px solid var(--border);margin:0}}

/* Contact buttons */
.contact-grid{{display:flex;gap:.45rem;flex-wrap:wrap}}
.contact-btn{{
  display:inline-flex;align-items:center;gap:5px;
  padding:.45rem .8rem;border-radius:20px;
  font-size:.78rem;font-weight:500;text-decoration:none;
  border:1px solid var(--border);background:var(--surface2);color:var(--text2);
  transition:all .15s;font-family:inherit;cursor:pointer;
}}
.contact-btn:hover{{background:var(--surface3);color:var(--text)}}
.contact-btn.phone{{border-color:rgba(35,134,54,.4);color:#3FB950}}
.contact-btn.phone:hover{{background:rgba(35,134,54,.1)}}
.contact-btn.email{{border-color:rgba(88,166,255,.3);color:#58A6FF}}
.contact-btn.email:hover{{background:rgba(88,166,255,.08)}}
.contact-btn.maps {{border-color:rgba(210,153,34,.3);color:#D29922}}
.contact-btn.maps:hover{{background:rgba(210,153,34,.08)}}
.contact-btn.web  {{border-color:rgba(124,58,237,.3);color:#C4B5FD}}
.contact-btn.web:hover{{background:rgba(124,58,237,.08)}}

/* Info grid */
.info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:.55rem .9rem}}
.info-row{{display:flex;flex-direction:column;gap:1px}}
.info-label{{font-size:.62rem;color:var(--text3);font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
.info-val{{font-size:.85rem;color:var(--text)}}
.info-sub{{font-size:.7rem;color:var(--text3)}}

/* Map embed */
.map-embed{{border-radius:var(--r-sm);overflow:hidden;height:200px;border:1px solid var(--border);margin-top:.65rem}}
.map-embed iframe{{width:100%;height:100%;border:none}}

/* Service cards */
.svc-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:.55rem}}
.svc-card{{
  background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--r-sm);padding:.75rem;
  display:flex;flex-direction:column;gap:.3rem;
}}
.svc-name{{font-weight:700;font-size:.85rem}}
.svc-meta{{font-size:.74rem;color:var(--text2)}}
.svc-prices{{margin-top:.25rem;display:flex;flex-wrap:wrap;gap:3px}}
.price-tag{{
  background:rgba(124,58,237,.15);color:#C4B5FD;
  border:1px solid rgba(124,58,237,.3);
  border-radius:6px;padding:2px 7px;font-size:.73rem;font-weight:700;
}}
.price-period{{font-weight:400;font-size:.67rem;opacity:.7}}

.desc-text{{color:var(--text2);font-size:.85rem;line-height:1.8}}

/* ── CRM Panel ── */
.crm-panel{{
  background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--r-sm);padding:1rem;
  display:flex;flex-direction:column;gap:.6rem;
}}
.crm-row{{display:grid;grid-template-columns:1fr 1fr;gap:.6rem}}
.crm-field{{display:flex;flex-direction:column;gap:.25rem}}
.crm-label{{font-size:.62rem;color:var(--text3);font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
.crm-select,.crm-input,.crm-textarea{{
  background:var(--surface3);border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-family:inherit;
  font-size:.82rem;padding:.45rem .65rem;outline:none;
  transition:border-color .2s;
}}
.crm-select:focus,.crm-input:focus,.crm-textarea:focus{{border-color:var(--accent)}}
.crm-textarea{{min-height:70px;resize:vertical;line-height:1.6}}
.crm-actions{{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}}
.crm-save-btn{{
  padding:.45rem 1rem;border-radius:var(--r-sm);font-family:inherit;font-size:.82rem;font-weight:700;
  background:rgba(124,58,237,.2);border:1px solid rgba(124,58,237,.4);
  color:#C4B5FD;cursor:pointer;transition:all .15s;
}}
.crm-save-btn:hover{{background:rgba(124,58,237,.35)}}
.crm-clear-btn{{
  padding:.45rem .8rem;border-radius:var(--r-sm);font-family:inherit;font-size:.8rem;
  background:rgba(218,54,51,.1);border:1px solid rgba(218,54,51,.25);
  color:#F85149;cursor:pointer;transition:all .15s;
}}
.crm-clear-btn:hover{{background:rgba(218,54,51,.2)}}
.crm-updated{{font-size:.68rem;color:var(--text3);margin-right:auto}}

/* ── LIGHTBOX ── */
.lightbox{{
  display:none;position:fixed;inset:0;z-index:400;
  background:rgba(0,0,0,.95);align-items:center;justify-content:center;
}}
.lightbox.open{{display:flex}}
.lightbox img{{max-width:95vw;max-height:95vh;object-fit:contain;border-radius:8px}}
.lightbox-close{{
  position:absolute;top:14px;right:14px;
  background:rgba(255,255,255,.1);border:none;color:#fff;
  width:38px;height:38px;border-radius:50%;font-size:1.2rem;
  display:flex;align-items:center;justify-content:center;cursor:pointer;
}}

/* ── FOOTER ── */
.main-footer{{
  text-align:center;padding:1.5rem;color:var(--text3);
  font-size:.72rem;border-top:1px solid var(--border);
  direction:rtl;
}}

/* ── RESPONSIVE ── */
@media(max-width:768px){{
  .sidebar{{transform:translateX(-100%)}}
  .sidebar.open{{transform:translateX(0)}}
  .sidebar-overlay.open{{display:block}}
  .hamburger{{display:flex}}
  .main{{margin-left:0}}
  #grid{{grid-template-columns:1fr;padding:1rem}}
  .charts-grid{{grid-template-columns:1fr}}
  .modal-drawer{{width:100vw}}
  .stat-strip{{padding:.65rem 1rem}}
  .topbar-filters{{gap:.35rem}}
  #grid.list-view .card{{flex-direction:column;max-height:none}}
  #grid.list-view .card-thumb{{width:100%;height:160px}}
  .info-grid{{grid-template-columns:1fr}}
}}
@media(min-width:769px) and (max-width:1100px){{
  #grid{{grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}}
}}
</style>
</head>
<body>

<!-- HAMBURGER (mobile) -->
<button class="hamburger" id="hamburger" onclick="toggleSidebar()">☰</button>
<div class="sidebar-overlay" id="sidebar-overlay" onclick="toggleSidebar()"></div>

<!-- SIDEBAR -->
<aside class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-logo">
      <div class="sidebar-logo-mark">ق</div>
      <div class="sidebar-logo-text">قرة</div>
    </div>
    <div class="sidebar-sub">دليل مراكز رعاية الأطفال</div>
  </div>
  <nav class="sidebar-nav">
    <div class="nav-section-label">التنقل</div>
    <button class="nav-item active" id="nav-home" onclick="navTo('home')">
      <span class="nav-icon">⊞</span>جميع المراكز
    </button>
    <button class="nav-item" id="nav-charts" onclick="navTo('charts')">
      <span class="nav-icon">◎</span>الإحصائيات
    </button>
    <div class="nav-section-label" style="margin-top:.5rem">المبيعات</div>
    <button class="nav-item" id="nav-called" onclick="navTo('called')">
      <span class="nav-icon">◈</span>سجل المكالمات
    </button>
    <button class="nav-item" id="nav-interested" onclick="navTo('interested')">
      <span class="nav-icon">◉</span>المهتمون
    </button>
    <button class="nav-item" id="nav-followup" onclick="navTo('followup')">
      <span class="nav-icon">◷</span>قيد المتابعة
    </button>
    <div class="nav-section-label" style="margin-top:.5rem">أدوات</div>
    <button class="nav-item" onclick="CRM.exportCSV()">
      <span class="nav-icon">↓</span>تصدير CRM
    </button>
    <button class="nav-item" onclick="exportCSV()">
      <span class="nav-icon">↓</span>تصدير المراكز
    </button>
  </nav>
  <div class="sidebar-footer">
    قرة دايركتوري · v2.0<br>
    آخر تحديث: {scraped_at}
  </div>
</aside>

<!-- MAIN -->
<div class="main">

  <!-- TOPBAR -->
  <div class="topbar">
    <div class="topbar-search">
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <input type="search" class="search-input" id="search" placeholder="ابحث بالاسم، المدينة، المنطقة..." autocomplete="off">
      </div>
    </div>
    <div class="topbar-filters">
      <select class="filter-select" id="region-filter" onchange="onRegionChange()">
        <option value="">كل المناطق</option>
      </select>
      <select class="filter-select" id="city-filter">
        <option value="">كل المدن</option>
      </select>
      <select class="filter-select" id="sub-filter">
        <option value="">كل الأنواع</option>
      </select>
      <select class="filter-select" id="accred-filter">
        <option value="">حالة الاعتماد</option>
        <option value="ACCREDITED">معتمد</option>
        <option value="PENDING_APPROVAL">قيد المراجعة</option>
      </select>
      <select class="filter-select sort-select" id="sort-select" onchange="applyFilter()">
        <option value="default">ترتيب: افتراضي</option>
        <option value="rating-desc">الأعلى تقييما</option>
        <option value="rating-asc">الأقل تقييما</option>
        <option value="price-asc">السعر: من الأقل</option>
        <option value="price-desc">السعر: من الأعلى</option>
        <option value="name-asc">الاسم: أ - ي</option>
        <option value="reviews-desc">الأكثر تقييما</option>
      </select>
      <div class="view-btns">
        <button class="view-btn active" id="btn-grid" onclick="setView('grid')" title="شبكة">⊞</button>
        <button class="view-btn" id="btn-list" onclick="setView('list')" title="قائمة">☰</button>
      </div>
      <span class="result-pill" id="result-pill">{total} نتيجة</span>
    </div>
    <div class="topbar-chips" id="chips">
      <span class="chip" data-filter="has-img" onclick="toggleChip(this)">لديها صور</span>
      <span class="chip" data-filter="has-svc" onclick="toggleChip(this)">لديها خدمات</span>
      <span class="chip" data-filter="rated" onclick="toggleChip(this)">مُقيَّم</span>
      <span class="chip" data-filter="crm-called" onclick="toggleChip(this)">تم الاتصال</span>
      <span class="chip" data-filter="crm-interested" onclick="toggleChip(this)">مهتم</span>
      <span class="chip" data-filter="crm-followup" onclick="toggleChip(this)">متابعة</span>
      <span class="chip" data-filter="crm-none" onclick="toggleChip(this)">لم يتم الاتصال</span>
    </div>
  </div>

  <!-- STAT STRIP -->
  <div class="stat-strip">
    <div class="stat-card">
      <div class="stat-num accent" id="shown-count">{total}</div>
      <div class="stat-label">إجمالي المراكز</div>
    </div>
    <div class="stat-card">
      <div class="stat-num green">{accred_count}</div>
      <div class="stat-label">معتمد</div>
    </div>
    <div class="stat-card">
      <div class="stat-num blue">{len(region_cities)}</div>
      <div class="stat-label">المناطق</div>
    </div>
    <div class="stat-card">
      <div class="stat-num gold">{avg_rating}</div>
      <div class="stat-label">متوسط التقييم</div>
    </div>
    <div class="stat-card">
      <div class="stat-num">{with_img}</div>
      <div class="stat-label">لديها صور</div>
    </div>
    <div class="stat-card">
      <div class="stat-num" id="stat-called">0</div>
      <div class="stat-label">تم الاتصال</div>
    </div>
  </div>

  <!-- CRM HEADER STATS -->
  <div id="crm-header-stats"></div>

  <!-- CHARTS TOGGLE + SECTION -->
  <div class="charts-toggle">
    <button class="toggle-btn" id="charts-toggle-btn" onclick="toggleCharts()">📊 إظهار الرسوم البيانية</button>
  </div>
  <div class="charts-section" id="charts-section">
    <div class="charts-grid">
      <div class="chart-card">
        <div class="chart-title">المراكز حسب المنطقة</div>
        <div class="chart-wrap"><canvas id="chart-regions"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">نوع المركز</div>
        <div class="chart-wrap"><canvas id="chart-types"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">أكثر المدن</div>
        <div class="chart-wrap"><canvas id="chart-cities"></canvas></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">سنة التأسيس</div>
        <div class="chart-wrap"><canvas id="chart-years"></canvas></div>
      </div>
    </div>
  </div>

  <!-- GRID -->
  <div id="grid"></div>

  <!-- FOOTER -->
  <footer class="main-footer">
    تم جمع {total} مركز &middot; آخر تحديث: {scraped_at} &middot; مصدر البيانات: qurrah.sa
  </footer>
</div>

<!-- DRAWER OVERLAY -->
<div class="drawer-overlay" id="drawer-overlay" onclick="closeDrawer()"></div>

<!-- MODAL DRAWER -->
<div class="modal-drawer" id="modal-drawer">
  <div class="drawer-close">
    <div class="drawer-nav">
      <button class="drawer-nav-btn" onclick="navDrawer(-1)" title="السابق">→</button>
      <button class="drawer-nav-btn" onclick="navDrawer(1)" title="التالي">←</button>
    </div>
    <button class="drawer-close-btn" onclick="closeDrawer()">✕</button>
  </div>
  <div id="drawer-content"></div>
</div>

<!-- LIGHTBOX -->
<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <button class="lightbox-close">✕</button>
  <img id="lightbox-img" src="" alt="">
</div>

<script>
// ── Data ──
const ALL = {cards_js};
const REGION_CITIES = {region_city_js};

// ── State ──
const activeChips = new Set();
let currentData = ALL.map((d, i) => ({{...d, _origIdx: i}}));
let currentDrawerIdx = -1;
let MODAL_DATA = null;
let chartsBuilt = false;

// ── DOM refs ──
const grid = document.getElementById('grid');
const regionSel = document.getElementById('region-filter');
const citySel = document.getElementById('city-filter');
const subSel = document.getElementById('sub-filter');

// ── Helpers ──
function esc(s) {{
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
function starsStr(r) {{
  const f = Math.round(r || 0);
  return '\u2605'.repeat(f) + '\u2606'.repeat(5 - f);
}}
function starsHtml(r, c) {{
  return `<span class="stars">${{starsStr(r)}}</span><span class="rcount"> ${{c}} تقييم</span>`;
}}
function fmt(n) {{ return Number(n).toLocaleString('ar-SA'); }}
function infoRow(label, val, sub) {{
  sub = sub || '';
  return `<div class="info-row"><div class="info-label">${{label}}</div><div class="info-val">${{esc(val)}}${{sub ? `<div class="info-sub">${{esc(sub)}}</div>` : ''}}</div></div>`;
}}
function copyText(t) {{
  navigator.clipboard.writeText(t).then(() => {{
    const msg = document.createElement('div');
    msg.textContent = 'تم النسخ';
    msg.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#238636;color:#fff;padding:.5rem 1.2rem;border-radius:8px;font-size:.85rem;z-index:500;animation:fadeInUp .3s ease';
    document.body.appendChild(msg);
    setTimeout(() => msg.remove(), 1500);
  }});
}}
function setHero(el) {{
  const hero = document.getElementById('modal-hero');
  if (hero) {{ hero.src = el.src; hero.style.display = ''; }}
}}

// Color hash for initials fallback
function hashColor(s) {{
  let h = 0;
  for (let i = 0; i < s.length; i++) h = s.charCodeAt(i) + ((h << 5) - h);
  const hue = Math.abs(h) % 360;
  return `hsl(${{hue}}, 55%, 40%)`;
}}

// ── Card builder ──
function buildCard(d, idx) {{
  const crm = CRM.get(d.id);
  const crmStatus = crm?.status || 'not_called';
  const crmCfg = STATUS_CONFIG[crmStatus] || {{}};
  const initials = (d.name_ar || '').slice(0, 2);
  const bgColor = hashColor(d.name_ar || '');

  const thumb = d.thumb_url
    ? `<img src="${{d.thumb_url}}" loading="lazy" alt="${{esc(d.name_ar)}}"
        onerror="this.onerror=null;this.parentElement.innerHTML='<div class=\\'no-thumb\\'><div class=\\'no-thumb-initials\\' style=\\'background:${{bgColor}}\\'>${{esc(initials)}}</div></div>'">`
    : `<div class="no-thumb"><div class="no-thumb-initials" style="background:${{bgColor}}">${{esc(initials)}}</div></div>`;

  const imgBadge = d.img_count > 1 ? `<div class="img-badge">${{d.img_count}} صورة</div>` : '';
  const ratingBadge = d.rcount > 0
    ? `<div class="rating-badge"><span class="stars">${{starsStr(d.rating)}}</span><span class="rcount">${{d.rcount}}</span></div>` : '';

  const priceRow = d.min_price != null
    ? `<div class="card-price">يبدأ من ${{fmt(d.min_price)}} ر.س/شهر</div>` : '';

  return `<div class="card" data-idx="${{idx}}" data-id="${{d.id}}" onclick="openDrawer(${{idx}})">
  <div class="card-thumb">
    ${{thumb}}
    <div class="card-badges">
      <span class="badge ${{d.accred_cls}}">${{d.accred_label}}</span>
      ${{d.sub_ar ? `<span class="badge badge-blue">${{d.sub_ar}}</span>` : ''}}
    </div>
    ${{imgBadge}}
    ${{ratingBadge}}
  </div>
  <div class="card-info">
    <div class="card-name">${{esc(d.name_ar)}}</div>
    ${{d.name_en ? `<div class="card-name-en">${{esc(d.name_en)}}</div>` : ''}}
    <div class="card-row">📍 ${{esc(d.city_ar)}}${{d.region_ar && d.region_ar !== d.city_ar ? '، ' + esc(d.region_ar) : ''}}</div>
    ${{d.phone ? `<div class="card-row"><a href="tel:${{esc(d.phone)}}" onclick="event.stopPropagation()" style="color:var(--text2);text-decoration:none">📞 <span class="card-phone">${{esc(d.phone)}}</span></a></div>` : ''}}
    ${{priceRow}}
    <div class="crm-badge-row">
      <span class="crm-dot crm-${{crmStatus}}" title="${{crmCfg.label || 'لم يتم الاتصال'}}"></span>
      <span class="crm-badge-label">${{crmCfg.label || 'لم يتم الاتصال'}}</span>
      ${{crm?.call_date ? `<span style="font-size:.67rem;color:var(--text3);margin-right:auto">${{crm.call_date}}</span>` : ''}}
    </div>
  </div>
</div>`;
}}

// ── Render grid ──
function renderGrid(items) {{
  const html = items.map((d, i) => buildCard(d, d._origIdx)).join('');
  grid.innerHTML = html || emptyState();
}}
function emptyState() {{
  return `<div class="empty-state"><span class="e-icon">🔍</span><h3>لا توجد نتائج</h3><p>جرب تغيير الفلتر أو كلمة البحث</p></div>`;
}}

// ── Populate filters ──
const regions = [...new Set(ALL.map(d => d.region_ar).filter(Boolean))].sort();
const subtypesArr = [...new Set(ALL.map(d => d.sub_ar).filter(Boolean))].sort();

regions.forEach(r => {{
  const o = document.createElement('option'); o.value = r; o.textContent = r;
  regionSel.appendChild(o);
}});
subtypesArr.forEach(s => {{
  const o = document.createElement('option'); o.value = s; o.textContent = s;
  subSel.appendChild(o);
}});

function onRegionChange() {{
  const r = regionSel.value;
  citySel.innerHTML = '<option value="">كل المدن</option>';
  if (r && REGION_CITIES[r]) {{
    REGION_CITIES[r].forEach(c => {{
      const o = document.createElement('option'); o.value = c; o.textContent = c;
      citySel.appendChild(o);
    }});
  }} else {{
    const allCities = [...new Set(ALL.map(d => d.city_ar).filter(Boolean))].sort();
    allCities.forEach(c => {{
      const o = document.createElement('option'); o.value = c; o.textContent = c;
      citySel.appendChild(o);
    }});
  }}
  applyFilter();
}}

// ── Chips ──
function toggleChip(el) {{
  const f = el.dataset.filter;
  if (activeChips.has(f)) {{ activeChips.delete(f); el.classList.remove('active'); }}
  else {{ activeChips.add(f); el.classList.add('active'); }}
  applyFilter();
}}

// ── Filter + Sort ──
function applyFilter() {{
  const q = document.getElementById('search').value.trim().toLowerCase();
  const region = regionSel.value;
  const city = citySel.value;
  const sub = subSel.value;
  const accred = document.getElementById('accred-filter').value;
  const sort = document.getElementById('sort-select').value;

  let result = ALL.map((d, i) => ({{...d, _origIdx: i}})).filter(d => {{
    if (q && !d.name_ar.toLowerCase().includes(q) && !(d.name_en || '').toLowerCase().includes(q)
           && !d.city_ar.includes(q) && !d.region_ar.includes(q)) return false;
    if (region && d.region_ar !== region) return false;
    if (city && d.city_ar !== city) return false;
    if (sub && d.sub_ar !== sub) return false;
    if (accred && d.accred !== accred) return false;
    if (activeChips.has('has-img') && d.img_count < 1) return false;
    if (activeChips.has('has-svc') && d.svc_count < 1) return false;
    if (activeChips.has('rated') && d.rcount < 1) return false;
    // CRM chips
    const crmRec = CRM.get(d.id);
    const crmSt = crmRec?.status || 'not_called';
    if (activeChips.has('crm-called') && crmSt === 'not_called') return false;
    if (activeChips.has('crm-interested') && crmSt !== 'interested' && crmSt !== 'closed') return false;
    if (activeChips.has('crm-followup') && crmSt !== 'follow_up') return false;
    if (activeChips.has('crm-none') && crmSt !== 'not_called') return false;
    return true;
  }});

  if (sort === 'rating-desc') result.sort((a, b) => b.rating - a.rating);
  if (sort === 'rating-asc') result.sort((a, b) => a.rating - b.rating);
  if (sort === 'reviews-desc') result.sort((a, b) => b.rcount - a.rcount);
  if (sort === 'name-asc') result.sort((a, b) => a.name_ar.localeCompare(b.name_ar, 'ar'));
  if (sort === 'price-asc') result.sort((a, b) => (a.min_price || 99999) - (b.min_price || 99999));
  if (sort === 'price-desc') result.sort((a, b) => (b.min_price || 0) - (a.min_price || 0));

  currentData = result;
  renderGrid(result);
  document.getElementById('shown-count').textContent = result.length;
  document.getElementById('result-pill').textContent = result.length + ' نتيجة';
  updateStatCalled();
}}

function updateStatCalled() {{
  const s = CRM.stats();
  const el = document.getElementById('stat-called');
  if (el) el.textContent = s.called;
}}

// ── Event listeners ──
document.getElementById('search').addEventListener('input', applyFilter);
document.getElementById('city-filter').addEventListener('change', applyFilter);
document.getElementById('sub-filter').addEventListener('change', applyFilter);
document.getElementById('accred-filter').addEventListener('change', applyFilter);

// ── View toggle ──
function setView(v) {{
  grid.className = v === 'list' ? 'list-view' : '';
  document.getElementById('btn-grid').classList.toggle('active', v === 'grid');
  document.getElementById('btn-list').classList.toggle('active', v === 'list');
}}

// ── Sidebar nav ──
function navTo(page) {{
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  if (page === 'home') {{
    document.getElementById('nav-home').classList.add('active');
    activeChips.forEach(c => activeChips.delete(c));
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    applyFilter();
    grid.scrollIntoView({{ behavior: 'smooth' }});
  }} else if (page === 'charts') {{
    document.getElementById('nav-charts').classList.add('active');
    const cs = document.getElementById('charts-section');
    if (!cs.classList.contains('visible')) toggleCharts();
    cs.scrollIntoView({{ behavior: 'smooth' }});
  }} else if (page === 'called') {{
    document.getElementById('nav-called').classList.add('active');
    activeChips.clear();
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    const calledChip = document.querySelector('.chip[data-filter="crm-called"]');
    if (calledChip) {{ activeChips.add('crm-called'); calledChip.classList.add('active'); }}
    applyFilter();
    grid.scrollIntoView({{ behavior: 'smooth' }});
  }} else if (page === 'interested') {{
    document.getElementById('nav-interested').classList.add('active');
    activeChips.clear();
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    const chip = document.querySelector('.chip[data-filter="crm-interested"]');
    if (chip) {{ activeChips.add('crm-interested'); chip.classList.add('active'); }}
    applyFilter();
    grid.scrollIntoView({{ behavior: 'smooth' }});
  }} else if (page === 'followup') {{
    document.getElementById('nav-followup').classList.add('active');
    activeChips.clear();
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    const chip = document.querySelector('.chip[data-filter="crm-followup"]');
    if (chip) {{ activeChips.add('crm-followup'); chip.classList.add('active'); }}
    applyFilter();
    grid.scrollIntoView({{ behavior: 'smooth' }});
  }}
  // Close sidebar on mobile
  if (window.innerWidth <= 768) toggleSidebar();
}}

// ── Sidebar mobile toggle ──
function toggleSidebar() {{
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebar-overlay').classList.toggle('open');
}}

// ── Charts toggle ──
function toggleCharts() {{
  const cs = document.getElementById('charts-section');
  const btn = document.getElementById('charts-toggle-btn');
  cs.classList.toggle('visible');
  if (cs.classList.contains('visible')) {{
    btn.classList.add('active');
    btn.textContent = '📊 إخفاء الرسوم البيانية';
    if (!chartsBuilt) buildCharts();
  }} else {{
    btn.classList.remove('active');
    btn.textContent = '📊 إظهار الرسوم البيانية';
  }}
}}

// ── Modal data cache ──
async function loadModalData() {{
  if (MODAL_DATA) return MODAL_DATA;
  const r = await fetch('data/modal.json');
  MODAL_DATA = await r.json();
  return MODAL_DATA;
}}

// ── Drawer ──
async function openDrawer(idx) {{
  const card = ALL[idx];
  if (!card) return;
  currentDrawerIdx = idx;

  const drawerContent = document.getElementById('drawer-content');
  drawerContent.innerHTML = `<div style="text-align:center;padding:4rem;color:var(--text2)">جاري التحميل...</div>`;
  document.getElementById('drawer-overlay').classList.add('open');
  document.getElementById('modal-drawer').classList.add('open');
  document.body.style.overflow = 'hidden';

  const allModal = await loadModalData();
  const d = allModal[card.id];
  if (!d) {{ drawerContent.innerHTML = '<div style="padding:2rem;color:var(--text3)">لا توجد بيانات</div>'; return; }}

  let html = d.gal_html;
  html += `<div class="drawer-body">`;

  // Header
  html += `<div class="modal-header">
    <div class="modal-name">${{esc(d.name_ar)}}</div>
    ${{d.name_en ? `<div class="modal-name-en">${{esc(d.name_en)}}</div>` : ''}}
    <div class="modal-badges">
      <span class="badge ${{d.accred_cls}}">${{d.accred_label}}</span>
      ${{d.sub_ar ? `<span class="badge badge-blue">${{d.sub_ar}}</span>` : ''}}
      ${{d.btype ? `<span class="badge badge-gray">${{d.btype}}</span>` : ''}}
      ${{d.created ? `<span class="badge badge-purple">تأسس ${{d.created}}</span>` : ''}}
    </div>
    ${{d.rcount > 0 ? `<div class="modal-rating">${{starsHtml(d.rating, d.rcount)}}</div>` : ''}}
  </div>`;

  // Contact buttons
  const btns = [];
  if (d.phone) btns.push(`<a href="tel:${{d.phone}}" class="contact-btn phone" onclick="event.stopPropagation()">📞 ${{esc(d.phone)}}</a>`);
  if (d.email) btns.push(`<a href="mailto:${{d.email}}" class="contact-btn email">✉ ${{esc(d.email)}}</a>`);
  if (d.maps_url) btns.push(`<a href="${{d.maps_url}}" target="_blank" class="contact-btn maps">📍 خريطة</a>`);
  if (d.branch_url) btns.push(`<a href="${{d.branch_url}}" target="_blank" class="contact-btn web">🔗 صفحة المركز</a>`);
  if (btns.length) html += `<div><div class="section-title">التواصل</div><div class="contact-grid">${{btns.join('')}}</div></div>`;

  html += '<hr class="section-divider">';

  // Location
  const addrRows = [];
  if (d.region_ar) addrRows.push(infoRow('المنطقة', d.region_ar));
  if (d.city_ar) addrRows.push(infoRow('المدينة', d.city_ar));
  if (d.street_ar) addrRows.push(infoRow('الشارع', d.street_ar));
  if (d.zip_code) addrRows.push(infoRow('الرمز البريدي', d.zip_code));
  if (addrRows.length) {{
    html += `<div><div class="section-title">الموقع</div><div class="info-grid">${{addrRows.join('')}}</div>`;
    if (d.lat && d.lng && d.lat !== 'None' && d.lng !== 'None' && d.lat !== '' && d.lng !== '') {{
      html += `<div class="map-embed">
        <iframe loading="lazy" src="https://maps.google.com/maps?q=${{d.lat}},${{d.lng}}&z=15&output=embed&hl=ar" allowfullscreen></iframe>
      </div>`;
    }}
    html += `</div>`;
  }}

  html += '<hr class="section-divider">';

  // Legal
  const legalRows = [...(d.lic_rows || []).map(r => infoRow(r.label, r.val, r.sub || ''))];
  if (d.cr_no) legalRows.push(infoRow('السجل التجاري', d.cr_no, d.cr_exp ? `تنتهي ${{d.cr_exp}}` : ''));
  if (legalRows.length) html += `<div><div class="section-title">البيانات الرسمية</div><div class="info-grid">${{legalRows.join('')}}</div></div>`;

  html += '<hr class="section-divider">';

  // Services
  if (d.svc_html) html += `<div><div class="section-title">الخدمات والأسعار</div>${{d.svc_html}}</div>`;

  // Description
  if (d.desc && d.desc.trim()) {{
    html += '<hr class="section-divider">';
    html += `<div><div class="section-title">عن المركز</div><p class="desc-text">${{esc(d.desc)}}</p></div>`;
  }}

  html += '<hr class="section-divider">';

  // CRM Panel
  html += `<div><div class="section-title">سجل المبيعات</div>${{renderCRMPanel(card.id)}}</div>`;

  html += `</div>`;

  drawerContent.innerHTML = html;

  // Hero click -> lightbox
  const hero = document.getElementById('modal-hero');
  if (hero) hero.addEventListener('click', () => openLightbox(hero.src));
}}

function closeDrawer() {{
  document.getElementById('drawer-overlay').classList.remove('open');
  document.getElementById('modal-drawer').classList.remove('open');
  document.body.style.overflow = '';
  currentDrawerIdx = -1;
  // Re-render grid to update CRM dots
  applyFilter();
}}

function navDrawer(dir) {{
  // Navigate to previous/next card in currentData
  if (currentDrawerIdx < 0) return;
  const currentInFiltered = currentData.findIndex(d => d._origIdx === currentDrawerIdx);
  if (currentInFiltered < 0) return;
  const nextIdx = currentInFiltered + dir;
  if (nextIdx < 0 || nextIdx >= currentData.length) return;
  openDrawer(currentData[nextIdx]._origIdx);
}}

document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') {{
    if (document.getElementById('lightbox').classList.contains('open')) closeLightbox();
    else closeDrawer();
  }}
  if (document.getElementById('modal-drawer').classList.contains('open')) {{
    if (e.key === 'ArrowLeft') navDrawer(1);
    if (e.key === 'ArrowRight') navDrawer(-1);
  }}
}});

// ── Lightbox ──
function openLightbox(src) {{
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox').classList.add('open');
}}
function closeLightbox() {{
  document.getElementById('lightbox').classList.remove('open');
}}

// ── CSV Export (branches) ──
function exportCSV() {{
  const rows = [['الاسم','المدينة','المنطقة','الهاتف','حالة الاعتماد','النوع','التقييم','عدد التقييمات','أقل سعر (ر.س)','سنة التأسيس']];
  currentData.forEach(d => {{
    rows.push([
      d.name_ar, d.city_ar, d.region_ar,
      d.phone, d.accred_label, d.sub_ar,
      d.rating, d.rcount,
      d.min_price != null ? d.min_price : '',
      d.created,
    ]);
  }});
  const csv = rows.map(r => r.map(c => `"${{String(c || '').replace(/"/g, '""')}}"`).join(',')).join('\\n');
  const blob = new Blob(['\\ufeff' + csv], {{ type: 'text/csv;charset=utf-8' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'qurrah-branches.csv';
  a.click();
}}

// ── Initial render ──
onRegionChange();
updateStatCalled();

// ── Charts (lazy, wrapped in try/catch) ──
function buildCharts() {{
  try {{
    const chartFont = {{ family: 'IBM Plex Sans Arabic, Inter, sans-serif' }};
    const chartOpts = (horizontal) => ({{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ rtl: true, bodyFont: chartFont, titleFont: chartFont }}
      }},
      indexAxis: horizontal ? 'y' : 'x',
      scales: {{
        x: {{ grid: {{ color: 'rgba(255,255,255,.04)' }}, ticks: {{ color: '#484F58', font: {{ size: 10, ...chartFont }} }} }},
        y: {{ grid: {{ color: 'rgba(255,255,255,.04)' }}, ticks: {{ color: '#484F58', font: {{ size: 10, ...chartFont }} }} }},
      }}
    }});
    const GRAD_PURPLE = ctx => {{
      const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, 200);
      g.addColorStop(0, 'rgba(124,58,237,.8)');
      g.addColorStop(1, 'rgba(37,99,235,.5)');
      return g;
    }};
    const GRAD_BLUE = ctx => {{
      const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, 200);
      g.addColorStop(0, 'rgba(88,166,255,.8)');
      g.addColorStop(1, 'rgba(35,134,54,.4)');
      return g;
    }};
    new Chart('chart-regions', {{
      type: 'bar', data: {{
        labels: {chart_regions_labels},
        datasets: [{{ data: {chart_regions_data}, backgroundColor: GRAD_PURPLE, borderRadius: 6, borderSkipped: false }}]
      }}, options: chartOpts()
    }});
    new Chart('chart-types', {{
      type: 'doughnut', data: {{
        labels: {chart_sub_labels},
        datasets: [{{ data: {chart_sub_data},
          backgroundColor: ['rgba(124,58,237,.7)', 'rgba(37,99,235,.7)', 'rgba(35,134,54,.7)', 'rgba(210,153,34,.7)', 'rgba(218,54,51,.7)', 'rgba(163,113,247,.7)', 'rgba(88,166,255,.5)'],
          borderWidth: 0, hoverOffset: 6
        }}]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ position: 'right', rtl: true, labels: {{ color: '#8B949E', font: {{ ...chartFont, size: 11 }}, padding: 12 }} }} }}
      }}
    }});
    new Chart('chart-cities', {{
      type: 'bar', data: {{
        labels: {chart_city_labels},
        datasets: [{{ data: {chart_city_data}, backgroundColor: GRAD_BLUE, borderRadius: 6, borderSkipped: false }}]
      }}, options: chartOpts(true)
    }});
    new Chart('chart-years', {{
      type: 'line', data: {{
        labels: {chart_year_labels},
        datasets: [{{ data: {chart_year_data},
          borderColor: 'rgba(210,153,34,.8)', backgroundColor: 'rgba(210,153,34,.06)',
          fill: true, tension: .4, pointBackgroundColor: 'rgba(210,153,34,.9)', pointRadius: 3
        }}]
      }}, options: chartOpts()
    }});
    chartsBuilt = true;
  }} catch (e) {{
    console.warn('Charts failed:', e);
  }}
}}
</script>
</body>
</html>"""


def main():
    """Load branches.json, build HTML + modal.json."""
    print(f"Loading {JSON_FILE}...")
    with open(JSON_FILE, encoding="utf-8") as f:
        branches = json.load(f)
    print(f"  {len(branches)} branches loaded")
    print("Building HTML...")
    html = build_html(branches)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Done -> {HTML_FILE} ({os.path.getsize(HTML_FILE) // 1024}KB)")


def rebuild_html():
    """Rebuild HTML from existing branches.json (no re-scrape)."""
    print("Rebuilding from existing data...")
    main()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rebuild":
        rebuild_html()
    else:
        main()
