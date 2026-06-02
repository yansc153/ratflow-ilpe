from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import settings
from app.logging_config import logger
from app.services.scanner_service import scan_orchestrator

scheduler = AsyncIOScheduler(timezone="UTC")


async def _run_scheduled_scan(scan_name: str):
    logger.info("scheduled_scan_start", name=scan_name)
    try:
        alerts = await scan_orchestrator.scan_all_sources()
        logger.info("scheduled_scan_done", name=scan_name, alerts_found=len(alerts))
    except Exception as e:
        logger.error("scheduled_scan_failed", name=scan_name, error=str(e))


def init_scheduler():
    """
    Register 3 daily scan jobs synced to Beijing time (UTC+8):

    - 08:00 BJT = 00:00 UTC: Morning scan (yesterday's market data)
    - 16:00 BJT = 08:00 UTC: Afternoon scan (pre-market starting)
    - 20:30 BJT = 12:30 UTC: Pre-market scan (1h before US open at 21:30 BJT)
    """

    jobs_registered = 0

    if settings.scan_schedule_morning and settings.enable_public_scraper:
        scheduler.add_job(
            _run_scheduled_scan,
            CronTrigger(hour=0, minute=0),
            args=["morning_scan_08BJT"],
            id="scan_morning",
            name="Morning Scan (08:00 BJT)",
            replace_existing=True,
        )
        jobs_registered += 1
        logger.info("scheduler_registered", job="scan_morning", cron="0 0 * * *", time_bjt="08:00")

    if settings.scan_schedule_afternoon and settings.enable_public_scraper:
        scheduler.add_job(
            _run_scheduled_scan,
            CronTrigger(hour=8, minute=0),
            args=["afternoon_scan_16BJT"],
            id="scan_afternoon",
            name="Afternoon Scan (16:00 BJT)",
            replace_existing=True,
        )
        jobs_registered += 1
        logger.info("scheduler_registered", job="scan_afternoon", cron="0 8 * * *", time_bjt="16:00")

    if settings.scan_schedule_premarket and settings.enable_public_scraper:
        scheduler.add_job(
            _run_scheduled_scan,
            CronTrigger(hour=12, minute=30),
            args=["premarket_scan_20_30BJT"],
            id="scan_premarket",
            name="Pre-Market Scan (20:30 BJT)",
            replace_existing=True,
        )
        jobs_registered += 1
        logger.info("scheduler_registered", job="scan_premarket", cron="30 12 * * *", time_bjt="20:30")

    if jobs_registered > 0:
        scheduler.start()
        logger.info("scheduler_started", jobs=jobs_registered)
    else:
        logger.info("scheduler_skipped", reason="public_scraper disabled or all schedules off")

    return scheduler


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("scheduler_shutdown")
