"""
On-page SEO / AEO / GEO audit — all from public data:
- Fetches the page HTML and inspects title, meta, headings, schema, OG tags…
- Checks robots.txt (incl. AI crawler rules), sitemap.xml, llms.txt
- Optionally fetches Google PageSpeed Insights (Lighthouse) scores
No paid APIs required. PAGESPEED_KEY env var is optional (higher quota).
"""
import json
import os
import re

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

AI_CRAWLERS = ["GPTBot", "ClaudeBot", "Google-Extended", "PerplexityBot", "CCBot"]

QUESTION_HINTS = ["?", "？", "how ", "what ", "why ", "when ", "which ", "如何", "什麼", "为什么", "為什麼", "怎麼", "怎么"]


def _fetch(url, timeout=15):
    try:
        return requests.get(url, headers=HEADERS, timeout=timeout)
    except Exception:
        return None


def collect_signals(url):
    """Fetch a page + robots/sitemap/llms.txt and extract raw audit signals."""
    from urllib.parse import urlparse
    from bs4 import BeautifulSoup

    p = urlparse(url)
    origin = f"{p.scheme}://{p.netloc}"
    s = {"url": url, "fetched": False}

    resp = _fetch(url)
    if resp is None or resp.status_code >= 400:
        return s
    s["fetched"] = True
    s["https"] = url.startswith("https://")

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    title = soup.find("title")
    s["title"] = title.text.strip() if title else ""
    desc = soup.find("meta", attrs={"name": "description"})
    s["meta_description"] = desc.get("content", "").strip() if desc else ""

    s["h1_count"] = len(soup.find_all("h1"))
    subheads = soup.find_all(["h2", "h3"])
    s["h2h3_count"] = len(subheads)
    s["question_headings"] = sum(
        1 for h in subheads
        if any(q in h.get_text().lower() for q in QUESTION_HINTS)
    )

    imgs = soup.find_all("img")
    with_alt = [i for i in imgs if (i.get("alt") or "").strip()]
    s["img_count"] = len(imgs)
    s["alt_coverage"] = round(len(with_alt) / len(imgs) * 100) if imgs else 100

    s["canonical"] = bool(soup.find("link", rel="canonical"))
    s["viewport"] = bool(soup.find("meta", attrs={"name": "viewport"}))
    s["og_tags"] = len(soup.find_all("meta", property=re.compile(r"^og:")))
    social_pat = re.compile(r"facebook\.com|linkedin\.com|instagram\.com|youtube\.com|twitter\.com|x\.com", re.I)
    s["social_links"] = len({a["href"] for a in soup.find_all("a", href=social_pat)})
    s["hreflang_count"] = len(soup.find_all("link", rel="alternate", hreflang=True))
    s["list_table_count"] = len(soup.find_all(["ul", "ol", "table"]))
    s["semantic_tags"] = len(soup.find_all(["article", "section", "nav", "main", "header", "footer"]))
    s["word_count"] = len(text.split())

    # JSON-LD structured data types
    schema_types = set()
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    t = item.get("@type")
                    if isinstance(t, list):
                        schema_types.update(str(x) for x in t)
                    elif t:
                        schema_types.add(str(t))
                    for g in item.get("@graph", []) if isinstance(item.get("@graph"), list) else []:
                        gt = g.get("@type") if isinstance(g, dict) else None
                        if isinstance(gt, list):
                            schema_types.update(str(x) for x in gt)
                        elif gt:
                            schema_types.add(str(gt))
        except Exception:
            continue
    s["schema_types"] = sorted(schema_types)

    # robots.txt — existence + whether AI crawlers are blocked
    robots = _fetch(origin + "/robots.txt", timeout=10)
    s["robots_txt"] = bool(robots is not None and robots.status_code == 200 and robots.text.strip())
    blocked = []
    if s["robots_txt"]:
        rt = robots.text
        for bot in AI_CRAWLERS:
            m = re.search(rf"user-agent:\s*{re.escape(bot)}\s*\n(?:[^\n]*\n)*?\s*disallow:\s*/\s*$", rt, re.IGNORECASE | re.MULTILINE)
            if m:
                blocked.append(bot)
    s["ai_crawlers_blocked"] = blocked

    # sitemap.xml
    sitemap = _fetch(origin + "/sitemap.xml", timeout=10)
    s["sitemap"] = bool(sitemap is not None and sitemap.status_code == 200 and "<" in (sitemap.text or ""))

    # llms.txt (GEO signal)
    llms = _fetch(origin + "/llms.txt", timeout=10)
    s["llms_txt"] = bool(
        llms is not None and llms.status_code == 200
        and llms.text.strip() and "<html" not in llms.text[:500].lower()
    )

    return s


