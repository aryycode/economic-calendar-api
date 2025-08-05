from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import time
from app.models.schemas import ScrapingRequest, ScrapingResponse, FilterParams
from app.services.scraper import BabyPipsScraper
from app.services.filter import EventFilter
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/scrape", response_model=ScrapingResponse)
async def scrape_economic_calendar(request: ScrapingRequest):
    """
    Scrape economic calendar data from BabyPips
    
    - **year**: Year to scrape (e.g., 2025)
    - **weeks**: List of week numbers (max 4 weeks)
    - **filters**: Optional filters for impact, pairs, sessions, etc.
    - **format**: Return format - "daily" or "weekly"
    """
    start_time = time.time()
    
    try:
        scraper = BabyPipsScraper()
        
        # Validate weeks
        if len(request.weeks) > 4:
            raise HTTPException(status_code=400, detail="Maximum 4 weeks allowed")
        
        if any(week < 1 or week > 53 for week in request.weeks):
            raise HTTPException(status_code=400, detail="Week numbers must be between 1 and 53")
        
        # Scrape data
        events = await scraper.scrape_multiple_weeks(
            request.year, 
            request.weeks, 
            request.filters
        )
        
        # Format response based on request format
        if request.format == "daily":
            filter_service = EventFilter()
            events_by_day = filter_service.group_by_day(events)
            # Flatten back to list but maintain day grouping info
            events = [event for day_events in events_by_day.values() for event in day_events]
        
        execution_time = time.time() - start_time
        weeks_scraped = [f"W{week:02d}" for week in request.weeks]
        
        scraper.close()
        
        return ScrapingResponse(
            success=True,
            data=events,
            total_events=len(events),
            weeks_scraped=weeks_scraped,
            filters_applied=request.filters,
            execution_time=round(execution_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Error in scrape endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scrape/quick")
async def quick_scrape(
    year: int = Query(..., description="Year to scrape"),
    week: int = Query(..., description="Week number"),
    impact: Optional[str] = Query(None, description="Comma-separated impact levels: Low,Medium,High"),
    pairs: Optional[str] = Query(None, description="Comma-separated currency pairs: USD,EUR,GBP"),
    sessions: Optional[str] = Query(None, description="Comma-separated sessions: Sydney,Tokyo,London,NewYork")
):
    """
    Quick scrape endpoint for single week with query parameters
    """
    try:
        # Build filters from query params
        filters = None
        if any([impact, pairs, sessions]):
            filters = FilterParams()
            if impact:
                filters.impact = impact.split(',')
            if pairs:
                filters.pairs = pairs.split(',')
            if sessions:
                filters.sessions = sessions.split(',')
        
        request = ScrapingRequest(
            year=year,
            weeks=[week],
            filters=filters,
            format="weekly"
        )
        
        return await scrape_economic_calendar(request)
        
    except Exception as e:
        logger.error(f"Error in quick_scrape endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Economic Calendar Scraper"}

@router.get("/sessions")
async def get_available_sessions():
    """Get available trading sessions with their time ranges"""
    return {
        "sessions": {
            "Sydney": "22:00-07:00 UTC",
            "Tokyo": "00:00-09:00 UTC", 
            "London": "08:00-17:00 UTC",
            "NewYork": "13:00-22:00 UTC"
        }
    }