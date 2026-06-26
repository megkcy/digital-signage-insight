import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/competitors.db")

COMPETITORS = [
    {"name": "Yodeck", "url": "https://yodeck.com", "facebook": "yodeckdigitalsignage", "instagram": "yodeck.digitalsignage", "x": "yodeck", "linkedin": "company/flipnode-llc"},
    {"name": "Qwaiting", "url": "https://qwaiting.com", "facebook": "qwaiting", "instagram": "", "x": "qwaiting", "linkedin": "company/qwaiting"},
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
    {"name": "Navori Labs", "url": "https://navori.com", "facebook": "navorilabs", "instagram": "navorilabs", "x": "navorilabs", "linkedin": "company/navori-labs"},
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


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            url TEXT,
            facebook_handle TEXT,
            instagram_handle TEXT,
            x_handle TEXT,
            linkedin_handle TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS seo_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER,
            snapshot_date TEXT,
            open_pagerank REAL,
            sitemap_pages INTEGER,
            meta_title TEXT,
            meta_description TEXT,
            tech_stack TEXT,
            FOREIGN KEY (competitor_id) REFERENCES competitors(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS social_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER,
            snapshot_date TEXT,
            facebook_followers INTEGER,
            instagram_followers INTEGER,
            x_followers INTEGER,
            linkedin_followers INTEGER,
            FOREIGN KEY (competitor_id) REFERENCES competitors(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS trends_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER,
            snapshot_date TEXT,
            trend_value REAL,
            FOREIGN KEY (competitor_id) REFERENCES competitors(id)
        )
    """)

    for comp in COMPETITORS:
        c.execute("""
            INSERT OR IGNORE INTO competitors (name, url, facebook_handle, instagram_handle, x_handle, linkedin_handle)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (comp["name"], comp["url"], comp["facebook"], comp["instagram"], comp["x"], comp["linkedin"]))

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def get_all_competitors():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM competitors ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_snapshots():
    conn = get_conn()
    query = """
        SELECT
            c.id, c.name, c.url,
            s.open_pagerank, s.sitemap_pages, s.meta_title, s.tech_stack, s.snapshot_date AS seo_date,
            so.facebook_followers, so.instagram_followers, so.x_followers, so.linkedin_followers,
            so.snapshot_date AS social_date
        FROM competitors c
        LEFT JOIN seo_snapshots s ON s.competitor_id = c.id
            AND s.id = (SELECT id FROM seo_snapshots WHERE competitor_id = c.id ORDER BY snapshot_date DESC LIMIT 1)
        LEFT JOIN social_snapshots so ON so.competitor_id = c.id
            AND so.id = (SELECT id FROM social_snapshots WHERE competitor_id = c.id ORDER BY snapshot_date DESC LIMIT 1)
        ORDER BY c.name
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_history(competitor_id: int):
    conn = get_conn()
    seo = conn.execute(
        "SELECT * FROM seo_snapshots WHERE competitor_id=? ORDER BY snapshot_date", (competitor_id,)
    ).fetchall()
    social = conn.execute(
        "SELECT * FROM social_snapshots WHERE competitor_id=? ORDER BY snapshot_date", (competitor_id,)
    ).fetchall()
    conn.close()
    return {"seo": [dict(r) for r in seo], "social": [dict(r) for r in social]}


def save_seo_snapshot(competitor_id, data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO seo_snapshots (competitor_id, snapshot_date, open_pagerank, sitemap_pages, meta_title, meta_description, tech_stack)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        competitor_id,
        datetime.utcnow().strftime("%Y-%m-%d"),
        data.get("open_pagerank"),
        data.get("sitemap_pages"),
        data.get("meta_title"),
        data.get("meta_description"),
        data.get("tech_stack"),
    ))
    conn.commit()
    conn.close()


def save_social_snapshot(competitor_id, data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO social_snapshots (competitor_id, snapshot_date, facebook_followers, instagram_followers, x_followers, linkedin_followers)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        competitor_id,
        datetime.utcnow().strftime("%Y-%m-%d"),
        data.get("facebook_followers"),
        data.get("instagram_followers"),
        data.get("x_followers"),
        data.get("linkedin_followers"),
    ))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
