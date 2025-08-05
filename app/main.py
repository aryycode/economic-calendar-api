from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.utils.logger import get_logger
import os

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Economic Calendar Scraper API",
    description="A high-performance API for scraping economic calendar data from BabyPips",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["Economic Calendar"])

@app.on_event("startup")
async def startup_event():
    logger.info("Economic Calendar Scraper API started")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Economic Calendar Scraper API stopped")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )