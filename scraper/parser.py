import logging
import os
from typing import Optional
from models import Product
import aiofiles
from config import settings

class Parser:
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
            print(title_element)
            if not title_element:
                return None
            # Get full title from aria-label attribute of add to cart button
            title_tag = product_element.find('a', {'data-title': True})
            # print(title_tag)
            title = title_tag["data-title"] if title_tag else title_element.text.strip()

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
            print(title, price_value, image_path)
            return Product(
                product_title=title, product_price=price_value, path_to_image=image_path
            )
        except Exception as e:
            logging.error(f"Error parsing product: {str(e)}")
            return None