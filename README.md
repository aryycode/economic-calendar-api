# Economic Calendar Scraper API

A high-performance, Docker-ready API for scraping economic calendar data from BabyPips without Selenium.

## Features

- **No Selenium**: Pure HTTP requests for better performance
- **Smart Defaults**: Automatic current year, week, and day detection
- **Daily Format**: Get events for specific days with today's date as default
- **Advanced Filtering**: Filter by impact, currency pairs, trading sessions
- **Concurrent Scraping**: Multi-threaded scraping for multiple weeks
- **Docker Ready**: Complete containerization setup
- **Clean API**: RESTful API with comprehensive documentation
- **Trading Sessions**: Sydney, Tokyo, London, NewYork session detection
- **Production Ready**: Proper logging, error handling, health checks

## Quick Start

### Using Docker

```bash
git clone https://github.com/aryycode/economic-calendar-api.git
cd economic-calendar-scraper
docker-compose up -d
```

### Manual Setup

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### POST /api/v1/scrape

Comprehensive scraping with smart defaults:

```json
// Minimal request - uses current year, current week, today's date
{
  "format": "daily"
}

// Full request with all options (impact is case-insensitive)
{
  "year": 2025,
  "weeks": [32, 33],
  "filters": {
    "impact": ["high", "MEDIUM"],
    "pairs": ["USD", "EUR"],
    "sessions": ["London", "NewYork"]
  },
  "format": "daily",
  "day": 5
}
```

**Parameters:**
- `year` (optional): Defaults to current year
- `weeks` (optional): Defaults to current week
- `format`: "daily" or "weekly" (default: "weekly")
- `day` (optional): Specific day for daily format, defaults to today
- `filters` (optional): Impact, pairs, sessions, etc.

### GET /api/v1/scrape/quick

Quick single-week scraping with smart defaults:

```
// Minimal - uses current year, current week, today's date
GET /api/v1/scrape/quick?format=daily

// With specific parameters (impact is case-insensitive)
GET /api/v1/scrape/quick?year=2025&week=32&format=daily&day=5&impact=high&pairs=USD,EUR
```

**Query Parameters:**
- `year` (optional): Defaults to current year
- `week` (optional): Defaults to current week
- `format` (optional): "daily" or "weekly" (default: "weekly")
- `day` (optional): Specific day for daily format, defaults to today
- `impact`, `pairs`, `sessions` (optional): Filters

### GET /api/v1/sessions

Get available trading sessions and their time ranges.

### GET /api/v1/health

Health check endpoint.

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Filters

- **Impact**: Low, Medium, High (case-insensitive: "high", "HIGH", "High" all work)
- **Pairs**: Any currency code (USD, EUR, GBP, etc.)
- **Sessions**: Sydney (22:00-07:00), Tokyo (00:00-09:00), London (08:00-17:00), NewYork (13:00-22:00)
- **Time Range**: Custom time window
- **Events**: Keyword matching in event names

## Performance

- No Selenium overhead
- Concurrent processing
- Connection pooling
- Exponential backoff retry logic
- Memory efficient parsing

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## License

MIT License