def get_pagespeed(url, strategy="mobile"):
    """Lighthouse scores via Google PageSpeed Insights API (free)."""
    params = {
        "url": url,
        "strategy": strategy,
        "category": ["performance", "seo", "accessibility", "best-practices"],
    }
    key = os.environ.get("PAGESPEED_KEY")
    if key:
        params["key"] = key
    try:
        resp = requests.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params=params,
            timeout=90,
        )
        lh = resp.json().get("lighthouseResult", {})
        cats = lh.get("categories", {})

        def pct(cid):
            score = cats.get(cid, {}).get("score")
            return round(score * 100) if score is not None else None

        result = {
            "performance": pct("performance"),
            "seo": pct("seo"),
            "accessibility": pct("accessibility"),
            "best_practices": pct("best-practices"),
        }

        # Page speed sub-score from the core speed metric audits
        audits = lh.get("audits", {})
        metric_scores = [
            audits.get(a, {}).get("score")
            for a in ["first-contentful-paint", "largest-contentful-paint",
                      "total-blocking-time", "cumulative-layout-shift", "speed-index"]
        ]
        metric_scores = [m for m in metric_scores if m is not None]
        result["speed"] = round(sum(metric_scores) / len(metric_scores) * 100) if metric_scores else None

        return result if any(v is not None for v in result.values()) else None
    except Exception as e:
        print(f"  PageSpeed error for {url}: {e}")
        return None


def _item(label, ok, advice):
    return {"label": label, "pass": bool(ok), "advice": None if ok else advice}


def score_seo(s):
    items = [
        (15, _item("Title 標籤（10–60 字元）", 10 <= len(s.get("title", "")) <= 65,
                   "撰寫 10–60 字元、包含主要關鍵字的頁面標題")),
        (15, _item("Meta description（50–160 字元）", 50 <= len(s.get("meta_description", "")) <= 165,
                   "加入 50–160 字元、能吸引點擊的頁面描述")),
        (10, _item("唯一的 H1 標題", s.get("h1_count") == 1,
                   "每頁應有且僅有一個 H1，包含核心關鍵字")),
        (10, _item("Canonical 標籤", s.get("canonical"),
                   "加入 canonical 連結標籤避免重複內容問題")),
        (10, _item("圖片 alt 覆蓋率 ≥80%", s.get("alt_coverage", 0) >= 80,
                   f"為圖片補上 alt 描述（目前 {s.get('alt_coverage', 0)}%）")),
        (10, _item("結構化資料（Schema）", bool(s.get("schema_types")),
                   "加入 JSON-LD 結構化資料（Organization、Product、FAQ…）")),
        (10, _item("sitemap.xml", s.get("sitemap"),
                   "提供 sitemap.xml 並提交到 Google Search Console")),
        (5, _item("robots.txt", s.get("robots_txt"), "建立 robots.txt 引導搜尋引擎爬取")),
        (5, _item("Open Graph 標籤", s.get("og_tags", 0) >= 3,
                  "加入 og:title / og:description / og:image 提升社群分享外觀")),
        (5, _item("HTTPS", s.get("https"), "全站改用 HTTPS")),
        (5, _item("行動裝置 viewport", s.get("viewport"), "加入 viewport meta 支援行動裝置")),
    ]
    total = sum(w for w, _ in items)
    got = sum(w for w, it in items if it["pass"])
    return {"score": round(got / total * 100), "items": [it for _, it in items]}


