import aiohttp
import asyncio
import os
from typing import List, Optional
from models import Product, ScrapingSettings
import aiofiles
import redis
from config import settings
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin

from scraper.parser import Parser


class DentalStallScraper:
    BASE_URL = "https://dentalstall.com/shop/page/42"

    def __init__(self, storage_strategy, notification_strategy):
        self.storage = storage_strategy
        self.notification = notification_strategy
        self.redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.session = None
        self.parser = Parser()

    async def _init_session(self, proxy: Optional[str] = None):
        if self.session is None:
            if proxy:
                self.session = aiohttp.ClientSession(proxy=proxy)
            else:
                self.session = aiohttp.ClientSession()

        # Set common headers
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    async def _scrape_page(self, page: int) -> List[Product]:
        url = f"{self.BASE_URL}/page/{page}/" if page > 1 else self.BASE_URL
        print(url)

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, "html.parser")

                    # Find all product elements
                    product_elements = soup.find_all("li", class_="product")
                    # print(product_elements)

                    # Check if we found any products
                    if not product_elements:
                        return []

                    # Parse products concurrently
                    products = []
                    for element in product_elements:
                        product = await self.parser.parse_product(element, self.session)
                        if product:
                            products.append(product)
                    return products
                elif response.status == 404:
                    # No more pages
                    return []
                else:
                    logging.error(
                        f"Error fetching page {page}: Status {response.status}"
                    )
                    raise Exception(f"Failed to fetch page {page}")
        except Exception as e:
            logging.error(f"Error scraping page {page}: {str(e)}")
            raise

    async def _scrape_with_retry(self, page: int) -> List[Product]:
        for attempt in range(settings.RETRY_ATTEMPTS):
            try:
                return await self._scrape_page(page)
            except Exception as e:
                if attempt == settings.RETRY_ATTEMPTS - 1:
                    raise e
                logging.warning(
                    f"Retry {attempt + 1}/{settings.RETRY_ATTEMPTS} for page {page}"
                )
                await asyncio.sleep(settings.RETRY_DELAY)

    async def scrape(self, scraping_settings: ScrapingSettings) -> int:
        await self._init_session(scraping_settings.proxy)

        try:
            page = 1
            total_products = 0
            updated_products = 0
            all_products = []

            while True:
                if scraping_settings.page_limit and page > scraping_settings.page_limit:
                    break

                try:
                    products = await self._scrape_with_retry(page)
                    if not products:
                        break

                    for product in products:
                        cache_key = f"product:{product.product_title}"
                        cached_price = self.redis.get(cache_key)

                        if (
                            cached_price is None
                            or float(cached_price) != product.product_price
                        ):
                            self.redis.set(cache_key, str(product.product_price))
                            updated_products += 1

                        total_products += 1
                        all_products.append(product)

                    logging.info(f"Scraped page {page}")
                    page += 1
                    #write in bacthes
                    await self.storage.save_products(products)

                    # Add a small delay between pages to be respectful
                    await asyncio.sleep(1)

                except Exception as e:
                    await self.notification.notify(
                        f"Error during scraping page {page}: {str(e)}"
                    )
                    raise e


            await self.notification.notify(
                f"Scraping completed. Total products: {total_products}, Updated: {updated_products}"
            )
            return total_products

        finally:
            if self.session:
                await self.session.close()
