"""
On-demand single-URL check: is this page in Google's index, and what
structured data does it expose?

Indexation is answered two ways, best first:

1. Search Console URL Inspection API — this is the same thing the "網址檢查"
   tool in the GSC UI reports, so it's authoritative rather than inferred.
   It's free (no SerpAPI quota) but only works for URLs that live under a
   property our GSC service account can read, i.e. our own sites.
2. SerpAPI `site:<url>` — only a strong hint (an absent result can also mean
   the operator just didn't match), and it costs monthly quota. Used only as
   a fallback for URLs outside our own properties.

Structured data is read straight from the page HTML. Unlike the weekly audit,
which only keeps @type names, this surfaces the key fields of each JSON-LD
block (headline, datePublished, author, …) so the result is actually
reviewable. When URL Inspection is available its richResultsResult is
included too — that's Google's own view of the markup, which can lag or
disagree with what's currently in the HTML.

Results are appended to the `url_checks` list on the insight/data Firestore
document, newest first, capped at MAX_CHECKS.

Usage:
  CHECK_URL=https://example.com/page python backend/url_check.py
"""
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper_static import OWN_SITES, HEADERS, _get_firestore  # noqa: E402

MAX_CHECKS = 20

# JSON-LD fields worth showing per block. Anything else is summarised as a
# count so a huge @graph doesn't drown the useful parts.
INTERESTING_FIELDS = [
    "headline", "name", "datePublished", "dateModified", "description",
    "author", "publisher", "image", "mainEntityOfPage", "url",
    "applicationCategory", "operatingSystem", "offers", "aggregateRating",
]


def _flatten(value, depth=0):
    """Render a JSON-LD value as a short readable string."""
    if depth > 2:
        return "…"
    if isinstance(value, dict):
        for key in ("name", "@id", "url", "headline"):
            if isinstance(value.get(key), str):
                return value[key]
        return f"{{{len(value)} 個欄位}}"
    if isinstance(value, list):
        if not value:
            return ""
        parts = [_flatten(v, depth + 1) for v in value[:3]]
        extra = f" +{len(value) - 3}" if len(value) > 3 else ""
        return ", ".join(p for p in parts if p) + extra
    text = str(value)
    return text if len(text) <= 300 else text[:300] + "…"


def _summarise_block(item):
    """Turn one JSON-LD object into {type, fields:{...}}."""
    t = item.get("@type")
    if isinstance(t, list):
        type_name = " / ".join(str(x) for x in t)
    else:
        type_name = str(t) if t else "(未指定 @type)"
    fields = {}
    for key in INTERESTING_FIELDS:
        if key in item:
            rendered = _flatten(item[key])
            if rendered:
                fields[key] = rendered
    return {"type": type_name, "fields": fields}


def extract_page_signals(url):
    """Fetch the page and pull out JSON-LD blocks + indexability meta tags."""
    from bs4 import BeautifulSoup

    out = {
        "fetched": False, "status": None, "title": "", "meta_description": "",
        "meta_robots": "", "canonical": "", "jsonld": [], "schema_types": [],
        "microdata_types": [], "error": "",
    }
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
    except Exception as e:
        out["error"] = f"無法連線：{e}"
        return out

    out["status"] = resp.status_code
    if resp.status_code >= 400:
        out["error"] = f"頁面回應 HTTP {resp.status_code}"
        return out
    out["fetched"] = True

    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.find("title")
    out["title"] = title.text.strip() if title else ""
    desc = soup.find("meta", attrs={"name": "description"})
    out["meta_description"] = (desc.get("content") or "").strip() if desc else ""
    robots = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    out["meta_robots"] = (robots.get("content") or "").strip() if robots else ""
    canonical = soup.find("link", rel="canonical")
    out["canonical"] = (canonical.get("href") or "").strip() if canonical else ""

    types = set()
    blocks = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            blocks.append({"type": "(JSON 解析失敗)", "fields": {}})
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            graph = item.get("@graph")
            targets = graph if isinstance(graph, list) else [item]
            for node in targets:
                if not isinstance(node, dict):
                    continue
                block = _summarise_block(node)
                blocks.append(block)
                for part in block["type"].split(" / "):
                    if part and not part.startswith("("):
                        types.add(part)

    out["jsonld"] = blocks
    out["schema_types"] = sorted(types)
    # Legacy microdata/RDFa still counts as structured data to Google
    out["microdata_types"] = sorted({
        str(el.get("itemtype", "")).rsplit("/", 1)[-1]
        for el in soup.find_all(attrs={"itemtype": True})
        if el.get("itemtype")
    })
    return out


