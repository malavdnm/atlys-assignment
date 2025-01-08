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


class Scraper:
    BASE_URL = "https://dentalstall.com/shop/"

    def __init__(self, storage_strategy, notification_strategy):
        self.storage = storage_strategy
        self.notification = notification_strategy
        self.redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.session = None

    async def _init_session(self, proxy: Optional[str] = None):
        if self.session is None:
            if proxy:
                self.session = aiohttp.ClientSession(base_url=proxy)
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

    async def _download_image(self, url: str, product_title: str) -> str:
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    # Create a valid filename from the product title
                    safe_title = "".join(
                        c for c in product_title if c.isalnum() or c in (" ", "-", "_")
                    ).rstrip()
                    file_name = f"{settings.IMAGES_PATH}{safe_title}.jpg"
                    os.makedirs(settings.IMAGES_PATH, exist_ok=True)

                    async with aiofiles.open(file_name, mode="wb") as f:
                        await f.write(await response.read())
                    return file_name
                else:
                    logging.warning(
                        f"Failed to download image from {url}: Status {response.status}"
                    )
                    return ""
        except Exception as e:
            logging.error(f"Error downloading image from {url}: {str(e)}")
            return ""

    async def _get_image_url(self, img_element) -> Optional[str]:
        """
        Extract the actual image URL from the img element handling lazy loading
        """
        if not img_element:
            return None

        # Check data-lazy-src first (actual image URL for lazy-loaded images)
        img_url = img_element.get("data-lazy-src")

        # If no lazy-src, check regular src
        if not img_url or img_url.endswith("svg+xml"):
            img_url = img_element.get("src")

        # If still no URL or it's an SVG placeholder, check srcset
        if not img_url or img_url.endswith("svg+xml"):
            srcset = img_element.get("srcset")
            if srcset:
                # Take the first URL from srcset
                img_url = srcset.split(",")[0].strip().split(" ")[0]

        # If still no URL, try data-lazy-srcset
        if not img_url or img_url.endswith("svg+xml"):
            lazy_srcset = img_element.get("data-lazy-srcset")
            if lazy_srcset:
                # Take the first URL from lazy-srcset
                img_url = lazy_srcset.split(",")[0].strip().split(" ")[0]

        return img_url

    async def _parse_product(self, product_element) -> Optional[Product]:
        try:
            # Find product title - using full title from href/link
            title_element = product_element.find(
                "h2", class_="woo-loop-product__title"
            ).find("a")
            if not title_element:
                return None
            # Get full title from aria-label attribute of add to cart button
            cart_button = product_element.find("a", class_="add_to_cart_button")
            title = (
                cart_button["data-title"] if cart_button else title_element.text.strip()
            )

            # Find price - handle sale prices
            price_box = product_element.find("span", class_="price")
            if not price_box:
                return None

            # Try to get sale price first (ins tag), if not found get regular price
            sale_price = price_box.find("ins")
            if sale_price:
                price_element = sale_price.find(
                    "span", class_="woocommerce-Price-amount"
                )
            else:
                price_element = price_box.find(
                    "span", class_="woocommerce-Price-amount"
                )

            if not price_element:
                return None

            # Extract price value and handle different formats
            price_text = price_element.text.strip()
            # Remove currency symbol and convert to float
            price_value = float(price_text.replace("₹", "").replace(",", "").strip())

            # Find image URL - handle lazy loading
            img_element = product_element.find(
                "img", class_="attachment-woocommerce_thumbnail"
            )
            if not img_element:
                return None

            img_url = await self._get_image_url(img_element)
            if not img_url:
                return None

            # Download image
            image_path = await self._download_image(img_url, title)

            return Product(
                product_title=title, product_price=price_value, path_to_image=image_path
            )
        except Exception as e:
            logging.error(f"Error parsing product: {str(e)}")
            return None

    async def _scrape_page(self, page: int) -> List[Product]:
        url = f"{self.BASE_URL}/page/{page}/" if page > 1 else self.BASE_URL

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
                        product = await self._parse_product(element)
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

                    page += 1
                    # Add a small delay between pages to be respectful
                    await asyncio.sleep(1)

                except Exception as e:
                    await self.notification.notify(
                        f"Error during scraping page {page}: {str(e)}"
                    )
                    raise e

            # Save all products at once
            await self.storage.save_products(all_products)

            await self.notification.notify(
                f"Scraping completed. Total products: {total_products}, Updated: {updated_products}"
            )
            return total_products

        finally:
            if self.session:
                await self.session.close()
