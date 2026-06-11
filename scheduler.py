from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from scanner import crypto_scan, intraday_scan, overnight_analysis, premarket_scan

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(timezone="America/New_York")
    _scheduler.add_job(intraday_scan, CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/5"))
    _scheduler.add_job(premarket_scan, CronTrigger(hour=4, minute=0))
    _scheduler.add_job(overnight_analysis, CronTrigger(hour=23, minute=0))
    _scheduler.add_job(crypto_scan, "interval", minutes=15)
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
