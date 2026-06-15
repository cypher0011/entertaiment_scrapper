#!/usr/bin/env python3
"""
Qurrah branches scraper — full data edition.
Fetches: list → detail → services → images → center
Outputs: data/branches.json + index.html
Usage:
  python3 scraper.py page0   # test with 9 branches
  python3 scraper.py full    # all 1500+ branches
"""

import json
import time
import os
import sys
import urllib.request
from datetime import datetime

BASE_LIST    = "https://api.qurrah.sa/api/v1/branches/?limit=9&offset={offset}"
BASE_DETAIL  = "https://api.qurrah.sa/api/v1/branches/{id}/"
BASE_SERVICES= "https://api.qurrah.sa/api/v1/branches/{id}/services/"
BASE_IMAGES  = "https://api.qurrah.sa/api/v1/branches/{id}/images/"
BASE_CENTER  = "https://api.qurrah.sa/api/v1/centers/{cid}/"
PAGE_SIZE    = 9
OUTPUT_DIR   = "data"
JSON_FILE    = os.path.join(OUTPUT_DIR, "branches.json")
HTML_FILE    = "index.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; QurrahScraper/1.0)",
    "Accept": "application/json",
}


def fetch_json(url: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"  [WARN] attempt {attempt+1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return {}


def fetch_list_page(offset: int):
    resp = fetch_json(BASE_LIST.format(offset=offset))
    data = resp.get("payload", {}).get("data", [])
    total = resp.get("payload", {}).get("count", 0)
    return data, total


def enrich_branch(b: dict) -> dict:
    bid = b["id"]
    cid = b.get("center_id", "")

    # 1. Detail
    det = fetch_json(BASE_DETAIL.format(id=bid)).get("payload", {}).get("data", {})
    merged = {**b, **det}

    # 2. Services
    svc_resp = fetch_json(BASE_SERVICES.format(id=bid)).get("payload", {}).get("data", [])
    merged["services"] = svc_resp

    # 3. Images
    img_resp = fetch_json(BASE_IMAGES.format(id=bid)).get("payload", {}).get("data", [])
    merged["gallery"] = img_resp

    # 4. Center (phone/email of parent org)
    if cid:
        ctr = fetch_json(BASE_CENTER.format(cid=cid)).get("payload", {}).get("data", {})
        merged["center_contact_phone"] = ctr.get("contact_phone_number", "")
        merged["center_contact_email"] = ctr.get("contact_email", "")

    return merged


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "page0"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if mode == "page0":
        print("=== MODE: page0 (offset=0) ===")
        raw_list, total = fetch_list_page(0)
        print(f"  Total in DB: {total}, fetched: {len(raw_list)}")
    else:
        print("=== MODE: full scrape ===")
        _, total = fetch_list_page(0)
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        raw_list = []
        for pg in range(pages):
            offset = pg * PAGE_SIZE
            print(f"  List page {pg+1}/{pages} (offset={offset})")
            items, _ = fetch_list_page(offset)
            raw_list.extend(items)
            time.sleep(0.25)

    print(f"\nEnriching {len(raw_list)} branches (detail + services + images + center)...")
    branches = []
    for i, b in enumerate(raw_list):
        label = b.get("name_ar") or b.get("name_en") or b["id"]
        print(f"  [{i+1}/{len(raw_list)}] {label}")
        enriched = enrich_branch(b)
        branches.append(enriched)
        time.sleep(0.3)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(branches, f, ensure_ascii=False, indent=2)
    print(f"\nSaved → {JSON_FILE}")

    build_html(branches, total, mode)
    print(f"HTML  → {HTML_FILE}")


# ─────────────────────── HTML builder ───────────────────────

ACCRED_AR = {
    "ACCREDITED":      "معتمد",
    "PENDING_APPROVAL": "قيد المراجعة",
    "REJECTED":        "مرفوض",
}
ACCRED_CLASS = {
    "ACCREDITED":      "badge-green",
    "PENDING_APPROVAL": "badge-yellow",
    "REJECTED":        "badge-red",
}
STATUS_AR = {
    "ACCEPTED": "مقبول",
    "PENDING":  "معلق",
    "REJECTED": "مرفوض",
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


def service_cards_html(services: list) -> str:
    if not services:
        return ""
    items = []
    for svc in services:
        st = svc.get("service_type") or {}
        name_ar = st.get("name_ar", "")
        age_from = st.get("age_from", "")
        age_to   = st.get("age_to", "")
        age_str  = f"{age_from} - {age_to} سنوات" if age_from != "" else ""
        wh = svc.get("working_hours") or {}
        hours = f'{wh.get("from_time","")[:5]} - {wh.get("to_time","")[:5]}' if wh else ""
        terms = svc.get("booking_terms") or []
        prices = []
        for t in terms:
            bt = t.get("booking_type") or {}
            price = float(t.get("total_price") or 0)
            bt_ar = bt.get("name_ar", "")
            if price:
                prices.append(f'<span class="price-tag">{price:,.0f} ر.س / {bt_ar}</span>')
        prices_html = " ".join(prices)
        items.append(f"""<div class="svc-card">
          <div class="svc-name">{name_ar}</div>
          {f'<div class="svc-age">👶 {age_str}</div>' if age_str else ""}
          {f'<div class="svc-hours">⏰ {hours}</div>' if hours else ""}
          {f'<div class="svc-prices">{prices_html}</div>' if prices_html else ""}
        </div>""")
    return '<div class="svc-grid">' + "\n".join(items) + "</div>"


def gallery_html(gallery: list, display_img: str) -> str:
    imgs = []
    if display_img:
        imgs.append(display_img)
    for g in gallery:
        url = g.get("file", "")
        if url and url not in imgs:
            imgs.append(url)
    if not imgs:
        return '<div class="no-img-big">لا توجد صور</div>'
    # First image is hero, rest are thumbnails
    hero = imgs[0]
    thumbs = imgs[1:]
    thumbs_html = ""
    if thumbs:
        thumb_items = "".join(
            f'<img src="{u}" loading="lazy" onclick="setHero(this.src)" onerror="this.style.display=\'none\'">'
            for u in thumbs
        )
        thumbs_html = f'<div class="thumb-strip">{thumb_items}</div>'
    return f"""<div class="gallery">
      <div class="hero-wrap">
        <img class="hero-img" src="{hero}" id="hero" onerror="this.style.display=\'none\'">
      </div>
      {thumbs_html}
    </div>"""


def build_card(b: dict) -> str:
    bid      = b.get("id", "")
    name_ar  = b.get("name_ar") or "—"
    name_en  = b.get("name_en") or ""
    desc     = b.get("description") or ""
    if desc == ".":
        desc = ""

    addr    = b.get("address") or {}
    city_ar = addr.get("city_name_ar") or addr.get("city_name_en") or ""
    city_en = addr.get("city_name_en") or ""
    region_ar = addr.get("region_name_ar") or ""
    street_ar = addr.get("street_name_ar") or addr.get("street_name_en") or ""
    zip_code  = addr.get("zip_code") or ""
    lat = addr.get("lat", "")
    lng = addr.get("lng", "")

    rating = b.get("avg_branch_rating", 0)
    rcount = b.get("total_ratings_count", 0)
    accred = b.get("accreditation_status", "")
    status = b.get("status", "")

    phone   = b.get("contact_phone_number") or b.get("center_contact_phone") or ""
    email   = b.get("contact_email") or b.get("center_contact_email") or ""

    # License
    licenses = b.get("branch_license") or []
    lic_items = []
    for lic in licenses:
        if isinstance(lic, dict):
            lic_no  = lic.get("license_number") or b.get("license_number") or ""
            lic_exp = lic.get("license_expiry_date") or b.get("license_expiry_date") or ""
            issuer  = lic.get("license_issuer") or ""
            issuer_ar = LICENSE_ISSUER_AR.get(issuer, issuer)
            lic_stat = lic.get("status") or ""
            if lic_no:
                lic_items.append(f'<div class="info-row"><span class="info-label">رقم الرخصة</span><span class="info-val">{lic_no} {f"<span class=exp-date>(ينتهي {lic_exp})</span>" if lic_exp else ""}</span></div>')
            if issuer_ar:
                lic_items.append(f'<div class="info-row"><span class="info-label">جهة الترخيص</span><span class="info-val">{issuer_ar}</span></div>')

    # CR
    cr = b.get("cr") or {}
    cr_no  = cr.get("number") or b.get("cr_number") or ""
    cr_exp = cr.get("expiry_date") or b.get("cr_expiry_date") or ""

    # Subtype
    sub = b.get("branch_subtype") or {}
    sub_name_ar = ""
    branch_type_ar = ""
    if isinstance(sub, dict):
        sub_name_ar    = sub.get("name_ar") or ""
        bt = sub.get("branch_type") or {}
        branch_type_ar = bt.get("name_ar") or ""

    # Services
    services = b.get("services") or []
    gallery  = b.get("gallery") or []
    disp_img = b.get("branch_display_image") or ""

    maps_url = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else ""
    branch_url = f"https://qurrah.sa/branch/{bid}"

    # badge for accreditation
    accred_label = ACCRED_AR.get(accred, accred)
    accred_cls   = ACCRED_CLASS.get(accred, "badge-gray")

    # pick thumbnail for card grid
    thumb_url = disp_img or (gallery[0].get("file","") if gallery else "")

    # Build services & gallery HTML for modal
    svc_html = service_cards_html(services)
    gal_html = gallery_html(gallery, disp_img)

    # address block
    addr_parts = []
    if region_ar:  addr_parts.append(f'<div class="info-row"><span class="info-label">المنطقة</span><span class="info-val">{region_ar}</span></div>')
    if city_ar:    addr_parts.append(f'<div class="info-row"><span class="info-label">المدينة</span><span class="info-val">{city_ar}</span></div>')
    if street_ar:  addr_parts.append(f'<div class="info-row"><span class="info-label">الشارع</span><span class="info-val">{street_ar}</span></div>')
    if zip_code:   addr_parts.append(f'<div class="info-row"><span class="info-label">الرمز البريدي</span><span class="info-val">{zip_code}</span></div>')
    addr_html = "\n".join(addr_parts)

    # safe escaping for data attributes
    safe_name = name_ar.replace('"', '').replace("'", "")
    safe_city_ar = city_ar.replace('"', '')
    safe_city_en = city_en.replace('"', '')

    # card thumb image
    thumb_html = (
        f'<img src="{thumb_url}" alt="{name_ar}" loading="lazy" onerror="this.parentElement.classList.add(\'no-img\')">'
        if thumb_url else '<div class="no-img-inner">لا توجد صورة</div>'
    )

    return f"""<div class="card"
      data-name="{safe_name} {name_en.lower()}"
      data-city-ar="{safe_city_ar}"
      data-city-en="{safe_city_en}"
      data-accred="{accred}"
      data-id="{bid}"
      onclick="openModal('{bid}')">
  <div class="card-thumb">
    {thumb_html}
    <div class="card-badges">
      <span class="badge {accred_cls}">{accred_label}</span>
      {f'<span class="badge badge-blue">{sub_name_ar}</span>' if sub_name_ar else ""}
    </div>
    {f'<div class="card-rating-overlay">{stars_html(rating, rcount)}</div>' if rcount else ""}
  </div>
  <div class="card-info">
    <h2 class="card-name">{name_ar}</h2>
    {f'<p class="card-name-en">{name_en}</p>' if name_en else ""}
    <div class="card-loc">📍 {city_ar}{f"، {region_ar}" if region_ar and region_ar != city_ar else ""}</div>
    {f'<div class="card-phone">📞 {phone}</div>' if phone else ""}
  </div>

  <!-- Modal data stored as JSON in a script tag -->
  <script type="application/json" id="modal-{bid}">{{
    "id": "{bid}",
    "name_ar": {json.dumps(name_ar)},
    "name_en": {json.dumps(name_en)},
    "desc": {json.dumps(desc)},
    "accred": "{accred}",
    "accred_label": "{accred_label}",
    "accred_cls": "{accred_cls}",
    "sub_name_ar": {json.dumps(sub_name_ar)},
    "branch_type_ar": {json.dumps(branch_type_ar)},
    "phone": {json.dumps(phone)},
    "email": {json.dumps(email)},
    "maps_url": {json.dumps(maps_url)},
    "branch_url": {json.dumps(branch_url)},
    "cr_no": {json.dumps(cr_no)},
    "cr_exp": {json.dumps(cr_exp)},
    "rating": {rating},
    "rcount": {rcount},
    "addr_html": {json.dumps(addr_html)},
    "lic_html": {json.dumps("".join(lic_items))},
    "svc_html": {json.dumps(svc_html)},
    "gal_html": {json.dumps(gal_html)}
  }}</script>
</div>"""


def build_html(branches: list, total: int, mode: str):
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    accredited_count = sum(1 for b in branches if b.get("accreditation_status") == "ACCREDITED")
    cities_ar = sorted(set(
        (b.get("address") or {}).get("city_name_ar", "") or
        (b.get("address") or {}).get("city_name_en", "")
        for b in branches
        if b.get("address")
    ))
    city_opts = "\n".join(
        f'<option value="{c}" data-en="{(b.get("address") or {}).get("city_name_en","")}">{c}</option>'
        for b in branches
        for c in [(b.get("address") or {}).get("city_name_ar", "")]
        if c
    )
    # deduplicate
    seen = set()
    city_opts_dedup = []
    for b in branches:
        addr = b.get("address") or {}
        car = addr.get("city_name_ar") or ""
        cen = addr.get("city_name_en") or ""
        if car and car not in seen:
            seen.add(car)
            city_opts_dedup.append(f'<option value="{car}">{car}</option>')
    city_opts_html = "\n".join(sorted(city_opts_dedup))

    cards_html = "\n".join(build_card(b) for b in branches)

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>دليل مراكز قرة</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg:       #080810;
      --surface:  #111120;
      --surface2: #181828;
      --surface3: #1e1e32;
      --border:   #252540;
      --accent:   #6c63ff;
      --accent2:  #4fc3f7;
      --green:    #00e676;
      --yellow:   #ffca28;
      --red:      #ff5252;
      --text:     #f0f0ff;
      --text2:    #8888aa;
      --text3:    #555570;
      --radius:   16px;
      --radius-sm: 10px;
    }}
    html {{ scroll-behavior: smooth; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'IBM Plex Sans Arabic', 'Segoe UI', system-ui, sans-serif;
      min-height: 100vh;
      overflow-x: hidden;
    }}

    /* ─── HEADER ─── */
    header {{
      position: relative;
      overflow: hidden;
      background: linear-gradient(160deg, #0d0d1f 0%, #0a1628 40%, #111135 100%);
      border-bottom: 1px solid var(--border);
      padding: 3rem 2rem 2.5rem;
      text-align: center;
    }}
    header::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(108,99,255,0.15), transparent);
      pointer-events: none;
    }}
    .header-logo {{
      font-size: 3rem;
      font-weight: 800;
      background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -1px;
      line-height: 1;
    }}
    .header-sub {{
      color: var(--text2);
      margin-top: 0.5rem;
      font-size: 1rem;
      font-weight: 400;
    }}
    .stats-row {{
      display: flex;
      justify-content: center;
      gap: 3rem;
      margin-top: 2rem;
      flex-wrap: wrap;
    }}
    .stat {{
      text-align: center;
      position: relative;
    }}
    .stat-num {{
      font-size: 2.2rem;
      font-weight: 700;
      background: linear-gradient(135deg, #a78bfa, #60a5fa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      line-height: 1;
    }}
    .stat-label {{
      font-size: 0.8rem;
      color: var(--text2);
      margin-top: 4px;
      letter-spacing: 0.5px;
    }}

    /* ─── CONTROLS ─── */
    .controls {{
      position: sticky;
      top: 0;
      z-index: 50;
      background: rgba(8,8,16,0.9);
      backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border);
      padding: 0.9rem 1.5rem;
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      align-items: center;
    }}
    .search-wrap {{
      flex: 1;
      min-width: 180px;
      position: relative;
    }}
    .search-icon {{
      position: absolute;
      right: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text3);
      pointer-events: none;
      font-size: 0.95rem;
    }}
    input[type=search] {{
      width: 100%;
      padding: 0.6rem 2.2rem 0.6rem 0.9rem;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      color: var(--text);
      font-family: inherit;
      font-size: 0.9rem;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }}
    input[type=search]:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(108,99,255,0.15);
    }}
    select {{
      padding: 0.6rem 0.9rem;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      color: var(--text);
      font-family: inherit;
      font-size: 0.88rem;
      outline: none;
      cursor: pointer;
      transition: border-color 0.2s;
    }}
    select:focus {{ border-color: var(--accent); }}
    .result-label {{
      color: var(--text2);
      font-size: 0.85rem;
      white-space: nowrap;
      padding: 0.3rem 0.6rem;
      background: var(--surface3);
      border-radius: 8px;
    }}

    /* ─── GRID ─── */
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1.25rem;
      padding: 1.5rem;
      max-width: 1700px;
      margin: 0 auto;
    }}

    /* ─── CARD ─── */
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      cursor: pointer;
      transition: transform 0.22s ease, border-color 0.22s, box-shadow 0.22s;
      display: flex;
      flex-direction: column;
      position: relative;
    }}
    .card:hover {{
      transform: translateY(-5px);
      border-color: rgba(108,99,255,0.6);
      box-shadow: 0 12px 40px rgba(108,99,255,0.2);
    }}
    .card.hidden {{ display: none; }}

    .card-thumb {{
      position: relative;
      height: 190px;
      background: var(--surface2);
      overflow: hidden;
    }}
    .card-thumb img {{
      width: 100%; height: 100%;
      object-fit: cover;
      transition: transform 0.35s ease;
    }}
    .card:hover .card-thumb img {{ transform: scale(1.06); }}
    .no-img-inner {{
      width: 100%; height: 100%;
      display: flex; align-items: center; justify-content: center;
      color: var(--text3);
      font-size: 0.85rem;
      background: linear-gradient(135deg, #111120, #1a1a30);
    }}

    .card-badges {{
      position: absolute;
      top: 10px;
      right: 10px;
      display: flex;
      gap: 5px;
      flex-wrap: wrap;
    }}
    .card-rating-overlay {{
      position: absolute;
      bottom: 8px;
      right: 8px;
      background: rgba(0,0,0,0.65);
      backdrop-filter: blur(8px);
      border-radius: 20px;
      padding: 3px 10px;
      display: flex;
      align-items: center;
      gap: 5px;
    }}

    .badge {{
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 0.72rem;
      font-weight: 600;
      backdrop-filter: blur(8px);
    }}
    .badge-green  {{ background: rgba(0,230,118,.18);  color: #4ade80; border: 1px solid rgba(0,230,118,.35); }}
    .badge-yellow {{ background: rgba(255,202,40,.18); color: #fbbf24; border: 1px solid rgba(255,202,40,.35); }}
    .badge-red    {{ background: rgba(255,82,82,.18);  color: #f87171; border: 1px solid rgba(255,82,82,.35); }}
    .badge-gray   {{ background: rgba(120,120,180,.18);color: #aaa;    border: 1px solid rgba(120,120,180,.3); }}
    .badge-blue   {{ background: rgba(79,195,247,.18); color: #7dd3fc; border: 1px solid rgba(79,195,247,.35); }}

    .card-info {{
      padding: 1.1rem 1.2rem 1.2rem;
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      flex: 1;
    }}
    .card-name {{
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.35;
      color: var(--text);
    }}
    .card-name-en {{
      font-size: 0.78rem;
      color: var(--text3);
      direction: ltr;
    }}
    .card-loc {{
      font-size: 0.85rem;
      color: var(--text2);
    }}
    .card-phone {{
      font-size: 0.82rem;
      color: var(--accent2);
      direction: ltr;
    }}

    .stars {{ color: #fbbf24; font-size: 0.9rem; letter-spacing: 1px; }}
    .rcount {{ color: var(--text2); font-size: 0.75rem; }}

    /* ─── EMPTY ─── */
    .empty-state {{
      grid-column: 1/-1;
      text-align: center;
      padding: 6rem 2rem;
      color: var(--text2);
    }}
    .empty-state .emoji {{ font-size: 3rem; display: block; margin-bottom: 1rem; }}
    .empty-state h3 {{ font-size: 1.4rem; margin-bottom: 0.5rem; color: var(--text); }}

    /* ─── MODAL ─── */
    .modal-overlay {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.75);
      backdrop-filter: blur(6px);
      z-index: 200;
      align-items: flex-start;
      justify-content: center;
      padding: 1.5rem;
      overflow-y: auto;
    }}
    .modal-overlay.open {{ display: flex; }}
    .modal {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      width: 100%;
      max-width: 820px;
      margin: auto;
      overflow: hidden;
      position: relative;
      animation: slideUp 0.25s ease;
    }}
    @keyframes slideUp {{
      from {{ transform: translateY(30px); opacity: 0; }}
      to   {{ transform: translateY(0);    opacity: 1; }}
    }}
    .modal-close {{
      position: absolute;
      top: 14px;
      left: 14px;
      background: rgba(255,255,255,0.08);
      border: none;
      color: var(--text2);
      font-size: 1.3rem;
      width: 36px; height: 36px;
      border-radius: 50%;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      z-index: 10;
      transition: background 0.2s, color 0.2s;
    }}
    .modal-close:hover {{ background: rgba(255,82,82,0.2); color: #f87171; }}

    /* Gallery inside modal */
    .gallery {{ width: 100%; }}
    .hero-wrap {{
      height: 300px;
      overflow: hidden;
      background: var(--surface2);
    }}
    .hero-img {{
      width: 100%; height: 100%;
      object-fit: cover;
    }}
    .thumb-strip {{
      display: flex;
      gap: 6px;
      padding: 8px;
      overflow-x: auto;
      background: var(--surface2);
    }}
    .thumb-strip img {{
      height: 70px;
      width: 100px;
      object-fit: cover;
      border-radius: 8px;
      cursor: pointer;
      border: 2px solid transparent;
      transition: border-color 0.15s, opacity 0.15s;
      flex-shrink: 0;
    }}
    .thumb-strip img:hover {{ border-color: var(--accent); opacity: 0.85; }}
    .no-img-big {{
      height: 200px;
      display: flex; align-items: center; justify-content: center;
      color: var(--text3);
      background: var(--surface2);
      font-size: 0.9rem;
    }}

    .modal-body {{
      padding: 1.6rem;
      display: flex;
      flex-direction: column;
      gap: 1.6rem;
    }}
    .modal-header {{
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }}
    .modal-title {{
      font-size: 1.5rem;
      font-weight: 700;
      line-height: 1.3;
    }}
    .modal-title-en {{
      font-size: 0.85rem;
      color: var(--text3);
      direction: ltr;
    }}
    .modal-badges {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-top: 0.3rem;
    }}
    .modal-rating {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 0.2rem;
    }}

    .section-label {{
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: var(--accent2);
      margin-bottom: 0.7rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.4rem;
    }}

    /* Info rows */
    .info-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.5rem 1rem;
    }}
    .info-row {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .info-label {{
      font-size: 0.72rem;
      color: var(--text3);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .info-val {{
      font-size: 0.9rem;
      color: var(--text);
    }}
    .exp-date {{ color: var(--text3); font-size: 0.78rem; }}

    /* Contact row */
    .contact-grid {{
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}
    .contact-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 0.55rem 1rem;
      border-radius: 10px;
      font-size: 0.86rem;
      font-weight: 500;
      text-decoration: none;
      border: 1px solid var(--border);
      background: var(--surface2);
      color: var(--text2);
      transition: background 0.2s, border-color 0.2s, color 0.2s;
      font-family: inherit;
      cursor: pointer;
    }}
    .contact-btn:hover {{ background: var(--surface3); border-color: var(--accent2); color: var(--accent2); }}
    .contact-btn.phone {{ border-color: rgba(0,230,118,.3); color: #4ade80; }}
    .contact-btn.email {{ border-color: rgba(79,195,247,.3); color: #7dd3fc; }}
    .contact-btn.maps  {{ border-color: rgba(251,191,36,.3); color: #fbbf24; }}
    .contact-btn.web   {{ border-color: rgba(108,99,255,.3); color: #a78bfa; }}

    /* Services */
    .svc-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 0.75rem;
    }}
    .svc-card {{
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }}
    .svc-name {{ font-weight: 700; font-size: 0.95rem; }}
    .svc-age, .svc-hours {{ font-size: 0.82rem; color: var(--text2); }}
    .svc-prices {{ margin-top: 0.4rem; display: flex; flex-wrap: wrap; gap: 4px; }}
    .price-tag {{
      background: rgba(108,99,255,.2);
      color: #c4b5fd;
      border: 1px solid rgba(108,99,255,.35);
      border-radius: 6px;
      padding: 2px 8px;
      font-size: 0.8rem;
      font-weight: 600;
    }}

    /* Description */
    .desc-text {{
      color: var(--text2);
      font-size: 0.9rem;
      line-height: 1.7;
    }}

    /* Footer */
    footer {{
      text-align: center;
      padding: 2rem;
      color: var(--text3);
      font-size: 0.8rem;
      border-top: 1px solid var(--border);
      margin-top: 3rem;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--accent); }}

    @media (max-width: 600px) {{
      .grid {{ grid-template-columns: 1fr; padding: 1rem; }}
      .stats-row {{ gap: 1.5rem; }}
      .info-grid {{ grid-template-columns: 1fr; }}
      .hero-wrap {{ height: 200px; }}
    }}
  </style>
</head>
<body>

<header>
  <div class="header-logo">دليل مراكز قرة</div>
  <p class="header-sub">مراكز رعاية الأطفال في المملكة العربية السعودية</p>
  <div class="stats-row">
    <div class="stat">
      <div class="stat-num" id="shown-count">{len(branches)}</div>
      <div class="stat-label">معروض</div>
    </div>
    <div class="stat">
      <div class="stat-num">{total}</div>
      <div class="stat-label">إجمالي في قاعدة البيانات</div>
    </div>
    <div class="stat">
      <div class="stat-num">{accredited_count}</div>
      <div class="stat-label">مركز معتمد</div>
    </div>
    <div class="stat">
      <div class="stat-num">{len(cities_ar)}</div>
      <div class="stat-label">مدينة</div>
    </div>
  </div>
</header>

<div class="controls">
  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input type="search" id="search" placeholder="ابحث بالاسم أو المدينة..." autocomplete="off">
  </div>
  <select id="city-filter">
    <option value="">كل المدن</option>
    {city_opts_html}
  </select>
  <select id="accred-filter">
    <option value="">كل الحالات</option>
    <option value="ACCREDITED">معتمد</option>
    <option value="PENDING_APPROVAL">قيد المراجعة</option>
    <option value="REJECTED">مرفوض</option>
  </select>
  <span class="result-label" id="result-count"></span>
</div>

<div class="grid" id="grid">
{cards_html}
  <div class="empty-state hidden" id="empty-state">
    <span class="emoji">🔍</span>
    <h3>لا توجد نتائج</h3>
    <p>جرب تغيير كلمة البحث أو الفلتر</p>
  </div>
</div>

<!-- Modal -->
<div class="modal-overlay" id="modal-overlay" onclick="closeModalOnBg(event)">
  <div class="modal" id="modal-box">
    <button class="modal-close" onclick="closeModal()">✕</button>
    <div id="modal-content"></div>
  </div>
</div>

<footer>
  تم جمع البيانات: {len(branches)} من أصل {total} مركز &nbsp;·&nbsp; {scraped_at} &nbsp;·&nbsp; وضع: {mode}
</footer>

<script>
// ── Filter ──
const cards = Array.from(document.querySelectorAll('.card'));
const shownEl = document.getElementById('shown-count');
const countEl = document.getElementById('result-count');
const emptyEl = document.getElementById('empty-state');

function applyFilter() {{
  const q = document.getElementById('search').value.trim().toLowerCase();
  const city = document.getElementById('city-filter').value;
  const accred = document.getElementById('accred-filter').value;
  let n = 0;
  cards.forEach(c => {{
    const name  = (c.dataset.name || '').toLowerCase();
    const cityAr = c.dataset.cityAr || '';
    const cityEn = (c.dataset.cityEn || '').toLowerCase();
    const ca = c.dataset.accred || '';
    const show =
      (!q || name.includes(q) || cityAr.includes(q) || cityEn.includes(q)) &&
      (!city || cityAr === city) &&
      (!accred || ca === accred);
    c.classList.toggle('hidden', !show);
    if (show) n++;
  }});
  shownEl.textContent = n;
  countEl.textContent = n + ' نتيجة';
  emptyEl.classList.toggle('hidden', n > 0);
}}

document.getElementById('search').addEventListener('input', applyFilter);
document.getElementById('city-filter').addEventListener('change', applyFilter);
document.getElementById('accred-filter').addEventListener('change', applyFilter);
applyFilter();

// ── Modal ──
function openModal(id) {{
  const el = document.getElementById('modal-' + id);
  if (!el) return;
  const d = JSON.parse(el.textContent);
  const ratingHtml = d.rcount
    ? `<div class="modal-rating">${{starsHtml(d.rating, d.rcount)}}</div>`
    : '';

  let sections = '';

  // Gallery
  sections += d.gal_html;

  sections += '<div class="modal-body">';

  // Header
  sections += `<div class="modal-header">
    <div class="modal-title">${{d.name_ar}}</div>
    ${{d.name_en ? `<div class="modal-title-en">${{d.name_en}}</div>` : ''}}
    <div class="modal-badges">
      <span class="badge ${{d.accred_cls}}">${{d.accred_label}}</span>
      ${{d.sub_name_ar ? `<span class="badge badge-blue">${{d.sub_name_ar}}</span>` : ''}}
      ${{d.branch_type_ar ? `<span class="badge badge-gray">${{d.branch_type_ar}}</span>` : ''}}
    </div>
    ${{ratingHtml}}
  </div>`;

  // Contact
  const contacts = [];
  if (d.phone) contacts.push(`<a href="tel:${{d.phone}}" class="contact-btn phone">📞 ${{d.phone}}</a>`);
  if (d.email) contacts.push(`<a href="mailto:${{d.email}}" class="contact-btn email">✉️ ${{d.email}}</a>`);
  if (d.maps_url) contacts.push(`<a href="${{d.maps_url}}" target="_blank" class="contact-btn maps">📍 خريطة</a>`);
  if (d.branch_url) contacts.push(`<a href="${{d.branch_url}}" target="_blank" class="contact-btn web">🔗 صفحة المركز</a>`);
  if (contacts.length) {{
    sections += `<div><div class="section-label">التواصل</div><div class="contact-grid">${{contacts.join('')}}</div></div>`;
  }}

  // Address
  if (d.addr_html) {{
    sections += `<div><div class="section-label">الموقع</div><div class="info-grid">${{d.addr_html}}</div></div>`;
  }}

  // License + CR
  let legal = d.lic_html || '';
  if (d.cr_no) {{
    legal += `<div class="info-row"><span class="info-label">السجل التجاري</span><span class="info-val">${{d.cr_no}} ${{d.cr_exp ? `<span class="exp-date">(ينتهي ${{d.cr_exp}})</span>` : ''}}</span></div>`;
  }}
  if (legal) {{
    sections += `<div><div class="section-label">البيانات الرسمية</div><div class="info-grid">${{legal}}</div></div>`;
  }}

  // Services
  if (d.svc_html) {{
    sections += `<div><div class="section-label">الخدمات</div>${{d.svc_html}}</div>`;
  }}

  // Description
  if (d.desc && d.desc.trim() && d.desc.trim() !== '.') {{
    sections += `<div><div class="section-label">عن المركز</div><p class="desc-text">${{d.desc}}</p></div>`;
  }}

  sections += '</div>';

  document.getElementById('modal-content').innerHTML = sections;
  document.getElementById('modal-overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}}

function closeModal() {{
  document.getElementById('modal-overlay').classList.remove('open');
  document.body.style.overflow = '';
}}

function closeModalOnBg(e) {{
  if (e.target === document.getElementById('modal-overlay')) closeModal();
}}

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeModal(); }});

function starsHtml(avg, count) {{
  const full = Math.round(avg);
  const s = '★'.repeat(full) + '☆'.repeat(5 - full);
  return `<span class="stars">${{s}}</span><span class="rcount"> ${{count}} تقييم</span>`;
}}

function setHero(src) {{
  const h = document.getElementById('hero');
  if (h) h.src = src;
}}
</script>
</body>
</html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_html():
    """Rebuild index.html from existing branches.json without re-scraping."""
    with open(JSON_FILE, encoding="utf-8") as f:
        branches = json.load(f)
    first = fetch_json(BASE_LIST.format(offset=0))
    total = first.get("payload", {}).get("count", 0)
    build_html(branches, total, "full")
    print(f"HTML rebuilt → {HTML_FILE} ({len(branches)} branches)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rebuild":
        rebuild_html()
    else:
        main()
