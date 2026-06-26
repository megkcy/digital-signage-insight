from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from database import init_db, get_all_competitors, get_latest_snapshots, get_history

app = FastAPI(title="Insight — Competitor Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "../docs")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/api/competitors")
def list_competitors():
    return get_all_competitors()


@app.get("/api/snapshots")
def list_snapshots():
    return get_latest_snapshots()


@app.get("/api/history/{competitor_id}")
def history(competitor_id: int):
    return get_history(competitor_id)


@app.post("/api/scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    """Manually trigger a scrape run."""
    def run():
        from scraper_static import scrape_all
        scrape_all()

    background_tasks.add_task(run)
    return {"status": "Scrape started in background"}


@app.get("/api/status")
def status():
    from database import get_conn
    conn = get_conn()
    counts = {
        "competitors": conn.execute("SELECT COUNT(*) FROM competitors").fetchone()[0],
        "seo_snapshots": conn.execute("SELECT COUNT(*) FROM seo_snapshots").fetchone()[0],
        "social_snapshots": conn.execute("SELECT COUNT(*) FROM social_snapshots").fetchone()[0],
    }
    last = conn.execute("SELECT MAX(snapshot_date) FROM seo_snapshots").fetchone()[0]
    conn.close()
    return {**counts, "last_scrape": last}
