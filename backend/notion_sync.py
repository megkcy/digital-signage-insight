"""
Sync the competitor roster from the company's Notion Competitors database.

Source of truth: the inline database on the "Competitors" page
(https://cayintech.notion.site/Competitors-d511fc0f3f504da094a23c67a5fe7a0e).
Columns used: Name (title), the unnamed url property, Country (multi_select),
Facebook / Instagram / X / LinkedIn (rich_text).

Requires the NOTION_API env var (internal integration secret, and the
integration must be connected to that page in Notion). Any failure returns
None so the scraper keeps its current roster untouched.

Handles flow both ways: Notion values seed a competitor that doesn't have one
yet, but the dashboard (Firestore) is the one people actually edit, so once a
handle is filled in there it wins and gets pushed back up to Notion by
update_notion_handles() — making Notion a mirror rather than a second place
to maintain by hand. That push only happens when the scraper runs (weekly,
or on demand), never instantly from the browser: the browser can't hold the
NOTION_API secret without exposing it to anyone who views the page source.
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


# Our handle field name -> the Notion rich_text property that holds it
HANDLE_PROPS = {
    "facebook": "Facebook", "instagram": "Instagram", "x": "X", "linkedin": "LinkedIn",
}


def parse_notion_row(row):
    """One Notion page row -> {id, name, url, country, facebook, instagram,
    x, linkedin} (or None if unusable)."""
    props = row.get("properties", {})
    name, url = "", ""
    for p in props.values():
        t = p.get("type")
        if t == "title":
            name = "".join(seg.get("plain_text", "") for seg in p.get("title", [])).strip()
        elif t == "url" and p.get("url"):
            url = str(p["url"]).strip()

    def rich_text(key):
        p = props.get(key, {})
        if p.get("type") != "rich_text":
            return ""
        return "".join(seg.get("plain_text", "") for seg in p.get("rich_text", [])).strip()

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
    return {
        "id": row.get("id"),
        "name": name, "url": url, "country": ", ".join(countries),
        **{field: rich_text(prop) for field, prop in HANDLE_PROPS.items()},
    }


def update_notion_handles(page_id, handles):
    """PATCH one Notion page's Facebook/Instagram/X/LinkedIn rich_text
    properties. `handles` is our field-name keyed dict (e.g. {"facebook": ...});
    only non-empty values are pushed, so this never blanks out a Notion cell.
    Returns True on success."""
    token = os.environ.get("NOTION_API")
    if not token:
        return False
    props = {
        HANDLE_PROPS[field]: {"rich_text": [{"text": {"content": value}}]}
        for field, value in handles.items() if value
    }
    if not props:
        return False
    try:
        resp = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            json={"properties": props}, timeout=15,
        )
        if resp.status_code != 200:
            print(f"  Notion handle push failed ({page_id}): {resp.status_code} {resp.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  Notion handle push error ({page_id}): {e}")
        return False


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
