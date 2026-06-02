from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    app_env: str = Field(default="production", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8080, alias="APP_PORT")
    app_timezone: str = Field(default="Asia/Ho_Chi_Minh", alias="APP_TIMEZONE")

    database_url: str = Field(default="sqlite:///./ratflow.db", alias="DATABASE_URL")

    deepseek_api_key: str = Field(default="replace_me", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL")
    deepseek_fast_model: str = Field(default="deepseek-v4-flash", alias="DEEPSEEK_FAST_MODEL")
    deepseek_reasoning_model: str = Field(default="deepseek-v4-pro", alias="DEEPSEEK_REASONING_MODEL")
    llm_temperature: float = Field(default=0.12, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=6000, alias="LLM_MAX_TOKENS")
    llm_timeout_seconds: int = Field(default=90, alias="LLM_TIMEOUT_SECONDS")

    discord_bot_token: str = Field(default="replace_me", alias="DISCORD_BOT_TOKEN")
    discord_channel_id: str = Field(default="1476975825067966474", alias="DISCORD_CHANNEL_ID")

    unusual_options_provider: str = Field(default="barchart_public", alias="UNUSUAL_OPTIONS_PROVIDER")
    enable_public_scraper: bool = Field(default=True, alias="ENABLE_PUBLIC_SCRAPER")
    enable_manual_alerts: bool = Field(default=True, alias="ENABLE_MANUAL_ALERTS")
    enable_csv_import: bool = Field(default=True, alias="ENABLE_CSV_IMPORT")
    enable_oi_confirmation: bool = Field(default=True, alias="ENABLE_OI_CONFIRMATION")
    enable_outcome_tracking: bool = Field(default=True, alias="ENABLE_OUTCOME_TRACKING")

    tradier_sandbox_token: Optional[str] = Field(default=None, alias="TRADIER_SANDBOX_TOKEN")
    watchlist_tickers: str = Field(
        default="AAPL,MSFT,NVDA,TSLA,AMZN,META,GOOGL,AMD,SMCI,PLTR,MARA,COIN,ARM,SNOW,INTC,BA,NFLX,CRM,DIS,UBER,PYPL,SQ,SHOP,RIOT,CLSK,SOFI,AFRM,RBLX,DKNG,PENN,CVNA,GME,AMC,SPY,QQQ,IWM",
        alias="WATCHLIST_TICKERS",
    )
    scan_schedule_morning: bool = Field(default=True, alias="SCAN_SCHEDULE_MORNING")
    scan_schedule_afternoon: bool = Field(default=True, alias="SCAN_SCHEDULE_AFTERNOON")
    scan_schedule_premarket: bool = Field(default=True, alias="SCAN_SCHEDULE_PREMARKET")

    scan_interval_minutes: int = Field(default=30, alias="SCAN_INTERVAL_MINUTES")
    oi_confirmation_hour_local: int = Field(default=21, alias="OI_CONFIRMATION_HOUR_LOCAL")
    max_alerts_per_scan: int = Field(default=15, alias="MAX_ALERTS_PER_SCAN")

    min_options_dna_research_score: int = Field(default=45, alias="MIN_OPTIONS_DNA_RESEARCH_SCORE")
    min_discord_alert_score: int = Field(default=65, alias="MIN_DISCORD_ALERT_SCORE")
    min_trade_signal_score: int = Field(default=75, alias="MIN_TRADE_SIGNAL_SCORE")

    http_user_agent: str = Field(default="RatFlowILPE/0.1 public-data-research", alias="HTTP_USER_AGENT")
    request_timeout_seconds: int = Field(default=25, alias="REQUEST_TIMEOUT_SECONDS")
    request_rate_limit_seconds: int = Field(default=2, alias="REQUEST_RATE_LIMIT_SECONDS")

    search_provider: str = Field(default="duckduckgo", alias="SEARCH_PROVIDER")
    serpapi_api_key: Optional[str] = Field(default=None, alias="SERPAPI_API_KEY")
    brave_search_api_key: Optional[str] = Field(default=None, alias="BRAVE_SEARCH_API_KEY")
    tavily_api_key: Optional[str] = Field(default=None, alias="TAVILY_API_KEY")

    report_language: str = Field(default="zh", alias="REPORT_LANGUAGE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
