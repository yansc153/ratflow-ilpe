# RATFLOW-ILPE

## RATFLOW Information Leakage Prediction Engine

An event-driven unusual-options investigation harness.

### What it does

1. Receives unusual option alerts (manual API, CSV import, or public scanner)
2. Scores the option structure for information-leakage characteristics
3. Runs parallel LLM-powered research agents to gather public evidence
4. A Judge Agent fuses evidence into event probabilities and leakage scores
5. A Trade Construction Agent produces original-contract follow suggestions
6. Publishes Chinese-language reports to Discord
7. Tracks next-day OI confirmation and multi-horizon outcomes
8. Calibrates model-estimated probabilities against actual results

### What it does not do

- Does not execute trades
- Does not use non-public information
- Does not guarantee profit
- Does not confirm insider trading

---

### Setup

```bash
git clone <repo_url>
cd ratflow-ilpe
cp .env.example .env
nano .env
```

Fill in:

```
DEEPSEEK_API_KEY=your_deepseek_api_key
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=1476975825067966474
```

```bash
docker compose up -d --build
```

The container stores SQLite data in `./data/ratflow.db` and logs in `./logs/`.
Secrets stay in `.env`; `.env`, local databases, logs, and raw data are excluded
from Git and Docker build context.

---

### Test

```bash
# Health check
curl http://localhost:8080/health

# Test Discord
curl -X POST http://localhost:8080/discord/test

# Run end-to-end mock alert
python scripts/seed_mock_alert.py
```

---

### Scan and Push Logic

RATFLOW separates scanning from publishing:

1. A continuous batch scanner rotates through the configured ticker universe.
2. Cheap filters find unusual option contracts first.
3. Duplicate contracts are skipped for a cooldown window.
4. Options DNA scores decide whether a case deserves LLM research.
5. Discord publishing only happens when the final leakage score passes the publish threshold.

Default production settings:

```text
TICKER_UNIVERSE_FILE=config/ticker_universe_us.txt
SCAN_CURSOR_STATE_FILE=data/scan_cursor.json
SCAN_BATCH_SIZE=75
SCAN_INTERVAL_MINUTES=30
SCAN_DEDUP_HOURS=24
MIN_OPTIONS_DNA_RESEARCH_SCORE=45
MIN_DISCORD_ALERT_SCORE=65
```

The scheduler runs:

```text
Continuous batch scan: every SCAN_INTERVAL_MINUTES
06:00 BJT: post-close recap scan
20:45 BJT: pre-market scan
22:45 BJT: open-confirmation scan
03:30 BJT: pre-close scan
```

To expand beyond the seed universe, edit the VPS file:

```bash
cd /docker/ratflow
mkdir -p config
nano config/ticker_universe_us.txt
docker compose up -d --build --force-recreate
```

Use one ticker per line or comma-separated tickers. The scanner deduplicates them and persists the next batch cursor in `data/scan_cursor.json`.

---

### Manual Alert Example

```bash
curl -X POST http://localhost:8080/alerts/options \
  -H "Content-Type: application/json" \
  -d '{
    "source": "manual",
    "ticker": "RZLV",
    "company_name": "RZLV Inc.",
    "option_type": "CALL",
    "strike": 4.0,
    "expiry": "2026-07-17",
    "dte": 49,
    "volume": 9391,
    "open_interest": 6243,
    "bid": 0.18,
    "ask": 0.20,
    "last_price": 0.19,
    "implied_volatility": 1.25,
    "iv_change": 0.12,
    "premium": 182000,
    "underlying_price": 2.95,
    "underlying_move_5d": 0.02,
    "raw_text": "Unusual call activity detected"
  }'
```

---

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/discord/test` | Test Discord message |
| POST | `/alerts/options` | Submit manual alert |
| POST | `/alerts/import-csv` | CSV import endpoint |
| GET | `/cases` | List cases |
| GET | `/cases/{id}` | Case detail with report |
| GET | `/reports/recent` | Recent reports |
| GET | `/reports/{id}` | Report detail |
| POST | `/oi/confirm` | Run OI confirmation |
| GET | `/oi/pending` | Pending OI confirmations |
| POST | `/outcomes/update` | Update outcome tracking |
| GET | `/outcomes/stats/calibration` | Calibration stats |

---

### Public Scraper Notes

Public unusual options sources may be unreliable or blocked by the source websites.
Manual alert ingestion always works via `POST /alerts/options`.

The system includes a graceful adapter interface:
- `barchart_public`: Returns empty list when unable to access (never fakes data)
- `yahoo_options`: Placeholder for OI enrichment
- All research uses LLM-based web knowledge, not live scraping

---

### OI Confirmation

Next-day OI confirmation is scaffolded, but provider-backed OI snapshots are not
configured in P0.

- With no real OI provider configured, the case is marked `OI_UNAVAILABLE`.
- The system does not fake confirmation by reusing the original OI value.
- Leakage scores are not upgraded or downgraded from unavailable OI.
- Provider-backed `OI_CONFIRMED` / `OI_REJECTED` paths can be enabled later when
  a real options data provider is wired in.

---

### Outcome Tracking

Every case is tracked at horizons: 1D, 3D, 7D, 14D, 30D, expiry.

Metrics:
- Underlying return
- Option estimated return
- Max favorable excursion (MFE)
- Max adverse excursion (MAE)
- Event confirmed (yes/no)
- Failure reason classification

---

### Calibration

Model-estimated probabilities are capped by calibration grade:

| Comparable Cases | Confidence | Probability Cap |
|-----------------|------------|-----------------|
| < 10 | Low | 64% (uncalibrated) |
| 10-30 | Low | 64% (early) |
| 30-100 | Medium | 70% (calibrating) |
| > 100 | High | 78% (calibrated) |

Brier score tracking is scaffolded for future calibration.

---

### Repository Structure

```
ratflow-ilpe/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Pydantic settings
│   ├── db.py                # SQLAlchemy engine
│   ├── models.py            # Database models
│   ├── schemas.py           # Pydantic schemas
│   ├── api/                 # Route handlers
│   ├── harness/             # Orchestrator, state machine, scoring
│   ├── agents/              # All research subagents + judge + trade
│   ├── data_sources/        # Public data adapters
│   ├── services/            # DeepSeek, Discord, renderer
│   ├── templates/           # Jinja2 Discord templates
│   └── utils/               # Time, math, text, JSON repair
├── tests/                   # pytest tests
├── scripts/                 # CLI tools
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

---

### Disclaimer

Public-data research only. This is not investment advice. Model-estimated probabilities are not guarantees. Past performance does not predict future results. The system does not confirm or allege insider trading.

### VPS Deployment

```bash
git clone <repo_url>
cd ratflow-ilpe
cp .env.example .env
nano .env
docker compose up -d --build
docker compose logs -f
```

Update an existing VPS deployment:

```bash
cd /docker/ratflow
git pull --ff-only
docker compose up -d --build --force-recreate
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/scan/status
```

Required `.env` values:

```text
DEEPSEEK_API_KEY=...
DISCORD_BOT_TOKEN=...
DISCORD_CHANNEL_ID=...
```

Health check:

```bash
curl http://localhost:8080/health
```
