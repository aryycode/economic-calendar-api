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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
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
                
                if len(response.text) < 200:
                    raise ValueError("Response too short, possibly blocked")
                
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
        """Parse HTML response into EconomicEvent objects"""
        soup = BeautifulSoup(html, 'lxml')
        events = []
        
        try:
            blocks = soup.find_all('div', class_='Section-module__container___WUPgM Table-module__day___As54H')
            
            for block in blocks:
                day_info = self._extract_day_info(block, year, week)
                if not day_info:
                    continue
                    
                event_rows = block.table.tbody.find_all('tr') if block.table and block.table.tbody else []
                
                for row in event_rows:
                    event = self._extract_event_data(row, day_info)
                    if event:
                        events.append(event)
                        
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            
        return events

    def _extract_day_info(self, block, year: str, week: str) -> Optional[dict]:
        """Extract day information from block"""
        try:
            month_element = block.table.thead.tr.td.find('div', class_='Table-module__month___PGbXI')
            day_element = block.table.thead.tr.td.find('div', class_='Table-module__dayNumber___dyJpm')
            weekday_element = block.table.tr.find('td', class_='Table-module__weekday___p3Buh')
            
            if not all([month_element, day_element, weekday_element]):
                return None
                
            month_name = month_element.text.strip()
            
            # Skip December events in week 1 (they belong to previous year)
            if week == 'W01' and month_name == 'Dec':
                return None
                
            return {
                'year': year,
                'week': f'W{week}',
                'month_name': month_name,
                'month_num': self.months.get(month_name, '01'),
                'day_number': day_element.text.strip(),
                'week_day': weekday_element.text.strip()
            }
        except Exception:
            return None

    def _extract_event_data(self, row, day_info: dict) -> Optional[EconomicEvent]:
        """Extract event data from table row"""
        try:
            time_elem = row.find('td', class_='Table-module__time___IHBtp')
            currency_elem = row.find('td', class_='Table-module__currency___gSAJ5')
            name_elem = row.find('td', class_='Table-module__name___FugPe')
            impact_elem = row.find('td', class_='Table-module__impact___kYuei')
            actual_elem = row.find('td', class_='Table-module__actual___kzVNq')
            forecast_elem = row.find('td', class_='Table-module__forecast___WchYX')
            previous_elem = row.find('td', class_='Table-module__previous___F0PHu')
            
            if not all([time_elem, currency_elem, name_elem, impact_elem]):
                return None
                
            event_data = {
                **day_info,
                'time': time_elem.text.strip(),
                'currency_name': currency_elem.text.strip(),
                'source_name': name_elem.text.strip(),
                'impact': impact_elem.text.strip(),
                'actual': actual_elem.text.strip() if actual_elem else None,
                'forecast': forecast_elem.text.strip() if forecast_elem else None,
                'previous': previous_elem.text.strip() if previous_elem else None,
            }
            
            event_data['timestamp'] = self._calculate_timestamp(event_data)
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
                hour = int(event_data['time'][:2])
                dt = datetime.datetime(
                    int(event_data['year']), 
                    int(event_data['month_num']), 
                    int(event_data['day_number']), 
                    hour, 
                    tzinfo=datetime.timezone.utc
                )
            return str(int(dt.timestamp()))
        except Exception:
            return "0"

    async def scrape_multiple_weeks(self, year: int, weeks: List[int], filters: Optional[FilterParams] = None) -> List[EconomicEvent]:
        """Scrape multiple weeks concurrently"""
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(self.scrape_week, year, week) for week in weeks]
            all_events = []
            
            for future in futures:
                events = future.result()
                all_events.extend(events)
        
        # Apply filters if provided
        if filters:
            all_events = self.filter_service.apply_filters(all_events, filters)
            
        return all_events

    def close(self):
        """Close the session"""
        self.session.close()