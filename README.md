# Economic Calendar Scraper API

A high-performance, Docker-ready API for scraping economic calendar data from BabyPips without Selenium.

## Features

- **No Selenium**: Pure HTTP requests for better performance
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

Comprehensive scraping with filters:

```json
{
  "year": 2025,
  "weeks": [32, 33],
  "filters": {
    "impact": ["High", "Medium"],
    "pairs": ["USD", "EUR"],
    "sessions": ["London", "NewYork"]
  },
  "format": "daily"
}
```

### GET /api/v1/scrape/quick

Quick single-week scraping:

```
GET /api/v1/scrape/quick?year=2025&week=32&impact=High&pairs=USD,EUR
```

### GET /api/v1/sessions

Get available trading sessions and their time ranges.

### GET /api/v1/health

Health check endpoint.

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Filters

- **Impact**: Low, Medium, High
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
