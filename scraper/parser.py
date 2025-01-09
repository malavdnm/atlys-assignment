import logging
import os
from typing import Optional

import aiohttp
from models import Product
import aiofiles
from config import settings


class Parser:
    async def _download_image(self, url: str, product_title: str, session: aiohttp.ClientSession) -> str:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    # Create a valid filename from the product title
                    safe_title = "".join(
                        c for c in product_title if c.isalnum() or c in (" ", "-", "_")
                    ).rstrip()
                    if not safe_title:
                        safe_title = "default_image"
                    file_name = os.path.join(settings.IMAGES_PATH, f"{safe_title}.jpg")
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
        try:
            if not img_element:
                return None

            img_url = img_element.get("data-lazy-src")
            if not img_url or img_url.endswith("svg+xml"):
                img_url = img_element.get("src")

            if not img_url or img_url.endswith("svg+xml"):
                srcset = img_element.get("srcset")
                if srcset:
                    img_url = srcset.split(",")[0].strip().split(" ")[0]

            if not img_url or img_url.endswith("svg+xml"):
                lazy_srcset = img_element.get("data-lazy-srcset")
                if lazy_srcset:
                    img_url = lazy_srcset.split(",")[0].strip().split(" ")[0]

            return img_url
        except Exception as e:
            logging.error(f"Error extracting image URL: {str(e)}")
            return None

    def _get_product_name(self, product_element) -> Optional[str]:
        """
        Extracts the product name from the product element.
        """
        try:
            title_element = product_element.find(
                "h2", class_="woo-loop-product__title"
            ).find("a")
            if not title_element:
                logging.warning("No title element found")
                return None

            title_tag = product_element.find("a", {"data-title": True})
            title = (
                title_tag["data-title"].strip()
                if title_tag and "data-title" in title_tag.attrs
                else title_element.text.strip()
            )

            if not title:
                logging.warning("Product title is empty")
                return None

            return title
        except Exception as e:
            logging.error(f"Error extracting product name: {str(e)}")
            return None

    def _get_product_price(self, product_element) -> Optional[float]:
        """
        Extracts the product price from the product element.
        """
        try:
            price_box = product_element.find("span", class_="price")
            if not price_box:
                logging.warning("No price found for the product")
                return None

            sale_price = price_box.find("ins")
            price_element = (
                sale_price.find("span", class_="woocommerce-Price-amount")
                if sale_price
                else price_box.find("span", class_="woocommerce-Price-amount")
            )

            if not price_element:
                logging.warning("No price element found for the product")
                return None

            price_text = price_element.text.strip()
            try:
                price_value = float(price_text.replace("₹", "").replace(",", "").strip())
            except ValueError:
                logging.error(f"Invalid price format: {price_text}")
                return None

            return price_value
        except Exception as e:
            logging.error(f"Error extracting product price: {str(e)}")
            return None

    async def parse_product(self, product_element, session: aiohttp.ClientSession) -> Optional[Product]:
        try:
            # Extract product name
            title = self._get_product_name(product_element)
            if not title:
                return None

            # Extract product price
            price_value = self._get_product_price(product_element)
            if price_value is None:
                logging.warning(f"Skipping product due to missing price: {title}")
                return None

            # Extract image URL
            img_element = product_element.find(
                "img", class_="attachment-woocommerce_thumbnail"
            )
            if not img_element:
                logging.warning(f"No image element found for product: {title}")
                return None

            img_url = await self._get_image_url(img_element)
            if not img_url:
                logging.warning(f"No valid image URL found for product: {title}")
                return None

            # Download image
            image_path = await self._download_image(img_url, title, session)
            if not image_path:
                logging.warning(f"Failed to download image for product: {title}")
                return None

            logging.info(f"Parsed product successfully: {title}")
            return Product(
                product_title=title, product_price=price_value, path_to_image=image_path
            )
        except Exception as e:
            logging.error(f"Error parsing product: {str(e)}")
            return None