"""
Smart-merge docs/data.json into Firestore.

Instead of blindly overwriting, this merges the two sources so neither
side's good data is lost:
- competitor latest fields: null values filled from the other source,
  then from that competitor's own history
- seo_audit: prefers the version that includes Lighthouse (psi) scores
- keyword_rankings / content_strategy / gsc / seo_health: prefers
  whichever side has non-empty results (newest last_updated wins ties)
The merged result is written to BOTH Firestore and docs/data.json.

Usage:
  python backend/import_to_firestore.py              # FIREBASE_SERVICE_ACCOUNT env var
  python backend/import_to_firestore.py key.json     # service account file
"""
import json
import os
import sys
import tempfile

FIELDS = [
    "open_pagerank", "sitemap_pages", "meta_title", "meta_description",
    "tech_stack", "google_indexed", "facebook_followers",
    "instagram_followers", "x_followers", "linkedin_followers",
    "trends_score", "serp_refreshed",
]


def _pick_section(a, b):
    """Prefer non-empty results; tie → newest last_updated."""
    a, b = a or {}, b or {}
    a_has, b_has = bool(a.get("results")), bool(b.get("results"))
    if a_has and not b_has:
        return a
    if b_has and not a_has:
        return b
    return a if a.get("last_updated", "") >= b.get("last_updated", "") else b


def _pick_audit(a, b):
    """Prefer the audit that has Lighthouse scores."""
    if a and a.get("psi") and any(v is not None for v in a["psi"].values()):
        return a
    if b and b.get("psi") and any(v is not None for v in b["psi"].values()):
        return b
    return a or b


def merge(fs_data, local_data):
    base = fs_data if fs_data else local_data
    other = local_data if fs_data else {}

    other_map = {c["name"]: c for c in other.get("competitors", [])}
    merged_comps = []
    for c in base.get("competitors", []):
        oc = other_map.get(c["name"], {})
        latest = dict(c.get("latest", {}))
        o_latest = oc.get("latest", {})
        history = c.get("history", []) or oc.get("history", [])
        # fill nulls: other source first, then own history
        for f in FIELDS:
            if latest.get(f) is None and o_latest.get(f) is not None:
                latest[f] = o_latest[f]
        for f in FIELDS:
            if latest.get(f) is None:
                for h in reversed(history):
                    if h.get(f) is not None:
                        latest[f] = h[f]
                        break
        latest["seo_audit"] = _pick_audit(latest.get("seo_audit"), o_latest.get("seo_audit"))
        merged_comps.append({**c, "latest": latest, "history": history})

    # competitors only present in the other source
    base_names = {c["name"] for c in merged_comps}
    for name, oc in other_map.items():
        if name not in base_names:
            merged_comps.append(oc)

    # dedupe by domain (a UI-added entry can duplicate a hardcoded one under
    # a different name, e.g. "digitalsignage.com/" vs "Digital Signage") —
    # keep the entry with the longer history
    from urllib.parse import urlparse

    def _domain_key(c):
        try:
            return urlparse(c.get("url", "")).netloc.lower().removeprefix("www.") or None
        except Exception:
            return None

    by_domain = {}
    deduped = []
    for c in merged_comps:
        dom = _domain_key(c)
        if not dom:
            deduped.append(c)
            continue
        if dom not in by_domain:
            by_domain[dom] = c
            deduped.append(c)
        else:
            kept = by_domain[dom]
            if len(c.get("history", [])) > len(kept.get("history", [])):
                deduped[deduped.index(kept)] = c
                by_domain[dom] = c
            print(f"Deduped competitor by domain: dropped one of {kept['name']!r} / {c['name']!r}")
    merged_comps = deduped

    sh_a, sh_b = base.get("seo_health", {}), other.get("seo_health", {})
    seo_health = sh_a if sh_a.get("sites") else sh_b
    if sh_a.get("sites") and sh_b.get("sites") and sh_b.get("last_updated", "") > sh_a.get("last_updated", ""):
        seo_health = sh_b

    ki_a, ki_b = base.get("keyword_intel"), other.get("keyword_intel")
    keyword_intel = ki_a or ki_b
    if ki_a and ki_b and (ki_b.get("generated_at") or "") > (ki_a.get("generated_at") or ""):
        keyword_intel = ki_b

    # keyword_rankings: pick the better section, but union ranking history
    # from both sides so no snapshot is ever lost
    kw = dict(_pick_section(base.get("keyword_rankings"), other.get("keyword_rankings")))
    hist_by_date = {}
    for src in (base.get("keyword_rankings") or {}, other.get("keyword_rankings") or {}):
        for h in src.get("history", []):
            hist_by_date[h.get("date")] = h
    if hist_by_date:
        kw["history"] = sorted(hist_by_date.values(), key=lambda h: h.get("date", ""))[-26:]

    return {
        "last_updated": max(base.get("last_updated") or "", other.get("last_updated") or "") or None,
        "competitors": merged_comps,
        "keyword_rankings": kw,
        "content_strategy": _pick_section(base.get("content_strategy"), other.get("content_strategy")),
        "gsc": _pick_section(base.get("gsc"), other.get("gsc")),
        "seo_health": seo_health,
        "keyword_intel": keyword_intel,
    }


def main():
    import firebase_admin
    from firebase_admin import credentials, firestore

    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if sa_json:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(sa_json)
            sa_path = f.name
    elif len(sys.argv) >= 2:
        sa_path = sys.argv[1]
        if not os.path.exists(sa_path):
            print(f"File not found: {sa_path}")
            sys.exit(1)
    else:
        print("Set FIREBASE_SERVICE_ACCOUNT env var or pass path/to/serviceAccountKey.json")
        sys.exit(1)

    cred = credentials.Certificate(sa_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    data_path = os.path.join(os.path.dirname(__file__), "../docs/data.json")
    with open(data_path, "r", encoding="utf-8") as f:
        local_data = json.load(f)

    snap = db.collection("insight").document("data").get()
    fs_data = snap.to_dict() if snap.exists else None
    print(f"Firestore doc exists: {bool(fs_data)}")

    merged = merge(fs_data, local_data)

    db.collection("insight").document("data").set(merged)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    fb = sum(1 for c in merged["competitors"] if c["latest"].get("facebook_followers") is not None)
    psi = sum(1 for c in merged["competitors"]
              if (c["latest"].get("seo_audit") or {}).get("psi"))
    kw = len(merged.get("keyword_rankings", {}).get("results", []))
    print(f"Merged: {len(merged['competitors'])} competitors | fb: {fb} | psi: {psi} | kw results: {kw}")
    print("Saved to Firestore and data.json")


if __name__ == "__main__":
    main()
