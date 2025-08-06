from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import time
from datetime import datetime
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
    
    - **year**: Year to scrape (e.g., 2025). If not provided, defaults to current year
    - **weeks**: List of week numbers (max 4 weeks). If not provided, defaults to current week
    - **filters**: Optional filters for impact, pairs, sessions, etc.
    - **format**: Return format - "daily" or "weekly"
    - **day**: Specific day of month (1-31) for daily format. If not provided, defaults to today's date
    """
    start_time = time.time()
    
    try:
        scraper = BabyPipsScraper()
        
        # Set defaults for year and weeks if not provided
        current_date = datetime.now()
        year = request.year if request.year is not None else current_date.year
        weeks = request.weeks if request.weeks is not None else [current_date.isocalendar()[1]]
        
        # Validate weeks
        if len(weeks) > 4:
            raise HTTPException(status_code=400, detail="Maximum 4 weeks allowed")
        
        if any(week < 1 or week > 53 for week in weeks):
            raise HTTPException(status_code=400, detail="Week numbers must be between 1 and 53")
        
        # Scrape data
        events = await scraper.scrape_multiple_weeks(
            year, 
            weeks, 
            request.filters
        )
        
        # Format response based on request format
        if request.format == "daily":
            filter_service = EventFilter()
            # Use today's day if no day is specified
            target_day = request.day if request.day is not None else datetime.now().day
            # Filter events for specific day (either provided or today)
            events = [event for event in events if int(event.day_number) == target_day]
        
        execution_time = time.time() - start_time
        weeks_scraped = [f"W{week:02d}" for week in weeks]
        
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
    year: Optional[int] = Query(None, description="Year to scrape (defaults to current year)"),
    week: Optional[int] = Query(None, description="Week number (defaults to current week)"),
    impact: Optional[str] = Query(None, description="Comma-separated impact levels: Low,Medium,High"),
    pairs: Optional[str] = Query(None, description="Comma-separated currency pairs: USD,EUR,GBP"),
    sessions: Optional[str] = Query(None, description="Comma-separated sessions: Sydney,Tokyo,London,NewYork"),
    format: str = Query("weekly", description="Return format: daily or weekly"),
    day: Optional[int] = Query(None, ge=1, le=31, description="Specific day of month for daily format. If not provided, defaults to today's date")
):
    """
    Quick scrape endpoint for single week with query parameters
     
     - **year**: Year to scrape. If not provided, defaults to current year
     - **week**: Week number. If not provided, defaults to current week
     - **format**: Return format - "daily" or "weekly" (default: weekly)
     - **day**: Specific day of month (1-31) for daily format. If not provided, defaults to today's date
    """
    try:
        # Set defaults for year and week if not provided
        current_date = datetime.now()
        actual_year = year if year is not None else current_date.year
        actual_week = week if week is not None else current_date.isocalendar()[1]
        
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
            year=actual_year,
            weeks=[actual_week],
            filters=filters,
            format=format,
            day=day
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