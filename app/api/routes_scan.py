from fastapi import APIRouter, BackgroundTasks
from app.services.scanner_service import scan_orchestrator
from app.logging_config import logger

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/trigger")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Manually trigger a full scan across all data sources."""
    background_tasks.add_task(_run_scan)
    return {"status": "scan_started"}


@router.get("/status")
async def scan_status():
    return {
        "status": "ok",
        "sources": ["tradier", "yfinance", "barchart_csv"],
        "note": "Scans run on schedule: 08:00, 16:00, 20:30 Beijing time",
    }


async def _run_scan():
    try:
        alerts = await scan_orchestrator.scan_all_sources()
        logger.info("manual_scan_done", alerts=len(alerts))
    except Exception as e:
        logger.error("manual_scan_failed", error=str(e))