def score_aeo(s):
    schema = set(s.get("schema_types", []))
    items = [
        (25, _item("FAQ / HowTo / QA Schema", bool(schema & {"FAQPage", "QAPage", "HowTo"}),
                   "為常見問題頁加入 FAQPage 結構化資料，讓 Google 精選摘要與 AI 直接引用你的答案")),
        (15, _item("問句式標題", s.get("question_headings", 0) >= 1,
                   "在 H2/H3 使用問句（如「什麼是數位看板？」），對應使用者搜尋的問題")),
        (15, _item("內容深度（≥300 字）", s.get("word_count", 0) >= 300,
                   "增加頁面文字內容深度，完整回答一個主題")),
        (10, _item("清單／表格內容", s.get("list_table_count", 0) >= 2,
                   "用條列與表格組織內容，利於精選摘要（Featured Snippet）擷取")),
        (10, _item("Meta description 直接回答", 50 <= len(s.get("meta_description", "")) <= 165,
                   "描述直接回答頁面主題的核心問題")),
        (10, _item("清楚的標題層級", s.get("h2h3_count", 0) >= 2,
                   "用多個 H2/H3 分段，每段回答一個子問題")),
        (10, _item("Article / Breadcrumb Schema", bool(schema & {"Article", "BlogPosting", "NewsArticle", "BreadcrumbList"}),
                   "為文章加上 Article schema、為路徑加上 BreadcrumbList")),
        (5, _item("Organization Schema", "Organization" in schema,
                  "加入 Organization schema 建立品牌實體")),
    ]
    total = sum(w for w, _ in items)
    got = sum(w for w, it in items if it["pass"])
    return {"score": round(got / total * 100), "items": [it for _, it in items]}


def score_geo(s):
    schema = set(s.get("schema_types", []))
    blocked = s.get("ai_crawlers_blocked", [])
    items = [
        (20, _item("AI 爬蟲未被封鎖", not blocked,
                   f"robots.txt 封鎖了 {', '.join(blocked)}，AI 搜尋（ChatGPT/Claude/Perplexity）無法讀取並引用你的內容" if blocked else "")),
        (20, _item("llms.txt", s.get("llms_txt"),
                   "新增 /llms.txt 用精簡文字向 AI 模型介紹網站內容與重點頁面")),
        (15, _item("結構化資料豐富度（≥2 種）", len(schema) >= 2,
                   "增加多種 schema（Organization + Product/FAQ/Article），AI 更容易理解與引用")),
        (15, _item("品牌實體（Organization Schema）", "Organization" in schema,
                   "加入 Organization schema（名稱、logo、社群連結）建立可被 AI 辨識的品牌實體")),
        (10, _item("語意化 HTML", s.get("semantic_tags", 0) >= 3,
                   "使用 article／section／nav 等語意標籤，利於 AI 解析內容結構")),
        (10, _item("內容可讀性（標題+描述）", bool(s.get("title")) and bool(s.get("meta_description")),
                   "完整的標題與描述讓 AI 能正確概括頁面")),
        (10, _item("多語系標記（hreflang）", s.get("hreflang_count", 0) >= 1,
                   "有多語系版本時加上 hreflang，AI 才能引用正確語言的頁面")),
    ]
    total = sum(w for w, _ in items)
    got = sum(w for w, it in items if it["pass"])
    return {"score": round(got / total * 100), "items": [it for _, it in items]}


