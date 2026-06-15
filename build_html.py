#!/usr/bin/env python3
"""
Build enhanced index.html from data/branches.json
Usage: python3 build_html.py
"""
import json
import os
from datetime import datetime
from collections import Counter

JSON_FILE = "data/branches.json"
HTML_FILE = "index.html"

ACCRED_AR = {
    "ACCREDITED":       "معتمد",
    "PENDING_APPROVAL": "قيد المراجعة",
    "REJECTED":         "مرفوض",
}
ACCRED_CLS = {
    "ACCREDITED":       "badge-green",
    "PENDING_APPROVAL": "badge-yellow",
    "REJECTED":         "badge-red",
}
LICENSE_ISSUER_AR = {
    "MOE": "وزارة التعليم",
    "MOH": "وزارة الصحة",
    "MOS": "وزارة الشؤون الاجتماعية",
}


def stars_html(avg, count):
    full = int(round(float(avg or 0)))
    s = "★" * full + "☆" * (5 - full)
    return f'<span class="stars">{s}</span><span class="rcount">{count} تقييم</span>'


def get_min_price(branch):
    """Return lowest monthly price across all services."""
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
    if not services:
        return ""
    items = []
    for svc in services:
        st = svc.get("service_type") or {}
        name_ar  = st.get("name_ar", "")
        age_from = st.get("age_from", "")
        age_to   = st.get("age_to", "")
        age_str  = f"{age_from} – {age_to} سنوات" if age_from != "" else ""
        wh = svc.get("working_hours") or {}
        from_t = (wh.get("from_time") or "")[:5]
        to_t   = (wh.get("to_time")   or "")[:5]
        hours  = f"{from_t} – {to_t}" if from_t else ""
        terms  = svc.get("booking_terms") or []
        price_tags = []
        for t in terms:
            bt = t.get("booking_type") or {}
            try:
                price = float(t.get("total_price") or 0)
            except Exception:
                price = 0
            if price > 0:
                price_tags.append(
                    f'<span class="price-tag">{price:,.0f} ر.س<span class="price-period"> / {bt.get("name_ar","")}</span></span>'
                )
        items.append(f"""<div class="svc-card">
  <div class="svc-name">{name_ar}</div>
  {f'<div class="svc-meta">👶 {age_str}</div>' if age_str else ""}
  {f'<div class="svc-meta">⏰ {hours}</div>' if hours else ""}
  {f'<div class="svc-prices">{"".join(price_tags)}</div>' if price_tags else ""}
</div>""")
    return '<div class="svc-grid">' + "".join(items) + "</div>"


def gallery_html(gallery, display_img):
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
            f'<img src="{u}" loading="lazy" onclick="setHero(this)" onerror="this.style.display=\'none\'">'
            for u in thumbs
        )
        thumb_html = f'<div class="thumb-strip">{tlist}</div>'
    count_badge = f'<div class="img-count">📷 {len(imgs)}</div>' if len(imgs) > 1 else ""
    return f"""<div class="gallery">
  <div class="hero-wrap">
    <img class="hero-img" id="modal-hero" src="{hero}" onerror="this.style.display='none'">
    {count_badge}
  </div>
  {thumb_html}
</div>"""


def build_card_data(b):
    """Extract all card/modal data into a dict for JSON embedding."""
    bid     = b.get("id", "")
    name_ar = b.get("name_ar") or "—"
    name_en = b.get("name_en") or ""
    desc    = (b.get("description") or "").strip()
    if desc == ".":
        desc = ""

    addr      = b.get("address") or {}
    city_ar   = addr.get("city_name_ar") or addr.get("city_name_en") or ""
    city_en   = addr.get("city_name_en") or ""
    region_ar = addr.get("region_name_ar") or ""
    street_ar = addr.get("street_name_ar") or addr.get("street_name_en") or ""
    zip_code  = addr.get("zip_code") or ""
    lat = addr.get("lat", "")
    lng = addr.get("lng", "")

    rating = float(b.get("avg_branch_rating") or 0)
    rcount = int(b.get("total_ratings_count") or 0)
    accred = b.get("accreditation_status", "")

    phone = b.get("contact_phone_number") or ""
    email = b.get("contact_email") or ""

    sub = b.get("branch_subtype") or {}
    sub_ar  = sub.get("name_ar") or "" if isinstance(sub, dict) else ""
    btype   = (sub.get("branch_type") or {}).get("name_ar") or "" if isinstance(sub, dict) else ""

    # License
    lic_rows = []
    for lic in (b.get("branch_license") or []):
        if not isinstance(lic, dict):
            continue
        lic_no  = lic.get("license_number") or b.get("license_number") or ""
        lic_exp = lic.get("license_expiry_date") or b.get("license_expiry_date") or ""
        issuer  = LICENSE_ISSUER_AR.get(lic.get("license_issuer") or "", lic.get("license_issuer") or "")
        if lic_no:
            lic_rows.append({"label": "رقم الرخصة", "val": lic_no, "sub": f"تنتهي {lic_exp}" if lic_exp else ""})
        if issuer:
            lic_rows.append({"label": "جهة الترخيص", "val": issuer})

    cr     = b.get("cr") or {}
    cr_no  = cr.get("number") or b.get("cr_number") or ""
    cr_exp = cr.get("expiry_date") or b.get("cr_expiry_date") or ""

    # Services
    services = b.get("services") or []
    gallery  = b.get("gallery") or []
    disp_img = b.get("branch_display_image") or ""

    min_price = get_min_price(b)
    img_count = len(gallery) + (1 if disp_img else 0)
    thumb_url = disp_img or (gallery[0].get("file", "") if gallery else "")

    # Compute year
    created = (b.get("created_at") or "")[:4]

    maps_url   = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else ""
    branch_url = f"https://qurrah.sa/branch/{bid}"

    card = {
        "id":           bid,
        "name_ar":      name_ar,
        "name_en":      name_en,
        "city_ar":      city_ar,
        "city_en":      city_en,
        "region_ar":    region_ar,
        "rating":       rating,
        "rcount":       rcount,
        "accred":       accred,
        "accred_label": ACCRED_AR.get(accred, accred),
        "accred_cls":   ACCRED_CLS.get(accred, "badge-gray"),
        "sub_ar":       sub_ar,
        "phone":        phone,
        "min_price":    min_price,
        "img_count":    img_count,
        "thumb_url":    thumb_url,
        "svc_count":    len(services),
        "created":      created,
    }
    modal = {
        "id":           bid,
        "name_ar":      name_ar,
        "name_en":      name_en,
        "desc":         desc,
        "city_ar":      city_ar,
        "region_ar":    region_ar,
        "street_ar":    street_ar,
        "zip_code":     zip_code,
        "lat":          str(lat),
        "lng":          str(lng),
        "rating":       rating,
        "rcount":       rcount,
        "accred_label": ACCRED_AR.get(accred, accred),
        "accred_cls":   ACCRED_CLS.get(accred, "badge-gray"),
        "sub_ar":       sub_ar,
        "btype":        btype,
        "phone":        phone,
        "email":        email,
        "lic_rows":     lic_rows,
        "cr_no":        cr_no,
        "cr_exp":       cr_exp,
        "min_price":    min_price,
        "branch_url":   branch_url,
        "maps_url":     maps_url,
        "created":      created,
        "svc_html":     service_cards_html(services),
        "gal_html":     gallery_html(gallery, disp_img),
    }
    return card, modal


