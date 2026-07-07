"""
Automated competitor keyword research via the Google Ads API.

Replaces the manual "export N CSVs from Keyword Planner, upload them" flow:
for each competitor domain, calls KeywordPlanIdeaService.GenerateKeywordIdeas
with a url_seed (Google Ads' own "start with a website" feature) and combines
the results into the same keyword_intel structure the dashboard already
renders (gap / top_common / overall_top).

Requires five env vars (see .github/workflows/weekly_scrape.yml):
  GOOGLE_ADS_DEVELOPER_TOKEN
  GOOGLE_ADS_CLIENT_ID
  GOOGLE_ADS_CLIENT_SECRET
  GOOGLE_ADS_REFRESH_TOKEN
  GOOGLE_ADS_LOGIN_CUSTOMER_ID
If any are missing, every function here is a no-op returning None/[] so the
scraper can carry on using whatever keyword_intel it already has.
"""
import os
import re
import time
from datetime import datetime

# Default targeting: English, worldwide-ish major English market (US). The
# dashboard's own competitor tracking is global/English-language, matching
# the manual Keyword Planner exports this replaces.
LANGUAGE_CONSTANT = "languageConstants/1000"     # English
GEO_TARGET_CONSTANTS = ["geoTargetConstants/2840"]  # United States

EXCLUDE_UNLESS_SIGNAGE = [
    "poster", "flyer", "handbill", "canvas", "wallmount", "wall mount",
    "tv mount", "bracket for tv", "television mounting", "tvwallmount",
]
KEEP_HINTS = ["digital", "signage"]


def _get_client():
    required = [
        "GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN",
        "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
    ]
    if not all(os.environ.get(k) for k in required):
        print("  Google Ads API skipped: credentials not fully configured")
        return None
    try:
        from google.ads.googleads.client import GoogleAdsClient
        config = {
            "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
            "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
            "login_customer_id": os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"],
            "use_proto_plus": True,
        }
        return GoogleAdsClient.load_from_dict(config)
    except Exception as e:
        print(f"  Google Ads API client init failed: {e}")
        return None


def _is_off_topic(kw):
    return any(p in kw for p in EXCLUDE_UNLESS_SIGNAGE) and not any(h in kw for h in KEEP_HINTS)


def get_keyword_ideas_for_domain(client, domain):
    """One GenerateKeywordIdeas call seeded from a competitor's website."""
    try:
        service = client.get_service("KeywordPlanIdeaService")
        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]
        request.language = LANGUAGE_CONSTANT
        request.geo_target_constants = GEO_TARGET_CONSTANTS
        request.keyword_plan_network = (
            client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
        )
        request.url_seed.url = domain if domain.startswith("http") else f"https://{domain}"

        response = service.generate_keyword_ideas(request=request)

        results = []
        for idea in response:
            m = idea.keyword_idea_metrics
            vol = m.avg_monthly_searches or 0
            comp_idx = m.competition_index or 0
            low = (m.low_top_of_page_bid_micros or 0) / 1_000_000
            high = (m.high_top_of_page_bid_micros or 0) / 1_000_000
            kw = idea.text.strip().lower()
            if not kw or _is_off_topic(kw):
                continue
            results.append({
                "keyword": kw, "volume": vol,
                "competition": comp_idx, "bid_low": low, "bid_high": high,
            })
        return results
    except Exception as e:
        print(f"  Keyword ideas error for {domain}: {e}")
        return []


def build_keyword_intel(competitor_domains, own_queries, tracked_keywords, delay=1.0):
    """
    competitor_domains: list of (name, domain) tuples
    own_queries: set of lowercased query strings already ranking on own GSC
    tracked_keywords: set of already-tracked keyword strings (excluded from gap)
    Returns a dict matching the keyword_intel schema the dashboard renders,
    or None if the API is unavailable / returned nothing usable.
    """
    client = _get_client()
    if client is None:
        return None

    combined = {}  # keyword -> {vol, seen, comp, low, high}
    domains_with_data = 0
    for name, domain in competitor_domains:
        print(f"  Google Ads keyword ideas: {name} ({domain})")
        ideas = get_keyword_ideas_for_domain(client, domain)
        if ideas:
            domains_with_data += 1
        for r in ideas:
            kw = r["keyword"]
            if kw not in combined:
                combined[kw] = {"vol": r["volume"], "seen": 1,
                                 "comp": r["competition"], "low": r["bid_low"], "high": r["bid_high"]}
            else:
                c = combined[kw]
                c["seen"] += 1
                if r["volume"] > c["vol"]:
                    c["vol"] = r["volume"]
        time.sleep(delay)

    if not combined:
        print("  Google Ads API returned no usable keyword ideas")
        return None

    n_domains = len(competitor_domains)

    def row(kw, c):
        return {"keyword": kw, "volume": c["vol"], "seen": c["seen"],
                "competition": c["comp"], "bid_low": round(c["low"], 2), "bid_high": round(c["high"], 2)}

    gap = [
        row(kw, c) for kw, c in combined.items()
        if kw not in own_queries and kw not in tracked_keywords
        and c["seen"] >= 2 and c["vol"] >= 150
    ]
    gap.sort(key=lambda r: -r["volume"])

    top_common = sorted(combined.items(), key=lambda x: (-x[1]["seen"], -x[1]["vol"]))
    top_common = [row(kw, c) for kw, c in top_common[:50]]

    overall = sorted(combined.items(), key=lambda x: -x[1]["vol"])[:60]
    overall = [row(kw, c) for kw, c in overall]

    return {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        "period": "rolling 12mo (Google Ads)",
        "n_exports": domains_with_data,
        "total_unique": len(combined),
        "own_queries_count": len(own_queries),
        "gap": gap[:120],
        "top_common": top_common,
        "overall_top": overall,
        "source": "google_ads_api",
    }
