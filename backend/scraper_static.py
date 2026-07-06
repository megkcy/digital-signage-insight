"""
Scraper that outputs to frontend/data.json (for GitHub Pages / static deployment).
Reads existing data.json to preserve history, appends new snapshot, saves back.
"""
import json
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

REFERENCE_KEYWORD = "digital signage"

TRACKED_KEYWORDS = [
    "digital signage",
    "menu board",
    "cloud-based digital signage",
]

OWN_SITES = [
    {"name": "CAYIN Technology", "url": "https://www.cayintech.com"},
    {"name": "GO CAYIN", "url": "https://www.gocayin.com"},
]

DATA_PATH = os.path.join(os.path.dirname(__file__), "../docs/data.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

COMPETITORS = [
    {"name": "Yodeck", "url": "https://yodeck.com", "facebook": "yodeckdigitalsignage", "instagram": "yodeck.digitalsignage", "x": "yodeck", "linkedin": "company/flipnode-llc"},
    {"name": "Qwaiting", "url": "https://qwaiting.com", "facebook": "qwaiting", "instagram": "", "x": "qwaiting", "linkedin": "company/qwaiting"},
    {"name": "Digital Signage", "url": "https://www.digitalsignage.com", "facebook": "", "instagram": "", "x": "", "linkedin": ""},
    {"name": "Look Digital Signage", "url": "https://www.lookdigitalsignage.com", "facebook": "lookdigitalsignage", "instagram": "lookdigitalsignage", "x": "lookdigitalsig", "linkedin": "company/look-digital-signage"},
    {"name": "Nento", "url": "https://nento.com", "facebook": "", "instagram": "", "x": "", "linkedin": "company/nento"},
    {"name": "Hexnode", "url": "https://www.hexnode.com", "facebook": "hexnode", "instagram": "hexnode", "x": "hexnode", "linkedin": "company/hexnode"},
    {"name": "22 Miles", "url": "https://www.22miles.com", "facebook": "22MilesInc", "instagram": "22miles_inc", "x": "22miles", "linkedin": "company/22miles"},
    {"name": "Able Sign", "url": "https://www.ablesign.tv", "facebook": "", "instagram": "", "x": "", "linkedin": ""},
    {"name": "adMooH", "url": "https://site.admooh.com", "facebook": "admooh", "instagram": "", "x": "admooh", "linkedin": "company/admooh"},
    {"name": "AI Screen", "url": "https://www.aiscreen.io", "facebook": "aiscreenio", "instagram": "", "x": "aiscreenio", "linkedin": "company/aiscreen"},
    {"name": "AMERIA", "url": "https://www.ameria.com", "facebook": "ameriaAG", "instagram": "", "x": "ameria_ag", "linkedin": "company/ameria"},
    {"name": "Ascen Star", "url": "https://www.ascenstar.com", "facebook": "", "instagram": "", "x": "", "linkedin": ""},
    {"name": "Aurora Signage", "url": "https://www.aurorasignage.com.au", "facebook": "aurorasignage", "instagram": "", "x": "", "linkedin": "company/aurora-signage"},
    {"name": "AXIOMTEK", "url": "https://www.axiomtek.com", "facebook": "axiomtek", "instagram": "axiomtek", "x": "axiomtek", "linkedin": "company/axiomtek"},
    {"name": "BenQ", "url": "https://www.benq.com", "facebook": "BenQ", "instagram": "benq_global", "x": "benq", "linkedin": "company/benq"},
    {"name": "Bricks", "url": "https://www.bricks.tools", "facebook": "", "instagram": "", "x": "", "linkedin": ""},
    {"name": "BrightSign", "url": "https://www.brightsign.biz", "facebook": "BrightSignLLC", "instagram": "brightsignllc", "x": "brightsignbiz", "linkedin": "company/brightsign"},
    {"name": "Broadsign", "url": "https://broadsign.com", "facebook": "broadsign", "instagram": "broadsign", "x": "broadsign", "linkedin": "company/broadsign"},
    {"name": "ComQi", "url": "https://comqi.com", "facebook": "ComQi", "instagram": "", "x": "comqi", "linkedin": "company/comqi"},
    {"name": "DotSignage", "url": "https://www.dotsignage.com", "facebook": "dotsignage", "instagram": "", "x": "dotsignage", "linkedin": "company/dotsignage"},
    {"name": "DynaScan", "url": "https://www.dynascandisplay.com", "facebook": "DynaScanTechnology", "instagram": "", "x": "dynascandisplay", "linkedin": "company/dynascan-technology"},
    {"name": "edbak", "url": "https://edbak.com", "facebook": "edbak", "instagram": "", "x": "", "linkedin": "company/edbak"},
    {"name": "ETS Media", "url": "https://etsmedia.com.tw", "facebook": "", "instagram": "", "x": "", "linkedin": ""},
    {"name": "FarBar x PAPAGO", "url": "https://www.farbar.ai", "facebook": "", "instagram": "", "x": "", "linkedin": ""},
    {"name": "friendlyway", "url": "https://www.friendlyway.com", "facebook": "friendlyway", "instagram": "friendlyway_official", "x": "friendlyway", "linkedin": "company/friendlyway"},
    {"name": "IAdea", "url": "https://www.iadea.com", "facebook": "IAdea", "instagram": "", "x": "iadeaworld", "linkedin": "company/iadea"},
    {"name": "iiyama", "url": "https://iiyama.com", "facebook": "iiyamaEurope", "instagram": "iiyama_europe", "x": "iiyama", "linkedin": "company/iiyama"},
    {"name": "LG Business", "url": "https://www.lg.com", "facebook": "LGElectronics", "instagram": "lgelectronics", "x": "lgus", "linkedin": "company/lg-electronics"},
    {"name": "Lookr (Kabob)", "url": "https://www.kabob.io", "facebook": "", "instagram": "", "x": "", "linkedin": "company/kabob-digital-signage"},
    {"name": "Mvix Digital Signage", "url": "https://mvixdigitalsignage.com", "facebook": "mvixdigitalsignage", "instagram": "mvixdigitalsignage", "x": "mvixusa", "linkedin": "company/mvix"},
    {"name": "Navori Labs", "url": "https://navori.com", "facebook": "navorilabs", "instagram": "navorilabs", "x": "navorilabs", "linkedin": "company/navori-sa"},
    {"name": "NewSoft (NuSoft)", "url": "https://www.nusoft.com.tw", "facebook": "nusoft.com.tw", "instagram": "", "x": "", "linkedin": "company/nusoft-technology"},
    {"name": "NoviSign", "url": "https://www.novisign.com", "facebook": "novisign", "instagram": "novisign", "x": "novisign", "linkedin": "company/novisign"},
    {"name": "NOW Signage", "url": "https://www.nowsignage.com", "facebook": "nowsignage", "instagram": "nowsignage", "x": "nowsignage", "linkedin": "company/now-signage"},
    {"name": "Omnivex", "url": "https://www.omnivex.com", "facebook": "omnivex", "instagram": "", "x": "omnivex", "linkedin": "company/omnivex"},
    {"name": "OnSign TV", "url": "https://onsign.tv", "facebook": "onsigntv", "instagram": "onsigntv", "x": "onsigntv", "linkedin": "company/onsign-tv"},
    {"name": "OptiSigns", "url": "https://www.optisigns.com", "facebook": "optisigns", "instagram": "optisigns", "x": "optisigns", "linkedin": "company/optisigns"},
    {"name": "Panasonic Connect NA", "url": "https://connect.na.panasonic.com", "facebook": "PanasonicNA", "instagram": "panasonicusa", "x": "panasonicna", "linkedin": "company/panasonic"},
    {"name": "Peerless-AV", "url": "https://eu.peerless-av.com", "facebook": "PeerlessAV", "instagram": "peerlessav", "x": "peerlessav", "linkedin": "company/peerless-av"},
    {"name": "Play Digital Signage", "url": "https://playsignage.com", "facebook": "playsignage", "instagram": "playsignage", "x": "playsignage", "linkedin": "company/play-digital-signage"},
    {"name": "Playengo", "url": "https://www.playengo.com", "facebook": "playengo", "instagram": "", "x": "", "linkedin": "company/playengo"},
    {"name": "Lakioo", "url": "https://lakioo.com", "facebook": "lakioo", "instagram": "", "x": "lakioo", "linkedin": "company/lakioo"},
    {"name": "Poppulo", "url": "https://www.poppulo.com", "facebook": "poppulo", "instagram": "poppulohq", "x": "poppulo", "linkedin": "company/poppulo"},
    {"name": "Poster Booking", "url": "https://posterbooking.com", "facebook": "posterbooking", "instagram": "posterbooking", "x": "posterbooking", "linkedin": "company/posterbooking"},
    {"name": "PosterMyWall", "url": "https://www.postermywall.com", "facebook": "postermywall", "instagram": "postermywall", "x": "postermywall", "linkedin": "company/postermywall"},
    {"name": "PPDS", "url": "https://www.ppds.com", "facebook": "ppds.global", "instagram": "ppds.global", "x": "ppds_global", "linkedin": "company/ppds"},
    {"name": "Radi Cloud", "url": "https://www.radi-cloud.com.tw", "facebook": "", "instagram": "", "x": "", "linkedin": ""},
    {"name": "Rapid Signage", "url": "https://www.rapidsignage.com", "facebook": "rapidsignage", "instagram": "", "x": "", "linkedin": "company/rapid-signage"},
    {"name": "RISE Vision", "url": "https://www.risevision.com", "facebook": "risevision", "instagram": "risevision", "x": "risevision", "linkedin": "company/rise-vision"},
    {"name": "Samsung VXT", "url": "https://vxt.samsung.com", "facebook": "SamsungBusiness", "instagram": "samsungbusiness", "x": "samsungbiz", "linkedin": "company/samsung-electronics"},
    {"name": "Scala", "url": "https://scala.com", "facebook": "scalainc", "instagram": "scala_inc", "x": "scalainc", "linkedin": "company/scala"},
    {"name": "ScreenCloud", "url": "https://screencloud.com", "facebook": "screencloud", "instagram": "screencloud", "x": "screencloud", "linkedin": "company/screencloud"},
    {"name": "Signagelive", "url": "https://signagelive.com", "facebook": "signagelive", "instagram": "signagelive", "x": "signagelive", "linkedin": "company/signagelive"},
]


def _parse_number(text):
    if not text:
        return None
    text = str(text).strip().replace(",", "").replace(" ", "")
    m = re.match(r"([\d.]+)([KkMmBb]?)", text)
    if not m:
        return None
    num = float(m.group(1))
    suffix = m.group(2).upper()
    if suffix == "K":
        num *= 1_000
    elif suffix == "M":
        num *= 1_000_000
    elif suffix == "B":
        num *= 1_000_000_000
    return int(num)


def get_open_pagerank(domain):
    try:
        resp = requests.get(
            f"https://openpagerank.com/api/v1.0/getPageRank?domains[]={domain}",
            headers={"API-OPR": "free"},
            timeout=10,
        )
        data = resp.json()
        return data["response"][0].get("page_rank_decimal")
    except Exception:
        return None


def get_meta_info(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.find("title")
        desc = soup.find("meta", attrs={"name": "description"})
        return {
            "meta_title": title.text.strip() if title else None,
            "meta_description": desc["content"].strip() if desc and desc.get("content") else None,
        }
    except Exception:
        return {"meta_title": None, "meta_description": None}


def get_sitemap_pages(url):
    try:
        domain = urlparse(url).scheme + "://" + urlparse(url).netloc
        for path in ["/sitemap.xml", "/sitemap_index.xml"]:
            resp = requests.get(urljoin(domain, path), headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                count = resp.text.count("<loc>")
                if count > 0:
                    return count
    except Exception:
        pass
    return None


def detect_tech_stack(url):
    techs = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        html = resp.text.lower()
        headers = {k.lower(): v for k, v in resp.headers.items()}
        checks = {
            "WordPress": "wp-content" in html or "wp-includes" in html,
            "Shopify": "cdn.shopify.com" in html,
            "Wix": "wix.com" in html,
            "Webflow": "webflow.com" in html,
            "HubSpot": "hs-scripts.com" in html or "hubspot" in html,
            "React": "__react" in html or "react-dom" in html,
            "Next.js": "__next" in html or "_next/static" in html,
            "Vue.js": "__vue__" in html,
            "Angular": "ng-version" in html,
            "Cloudflare": "cloudflare" in headers.get("server", "") or "cf-ray" in headers,
            "AWS": "amazonaws" in html,
            "Nginx": "nginx" in headers.get("server", ""),
            "Apache": "apache" in headers.get("server", ""),
        }
        techs = [k for k, v in checks.items() if v]
    except Exception:
        pass
    return ", ".join(techs) if techs else None


def scrape_facebook(handle):
    if not handle:
        return None
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={"engine": "facebook_profile", "profile_id": handle, "api_key": api_key},
            timeout=15,
        )
        data = resp.json()
        followers = data.get("profile_results", {}).get("followers")
        if followers:
            return _parse_number(str(followers))
    except Exception as e:
        print(f"  SerpApi Facebook error for {handle}: {e}")
    return None


def scrape_instagram(handle):
    if not handle:
        return None
    try:
        resp = requests.get(f"https://www.instagram.com/{handle}/", headers=HEADERS, timeout=15)
        for pat in [r'"edge_followed_by":\{"count":(\d+)\}', r'"followers":\{"count":(\d+)']:
            m = re.search(pat, resp.text)
            if m:
                return int(m.group(1))
    except Exception:
        pass
    return None


def scrape_x(handle):
    if not handle:
        return None
    instances = [
        "https://xcancel.com",
        "https://nitter.privacyredirect.com",
        "https://nitter.poast.org",
        "https://nitter.tiekoetter.com",
        "https://nitter.catsarch.com",
    ]
    for base in instances:
        try:
            resp = requests.get(f"{base}/{handle}", headers=HEADERS, timeout=10)
            m = re.search(r'([\d,]+)\s*Followers', resp.text, re.IGNORECASE)
            if m:
                return _parse_number(m.group(1))
        except Exception:
            continue
    return None


def scrape_linkedin_bulk(competitors):
    """Fetch LinkedIn follower counts for all competitors via Bright Data dataset API."""
    api_key = os.environ.get("BRIGHTDATA_KEY")
    if not api_key:
        print("  LinkedIn skipped: BRIGHTDATA_KEY not set")
        return {}

    # Build URL list for companies that have a linkedin handle
    targets = []
    handle_map = {}  # url -> competitor name
    for c in competitors:
        handle = c.get("linkedin", "")
        if not handle:
            continue
        slug = handle.replace("company/", "").strip("/")
        url = f"https://www.linkedin.com/company/{slug}/"
        targets.append({"url": url})
        handle_map[url] = c["name"]

    if not targets:
        return {}

    try:
        # Trigger snapshot
        trigger_resp = requests.post(
            "https://api.brightdata.com/datasets/v3/trigger",
            params={"dataset_id": "gd_l1vikfnt1wgvvqz95w", "format": "json"},
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=targets,
            timeout=30,
        )
        snapshot_id = trigger_resp.json().get("snapshot_id")
        if not snapshot_id:
            print(f"  LinkedIn trigger failed: {trigger_resp.text}")
            return {}
        print(f"  LinkedIn snapshot triggered: {snapshot_id}")

        # Poll for results (max 10 minutes)
        for attempt in range(20):
            time.sleep(30)
            status_resp = requests.get(
                f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                params={"format": "json"},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30,
            )
            if status_resp.status_code == 200:
                rows = status_resp.json()
                result = {}
                for row in rows:
                    row_url = row.get("url", "").rstrip("/") + "/"
                    name = handle_map.get(row_url)
                    if name and row.get("followers"):
                        result[name] = _parse_number(str(row["followers"]))
                print(f"  LinkedIn: got {len(result)} results")
                return result
            print(f"  LinkedIn polling attempt {attempt+1}/20...")

        print("  LinkedIn: timed out waiting for results")
        return {}
    except Exception as e:
        print(f"  LinkedIn error: {e}")
        return {}


def get_google_trends(name):
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        print(f"  Trends skipped for {name}: SERPAPI_KEY not set")
        return None
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_trends",
                "q": name,
                "date": "today 12-w",
                "api_key": api_key,
            },
            timeout=15,
        )
        data = resp.json()
        timeline = data.get("interest_over_time", {}).get("timeline_data", [])
        if not timeline:
            return None
        values = [v["value"] for entry in timeline for v in entry.get("values", []) if v.get("query") == name]
        if not values:
            # fallback: take first value series
            values = [v["value"] for entry in timeline for v in entry.get("values", [])]
        avg = int(sum(values) / len(values)) if values else None
        return avg if avg and avg > 0 else None
    except Exception as e:
        print(f"  Trends error for {name}: {e}")
        return None


