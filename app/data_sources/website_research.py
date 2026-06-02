from typing import Dict, Any
from app.data_sources.base import DataSourceBase


class WebsiteResearchAdapter(DataSourceBase):
    source_name = "website_research"

    async def fetch(self, url: str = "", **kwargs) -> Dict[str, Any]:
        return self.unavailable_response("Website scraping not configured for MVP")


class JobsResearchAdapter(DataSourceBase):
    source_name = "jobs_research"

    async def fetch(self, company: str = "", **kwargs) -> Dict[str, Any]:
        return self.unavailable_response("Job posting search not configured for MVP")


class SocialResearchAdapter(DataSourceBase):
    source_name = "social_research"

    async def fetch(self, ticker: str = "", **kwargs) -> Dict[str, Any]:
        return self.unavailable_response("Social media research not configured for MVP")


class PatentsResearchAdapter(DataSourceBase):
    source_name = "patents_research"

    async def fetch(self, company: str = "", **kwargs) -> Dict[str, Any]:
        return self.unavailable_response("Patent search not configured for MVP")


class GovContractsResearchAdapter(DataSourceBase):
    source_name = "gov_contracts_research"

    async def fetch(self, company: str = "", **kwargs) -> Dict[str, Any]:
        return self.unavailable_response("Government contract search not configured for MVP")


class PriceDataAdapter(DataSourceBase):
    source_name = "price_data"

    async def fetch(self, ticker: str = "", **kwargs) -> Dict[str, Any]:
        return self.unavailable_response("Price data not configured for MVP")
