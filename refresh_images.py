#!/usr/bin/env python3
"""
Refresh expired S3 image URLs in branches.json.
Run before build_html.py each session.
Usage: python3 refresh_images.py
"""
import json, time, urllib.request, os

JSON_FILE = "data/branches.json"
BASE_DETAIL  = "https://api.qurrah.sa/api/v1/branches/{id}/"
BASE_IMAGES  = "https://api.qurrah.sa/api/v1/branches/{id}/images/"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def fetch(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print(f"  [warn] {attempt+1}/3 {url[:60]}: {e}")
            if attempt < 2: time.sleep(1.5)
    return {}

with open(JSON_FILE, encoding="utf-8") as f:
    branches = json.load(f)

print(f"Refreshing images for {len(branches)} branches...")
updated = 0
for i, b in enumerate(branches):
    bid = b["id"]
    print(f"\r  [{i+1}/{len(branches)}]", end="", flush=True)

    det = fetch(BASE_DETAIL.format(id=bid)).get("payload", {}).get("data", {})
    new_img = det.get("branch_display_image") or ""
    if new_img:
        b["branch_display_image"] = new_img

    imgs = fetch(BASE_IMAGES.format(id=bid)).get("payload", {}).get("data", [])
    if imgs:
        b["gallery"] = imgs
        updated += 1

    time.sleep(0.2)

print(f"\nUpdated {updated} branches with fresh images.")
with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(branches, f, ensure_ascii=False, indent=2)
print(f"Saved → {JSON_FILE}")
print("Now run: python3 build_html.py")
