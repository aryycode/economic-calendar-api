from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

class EconomicEvent(BaseModel):
    year: str
    week: str
    month_num: str
    month_name: str
    day_number: str
    week_day: str
    time: str
    currency_name: str
    source_name: str
    impact: str
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    timestamp: str
    session: Optional[str] = None

class FilterParams(BaseModel):
    impact: Optional[List[str]] = None
    pairs: Optional[List[str]] = None
    sessions: Optional[List[Literal["Sydney", "Tokyo", "London", "NewYork"]]] = None
    time_range: Optional[tuple[str, str]] = None
    events: Optional[List[str]] = None

class ScrapingRequest(BaseModel):
    year: Optional[int] = Field(None, description="Year to scrape (defaults to current year)")
    weeks: Optional[List[int]] = Field(None, max_items=4, description="Week numbers (max 4, defaults to current week)")
    filters: Optional[FilterParams] = None
    format: Literal["daily", "weekly"] = "weekly"
    day: Optional[int] = Field(None, ge=1, le=31, description="Specific day of month for daily format")

class ScrapingResponse(BaseModel):
    success: bool
    data: List[EconomicEvent]
    total_events: int
    weeks_scraped: List[str]
    filters_applied: Optional[FilterParams] = None
    execution_time: float