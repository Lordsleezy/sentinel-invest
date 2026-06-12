from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime
from typing import TypeVar
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from scanner import crypto_scan, intraday_scan, overnight_analysis, premarket_scan

_scheduler: BackgroundScheduler | None = None
logger = logging.getLogger("sentinel_invest.scheduler")
T = TypeVar("T")
EASTERN = ZoneInfo("America/New_York")


def _logged_job(name: str, fn: Callable[[], T]) -> Callable[[], T]:
    def run() -> T:
        start = time.time()
        logger.info("scheduler job %s started", name)
        try:
            result = fn()
        except Exception:
            logger.exception("scheduler job %s failed", name)
            raise
        logger.info("scheduler job %s completed in %.2fs", name, time.time() - start)
        return result

    return run


def start_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(timezone=EASTERN)
    _scheduler.add_job(
        _logged_job("intraday_scan", intraday_scan),
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/5", timezone=EASTERN),
        id="intraday_scan",
        name="intraday_scan every 5 min during market hours",
    )
    _scheduler.add_job(
        _logged_job("premarket_scan", premarket_scan),
        CronTrigger(hour=4, minute=0, timezone=EASTERN),
        id="premarket_scan",
        name="premarket_scan 4am ET",
    )
    _scheduler.add_job(
        _logged_job("overnight_analysis", overnight_analysis),
        CronTrigger(hour=23, minute=0, timezone=EASTERN),
        id="overnight_analysis",
        name="overnight_analysis 11pm ET",
    )
    _scheduler.add_job(
        _logged_job("crypto_scan", crypto_scan),
        "interval",
        minutes=15,
        id="crypto_scan",
        name="crypto_scan every 15 min",
        next_run_time=datetime.now(EASTERN),
    )
    _scheduler.start()
    for job in _scheduler.get_jobs():
        logger.info("registered scheduler job %s next_run=%s", job.id, job.next_run_time)


def stop_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
