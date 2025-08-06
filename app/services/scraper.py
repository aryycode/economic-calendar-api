import requests
from bs4 import BeautifulSoup
import datetime
from typing import List, Optional
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.models.schemas import EconomicEvent, FilterParams
from app.utils.logger import get_logger
from app.services.filter import EventFilter

logger = get_logger(__name__)

class BabyPipsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Upgrade-Insecure-Requests': '1',
        })
        self.months = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }
        self.filter_service = EventFilter()

    def scrape_week(self, year: int, week: int, max_retries: int = 3) -> List[EconomicEvent]:
        """Scrape economic calendar for a specific week"""
        year_str = str(year)
        week_str = f"{week:02d}"
        url = f'https://www.babypips.com/economic-calendar?week={year_str}-W{week_str}'
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Scraping {url}, attempt {attempt + 1}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                if len(response.text) < 1000:  # Lowered threshold
                    raise ValueError("Response too short, possibly blocked")
                
                logger.info(f"Response received: {len(response.text)} characters")
                return self._parse_response(response.text, year_str, week_str)
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to scrape {url} after {max_retries} attempts")
                    return []
        
        return []

    def _parse_response(self, html: str, year: str, week: str) -> List[EconomicEvent]:
        """Parse HTML response - USING ROBUST LOGIC"""
        # Try multiple parsers
        soup = None
        parsers = ['html.parser', 'lxml', 'html5lib']
        
        for parser in parsers:
            try:
                soup = BeautifulSoup(html, parser)
                logger.info(f"Using parser: {parser}")
                break
            except Exception as e:
                logger.warning(f"Parser {parser} failed: {e}")
                continue
        
        if not soup:
            logger.error("No parser available")
            return []
        
        events = []
        
        try:
            # Find calendar blocks
            blocks = soup.find_all('div', class_='Section-module__container___WUPgM Table-module__day___As54H')
            logger.info(f"Found {len(blocks)} calendar blocks")
            
            if not blocks:
                logger.warning("No blocks found")
                return []
            
            for i, block in enumerate(blocks):
                logger.info(f"Processing block {i+1}/{len(blocks)}")
                
                try:
                    # Extract day information using ROBUST method
                    day_info = self._extract_day_info(block, year, week)
                    if not day_info:
                        logger.warning(f"Block {i+1}: Could not extract day info")
                        continue
                    
                    logger.info(f"Block {i+1}: {day_info['month_name']} {day_info['day_number']} ({day_info['week_day']})")
                    
                    # ✅ STRATEGY 3: Find events with robust approach (like robust_scraper)
                    event_rows = []
                    
                    # Try tbody first
                    tbody = block.find('tbody')
                    if tbody:
                        event_rows = tbody.find_all('tr')
                        logger.info(f"Block {i+1}: Found {len(event_rows)} rows via tbody")
                    else:
                        # Fallback: find all tr in block
                        all_trs = block.find_all('tr')
                        # Skip first tr (likely header)
                        event_rows = all_trs[1:] if len(all_trs) > 1 else all_trs
                        logger.info(f"Block {i+1}: Found {len(event_rows)} rows via all tr (fallback)")
                    
                    for j, row in enumerate(event_rows):
                        event = self._extract_event_data_robust(row, day_info)
                        if event:
                            events.append(event)
                        else:
                            logger.debug(f"Block {i+1}, Row {j+1}: Failed to extract event")
                            
                except Exception as e:
                    logger.error(f"Error processing block {i+1}: {e}")
                    continue
                        
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            
        logger.info(f"Total events extracted: {len(events)}")
        return events

    def _extract_day_info(self, block, year: str, week: str) -> Optional[dict]:
        """Extract day information from block - USING ROBUST LOGIC"""
        try:
            # ✅ STRATEGY 1: Find month/day elements ANYWHERE in the block (like robust_scraper)
            month_element = block.find('div', class_='Table-module__month___PGbXI')
            day_element = block.find('div', class_='Table-module__dayNumber___dyJpm')
            
            if not month_element or not day_element:
                logger.debug(f"Day info: month={month_element is not None}, day={day_element is not None}")
                return None
            
            month_name = month_element.text.strip()
            day_number = day_element.text.strip()
            
            # Skip December events in week 1 (they belong to previous year)
            if week == '01' and month_name == 'Dec':
                logger.debug("Day info: Skipping December in W01")
                return None
            
            # ✅ STRATEGY 2: Find weekday with multiple approaches (like robust_scraper)
            weekday = 'Unknown'
            
            # Try original approach
            weekday_element = block.find('td', class_='Table-module__weekday___p3Buh')
            if weekday_element:
                weekday = weekday_element.text.strip()
                logger.debug(f"Weekday (method 1): {weekday}")
            else:
                # Alternative: look for weekday in any text content
                weekday_patterns = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                block_text = block.get_text()
                for pattern in weekday_patterns:
                    if pattern in block_text:
                        weekday = pattern
                        logger.debug(f"Weekday (method 2): {weekday}")
                        break
            
            return {
                'year': year,
                'week': f'W{week}',
                'month_name': month_name,
                'month_num': self.months.get(month_name, '01'),
                'day_number': day_number,
                'week_day': weekday
            }
            
        except Exception as e:
            logger.error(f"Error extracting day info: {e}")
            return None

    def _extract_event_data_robust(self, row, day_info: dict) -> Optional[EconomicEvent]:
        """Extract event data with ROBUST logic - exactly like robust_scraper.py"""
        try:
            # ✅ Robust cell extraction (exactly like robust_scraper)
            cells = row.find_all(['td', 'th'])
            
            # Find cells by class (preferred)
            time_elem = row.find('td', class_='Table-module__time___IHBtp')
            currency_elem = row.find('td', class_='Table-module__currency___gSAJ5')
            name_elem = row.find('td', class_='Table-module__name___FugPe')
            impact_elem = row.find('td', class_='Table-module__impact___kYuei')
            actual_elem = row.find('td', class_='Table-module__actual___kzVNq')
            forecast_elem = row.find('td', class_='Table-module__forecast___WchYX')
            previous_elem = row.find('td', class_='Table-module__previous___F0PHu')
            
            # ✅ Fallback: extract by position if classes don't work
            if not all([time_elem, currency_elem, name_elem, impact_elem]) and len(cells) >= 4:
                logger.debug("Using positional fallback for event extraction")
                time_elem = cells[0] if len(cells) > 0 else None
                currency_elem = cells[1] if len(cells) > 1 else None
                name_elem = cells[2] if len(cells) > 2 else None
                impact_elem = cells[3] if len(cells) > 3 else None
                actual_elem = cells[4] if len(cells) > 4 else None
                forecast_elem = cells[5] if len(cells) > 5 else None
                previous_elem = cells[6] if len(cells) > 6 else None
            
            # Validate required fields
            if not all([time_elem, currency_elem, name_elem, impact_elem]):
                logger.debug("Event data: Missing required elements")
                return None
            
            # Build event data
            event_data = {
                **day_info,
                'time': time_elem.text.strip() if time_elem else '',
                'currency_name': currency_elem.text.strip() if currency_elem else '',
                'source_name': name_elem.text.strip() if name_elem else '',
                'impact': impact_elem.text.strip() if impact_elem else '',  # Keep original case for now
                'actual': actual_elem.text.strip() if actual_elem else None,
                'forecast': forecast_elem.text.strip() if forecast_elem else None,
                'previous': previous_elem.text.strip() if previous_elem else None,
            }
            
            # Calculate timestamp
            event_data['timestamp'] = self._calculate_timestamp(event_data)
            
            # Determine session
            event_data['session'] = self.filter_service.determine_session(event_data['time'])
            
            return EconomicEvent(**event_data)
            
        except Exception as e:
            logger.error(f"Error extracting event data: {e}")
            return None

    def _calculate_timestamp(self, event_data: dict) -> str:
        """Calculate timestamp for event"""
        try:
            if event_data['time'] in ['All Day', '']:
                dt = datetime.datetime(
                    int(event_data['year']), 
                    int(event_data['month_num']), 
                    int(event_data['day_number']), 
                    0, 
                    tzinfo=datetime.timezone.utc
                )
            else:
                # Parse time (format: "HH:MM" or just "HH")
                time_str = event_data['time']
                if ':' in time_str:
                    hour = int(time_str.split(':')[0])
                    minute = int(time_str.split(':')[1])
                else:
                    hour = int(time_str[:2])
                    minute = 0
                
                dt = datetime.datetime(
                    int(event_data['year']), 
                    int(event_data['month_num']), 
                    int(event_data['day_number']), 
                    hour,
                    minute,
                    tzinfo=datetime.timezone.utc
                )
            
            return str(int(dt.timestamp()))
        except Exception as e:
            logger.error(f"Error calculating timestamp: {e}")
            return "0"

    def _normalize_impact(self, impact: str) -> str:
        """Normalize impact values"""
        impact_lower = impact.lower().strip()
        if impact_lower in ['low', 'l']:
            return 'Low'
        elif impact_lower in ['med', 'medium', 'm']:
            return 'Medium' 
        elif impact_lower in ['high', 'h']:
            return 'High'
        return impact.capitalize()  # Fallback

    async def scrape_multiple_weeks(self, year: int, weeks: List[int], filters: Optional[FilterParams] = None) -> List[EconomicEvent]:
        """Scrape multiple weeks concurrently"""
        logger.info(f"Scraping {len(weeks)} weeks: {weeks}")
        
        with ThreadPoolExecutor(max_workers=min(4, len(weeks))) as executor:
            futures = [executor.submit(self.scrape_week, year, week) for week in weeks]
            all_events = []
            
            for i, future in enumerate(futures):
                try:
                    events = future.result()
                    all_events.extend(events)
                    logger.info(f"Week {weeks[i]}: {len(events)} events")
                except Exception as e:
                    logger.error(f"Week {weeks[i]} failed: {e}")
        
        logger.info(f"Total events before filtering: {len(all_events)}")
        
        # Apply filters if provided
        if filters:
            all_events = self.filter_service.apply_filters(all_events, filters)
            logger.info(f"Total events after filtering: {len(all_events)}")
            
        return all_events

    def close(self):
        """Close the session"""
        self.session.close()