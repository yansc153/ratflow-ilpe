from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.logging_config import logger
from app.db import init_db
from app.api.routes_health import router as health_router
from app.api.routes_alerts import router as alerts_router
from app.api.routes_reports import router as reports_router
from app.api.routes_discord import router as discord_router
from app.api.routes_oi import router as oi_router
from app.api.routes_outcomes import router as outcomes_router
from app.api.routes_scan import router as scan_router
from app.services.scheduler_service import init_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ratflow_startup", env=settings.app_env)
    init_db()
    logger.info("database_initialized")
    init_scheduler()
    yield
    shutdown_scheduler()
    logger.info("ratflow_shutdown")


app = FastAPI(
    title="RATFLOW-ILPE",
    description="RATFLOW Information Leakage Prediction Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(discord_router)
app.include_router(oi_router)
app.include_router(outcomes_router)
app.include_router(scan_router)
