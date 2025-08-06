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
        """Parse HTML response into EconomicEvent objects with robust parsing"""
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
                logger.warning("No blocks found with original class names, trying fallback")
                # Save HTML for debugging
                try:
                    with open(f'debug_response_{year}_W{week}.html', 'w', encoding='utf-8') as f:
                        f.write(html)
                    logger.info(f"HTML saved for debugging: debug_response_{year}_W{week}.html")
                except:
                    pass
                return []
            
            for i, block in enumerate(blocks):
                logger.info(f"Processing block {i+1}/{len(blocks)}")
                
                try:
                    # Validate block structure
                    if not (block.table and block.table.thead and block.table.tbody):
                        logger.warning(f"Block {i+1}: Invalid structure (missing table/thead/tbody)")
                        continue
                    
                    # Extract day information
                    day_info = self._extract_day_info(block, year, week)
                    if not day_info:
                        logger.warning(f"Block {i+1}: Could not extract day info")
                        continue
                    
                    logger.info(f"Block {i+1}: {day_info['month_name']} {day_info['day_number']} ({day_info['week_day']})")
                    
                    # Extract events from this day
                    event_rows = block.table.tbody.find_all('tr')
                    logger.info(f"Block {i+1}: Found {len(event_rows)} event rows")
                    
                    for j, row in enumerate(event_rows):
                        event = self._extract_event_data(row, day_info)
                        if event:
                            events.append(event)
                            logger.debug(f"Block {i+1}, Row {j+1}: {event.currency_name} - {event.source_name}")
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
        """Extract day information from block"""
        try:
            # Validate structure - FIXED: Check for th instead of td
            if not (block.table and block.table.thead and block.table.thead.tr):
                logger.debug("Day info: Invalid block structure")
                return None
            
            thead_tr = block.table.thead.tr
            
            # FIXED: Look for th elements instead of td
            thead_cells = thead_tr.find_all(['th', 'td'])
            if not thead_cells:
                logger.debug("Day info: No thead cells found")
                return None
            
            first_cell = thead_cells[0]  # First cell contains date info
            
            month_element = first_cell.find('div', class_='Table-module__month___PGbXI')
            day_element = first_cell.find('div', class_='Table-module__dayNumber___dyJpm')
            
            if not month_element or not day_element:
                logger.debug("Day info: Month or day element not found")
                return None
            
            month_name = month_element.text.strip()
            day_number = day_element.text.strip()
            
            # Skip December events in week 1 (they belong to previous year)
            if week == '01' and month_name == 'Dec':
                logger.debug("Day info: Skipping December in W01")
                return None
            
            # Get weekday - FIXED: Look for weekday in thead
            weekday = 'Unknown'
            weekday_element = thead_tr.find('th', class_='Table-module__weekday___p3Buh')
            if weekday_element:
                # Extract text from span inside weekday element
                weekday_span = weekday_element.find('span', class_='Table-module__weekdayContent___MzEAb')
                if weekday_span:
                    weekday = weekday_span.text.strip()
                else:
                    weekday = weekday_element.text.strip()
                    # Clean up extra content (remove button text, etc.)
                    weekday = weekday.split()[0] if weekday else 'Unknown'
            
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

    def _extract_event_data(self, row, day_info: dict) -> Optional[EconomicEvent]:
        """Extract event data from table row"""
        try:
            # Find all required elements
            time_elem = row.find('td', class_='Table-module__time___IHBtp')
            currency_elem = row.find('td', class_='Table-module__currency___gSAJ5')
            name_elem = row.find('td', class_='Table-module__name___FugPe')
            impact_elem = row.find('td', class_='Table-module__impact___kYuei')
            
            # Check required elements
            if not all([time_elem, currency_elem, name_elem, impact_elem]):
                logger.debug("Event data: Missing required elements")
                return None
            
            # Optional elements
            actual_elem = row.find('td', class_='Table-module__actual___kzVNq')
            forecast_elem = row.find('td', class_='Table-module__forecast___WchYX')
            previous_elem = row.find('td', class_='Table-module__previous___F0PHu')
            
            # Build event data
            event_data = {
                **day_info,
                'time': time_elem.text.strip(),
                'currency_name': currency_elem.text.strip(),
                'source_name': name_elem.text.strip(),
                'impact': self._normalize_impact(impact_elem.text.strip()),
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