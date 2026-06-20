import requests
import time
import json
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from database import get_all_competitors, save_seo_snapshot, save_social_snapshot

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ─── SEO scrapers ─────────────────────────────────────────────────────────────

def get_open_pagerank(domain: str) -> float | None:
    """Free Open PageRank API — no key needed."""
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


def get_meta_info(url: str) -> dict:
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


def get_sitemap_pages(url: str) -> int | None:
    """Count URLs in sitemap.xml."""
    try:
        domain = urlparse(url).scheme + "://" + urlparse(url).netloc
        sitemap_url = urljoin(domain, "/sitemap.xml")
        resp = requests.get(sitemap_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            count = resp.text.count("<loc>")
            if count > 0:
                return count
        # Try sitemap_index
        sitemap_index_url = urljoin(domain, "/sitemap_index.xml")
        resp2 = requests.get(sitemap_index_url, headers=HEADERS, timeout=15)
        if resp2.status_code == 200:
            return resp2.text.count("<loc>")
    except Exception:
        pass
    return None


def detect_tech_stack(url: str) -> str:
    """Detect common CMS/frameworks from response headers and HTML."""
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
            "React": "react" in html and ("__react" in html or "react-dom" in html),
            "Next.js": "__next" in html or "_next/static" in html,
            "Vue.js": "vue.js" in html or "__vue__" in html,
            "Angular": "ng-version" in html or "angular" in headers.get("x-powered-by", ""),
            "Cloudflare": "cloudflare" in headers.get("server", "") or "cf-ray" in headers,
            "AWS": "amazonaws" in html or "aws" in headers.get("server", ""),
            "Nginx": "nginx" in headers.get("server", ""),
            "Apache": "apache" in headers.get("server", ""),
        }
        techs = [k for k, v in checks.items() if v]
    except Exception:
        pass
    return ", ".join(techs) if techs else "Unknown"


# ─── Social scrapers ───────────────────────────────────────────────────────────

def _parse_number(text: str) -> int | None:
    """Parse '1.2K', '3.4M', '12,345' style numbers."""
    if not text:
        return None
    text = text.strip().replace(",", "").replace(" ", "")
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


def scrape_facebook_followers(page_handle: str) -> int | None:
    if not page_handle:
        return None
    try:
        url = f"https://www.facebook.com/{page_handle}"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        html = resp.text

        patterns = [
            r'"follower_count":(\d+)',
            r'([\d,]+)\s+(?:people follow|followers)',
            r'([\d.,]+[KkMm]?)\s+Followers',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return _parse_number(m.group(1))
    except Exception:
        pass
    return None


def scrape_instagram_followers(handle: str) -> int | None:
    if not handle:
        return None
    try:
        url = f"https://www.instagram.com/{handle}/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        m = re.search(r'"edge_followed_by":\{"count":(\d+)\}', resp.text)
        if m:
            return int(m.group(1))
        m2 = re.search(r'"followers":\{"count":(\d+)', resp.text)
        if m2:
            return int(m2.group(1))
    except Exception:
        pass
    return None


def scrape_x_followers(handle: str) -> int | None:
    if not handle:
        return None
    try:
        url = f"https://publish.twitter.com/oembed?url=https://twitter.com/{handle}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            # oEmbed doesn't give follower count; try nitter as fallback
            pass
        # Try nitter (public Twitter front-end)
        nitter_url = f"https://nitter.net/{handle}"
        resp2 = requests.get(nitter_url, headers=HEADERS, timeout=10)
        m = re.search(r'([\d,]+)\s*Followers', resp2.text, re.IGNORECASE)
        if m:
            return _parse_number(m.group(1))
    except Exception:
        pass
    return None


def scrape_linkedin_followers(company_handle: str) -> int | None:
    """LinkedIn heavily blocks scraping; returns None in most cases."""
    return None


# ─── Main runner ──────────────────────────────────────────────────────────────

def scrape_all(delay: float = 2.0):
    competitors = get_all_competitors()
    total = len(competitors)

    for i, comp in enumerate(competitors, 1):
        print(f"[{i}/{total}] Scraping: {comp['name']}")
        domain = urlparse(comp["url"]).netloc.lstrip("www.")

        # SEO
        try:
            pagerank = get_open_pagerank(domain)
            meta = get_meta_info(comp["url"])
            pages = get_sitemap_pages(comp["url"])
            tech = detect_tech_stack(comp["url"])

            seo_data = {
                "open_pagerank": pagerank,
                "sitemap_pages": pages,
                "meta_title": meta["meta_title"],
                "meta_description": meta["meta_description"],
                "tech_stack": tech,
            }
            save_seo_snapshot(comp["id"], seo_data)
            print(f"  SEO OK — PageRank: {pagerank}, Pages: {pages}, Tech: {tech}")
        except Exception as e:
            print(f"  SEO ERROR: {e}")

        time.sleep(delay)

        # Social
        try:
            fb = scrape_facebook_followers(comp.get("facebook_handle", ""))
            ig = scrape_instagram_followers(comp.get("instagram_handle", ""))
            x = scrape_x_followers(comp.get("x_handle", ""))
            li = scrape_linkedin_followers(comp.get("linkedin_handle", ""))

            social_data = {
                "facebook_followers": fb,
                "instagram_followers": ig,
                "x_followers": x,
                "linkedin_followers": li,
            }
            save_social_snapshot(comp["id"], social_data)
            print(f"  Social OK — FB: {fb}, IG: {ig}, X: {x}, LI: {li}")
        except Exception as e:
            print(f"  Social ERROR: {e}")

        time.sleep(delay)

    print("\nDone scraping all competitors.")


if __name__ == "__main__":
    from database import init_db
    init_db()
    scrape_all()
