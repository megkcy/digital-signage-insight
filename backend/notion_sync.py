"""
Sync the competitor roster from the company's Notion Competitors database.

Source of truth: the inline database on the "Competitors" page
(https://cayintech.notion.site/Competitors-d511fc0f3f504da094a23c67a5fe7a0e).
Columns used: Name (title), the unnamed url property, Country (multi_select).

Requires the NOTION_API env var (internal integration secret, and the
integration must be connected to that page in Notion). Any failure returns
None so the scraper keeps its current roster untouched.
"""
import os
from urllib.parse import urlparse, urlunparse

import requests

NOTION_DATABASE_ID = "133d3aba6e02448fb43bbadae99a7bc6"
NOTION_VERSION = "2022-06-28"


def fetch_notion_competitors():
    """Returns [{name, url, country}] from the Notion database, or None."""
    token = os.environ.get("NOTION_API")
    if not token:
        print("  Notion sync skipped: NOTION_API not set")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    rows = []
    cursor = None
    try:
        while True:
            payload = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            resp = requests.post(
                f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
                headers=headers, json=payload, timeout=30,
            )
            if resp.status_code != 200:
                print(f"  Notion query failed: {resp.status_code} {resp.text[:200]}")
                return None
            data = resp.json()
            rows.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
    except Exception as e:
        print(f"  Notion sync error: {e}")
        return None

    return [c for c in (parse_notion_row(r) for r in rows) if c]


def parse_notion_row(row):
    """One Notion page row -> {name, url, country} (or None if unusable)."""
    props = row.get("properties", {})
    name, url = "", ""
    for p in props.values():
        t = p.get("type")
        if t == "title":
            name = "".join(seg.get("plain_text", "") for seg in p.get("title", [])).strip()
        elif t == "url" and p.get("url"):
            url = str(p["url"]).strip()

    countries = []
    cprop = props.get("Country", {})
    if cprop.get("type") == "multi_select":
        countries = [o.get("name", "") for o in cprop.get("multi_select", []) if o.get("name")]

    if not name:
        return None
    if not url:
        print(f"  Notion row skipped (no URL): {name}")
        return None
    if not url.startswith("http"):
        url = "https://" + url
    url = _strip_tracking_params(url)
    return {"name": name, "url": url, "country": ", ".join(countries)}


def _strip_tracking_params(url):
    """Drop the query string and fragment — some Notion rows hold a pasted
    ad-click landing link (?utm_source=...&gclid=...) instead of a clean
    homepage URL, and a 150+ char single-line value blows out the table
    layout (white-space: nowrap has nowhere to break)."""
    try:
        p = urlparse(url)
        return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
    except Exception:
        return url
