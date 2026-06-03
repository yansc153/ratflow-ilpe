# Agent Hardening Roadmap

## Goal

Move RATFLOW from prompt-only public research toward tool-backed, auditable research.

## Stage 1: Immediate visibility

- Add `agent_audit` summary to Discord reports
- Expose `agent_runs` and `evidence_items` in `/cases/{id}`
- Keep final Discord score output, but show why the score was produced

## Stage 2: First tool-backed source

- `sec_filings_agent`
- Use SEC EDGAR ticker map and submissions JSON before calling the LLM
- Pass recent real filing metadata into the prompt
- Fail closed: if filings are unavailable, say so explicitly

## Stage 3: Next data-source priorities

- `earnings_surprise_agent`
- Add earnings-calendar and guidance retrieval before analysis
- Candidate sources: Yahoo Finance earnings calendar, Nasdaq earnings pages, company IR calendars

- `major_contract_agent`
- Add public search and procurement evidence before analysis
- Candidate sources: SAM.gov, defense.gov, company press releases, partner/customer pages

- `ai_transformation_agent`
- Add company-site, jobs-page, and press-release evidence before analysis
- Candidate sources: homepage, product pages, IR news, careers pages, developer docs

- `public_attention_noise_agent`
- Add public-news and crowding evidence before analysis
- Candidate sources: news search, Stocktwits/X/Reddit sentiment proxies, recent price/IV moves

## Stage 4: Report-level trust upgrades

- Include source counts per agent in Discord
- Add a `data_limitations` block to every report
- Store per-agent retrieval payloads separately from LLM summaries
- Distinguish `no evidence found` from `could not access source`

## Acceptance bar

- A pushed Discord report should show which agents found evidence and which agents were source-limited
- A case detail request should reveal the full intermediate trail
- At least one high-value agent should use real retrieved inputs instead of pure model recall
