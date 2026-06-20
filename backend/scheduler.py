"""Weekly scheduler — runs every Monday at 06:00."""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scheduler")


def job():
    log.info("Starting weekly scrape…")
    from database import init_db
    from scraper import scrape_all
    init_db()
    scrape_all()
    log.info("Weekly scrape done.")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(job, CronTrigger(day_of_week="mon", hour=6, minute=0))
    log.info("Scheduler started — scrapes every Monday at 06:00")

    # Run once immediately on startup
    log.info("Running initial scrape on startup…")
    job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")