def build_html(branches):
    total      = len(branches)
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    accred_count = sum(1 for b in branches if b.get("accreditation_status") == "ACCREDITED")

    # Build card + modal data (split)
    cards = []
    modal_map = {}
    for b in branches:
        card, modal = build_card_data(b)
        cards.append(card)
        modal_map[card["id"]] = modal

    # Write modal data to separate file
    os.makedirs("data", exist_ok=True)
    with open("data/modal.json", "w", encoding="utf-8") as f:
        json.dump(modal_map, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  modal.json written ({os.path.getsize('data/modal.json')//1024}KB)")

    # Stats for charts
    regions   = Counter(c["region_ar"] for c in cards if c["region_ar"])
    subtypes  = Counter(c["sub_ar"] for c in cards if c["sub_ar"])
    top_cities = Counter(c["city_ar"] for c in cards if c["city_ar"]).most_common(10)
    years     = Counter(c["created"] for c in cards if c["created"])

    # Unique cities per region for cascading filter
    region_cities = {}
    for c in cards:
        r = c["region_ar"]
        ci = c["city_ar"]
        if r and ci:
            region_cities.setdefault(r, set()).add(ci)

    region_city_js = json.dumps(
        {r: sorted(list(cs)) for r, cs in sorted(region_cities.items())},
        ensure_ascii=False
    )

    # All card data as JS array
    cards_js = json.dumps(cards, ensure_ascii=False)

    # Chart data
    chart_regions_labels = json.dumps([k for k,_ in regions.most_common(13)], ensure_ascii=False)
    chart_regions_data   = json.dumps([v for _,v in regions.most_common(13)])
    chart_sub_labels     = json.dumps([k for k,_ in subtypes.most_common()], ensure_ascii=False)
    chart_sub_data       = json.dumps([v for _,v in subtypes.most_common()])
    chart_city_labels    = json.dumps([k for k,_ in top_cities], ensure_ascii=False)
    chart_city_data      = json.dumps([v for _,v in top_cities])
    chart_year_labels    = json.dumps(sorted(years.keys()))
    chart_year_data      = json.dumps([years[y] for y in sorted(years.keys())])

    rated = [c["rating"] for c in cards if c["rcount"] > 0]
    avg_rating = f"{sum(rated)/len(rated):.2f}" if rated else "—"
    with_img   = sum(1 for c in cards if c["img_count"] > 0)
    with_svc   = sum(1 for c in cards if c["svc_count"] > 0)

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>دليل مراكز قرة</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="crm.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#07070f;--s1:#0f0f1e;--s2:#14142a;--s3:#1a1a33;--s4:#202040;
  --border:#252545;--border2:#303060;
  --accent:#7c6fff;--accent2:#4fc3f7;--accent3:#34d399;
  --gold:#fbbf24;--red:#f87171;--purple:#c084fc;
  --text:#eeeeff;--text2:#9090bb;--text3:#50507a;
  --r:14px;--r-sm:9px;
  --glow:0 0 40px rgba(124,111,255,.15);
}}
html{{scroll-behavior:smooth}}
body{{
  background:var(--bg);color:var(--text);
  font-family:'IBM Plex Sans Arabic',system-ui,sans-serif;
  min-height:100vh;overflow-x:hidden;
}}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-track{{background:var(--bg)}}
::-webkit-scrollbar-thumb{{background:var(--border2);border-radius:3px}}
::-webkit-scrollbar-thumb:hover{{background:var(--accent)}}

/* ── HEADER ── */
header{{
  position:relative;overflow:hidden;
  background:linear-gradient(150deg,#080818 0%,#0c0c24 50%,#0a1030 100%);
  border-bottom:1px solid var(--border);
  padding:3rem 2rem 2.5rem;text-align:center;
}}
header::before{{
  content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse 100% 80% at 50% -10%,rgba(124,111,255,.18),transparent);
  pointer-events:none;
}}
header::after{{
  content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--accent),transparent);
}}
.logo{{
  font-size:2.8rem;font-weight:800;letter-spacing:-1px;line-height:1;
  background:linear-gradient(120deg,#a78bfa 0%,#60a5fa 50%,#34d399 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}
.logo-sub{{color:var(--text2);font-size:.95rem;margin-top:.5rem;font-weight:400}}

.stats-row{{
  display:flex;justify-content:center;gap:2rem;
  margin-top:2rem;flex-wrap:wrap;
}}
.stat{{
  text-align:center;padding:.8rem 1.4rem;
  background:rgba(255,255,255,.03);border:1px solid var(--border);
  border-radius:12px;min-width:110px;
  transition:border-color .2s,background .2s;
}}
.stat:hover{{border-color:var(--accent);background:rgba(124,111,255,.06)}}
.stat-num{{
  font-size:2rem;font-weight:800;line-height:1;
  background:linear-gradient(135deg,#a78bfa,#60a5fa);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}}
.stat-label{{font-size:.72rem;color:var(--text3);margin-top:4px;letter-spacing:.5px}}

/* ── CHARTS SECTION ── */
.charts-section{{
  max-width:1600px;margin:2rem auto;padding:0 1.5rem;
  display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1.25rem;
}}
.chart-card{{
  background:var(--s1);border:1px solid var(--border);border-radius:var(--r);
  padding:1.25rem;
}}
.chart-title{{font-size:.75rem;font-weight:700;color:var(--text2);
  text-transform:uppercase;letter-spacing:1px;margin-bottom:1rem}}
.chart-wrap{{position:relative;height:200px}}

/* ── CONTROLS ── */
.controls{{
  position:sticky;top:0;z-index:50;
  background:rgba(7,7,15,.92);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);
  padding:.85rem 1.5rem;
  display:flex;gap:.65rem;flex-wrap:wrap;align-items:center;
}}
.search-wrap{{flex:1;min-width:160px;position:relative}}
.search-icon{{
  position:absolute;right:11px;top:50%;transform:translateY(-50%);
  color:var(--text3);pointer-events:none;font-size:.9rem;
}}
input[type=search]{{
  width:100%;padding:.58rem 2.2rem .58rem .85rem;
  background:var(--s2);border:1px solid var(--border);
  border-radius:var(--r-sm);color:var(--text);
  font-family:inherit;font-size:.88rem;outline:none;
  transition:border-color .2s,box-shadow .2s;
}}
input[type=search]:focus{{border-color:var(--accent);box-shadow:0 0 0 3px rgba(124,111,255,.12)}}
select{{
  padding:.55rem .85rem;background:var(--s2);border:1px solid var(--border);
  border-radius:var(--r-sm);color:var(--text);font-family:inherit;font-size:.85rem;
  outline:none;cursor:pointer;transition:border-color .2s;
}}
select:focus{{border-color:var(--accent)}}

.filter-chips{{display:flex;gap:.4rem;flex-wrap:wrap}}
.chip{{
  padding:.35rem .8rem;border-radius:20px;font-size:.75rem;font-weight:600;
  background:var(--s2);border:1px solid var(--border);
  color:var(--text2);cursor:pointer;transition:all .18s;white-space:nowrap;
}}
.chip:hover{{border-color:var(--accent2);color:var(--accent2)}}
.chip.active{{background:rgba(124,111,255,.2);border-color:var(--accent);color:#c4b5fd}}

.view-btns{{display:flex;gap:.3rem}}
.view-btn{{
  background:var(--s2);border:1px solid var(--border);
  color:var(--text3);padding:.45rem .6rem;border-radius:var(--r-sm);
  cursor:pointer;font-size:1rem;transition:all .18s;
}}
.view-btn.active{{background:rgba(124,111,255,.2);border-color:var(--accent);color:var(--accent)}}

.sort-select{{max-width:160px}}

.result-pill{{
  color:var(--text2);font-size:.8rem;white-space:nowrap;
  padding:.3rem .75rem;background:var(--s3);border-radius:20px;
  border:1px solid var(--border);
}}

/* ── GRID ── */
#grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
  gap:1.25rem;padding:1.5rem;max-width:1700px;margin:0 auto;
}}
#grid.list-view{{grid-template-columns:1fr}}

/* ── CARD ── */
.card{{
  background:var(--s1);border:1px solid var(--border);border-radius:var(--r);
  overflow:hidden;cursor:pointer;
  display:flex;flex-direction:column;
  transition:transform .22s,border-color .22s,box-shadow .22s;
}}
.card:hover{{
  transform:translateY(-5px);
  border-color:rgba(124,111,255,.55);
  box-shadow:0 12px 40px rgba(124,111,255,.18);
}}
.card.hidden{{display:none!important}}

/* List view card */
#grid.list-view .card{{
  flex-direction:row;align-items:stretch;max-height:140px;
}}
#grid.list-view .card-thumb{{width:180px;flex-shrink:0;height:auto}}
#grid.list-view .card-info{{flex:1}}
#grid.list-view .card:hover{{transform:translateX(-4px)}}

.card-thumb{{
  position:relative;height:185px;background:var(--s2);overflow:hidden;
}}
.card-thumb img{{
  width:100%;height:100%;object-fit:cover;
  transition:transform .35s;
}}
.card:hover .card-thumb img{{transform:scale(1.07)}}
.no-thumb{{
  width:100%;height:100%;display:flex;align-items:center;
  justify-content:center;color:var(--text3);font-size:.82rem;
  background:linear-gradient(135deg,var(--s1),var(--s3));
}}
.card-badges{{
  position:absolute;top:9px;right:9px;
  display:flex;gap:5px;flex-wrap:wrap;
}}
.img-badge{{
  position:absolute;bottom:8px;left:8px;
  background:rgba(0,0,0,.6);backdrop-filter:blur(6px);
  border-radius:20px;padding:3px 9px;
  font-size:.7rem;color:rgba(255,255,255,.8);
}}
.rating-badge{{
  position:absolute;bottom:8px;right:8px;
  background:rgba(0,0,0,.65);backdrop-filter:blur(8px);
  border-radius:20px;padding:3px 10px;
  display:flex;align-items:center;gap:4px;
}}

.badge{{
  padding:3px 10px;border-radius:20px;font-size:.69rem;font-weight:700;
  backdrop-filter:blur(8px);letter-spacing:.3px;
}}
.badge-green {{background:rgba(52,211,153,.15);color:#34d399;border:1px solid rgba(52,211,153,.3)}}
.badge-yellow{{background:rgba(251,191,36,.15);color:#fbbf24;border:1px solid rgba(251,191,36,.3)}}
.badge-red   {{background:rgba(248,113,113,.15);color:#f87171;border:1px solid rgba(248,113,113,.3)}}
.badge-gray  {{background:rgba(144,144,187,.1); color:#9090bb;border:1px solid rgba(144,144,187,.2)}}
.badge-blue  {{background:rgba(79,195,247,.15); color:#7dd3fc;border:1px solid rgba(79,195,247,.3)}}
.badge-purple{{background:rgba(192,132,252,.15);color:#d8b4fe;border:1px solid rgba(192,132,252,.3)}}

.card-info{{padding:1rem 1.1rem 1.1rem;display:flex;flex-direction:column;gap:.4rem;flex:1}}
.card-name{{font-size:.98rem;font-weight:700;line-height:1.35;color:var(--text)}}
.card-name-en{{font-size:.72rem;color:var(--text3);direction:ltr;margin-top:-2px}}
.card-row{{display:flex;align-items:center;gap:.4rem;font-size:.8rem;color:var(--text2)}}
.card-price{{
  margin-top:auto;padding-top:.6rem;border-top:1px solid var(--border);
  font-size:.82rem;color:var(--accent3);font-weight:600;
}}

.stars{{color:var(--gold);letter-spacing:1px;font-size:.85rem}}
.rcount{{color:var(--text3);font-size:.72rem}}

/* ── EMPTY ── */
.empty-state{{
  grid-column:1/-1;text-align:center;padding:6rem 2rem;color:var(--text2);
}}
.empty-state .e-icon{{font-size:3.5rem;display:block;margin-bottom:1rem}}
.empty-state h3{{font-size:1.5rem;color:var(--text);margin-bottom:.5rem}}

/* ── MODAL ── */
.modal-overlay{{
  display:none;position:fixed;inset:0;
  background:rgba(0,0,0,.8);backdrop-filter:blur(8px);
  z-index:200;align-items:flex-start;justify-content:center;
  padding:1.5rem;overflow-y:auto;
}}
.modal-overlay.open{{display:flex}}
.modal{{
  background:var(--s1);border:1px solid var(--border2);border-radius:20px;
  width:100%;max-width:860px;margin:auto;overflow:hidden;
  position:relative;animation:slideUp .25s ease;
  box-shadow:0 24px 80px rgba(0,0,0,.6),var(--glow);
}}
@keyframes slideUp{{
  from{{transform:translateY(28px);opacity:0}}
  to{{transform:translateY(0);opacity:1}}
}}
.modal-close{{
  position:absolute;top:12px;left:12px;z-index:10;
  background:rgba(255,255,255,.07);border:none;color:var(--text2);
  width:34px;height:34px;border-radius:50%;font-size:1.1rem;
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;transition:background .2s,color .2s;
}}
.modal-close:hover{{background:rgba(248,113,113,.2);color:#f87171}}

/* Gallery */
.gallery{{width:100%}}
.hero-wrap{{
  height:320px;overflow:hidden;background:var(--s2);position:relative;
}}
.hero-img{{width:100%;height:100%;object-fit:cover;cursor:zoom-in}}
.img-count{{
  position:absolute;bottom:10px;right:10px;
  background:rgba(0,0,0,.65);backdrop-filter:blur(6px);
  border-radius:20px;padding:3px 10px;font-size:.75rem;
  color:rgba(255,255,255,.75);
}}
.thumb-strip{{
  display:flex;gap:5px;padding:6px 8px;
  overflow-x:auto;background:rgba(0,0,0,.3);
}}
.thumb-strip img{{
  height:68px;width:95px;object-fit:cover;border-radius:7px;
  cursor:pointer;border:2px solid transparent;
  transition:border-color .15s,opacity .15s;flex-shrink:0;
}}
.thumb-strip img:hover{{border-color:var(--accent)}}
.thumb-strip img.active{{border-color:var(--accent)}}
.no-img-big{{
  height:180px;display:flex;align-items:center;justify-content:center;
  color:var(--text3);background:var(--s2);
}}

.modal-body{{padding:1.6rem;display:flex;flex-direction:column;gap:1.5rem}}
.modal-header{{display:flex;flex-direction:column;gap:.35rem}}
.modal-name{{font-size:1.55rem;font-weight:800;line-height:1.3}}
.modal-name-en{{font-size:.85rem;color:var(--text3);direction:ltr}}
.modal-badges{{display:flex;gap:6px;flex-wrap:wrap;margin-top:.25rem}}
.modal-rating{{display:flex;align-items:center;gap:8px;margin-top:.2rem}}

.section-title{{
  font-size:.68rem;font-weight:700;letter-spacing:1.5px;
  text-transform:uppercase;color:var(--accent2);
  padding-bottom:.45rem;border-bottom:1px solid var(--border);margin-bottom:.85rem;
}}

.info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:.65rem 1.2rem}}
.info-row{{display:flex;flex-direction:column;gap:2px}}
.info-label{{font-size:.65rem;color:var(--text3);font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
.info-val{{font-size:.88rem;color:var(--text)}}
.info-sub{{font-size:.72rem;color:var(--text3)}}

.contact-grid{{display:flex;gap:.6rem;flex-wrap:wrap}}
.contact-btn{{
  display:inline-flex;align-items:center;gap:6px;
  padding:.5rem .95rem;border-radius:var(--r-sm);
  font-size:.83rem;font-weight:500;text-decoration:none;
  border:1px solid var(--border);background:var(--s2);color:var(--text2);
  transition:all .18s;font-family:inherit;cursor:pointer;
}}
.contact-btn:hover{{background:var(--s3);border-color:var(--border2);color:var(--text)}}
.contact-btn.phone{{border-color:rgba(52,211,153,.3);color:#34d399}}
.contact-btn.email{{border-color:rgba(79,195,247,.3);color:#7dd3fc}}
.contact-btn.maps {{border-color:rgba(251,191,36,.3);color:#fbbf24}}
.contact-btn.web  {{border-color:rgba(124,111,255,.3);color:#a78bfa}}
.contact-btn.copy {{border-color:rgba(144,144,187,.2);color:var(--text3)}}

.svc-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:.65rem}}
.svc-card{{
  background:var(--s2);border:1px solid var(--border);
  border-radius:var(--r-sm);padding:.9rem;
  display:flex;flex-direction:column;gap:.35rem;
}}
.svc-name{{font-weight:700;font-size:.9rem}}
.svc-meta{{font-size:.78rem;color:var(--text2)}}
.svc-prices{{margin-top:.3rem;display:flex;flex-wrap:wrap;gap:4px}}
.price-tag{{
  background:rgba(124,111,255,.18);color:#c4b5fd;
  border:1px solid rgba(124,111,255,.3);
  border-radius:6px;padding:3px 9px;font-size:.77rem;font-weight:700;
}}
.price-period{{font-weight:400;font-size:.7rem;opacity:.7}}

.desc-text{{color:var(--text2);font-size:.88rem;line-height:1.8}}

/* map embed */
.map-embed{{border-radius:var(--r-sm);overflow:hidden;height:220px;border:1px solid var(--border)}}
.map-embed iframe{{width:100%;height:100%;border:none}}

/* CSV export btn */
.export-btn{{
  display:inline-flex;align-items:center;gap:6px;
  padding:.45rem .9rem;border-radius:var(--r-sm);
  font-size:.8rem;font-weight:600;cursor:pointer;
  background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.3);
  color:#34d399;font-family:inherit;transition:all .2s;
}}
.export-btn:hover{{background:rgba(52,211,153,.2)}}

/* ── CRM ── */
.crm-dot{{
  width:10px;height:10px;border-radius:50%;display:inline-block;
  flex-shrink:0;border:2px solid rgba(255,255,255,.15);
  transition:background .2s;
}}
.crm-not_called {{background:#333355}}
.crm-no_answer  {{background:#f59e0b}}
.crm-interested {{background:#22c55e}}
.crm-follow_up  {{background:#60a5fa}}
.crm-rejected   {{background:#ef4444}}
.crm-closed     {{background:#a78bfa}}

.crm-badge-row{{
  display:flex;align-items:center;gap:6px;
  padding:.35rem .55rem;
  border-top:1px solid var(--border);margin-top:.3rem;
  font-size:.75rem;color:var(--text2);
}}
.crm-badge-label{{font-size:.72rem;}}

#crm-header-stats{{
  display:flex;gap:.5rem;flex-wrap:wrap;
  justify-content:center;margin-top:1rem;
}}
.crm-stat-chip{{
  padding:.3rem .75rem;border-radius:20px;font-size:.78rem;
  background:var(--s2);border:1px solid var(--border);color:var(--text2);
}}
.crm-chip-green  {{border-color:rgba(34,197,94,.3);color:#4ade80}}
.crm-chip-blue   {{border-color:rgba(96,165,250,.3);color:#93c5fd}}
.crm-chip-purple {{border-color:rgba(167,139,250,.3);color:#c4b5fd}}

.crm-panel{{
  background:var(--s2);border:1px solid var(--border);
  border-radius:var(--r-sm);padding:1.1rem;
  display:flex;flex-direction:column;gap:.7rem;
}}
.crm-row{{display:grid;grid-template-columns:1fr 1fr;gap:.7rem}}
.crm-field{{display:flex;flex-direction:column;gap:.3rem}}
.crm-label{{font-size:.68rem;color:var(--text3);font-weight:700;text-transform:uppercase;letter-spacing:.5px}}
.crm-select,.crm-input,.crm-textarea{{
  background:var(--s3);border:1px solid var(--border2);
  border-radius:7px;color:var(--text);font-family:inherit;
  font-size:.85rem;padding:.5rem .75rem;outline:none;
  transition:border-color .2s;
}}
.crm-select:focus,.crm-input:focus,.crm-textarea:focus{{border-color:var(--accent)}}
.crm-textarea{{min-height:80px;resize:vertical;line-height:1.6}}
.crm-actions{{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap}}
.crm-save-btn{{
  padding:.5rem 1.2rem;border-radius:8px;font-family:inherit;font-size:.85rem;font-weight:700;
  background:rgba(124,111,255,.25);border:1px solid rgba(124,111,255,.5);
  color:#c4b5fd;cursor:pointer;transition:all .2s;
}}
.crm-save-btn:hover{{background:rgba(124,111,255,.4)}}
.crm-clear-btn{{
  padding:.5rem .9rem;border-radius:8px;font-family:inherit;font-size:.82rem;
  background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.25);
  color:#f87171;cursor:pointer;transition:all .2s;
}}
.crm-clear-btn:hover{{background:rgba(239,68,68,.2)}}
.crm-updated{{font-size:.72rem;color:var(--text3);margin-right:auto}}

/* ── LIGHTBOX ── */
.lightbox{{
  display:none;position:fixed;inset:0;z-index:400;
  background:rgba(0,0,0,.95);align-items:center;justify-content:center;
}}
.lightbox.open{{display:flex}}
.lightbox img{{max-width:95vw;max-height:95vh;object-fit:contain;border-radius:8px}}
.lightbox-close{{
  position:absolute;top:16px;right:16px;
  background:rgba(255,255,255,.1);border:none;color:#fff;
  width:40px;height:40px;border-radius:50%;font-size:1.3rem;
  display:flex;align-items:center;justify-content:center;cursor:pointer;
}}

/* ── FOOTER ── */
footer{{
  text-align:center;padding:2rem;color:var(--text3);
  font-size:.78rem;border-top:1px solid var(--border);margin-top:3rem;
}}

@media(max-width:640px){{
  #grid{{grid-template-columns:1fr;padding:1rem}}
  .stats-row{{gap:1rem}}
  .info-grid{{grid-template-columns:1fr}}
  .hero-wrap{{height:220px}}
  .controls{{padding:.7rem 1rem}}
  .charts-section{{padding:0 1rem}}
  #grid.list-view .card{{flex-direction:column;max-height:none}}
  #grid.list-view .card-thumb{{width:100%;height:160px}}
}}
</style>
</head>
<body>

<!-- HEADER -->
<header>
  <div class="logo">دليل مراكز قرة</div>
  <p class="logo-sub">مراكز رعاية وتعليم الأطفال — المملكة العربية السعودية</p>
  <div class="stats-row">
    <div class="stat">
      <div class="stat-num" id="shown-count">{total}</div>
      <div class="stat-label">معروض</div>
    </div>
    <div class="stat">
      <div class="stat-num">{total}</div>
      <div class="stat-label">إجمالي المراكز</div>
    </div>
    <div class="stat">
      <div class="stat-num">{accred_count}</div>
      <div class="stat-label">مركز معتمد</div>
    </div>
    <div class="stat">
      <div class="stat-num">{len(region_cities)}</div>
      <div class="stat-label">منطقة</div>
    </div>
    <div class="stat">
      <div class="stat-num">{avg_rating}</div>
      <div class="stat-label">متوسط التقييم</div>
    </div>
    <div class="stat">
      <div class="stat-num">{with_img}</div>
      <div class="stat-label">لديها صور</div>
    </div>
  </div>
  <div id="crm-header-stats"></div>
</header>

<!-- CHARTS -->
<div class="charts-section">
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

<!-- CONTROLS -->
<div class="controls">
  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input type="search" id="search" placeholder="ابحث بالاسم أو المدينة..." autocomplete="off">
  </div>

  <select id="region-filter" onchange="onRegionChange()">
    <option value="">كل المناطق</option>
  </select>

  <select id="city-filter">
    <option value="">كل المدن</option>
  </select>

  <select id="sub-filter">
    <option value="">كل الأنواع</option>
  </select>

  <select id="accred-filter">
    <option value="">حالة الاعتماد</option>
    <option value="ACCREDITED">معتمد</option>
    <option value="PENDING_APPROVAL">قيد المراجعة</option>
  </select>

  <select id="sort-select" class="sort-select" onchange="applyFilter()">
    <option value="default">ترتيب: افتراضي</option>
    <option value="rating-desc">الأعلى تقييماً</option>
    <option value="rating-asc">الأقل تقييماً</option>
    <option value="price-asc">السعر: من الأقل</option>
    <option value="price-desc">السعر: من الأعلى</option>
    <option value="name-asc">الاسم: أ - ي</option>
    <option value="reviews-desc">الأكثر تقييماً</option>
  </select>

  <div class="filter-chips" id="chips">
    <span class="chip" data-filter="has-img"   onclick="toggleChip(this)">📷 لديها صور</span>
    <span class="chip" data-filter="has-svc"   onclick="toggleChip(this)">📋 لديها خدمات</span>
    <span class="chip" data-filter="rated"     onclick="toggleChip(this)">⭐ مُقيَّم</span>
    <span class="chip" data-filter="has-phone" onclick="toggleChip(this)">📞 رقم الهاتف</span>
    <span class="chip" data-filter="crm-called"     onclick="toggleChip(this)">📞 تم الاتصال</span>
    <span class="chip" data-filter="crm-interested" onclick="toggleChip(this)">🟢 مهتم</span>
    <span class="chip" data-filter="crm-followup"   onclick="toggleChip(this)">🔵 متابعة</span>
    <span class="chip" data-filter="crm-none"       onclick="toggleChip(this)">⬜ لم يتم الاتصال</span>
  </div>

  <div class="view-btns">
    <button class="view-btn active" id="btn-grid" onclick="setView('grid')" title="شبكة">⊞</button>
    <button class="view-btn"        id="btn-list" onclick="setView('list')" title="قائمة">☰</button>
  </div>

  <button class="export-btn" onclick="exportCSV()">⬇ CSV</button>

  <span class="result-pill" id="result-pill">{total} نتيجة</span>
</div>

<!-- GRID -->
<div id="grid"></div>

<!-- MODAL -->
<div class="modal-overlay" id="modal-overlay" onclick="closeModalOnBg(event)">
  <div class="modal" id="modal-box">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div id="modal-content"></div>
  </div>
</div>

<!-- LIGHTBOX -->
<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <button class="lightbox-close">✕</button>
  <img id="lightbox-img" src="" alt="">
</div>

<!-- FOOTER -->
<footer>
  تم جمع {total} مركز · آخر تحديث: {scraped_at} · مصدر البيانات: qurrah.sa
</footer>

<script>
// ── Data ──
const ALL = {cards_js};
const REGION_CITIES = {region_city_js};

// ── Build DOM cards ──
const grid = document.getElementById('grid');

function buildCard(d, idx) {{
  const crm = CRM.get(d.id);
  const crmStatus = crm?.status || 'not_called';
  const crmCfg = STATUS_CONFIG[crmStatus] || {{}};

  const thumb = d.thumb_url
    ? `<img src="${{d.thumb_url}}" loading="lazy" alt="${{esc(d.name_ar)}}"
        onerror="this.onerror=null;this.parentElement.classList.add('no-img-state');this.parentElement.innerHTML='<div class=no-thumb>لا توجد صورة</div>'">`
    : `<div class="no-thumb">لا توجد صورة</div>`;

  const imgBadge = d.img_count > 1 ? `<div class="img-badge">📷 ${{d.img_count}}</div>` : '';
  const ratingBadge = d.rcount > 0
    ? `<div class="rating-badge"><span class="stars">${{starsStr(d.rating)}}</span><span class="rcount">${{d.rcount}}</span></div>` : '';

  const priceRow = d.min_price != null
    ? `<div class="card-price">يبدأ من ${{fmt(d.min_price)}} ر.س / شهر</div>` : '';

  return `<div class="card" data-idx="${{idx}}" data-id="${{d.id}}" onclick="openModal(${{idx}})">
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
    ${{d.phone ? `<div class="card-row">📞 <span style="direction:ltr;display:inline">${{esc(d.phone)}}</span></div>` : ''}}
    ${{priceRow}}
    <div class="crm-badge-row">
      <span class="crm-dot crm-${{crmStatus}}" title="${{crmCfg.label||'لم يتم الاتصال'}}"></span>
      <span class="crm-badge-label">${{crmCfg.label || 'لم يتم الاتصال'}}</span>
      ${{crm?.call_date ? `<span style="font-size:.7rem;color:var(--text3);margin-right:auto">${{crm.call_date}}</span>` : ''}}
    </div>
  </div>
</div>`;
}}

function renderGrid(items) {{
  const html = items.map((d, i) => buildCard(d, d._origIdx)).join('');
  grid.innerHTML = html + (items.length === 0 ? emptyState() : '');
}}

function emptyState() {{
  return `<div class="empty-state"><span class="e-icon">🔍</span><h3>لا توجد نتائج</h3><p>جرب تغيير الفلتر أو كلمة البحث</p></div>`;
}}

// ── Populate filters ──
const regions = [...new Set(ALL.map(d => d.region_ar).filter(Boolean))].sort();
const subtypes = [...new Set(ALL.map(d => d.sub_ar).filter(Boolean))].sort();
const regionSel = document.getElementById('region-filter');
const citySel   = document.getElementById('city-filter');
const subSel    = document.getElementById('sub-filter');

regions.forEach(r => {{
  const o = document.createElement('option'); o.value = r; o.textContent = r;
  regionSel.appendChild(o);
}});
subtypes.forEach(s => {{
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
    // show all cities
    const allCities = [...new Set(ALL.map(d => d.city_ar).filter(Boolean))].sort();
    allCities.forEach(c => {{
      const o = document.createElement('option'); o.value = c; o.textContent = c;
      citySel.appendChild(o);
    }});
  }}
  applyFilter();
}}

// ── Active chips ──
const activeChips = new Set();
function toggleChip(el) {{
  const f = el.dataset.filter;
  if (activeChips.has(f)) {{ activeChips.delete(f); el.classList.remove('active'); }}
  else {{ activeChips.add(f); el.classList.add('active'); }}
  applyFilter();
}}

// ── Filter + Sort ──
let currentData = ALL.map((d, i) => ({{...d, _origIdx: i}}));

function applyFilter() {{
  const q      = document.getElementById('search').value.trim().toLowerCase();
  const region = regionSel.value;
  const city   = citySel.value;
  const sub    = subSel.value;
  const accred = document.getElementById('accred-filter').value;
  const sort   = document.getElementById('sort-select').value;

  let result = ALL.map((d, i) => ({{...d, _origIdx: i}})).filter(d => {{
    if (q && !d.name_ar.includes(q) && !(d.name_en||'').toLowerCase().includes(q)
           && !d.city_ar.includes(q) && !d.region_ar.includes(q)) return false;
    if (region && d.region_ar !== region) return false;
    if (city   && d.city_ar   !== city)   return false;
    if (sub    && d.sub_ar    !== sub)     return false;
    if (accred && d.accred    !== accred)  return false;
    if (activeChips.has('has-img')   && d.img_count < 1) return false;
    if (activeChips.has('has-svc')   && d.svc_count < 1) return false;
    if (activeChips.has('rated')     && d.rcount < 1)    return false;
    if (activeChips.has('has-phone') && !d.phone)        return false;
    // CRM chips
    const crmRec = CRM.get(d.id);
    const crmSt  = crmRec?.status || 'not_called';
    if (activeChips.has('crm-called')     && crmSt === 'not_called') return false;
    if (activeChips.has('crm-interested') && crmSt !== 'interested' && crmSt !== 'closed') return false;
    if (activeChips.has('crm-followup')   && crmSt !== 'follow_up') return false;
    if (activeChips.has('crm-none')       && crmSt !== 'not_called') return false;
    return true;
  }});

  // Sort
  if (sort === 'rating-desc')  result.sort((a,b) => b.rating - a.rating);
  if (sort === 'rating-asc')   result.sort((a,b) => a.rating - b.rating);
  if (sort === 'reviews-desc') result.sort((a,b) => b.rcount - a.rcount);
  if (sort === 'name-asc')     result.sort((a,b) => a.name_ar.localeCompare(b.name_ar, 'ar'));
  if (sort === 'price-asc')    result.sort((a,b) => (a.min_price||99999) - (b.min_price||99999));
  if (sort === 'price-desc')   result.sort((a,b) => (b.min_price||0) - (a.min_price||0));

  currentData = result;
  renderGrid(result);
  document.getElementById('shown-count').textContent = result.length;
  document.getElementById('result-pill').textContent = result.length + ' نتيجة';
}}

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

// ── Modal data cache ──
let MODAL_DATA = null;
async function loadModalData() {{
  if (MODAL_DATA) return MODAL_DATA;
  const r = await fetch('data/modal.json');
  MODAL_DATA = await r.json();
  return MODAL_DATA;
}}

// ── Modal ──
async function openModal(idx) {{
  const card = ALL[idx];
  if (!card) return;

  // Show spinner immediately
  document.getElementById('modal-content').innerHTML =
    `<div style="text-align:center;padding:4rem;color:var(--text2)">⏳ جاري التحميل...</div>`;
  document.getElementById('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';

  const allModal = await loadModalData();
  const d = allModal[card.id];
  if (!d) return;

  let html = d.gal_html;
  html += `<div class="modal-body">`;

  // Header
  html += `<div class="modal-header">
    <div class="modal-name">${{esc(d.name_ar)}}</div>
    ${{d.name_en ? `<div class="modal-name-en">${{esc(d.name_en)}}</div>` : ''}}
    <div class="modal-badges">
      <span class="badge ${{d.accred_cls}}">${{d.accred_label}}</span>
      ${{d.sub_ar  ? `<span class="badge badge-blue">${{d.sub_ar}}</span>` : ''}}
      ${{d.btype   ? `<span class="badge badge-gray">${{d.btype}}</span>` : ''}}
      ${{d.created ? `<span class="badge badge-purple">تأسس ${{d.created}}</span>` : ''}}
    </div>
    ${{d.rcount > 0 ? `<div class="modal-rating">${{starsHtml(d.rating, d.rcount)}}</div>` : ''}}
  </div>`;

  // Contact
  const btns = [];
  if (d.phone)      btns.push(`<a href="tel:${{d.phone}}" class="contact-btn phone">📞 ${{esc(d.phone)}}</a>`);
  if (d.email)      btns.push(`<a href="mailto:${{d.email}}" class="contact-btn email">✉️ ${{esc(d.email)}}</a>`);
  if (d.maps_url)   btns.push(`<a href="${{d.maps_url}}" target="_blank" class="contact-btn maps">📍 خريطة</a>`);
  if (d.branch_url) btns.push(`<a href="${{d.branch_url}}" target="_blank" class="contact-btn web">🔗 صفحة المركز</a>`);
  if (d.phone)      btns.push(`<button class="contact-btn copy" onclick="copyText('${{d.phone}}')">📋 نسخ الرقم</button>`);
  if (btns.length) html += `<div><div class="section-title">التواصل</div><div class="contact-grid">${{btns.join('')}}</div></div>`;

  // Address + map
  const addrRows = [];
  if (d.region_ar) addrRows.push(infoRow('المنطقة', d.region_ar));
  if (d.city_ar)   addrRows.push(infoRow('المدينة', d.city_ar));
  if (d.street_ar) addrRows.push(infoRow('الشارع', d.street_ar));
  if (d.zip_code)  addrRows.push(infoRow('الرمز البريدي', d.zip_code));
  if (addrRows.length) {{
    html += `<div><div class="section-title">الموقع</div><div class="info-grid">${{addrRows.join('')}}</div>`;
    if (d.lat && d.lng && d.lat !== 'None' && d.lng !== 'None') {{
      html += `<div class="map-embed" style="margin-top:.85rem">
        <iframe loading="lazy" src="https://maps.google.com/maps?q=${{d.lat}},${{d.lng}}&z=15&output=embed&hl=ar" allowfullscreen></iframe>
      </div>`;
    }}
    html += `</div>`;
  }}

  // Legal
  const legalRows = [...(d.lic_rows||[]).map(r =>
    infoRow(r.label, r.val, r.sub||'')
  )];
  if (d.cr_no) legalRows.push(infoRow('السجل التجاري', d.cr_no, d.cr_exp ? `تنتهي ${{d.cr_exp}}` : ''));
  if (legalRows.length) html += `<div><div class="section-title">البيانات الرسمية</div><div class="info-grid">${{legalRows.join('')}}</div></div>`;

  // Services
  if (d.svc_html) html += `<div><div class="section-title">الخدمات والأسعار</div>${{d.svc_html}}</div>`;

  // Description
  if (d.desc && d.desc.trim()) html += `<div><div class="section-title">عن المركز</div><p class="desc-text">${{esc(d.desc)}}</p></div>`;

  // CRM Panel
  html += `<div><div class="section-title">📋 سجل المبيعات والمكالمات</div>${{renderCRMPanel(card.id)}}</div>`;

  html += `</div>`;

  document.getElementById('modal-content').innerHTML = html;

  // Thumb click → hero
  document.querySelectorAll('.thumb-strip img').forEach(img => {{
    img.addEventListener('click', () => {{
      document.querySelectorAll('.thumb-strip img').forEach(i => i.classList.remove('active'));
      img.classList.add('active');
    }});
  }});

  // Hero click → lightbox
  const hero = document.getElementById('modal-hero');
  if (hero) hero.addEventListener('click', () => openLightbox(hero.src));
}}

function closeModal() {{
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
}}
function closeModalOnBg(e) {{
  if (e.target === document.getElementById('modal-overlay')) closeModal();
}}
document.addEventListener('keydown', e => {{ if (e.key === 'Escape') {{ closeModal(); closeLightbox(); }} }});

// ── Lightbox ──
function openLightbox(src) {{
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox').classList.add('open');
}}
function closeLightbox() {{
  document.getElementById('lightbox').classList.remove('open');
}}

// ── Helpers ──
function esc(s) {{
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}
function starsStr(r) {{
  const f = Math.round(r||0);
  return '★'.repeat(f) + '☆'.repeat(5-f);
}}
function starsHtml(r, c) {{
  return `<span class="stars">${{starsStr(r)}}</span><span class="rcount"> ${{c}} تقييم</span>`;
}}
function fmt(n) {{ return Number(n).toLocaleString('ar-SA'); }}
function infoRow(label, val, sub='') {{
  return `<div class="info-row"><div class="info-label">${{label}}</div><div class="info-val">${{esc(val)}}${{sub ? `<div class="info-sub">${{esc(sub)}}</div>` : ''}}</div></div>`;
}}
function copyText(t) {{
  navigator.clipboard.writeText(t).then(() => alert('تم النسخ: ' + t));
}}
function setHero(el) {{
  const hero = document.getElementById('modal-hero');
  if (hero) {{ hero.src = el.src; hero.style.display=''; }}
}}

// ── CSV Export ──
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
  const csv = rows.map(r => r.map(c => `"${{String(c||'').replace(/"/g,'""')}}"`).join(',')).join('\\n');
  const blob = new Blob(['\\ufeff'+csv], {{type:'text/csv;charset=utf-8'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'qurrah-branches.csv';
  a.click();
}}

// ── Initial render (FIRST — activeChips/all consts must be declared before this) ──
onRegionChange(); // populates city dropdown then calls applyFilter()

// ── Charts (wrapped so a CDN failure doesn't block cards) ──
try {{
const chartOpts = (horizontal=false) => ({{
  responsive:true, maintainAspectRatio:false,
  plugins:{{ legend:{{display:false}}, tooltip:{{rtl:true, bodyFont:{{family:'IBM Plex Sans Arabic'}} }} }},
  indexAxis: horizontal ? 'y' : 'x',
  scales:{{
    x:{{ grid:{{color:'rgba(255,255,255,.05)'}}, ticks:{{color:'#50507a', font:{{size:10}} }} }},
    y:{{ grid:{{color:'rgba(255,255,255,.05)'}}, ticks:{{color:'#50507a', font:{{size:10}} }} }},
  }}
}});
const GRAD_PURPLE = ctx => {{
  const g = ctx.chart.ctx.createLinearGradient(0,0,0,200);
  g.addColorStop(0,'rgba(124,111,255,.8)'); g.addColorStop(1,'rgba(79,195,247,.5)'); return g;
}};
const GRAD_TEAL = ctx => {{
  const g = ctx.chart.ctx.createLinearGradient(0,0,0,200);
  g.addColorStop(0,'rgba(52,211,153,.8)'); g.addColorStop(1,'rgba(79,195,247,.4)'); return g;
}};
new Chart('chart-regions', {{
  type:'bar', data:{{
    labels:{chart_regions_labels},
    datasets:[{{ data:{chart_regions_data}, backgroundColor:GRAD_PURPLE, borderRadius:6, borderSkipped:false }}]
  }}, options:chartOpts()
}});
new Chart('chart-types', {{
  type:'doughnut', data:{{
    labels:{chart_sub_labels},
    datasets:[{{ data:{chart_sub_data},
      backgroundColor:['rgba(124,111,255,.7)','rgba(79,195,247,.7)','rgba(52,211,153,.7)','rgba(251,191,36,.7)','rgba(248,113,113,.7)','rgba(192,132,252,.7)'],
      borderWidth:0, hoverOffset:8
    }}]
  }},
  options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'right', labels:{{color:'#9090bb', font:{{family:'IBM Plex Sans Arabic', size:11}} }} }} }}}}
}});
new Chart('chart-cities', {{
  type:'bar', data:{{
    labels:{chart_city_labels},
    datasets:[{{ data:{chart_city_data}, backgroundColor:GRAD_TEAL, borderRadius:6, borderSkipped:false }}]
  }}, options:{{ ...chartOpts(true), scales:{{ x:{{ grid:{{color:'rgba(255,255,255,.05)'}}, ticks:{{color:'#50507a', font:{{size:10}} }} }}, y:{{ grid:{{color:'rgba(255,255,255,.05)'}}, ticks:{{color:'#50507a', font:{{size:10}} }} }} }} }}
}});
new Chart('chart-years', {{
  type:'line', data:{{
    labels:{chart_year_labels},
    datasets:[{{ data:{chart_year_data},
      borderColor:'rgba(251,191,36,.8)', backgroundColor:'rgba(251,191,36,.08)',
      fill:true, tension:.4, pointBackgroundColor:'rgba(251,191,36,.9)', pointRadius:4
    }}]
  }}, options:chartOpts()
}});
}} catch(e) {{ console.warn('Charts failed:', e); }}
</script>
</body>
</html>"""


def main():
    print(f"Loading {JSON_FILE}...")
    with open(JSON_FILE, encoding="utf-8") as f:
        branches = json.load(f)
    print(f"  {len(branches)} branches loaded")
    print("Building HTML...")
    html = build_html(branches)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Done → {HTML_FILE}")


if __name__ == "__main__":
    main()
