from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
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
    Register continuous batch scans plus daily anchor scans synced to Beijing time (UTC+8):

    - Continuous interval scans rotate through the ticker universe in batches.
    - 06:00 BJT = 22:00 UTC: Post-close recap scan
    - 20:45 BJT = 12:45 UTC: Pre-market scan
    - 22:45 BJT = 14:45 UTC: Open-confirmation scan
    - 03:30 BJT = 19:30 UTC: Pre-close scan
    """

    jobs_registered = 0

    if settings.scan_continuous_enabled and settings.enable_public_scraper:
        interval_minutes = max(5, settings.scan_interval_minutes)
        scheduler.add_job(
            _run_scheduled_scan,
            IntervalTrigger(minutes=interval_minutes),
            args=[f"continuous_batch_scan_{interval_minutes}m"],
            id="scan_continuous",
            name=f"Continuous Batch Scan ({interval_minutes}m)",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        jobs_registered += 1
        logger.info("scheduler_registered", job="scan_continuous", interval_minutes=interval_minutes)

    if settings.scan_schedule_morning and settings.enable_public_scraper:
        scheduler.add_job(
            _run_scheduled_scan,
            CronTrigger(hour=22, minute=0),
            args=["post_close_scan_06BJT"],
            id="scan_morning",
            name="Post-Close Scan (06:00 BJT)",
            replace_existing=True,
        )
        jobs_registered += 1
        logger.info("scheduler_registered", job="scan_morning", cron="0 22 * * *", time_bjt="06:00")

    if (settings.scan_schedule_premarket or settings.scan_schedule_afternoon) and settings.enable_public_scraper:
        scheduler.add_job(
            _run_scheduled_scan,
            CronTrigger(hour=12, minute=45),
            args=["premarket_scan_20_45BJT"],
            id="scan_premarket",
            name="Pre-Market Scan (20:45 BJT)",
            replace_existing=True,
        )
        jobs_registered += 1
        logger.info("scheduler_registered", job="scan_premarket", cron="45 12 * * *", time_bjt="20:45")

    if settings.scan_schedule_open_confirm and settings.enable_public_scraper:
        scheduler.add_job(
            _run_scheduled_scan,
            CronTrigger(hour=14, minute=45),
            args=["open_confirm_scan_22_45BJT"],
            id="scan_open_confirm",
            name="Open-Confirmation Scan (22:45 BJT)",
            replace_existing=True,
        )
        jobs_registered += 1
        logger.info("scheduler_registered", job="scan_open_confirm", cron="45 14 * * *", time_bjt="22:45")

    if settings.scan_schedule_preclose and settings.enable_public_scraper:
        scheduler.add_job(
            _run_scheduled_scan,
            CronTrigger(hour=19, minute=30),
            args=["preclose_scan_03_30BJT"],
            id="scan_preclose",
            name="Pre-Close Scan (03:30 BJT)",
            replace_existing=True,
        )
        jobs_registered += 1
        logger.info("scheduler_registered", job="scan_preclose", cron="30 19 * * *", time_bjt="03:30")

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