def scrape_keyword_rankings(competitors):
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        print("  Keyword rankings skipped: SERPAPI_KEY not set")
        return []

    domain_map = {}
    for c in competitors:
        domain = urlparse(c["url"]).netloc.lstrip("www.")
        domain_map[domain] = {"name": c["name"], "is_own": False}
    for s in OWN_SITES:
        domain = urlparse(s["url"]).netloc.lstrip("www.")
        domain_map[domain] = {"name": s["name"], "is_own": True}

    results = []
    for kw in TRACKED_KEYWORDS:
        print(f"  Keyword: '{kw}'")
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google",
                    "q": kw,
                    "num": 20,
                    "api_key": api_key,
                },
                timeout=15,
            )
            data = resp.json()
            organic = data.get("organic_results", [])
            for item in organic:
                item_url = item.get("link", "")
                item_domain = urlparse(item_url).netloc.lstrip("www.")
                matched = None
                for domain, info in domain_map.items():
                    if item_domain == domain or item_domain.endswith("." + domain):
                        matched = info
                        break
                if matched:
                    results.append({
                        "keyword": kw,
                        "rank": item.get("position"),
                        "competitor": matched["name"],
                        "is_own": matched["is_own"],
                        "url": item_url,
                        "title": item.get("title", ""),
                    })
                    tag = "★ 自己" if matched["is_own"] else ""
                    print(f"    #{item.get('position')} {matched['name']} {tag} — {item_url}")
            time.sleep(1)
        except Exception as e:
            print(f"  Keyword ranking error for '{kw}': {e}")
    return results


