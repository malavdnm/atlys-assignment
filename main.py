from fastapi import FastAPI, Depends
from models import ScrapingSettings
from storage.json_storage import JsonStorage
from notifications.console import ConsoleNotification
from scraper.scraper import Scraper
from dependencies import verify_token
from config import settings

app = FastAPI()


@app.post("/scrape/")
async def scrape_products(
    scraping_settings: ScrapingSettings, token: str = Depends(verify_token)
):
    storage = JsonStorage(settings.DB_PATH)
    notification = ConsoleNotification()
    scraper = Scraper(storage, notification)

    products_scraped = await scraper.scrape(scraping_settings)
    return {"status": "task scheduled", "products_scraped": products_scraped}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
