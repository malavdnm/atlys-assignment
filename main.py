from typing import Dict
import uuid
from fastapi import BackgroundTasks, FastAPI, Depends
from models import ScrapingResponse, ScrapingSettings
from storage.json_storage import JsonStorage
from notifications.console import ConsoleNotification
from scraper.scraper import DentalStallScraper
from dependencies import verify_token
from config import settings

app = FastAPI()

job_statuses: Dict[str, str] = {}

async def run_scraping_job(job_id: str, scraping_settings: ScrapingSettings):
    try:
        storage = JsonStorage(settings.DB_PATH)
        notification = ConsoleNotification()
        scraper = DentalStallScraper(storage, notification)
        
        job_statuses[job_id] = "running"
        total_products = await scraper.scrape(scraping_settings)
        
        # Update job status on completion
        job_statuses[job_id] = "completed"
        await notification.notify(
            f"Job {job_id} completed successfully. Total products scraped: {total_products}"
        )
        
    except Exception as e:
        job_statuses[job_id] = f"failed: {str(e)}"
        await notification.notify(f"Job {job_id} failed: {str(e)}")

@app.post("/scrape/", response_model=ScrapingResponse)
async def scrape_products(
    scraping_settings: ScrapingSettings,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Add scraping task to background tasks
    background_tasks.add_task(run_scraping_job, job_id, scraping_settings)
    
    return ScrapingResponse(
        job_id=job_id,
        status="accepted",
        message="Scraping job started successfully"
    )

@app.get("/job/{job_id}", response_model=ScrapingResponse)
async def get_job_status(
    job_id: str,
    token: str = Depends(verify_token)
):
    if job_id not in job_statuses:
        return ScrapingResponse(
            job_id=job_id,
            status="not_found",
            message="Job not found"
        )
    
    return ScrapingResponse(
        job_id=job_id,
        status=job_statuses[job_id],
        message=f"Job status: {job_statuses[job_id]}"
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