def _gsc_property_for(url):
    """The OWN_SITES property this URL belongs to, if any."""
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for site in OWN_SITES:
        if urlparse(site["url"]).netloc.lower().removeprefix("www.") == host:
            return site["url"].rstrip("/") + "/"
    return None


def inspect_via_gsc(url):
    """Authoritative index status via the Search Console URL Inspection API.

    Returns None when the URL isn't under one of our properties or the API
    isn't configured — the caller then falls back to the SerpAPI hint.
    """
    site_url = _gsc_property_for(url)
    if not site_url:
        return None
    sa_json = os.environ.get("GSC_SERVICE_ACCOUNT")
    if not sa_json:
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(sa_json)
            sa_path = f.name
        creds = service_account.Credentials.from_service_account_file(
            sa_path, scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        service = build("searchconsole", "v1", credentials=creds)
        resp = service.urlInspection().index().inspect(body={
            "inspectionUrl": url,
            "siteUrl": site_url,
            "languageCode": "zh-TW",
        }).execute()
    except Exception as e:
        print(f"  URL Inspection failed: {e}")
        return {"source": "gsc", "error": str(e)}

    result = resp.get("inspectionResult", {}) or {}
    idx = result.get("indexStatusResult", {}) or {}
    rich = result.get("richResultsResult", {}) or {}

    detected = []
    for item in rich.get("detectedItems", []) or []:
        detected.append({
            "type": item.get("richResultType", "(未命名)"),
            "count": len(item.get("items", []) or []),
        })

    return {
        "source": "gsc",
        "verdict": idx.get("verdict", ""),            # PASS / NEUTRAL / FAIL
        "coverage_state": idx.get("coverageState", ""),
        "robots_state": idx.get("robotsTxtState", ""),
        "indexing_state": idx.get("indexingState", ""),
        "last_crawl": idx.get("lastCrawlTime", ""),
        "page_fetch": idx.get("pageFetchState", ""),
        "google_canonical": idx.get("googleCanonical", ""),
        "user_canonical": idx.get("userCanonical", ""),
        "sitemaps": idx.get("sitemap", []) or [],
        "crawled_as": idx.get("crawledAs", ""),
        "rich_verdict": rich.get("verdict", ""),
        "rich_items": detected,
        "inspection_link": result.get("inspectionResultLink", ""),
    }


def check_indexed_via_serp(url):
    """Fallback hint for URLs outside our GSC properties. Costs 1 search."""
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        return {"source": "serpapi", "error": "SERPAPI_KEY 未設定，無法查詢站外網址"}
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={"engine": "google", "q": f"site:{url}", "num": 5, "api_key": api_key},
            timeout=30,
        )
        data = resp.json()
        if data.get("error"):
            return {"source": "serpapi", "error": data["error"]}
        results = data.get("organic_results", []) or []
        target = url.rstrip("/")
        exact = any((r.get("link") or "").rstrip("/") == target for r in results)
        return {
            "source": "serpapi",
            "found": bool(results),
            "exact_match": exact,
            "result_count": len(results),
            "top_links": [r.get("link") for r in results[:3] if r.get("link")],
        }
    except Exception as e:
        return {"source": "serpapi", "error": str(e)}


def check_url(url):
    print(f"Checking {url}")
    page = extract_page_signals(url)
    print(f"  page fetched={page['fetched']} schema={page['schema_types']}")

    index = inspect_via_gsc(url)
    if index is None:
        print("  Not one of our GSC properties — falling back to SerpAPI hint")
        index = check_indexed_via_serp(url)
    else:
        print(f"  GSC verdict={index.get('verdict')} coverage={index.get('coverage_state')}")

    return {
        "url": url,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "index": index,
        "page": page,
    }


def save_check(result):
    db = _get_firestore()
    if not db:
        print("Firestore unavailable — printing result only")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    ref = db.collection("insight").document("data")
    snap = ref.get()
    existing = snap.to_dict() if snap.exists else {}
    checks = [c for c in (existing.get("url_checks") or []) if c.get("url") != result["url"]]
    checks.insert(0, result)
    ref.update({"url_checks": checks[:MAX_CHECKS]})
    print(f"Saved. url_checks now holds {min(len(checks), MAX_CHECKS)} entries.")


def main():
    url = (os.environ.get("CHECK_URL") or (sys.argv[1] if len(sys.argv) > 1 else "")).strip()
    if not url:
        print("Set CHECK_URL or pass the URL as an argument")
        sys.exit(1)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    save_check(check_url(url))


if __name__ == "__main__":
    main()
