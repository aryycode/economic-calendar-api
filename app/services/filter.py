from typing import List, Optional
from app.models.schemas import EconomicEvent, FilterParams
import re

class EventFilter:
    def __init__(self):
        self.session_times = {
            'Sydney': [('22:00', '23:59'), ('00:00', '07:00')],
            'Tokyo': [('00:00', '09:00')],
            'London': [('08:00', '17:00')],
            'NewYork': [('13:00', '22:00')]
        }

    def determine_session(self, time_str: str) -> Optional[str]:
        """Determine trading session based on time"""
        if not time_str or time_str == 'All Day':
            return None
            
        try:
            # Extract hour from time string (format: "HH:MM" or "HH")
            hour_match = re.match(r'(\d{1,2})', time_str)
            if not hour_match:
                return None
                
            hour = int(hour_match.group(1))
            
            for session, time_ranges in self.session_times.items():
                for start_time, end_time in time_ranges:
                    start_hour = int(start_time.split(':')[0])
                    end_hour = int(end_time.split(':')[0])
                    
                    if start_hour <= end_hour:  # Same day
                        if start_hour <= hour <= end_hour:
                            return session
                    else:  # Crosses midnight
                        if hour >= start_hour or hour <= end_hour:
                            return session
            return None
        except Exception:
            return None

    def apply_filters(self, events: List[EconomicEvent], filters: FilterParams) -> List[EconomicEvent]:
        """Apply all filters to events list with ROBUST filtering"""
        filtered_events = events
        
        # Impact filter with case-insensitive matching
        if filters.impact:
            # Normalize requested impacts
            normalized_impacts = [self._normalize_impact(imp) for imp in filters.impact]
            filtered_events = [e for e in filtered_events 
                             if self._normalize_impact(e.impact) in normalized_impacts]
            
        # Currency filter (pairs) - exact match but case insensitive
        if filters.pairs:
            # Normalize to uppercase for comparison
            normalized_pairs = [pair.upper() for pair in filters.pairs]
            filtered_events = [e for e in filtered_events 
                             if e.currency_name.upper() in normalized_pairs]
            
        # Sessions filter
        if filters.sessions:
            filtered_events = [e for e in filtered_events if e.session in filters.sessions]
            
        # Events filter (keyword matching in event names)
        if filters.events:
            pattern = '|'.join(filters.events)
            filtered_events = [e for e in filtered_events 
                             if re.search(pattern, e.source_name, re.IGNORECASE)]
            
        # Time range filter
        if filters.time_range:
            start_time, end_time = filters.time_range
            filtered_events = self._filter_by_time_range(filtered_events, start_time, end_time)
            
        return filtered_events

    def _normalize_impact(self, impact: str) -> str:
        """Normalize impact values to standard format with proper capitalization"""
        if not impact:
            return 'Unknown'
            
        impact_lower = impact.lower().strip()
        if impact_lower in ['low', 'l']:
            return 'Low'
        elif impact_lower in ['med', 'medium', 'm']:
            return 'Medium' 
        elif impact_lower in ['high', 'h']:
            return 'High'
        else:
            # Capitalize first letter for unknown values
            return impact.strip().capitalize()

    def _filter_by_time_range(self, events: List[EconomicEvent], start_time: str, end_time: str) -> List[EconomicEvent]:
        """Filter events by time range"""
        try:
            start_hour = int(start_time.split(':')[0])
            end_hour = int(end_time.split(':')[0])
            
            filtered = []
            for event in events:
                if event.time and event.time != 'All Day':
                    try:
                        event_hour = int(event.time.split(':')[0])
                        if start_hour <= end_hour:  # Same day
                            if start_hour <= event_hour <= end_hour:
                                filtered.append(event)
                        else:  # Crosses midnight
                            if event_hour >= start_hour or event_hour <= end_hour:
                                filtered.append(event)
                    except:
                        # If time parsing fails, include the event
                        filtered.append(event)
                        
            return filtered
        except Exception:
            return events

    def group_by_day(self, events: List[EconomicEvent]) -> dict:
        """Group events by day"""
        grouped = {}
        for event in events:
            key = f"{event.year}-{event.month_num}-{event.day_number}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(event)
        return grouped