def compute_subscores(s, psi):
    """Detailed sub-metric scores (0-100) per category, for side-by-side
    comparison tables. All heuristic, from public on-page signals + PSI."""
    psi = psi or {}

    def clamp(v):
        return max(0, min(100, round(v)))

    schema = set(s.get("schema_types", []))
    title_ok = 10 <= len(s.get("title", "")) <= 65
    desc_ok = 50 <= len(s.get("meta_description", "")) <= 165

    seo = {
        "performance": psi.get("performance"),
        "onpage": clamp(25 * title_ok + 25 * desc_ok + 20 * (s.get("h1_count") == 1)
                        + 0.2 * s.get("alt_coverage", 0) + 10 * (s.get("og_tags", 0) >= 3)),
        "technical": clamp(20 * bool(s.get("canonical")) + 20 * bool(s.get("robots_txt"))
                           + 20 * bool(s.get("sitemap")) + 15 * bool(s.get("https"))
                           + 15 * bool(s.get("viewport")) + 10 * (s.get("hreflang_count", 0) > 0)),
        "meta": clamp(40 * title_ok + 40 * desc_ok + 20 * (s.get("og_tags", 0) >= 3)),
        "mobile": clamp(50 * bool(s.get("viewport")) + 0.5 * (psi.get("performance") or 50)),
        "speed": psi.get("speed", psi.get("performance")),
    }

    blocked = len(s.get("ai_crawlers_blocked", []))
    geo = {
        "citable": clamp(20 * title_ok + 20 * desc_ok + 20 * (s.get("word_count", 0) >= 300)
                         + 20 * (s.get("list_table_count", 0) >= 2) + 20 * (s.get("semantic_tags", 0) >= 3)),
        "ai_open": clamp(100 * (len(AI_CRAWLERS) - blocked) / len(AI_CRAWLERS)),
        "schema": clamp(min(4, len(schema)) * 25),
        "eeat": clamp(40 * ("Organization" in schema)
                      + 30 * bool(schema & {"Article", "BlogPosting", "NewsArticle"})
                      + 15 * ("BreadcrumbList" in schema) + 15 * (s.get("og_tags", 0) >= 3)),
        "brand": clamp(40 * ("Organization" in schema) + 30 * (s.get("social_links", 0) >= 2)
                       + 30 * (s.get("hreflang_count", 0) > 0)),
        "platform": clamp(60 * bool(s.get("llms_txt")) + 20 * bool(s.get("sitemap"))
                          + 20 * bool(s.get("robots_txt"))),
    }

    aeo = {
        "answer": clamp(40 * desc_ok + 30 * (s.get("word_count", 0) >= 300)
                        + 30 * (s.get("h2h3_count", 0) >= 2)),
        "faq": 100 if schema & {"FAQPage", "QAPage"} else (40 if s.get("question_headings", 0) > 0 else 0),
        "snippet": clamp(40 * (s.get("list_table_count", 0) >= 2) + 30 * desc_ok
                         + 30 * (s.get("h2h3_count", 0) >= 3)),
        "howto": 100 if "HowTo" in schema else 0,
        "qhead": clamp(s.get("question_headings", 0) * 25),
        "paa": clamp(50 * (s.get("question_headings", 0) > 0)
                     + 30 * bool(schema & {"FAQPage", "QAPage"}) + 20 * (s.get("h2h3_count", 0) >= 2)),
    }

    return {"seo": seo, "geo": geo, "aeo": aeo}


def audit_site(url, with_pagespeed=True):
    """Full audit: signals + SEO/AEO/GEO scores (+ Lighthouse if requested)."""
    signals = collect_signals(url)
    if not signals.get("fetched"):
        return None
    result = {
        "seo": score_seo(signals),
        "aeo": score_aeo(signals),
        "geo": score_geo(signals),
        "schema_types": signals.get("schema_types", []),
        "ai_crawlers_blocked": signals.get("ai_crawlers_blocked", []),
        "llms_txt": signals.get("llms_txt", False),
    }
    if with_pagespeed:
        result["psi"] = get_pagespeed(url)
    result["subs"] = compute_subscores(signals, result.get("psi"))
    return result


def audit_competitor(url):
    """Compact audit for a competitor row (no advice text, smaller payload)."""
    full = audit_site(url, with_pagespeed=True)
    if not full:
        return None
    return {
        "psi": full.get("psi"),
        "seo_score": full["seo"]["score"],
        "aeo_score": full["aeo"]["score"],
        "geo_score": full["geo"]["score"],
        "checks": {it["label"]: it["pass"] for it in full["seo"]["items"]},
        "schema_types": full["schema_types"],
        "subs": full.get("subs"),
    }