def fetch_gsc_data():
    sa_json = os.environ.get("GSC_SERVICE_ACCOUNT")
    if not sa_json:
        print("GSC skipped: GSC_SERVICE_ACCOUNT not set")
        return []
    try:
        import tempfile
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(sa_json)
            sa_path = f.name

        creds = service_account.Credentials.from_service_account_file(
            sa_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        service = build("searchconsole", "v1", credentials=creds)

        results = []
        for site in OWN_SITES:
            site_url = site["url"].rstrip("/") + "/"
            print(f"  GSC: {site['name']} ({site_url})")
            try:
                # Top queries — rolling 30-day window (GSC data lags ~2-3 days,
                # so month-to-date returns nothing at the start of a month)
                body = {
                    "startDate": (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "endDate": datetime.utcnow().strftime("%Y-%m-%d"),
                    "dimensions": ["query"],
                    "rowLimit": 20,
                    "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
                }
                resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
                queries = []
                for row in resp.get("rows", []):
                    queries.append({
                        "query": row["keys"][0],
                        "clicks": int(row.get("clicks", 0)),
                        "impressions": int(row.get("impressions", 0)),
                        "ctr": round(row.get("ctr", 0) * 100, 1),
                        "position": round(row.get("position", 0), 1),
                    })

                # Top countries
                body_country = {
                    "startDate": (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"),
                    "endDate": datetime.utcnow().strftime("%Y-%m-%d"),
                    "dimensions": ["country"],
                    "rowLimit": 10,
                    "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
                }
                resp_c = service.searchanalytics().query(siteUrl=site_url, body=body_country).execute()
                countries = []
                for row in resp_c.get("rows", []):
                    countries.append({
                        "country": row["keys"][0].upper(),
                        "clicks": int(row.get("clicks", 0)),
                        "impressions": int(row.get("impressions", 0)),
                        "ctr": round(row.get("ctr", 0) * 100, 1),
                        "position": round(row.get("position", 0), 1),
                    })

                results.append({
                    "site": site["name"],
                    "site_url": site["url"],
                    "queries": queries,
                    "countries": countries,
                })
                print(f"    {len(queries)} queries, {len(countries)} countries fetched")
            except Exception as e:
                print(f"  GSC error for {site['name']}: {e}")
        return results
    except Exception as e:
        print(f"GSC unavailable: {e}")
        return []


def scrape_google_indexed_count(domain):
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={"engine": "google", "q": f"site:{domain}", "num": 1, "api_key": api_key},
            timeout=15,
        )
        data = resp.json()
        raw = data.get("search_information", {}).get("total_results")
        if raw is not None:
            return int(str(raw).replace(",", "").replace(".", ""))
        return None
    except Exception as e:
        print(f"  Google indexed error for {domain}: {e}")
        return None


def scrape_content_pages(domain, keyword, n=5):
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        return []
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={"engine": "google", "q": f"site:{domain} {keyword}", "num": n, "api_key": api_key},
            timeout=15,
        )
        data = resp.json()
        return [
            {
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in data.get("organic_results", [])[:n]
        ]
    except Exception as e:
        print(f"  Content pages error for {domain}/{keyword}: {e}")
        return []


def scrape_all_content_pages(keyword_rankings):
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        print("  Content strategy skipped: SERPAPI_KEY not set")
        return []
    seen = set()
    pairs = []
    for r in keyword_rankings:
        if r.get("is_own"):
            continue
        key = (r["competitor"], r["keyword"])
        if key in seen:
            continue
        seen.add(key)
        try:
            domain = urlparse(r["url"]).netloc.lstrip("www.")
        except Exception:
            continue
        pairs.append((r["competitor"], domain, r["keyword"]))
    results = []
    for competitor, domain, keyword in pairs:
        print(f"  Content strategy: {competitor} × '{keyword}'")
        pages = scrape_content_pages(domain, keyword)
        if pages:
            results.append({
                "keyword": keyword,
                "competitor": competitor,
                "domain": domain,
                "pages": pages,
            })
        time.sleep(1)
    return results


def _get_firestore():
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore as fs
        if not firebase_admin._apps:
            sa = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
            if not sa:
                print("FIREBASE_SERVICE_ACCOUNT env var not set, skipping Firestore")
                return None
            print(f"FIREBASE_SERVICE_ACCOUNT found, length={len(sa)}")
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(sa)
                sa_path = f.name
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
            print("Firebase app initialized")
        return fs.client()
    except Exception as e:
        print(f"Firestore unavailable: {e}")
        return None


def load_existing():
    db = _get_firestore()
    if db:
        try:
            snap = db.collection("insight").document("data").get()
            if snap.exists:
                return snap.to_dict()
        except Exception as e:
            print(f"Firestore read failed: {e}")
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "competitors": []}


def save_data(data):
    # Write to Firestore
    db = _get_firestore()
    if db:
        try:
            db.collection("insight").document("data").set(data)
            print("Saved to Firestore")
        except Exception as e:
            print(f"Firestore write failed: {e}")
    # Also write local data.json as backup
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _same_month(date_str: str, today: str) -> bool:
    """True if date_str falls in the same calendar month as today (YYYY-MM-DD)."""
    return bool(date_str) and date_str[:7] == today[:7]


def _within_days(date_str: str, today: str, days: int) -> bool:
    """True if date_str is within the last `days` days from today."""
    if not date_str:
        return False
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        t = datetime.strptime(today, "%Y-%m-%d")
        return (t - d).days < days
    except Exception:
        return False


def scrape_all(delay=2.0):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    existing = load_existing()

    existing_map = {c["name"]: c for c in existing.get("competitors", [])}

    # Build effective competitor list:
    # - Use Firestore data (UI edits) as source of truth for handles/url
    # - Fall back to hardcoded COMPETITORS for any not yet in Firestore
    # - Dedupe by domain so a UI-added entry can't duplicate a hardcoded one
    #   (e.g. "digitalsignage.com/" vs "Digital Signage")
    def _domain_key(url):
        try:
            return urlparse(url).netloc.lower().removeprefix("www.") or None
        except Exception:
            return None

    hardcoded_names = {c["name"] for c in COMPETITORS}
    effective_competitors = []
    seen_names = set()
    seen_domains = set()
    for c in existing.get("competitors", []):
        dom = _domain_key(c.get("url", ""))
        if dom and dom in seen_domains:
            print(f"  Skipping duplicate competitor (same domain): {c['name']}")
            continue
        # If a UI-added entry shares a domain with a hardcoded competitor of a
        # different name, keep only the hardcoded one (processed below)
        if dom and c["name"] not in hardcoded_names and any(
            _domain_key(h["url"]) == dom for h in COMPETITORS
        ):
            print(f"  Skipping duplicate of hardcoded competitor: {c['name']}")
            continue
        handles = c.get("handles", {})
        effective_competitors.append({
            "name": c["name"],
            "url": c.get("url", ""),
            "facebook": handles.get("facebook", ""),
            "instagram": handles.get("instagram", ""),
            "x": handles.get("x", ""),
            "linkedin": handles.get("linkedin", ""),
        })
        seen_names.add(c["name"])
        if dom:
            seen_domains.add(dom)
    for c in COMPETITORS:
        dom = _domain_key(c["url"])
        if c["name"] not in seen_names and (not dom or dom not in seen_domains):
            effective_competitors.append(c)
            if dom:
                seen_domains.add(dom)

    result_competitors = []
    total = len(effective_competitors)

    def _monthly_done(name):
        """A competitor's monthly refresh only counts if the SerpAPI scrape
        actually succeeded (serp_refreshed stamped in this month). A quota-
        exhausted run leaves the stamp untouched so the next weekly run
        retries instead of caching the failure for a month."""
        pl = existing_map.get(name, {}).get("latest", {})
        return _same_month(pl.get("serp_refreshed", ""), today)

    # LinkedIn bulk fetch — only for competitors that need a monthly refresh
    needs_monthly = [c for c in effective_competitors if not _monthly_done(c["name"])]
    print(f"Fetching LinkedIn followers via Bright Data… ({len(needs_monthly)}/{total} need refresh)")
    linkedin_map = scrape_linkedin_bulk(needs_monthly)

    for i, comp in enumerate(effective_competitors, 1):
        print(f"[{i}/{total}] {comp['name']}")
        domain = urlparse(comp["url"]).netloc.lstrip("www.")

        prev = existing_map.get(comp["name"], {})
        prev_latest = prev.get("latest", {})
        history = prev.get("history", [])
        skip_monthly = _monthly_done(comp["name"])

        # SEO — always weekly (no SerpAPI cost)
        pagerank = get_open_pagerank(domain)
        meta = get_meta_info(comp["url"])
        pages = get_sitemap_pages(comp["url"])
        tech = detect_tech_stack(comp["url"])

        # Google indexed — monthly only
        if skip_monthly:
            google_idx = prev_latest.get("google_indexed")
        else:
            google_idx = scrape_google_indexed_count(domain)
        time.sleep(delay)

        # SEO/AEO/GEO audit + Lighthouse — monthly only (slow but free)
        if skip_monthly:
            seo_audit = prev_latest.get("seo_audit")
        else:
            try:
                from seo_audit import audit_competitor
                seo_audit = audit_competitor(comp["url"])
            except Exception as e:
                print(f"  SEO audit error: {e}")
                seo_audit = None
        if seo_audit is None:
            seo_audit = prev_latest.get("seo_audit")

        # Target keywords from sitemap slugs (free) + Google ad activity
        # (SerpAPI) — monthly only
        if skip_monthly:
            target_kw = prev_latest.get("target_keywords")
            ads_info = prev_latest.get("ads_transparency")
        else:
            try:
                from seo_audit import extract_target_keywords, scrape_ads_transparency
                target_kw = extract_target_keywords(comp["url"])
                ads_info = scrape_ads_transparency(domain)
            except Exception as e:
                print(f"  Target keywords/ads error: {e}")
                target_kw, ads_info = None, None
        if not target_kw:
            target_kw = prev_latest.get("target_keywords")
        if ads_info is None:
            ads_info = prev_latest.get("ads_transparency")

        # Social — monthly only
        if skip_monthly:
            fb = prev_latest.get("facebook_followers")
            ig = prev_latest.get("instagram_followers")
            x = prev_latest.get("x_followers")
            li = prev_latest.get("linkedin_followers")
            trends = prev_latest.get("trends_score")
        else:
            fb = scrape_facebook(comp["facebook"])
            ig = scrape_instagram(comp["instagram"])
            x = scrape_x(comp["x"])
            li = linkedin_map.get(comp["name"])
            trends = get_google_trends(comp["name"])
        time.sleep(delay)

        # Stamp serp_refreshed only when the refresh actually returned data,
        # so a quota-exhausted run gets retried on the next weekly scrape
        if skip_monthly:
            serp_refreshed = prev_latest.get("serp_refreshed", "")
        elif google_idx is not None or fb is not None or trends is not None:
            serp_refreshed = today
        else:
            serp_refreshed = prev_latest.get("serp_refreshed", "")

        # Never overwrite a good value with null (failed/blocked scrape):
        # carry the previous value forward so data survives quota outages
        def _keep(new, field):
            return new if new is not None else prev_latest.get(field)
        google_idx = _keep(google_idx, "google_indexed")
        fb = _keep(fb, "facebook_followers")
        ig = _keep(ig, "instagram_followers")
        x = _keep(x, "x_followers")
        li = _keep(li, "linkedin_followers")
        trends = _keep(trends, "trends_score")
        pagerank = _keep(pagerank, "open_pagerank")
        pages = _keep(pages, "sitemap_pages")
        tech = _keep(tech, "tech_stack")

        snapshot = {
            "date": today,
            "serp_refreshed": serp_refreshed,
            "seo_audit": seo_audit,
            "target_keywords": target_kw,
            "ads_transparency": ads_info,
            "open_pagerank": pagerank,
            "sitemap_pages": pages,
            "meta_title": meta.get("meta_title"),
            "meta_description": meta.get("meta_description"),
            "tech_stack": tech,
            "google_indexed": google_idx,
            "facebook_followers": fb,
            "instagram_followers": ig,
            "x_followers": x,
            "linkedin_followers": li,
            "trends_score": trends,
        }

        # Keep last 52 weeks of history (large audit/keyword payloads stay in
        # latest only, to keep the Firestore document under its 1 MB limit)
        _latest_only = {"seo_audit", "target_keywords", "ads_transparency"}
        history = [h for h in history if h.get("date") != today]
        history.append({k: v for k, v in snapshot.items() if k not in _latest_only})
        history = history[-52:]

        result_competitors.append({
            "name": comp["name"],
            "url": comp["url"],
            "handles": {
                "facebook": comp["facebook"],
                "instagram": comp["instagram"],
                "x": comp["x"],
                "linkedin": comp["linkedin"],
            },
            "latest": snapshot,
            "history": history,
        })

        tag = "(cached)" if skip_monthly else ""
        print(f"  PR:{pagerank} Pages:{pages} GIdx:{google_idx} LI:{li} Trends:{trends} {tag}")

    # Keyword rankings + content strategy — once per month.
    # An empty result set never counts as a successful run (quota exhaustion
    # returns nothing) — keep the old data and retry on the next weekly scrape.
    existing_kw = existing.get("keyword_rankings", {})
    existing_cs = existing.get("content_strategy", {})
    skip_kw = _same_month(existing_kw.get("last_updated", ""), today) and bool(existing_kw.get("results"))

    print("\nScraping keyword rankings…")
    if skip_kw:
        print(f"  Skipped (refreshed {existing_kw.get('last_updated')} this month)")
        kw_obj = existing_kw
    else:
        results = scrape_keyword_rankings(COMPETITORS)
        if results:
            # Append a compact snapshot to the ranking history so the
            # dashboard can chart rank movement over time
            kw_history = [
                h for h in existing_kw.get("history", []) if h.get("date") != today
            ]
            kw_history.append({
                "date": today,
                "results": [
                    {"keyword": r["keyword"], "rank": r["rank"],
                     "competitor": r["competitor"], "is_own": r.get("is_own", False)}
                    for r in results
                ],
            })
            kw_obj = {
                "last_updated": today,
                "keywords": TRACKED_KEYWORDS,
                "results": results,
                "history": kw_history[-26:],
            }
        else:
            print("  No results (quota exhausted?) — keeping previous data")
            kw_obj = existing_kw

    print("\nScraping content strategy…")
    if skip_kw and existing_cs.get("results"):
        print("  Skipped (refreshed this month)")
        cs_obj = existing_cs
    else:
        cs_results = scrape_all_content_pages(kw_obj.get("results", []))
        if cs_results:
            cs_obj = {"last_updated": today, "results": cs_results}
        else:
            print("  No results — keeping previous data")
            cs_obj = existing_cs

    print("\nFetching GSC data…")
    gsc_data = fetch_gsc_data()
    if any(r.get("queries") for r in gsc_data):
        gsc_obj = {"last_updated": today, "results": gsc_data}
    else:
        print("  GSC returned no rows — keeping previous data")
        gsc_obj = existing.get("gsc", {})

    # Own-site SEO / AEO / GEO health — weekly (2 sites, free APIs only)
    print("\nAuditing own sites (SEO/AEO/GEO)…")
    existing_health = {
        s.get("site"): s for s in existing.get("seo_health", {}).get("sites", [])
    }
    health_sites = []
    for site in OWN_SITES:
        print(f"  {site['name']}")
        try:
            from seo_audit import audit_site
            audit = audit_site(site["url"])
        except Exception as e:
            print(f"  audit error: {e}")
            audit = None
        if audit is None:
            prev_site = existing_health.get(site["name"])
            if prev_site:
                health_sites.append(prev_site)
            continue
        health_sites.append({"site": site["name"], "url": site["url"], **audit})
    seo_health_obj = (
        {"last_updated": today, "sites": health_sites}
        if health_sites else existing.get("seo_health", {})
    )

    # Manual Keyword Planner cross-analysis (not scraped automatically yet —
    # pending Google Ads API access); carry forward untouched. Firestore is
    # normally the source of truth, but if it hasn't been synced since the
    # last manual update (e.g. the restore workflow wasn't run yet), fall
    # back to whatever is committed in the local data.json so a scrape never
    # wipes it out.
    keyword_intel = existing.get("keyword_intel")
    if not keyword_intel and os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                keyword_intel = json.load(f).get("keyword_intel")
        except Exception:
            pass

    data = {
        "last_updated": today,
        "competitors": result_competitors,
        "keyword_rankings": kw_obj,
        "content_strategy": cs_obj,
        "gsc": gsc_obj,
        "seo_health": seo_health_obj,
        "keyword_intel": keyword_intel,
    }
    save_data(data)
    print(f"\nSaved to {DATA_PATH}")


if __name__ == "__main__":
    scrape_all()
