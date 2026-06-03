from typing import Dict, Any, List, Optional
import httpx
from app.data_sources.base import DataSourceBase
from app.config import settings
from app.logging_config import logger


class SECEdgarAdapter(DataSourceBase):
    source_name = "sec_edgar"
    company_tickers_url = "https://www.sec.gov/files/company_tickers.json"
    submissions_url = "https://data.sec.gov/submissions/CIK{cik}.json"

    async def fetch(self, ticker: str = "", **kwargs) -> Dict[str, Any]:
        logger.info("sec_edgar_fetch", ticker=ticker)
        data = await self.get_recent_filings(ticker=ticker, limit=kwargs.get("limit", 10))
        if not data:
            return self.unavailable_response("No recent SEC filings found")
        return {
            "source": self.source_name,
            "status": "ok",
            "data": data,
        }

    async def get_recent_filings(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        logger.info("sec_edgar_filings", ticker=ticker)
        ticker = (ticker or "").upper().strip()
        if not ticker:
            return []

        cik = await self._lookup_cik(ticker)
        if not cik:
            return []

        headers = {
            "User-Agent": settings.http_user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
            try:
                response = await client.get(self.submissions_url.format(cik=cik))
                response.raise_for_status()
            except Exception as e:
                logger.warning("sec_edgar_submissions_failed", ticker=ticker, cik=cik, error=str(e))
                return []

        recent = response.json().get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        filings: List[Dict[str, Any]] = []
        for idx, form in enumerate(forms):
            if len(filings) >= limit:
                break
            accession = accession_numbers[idx] if idx < len(accession_numbers) else ""
            filing_date = filing_dates[idx] if idx < len(filing_dates) else ""
            primary_doc = primary_docs[idx] if idx < len(primary_docs) else ""
            description = descriptions[idx] if idx < len(descriptions) else ""
            accession_compact = accession.replace("-", "")
            url = ""
            if accession_compact and primary_doc:
                url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_compact}/{primary_doc}"
            filings.append({
                "ticker": ticker,
                "cik": cik,
                "form": form,
                "filing_date": filing_date,
                "accession_number": accession,
                "primary_document": primary_doc,
                "description": description,
                "url": url,
            })
        return filings

    async def _lookup_cik(self, ticker: str) -> Optional[str]:
        headers = {
            "User-Agent": settings.http_user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers) as client:
            try:
                response = await client.get(self.company_tickers_url)
                response.raise_for_status()
            except Exception as e:
                logger.warning("sec_edgar_ticker_map_failed", ticker=ticker, error=str(e))
                return None

        payload = response.json()
        for item in payload.values():
            if str(item.get("ticker", "")).upper() == ticker:
                return str(item.get("cik_str", "")).zfill(10)
        logger.info("sec_edgar_cik_not_found", ticker=ticker)
        return None
