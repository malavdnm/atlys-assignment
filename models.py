from typing import Optional, List
from pydantic import BaseModel
from typing_extensions import TypeAlias


class ScrapingSettings(BaseModel):
    page_limit: Optional[int] = None
    proxy: Optional[str] = None


class Product(BaseModel):
    product_title: str
    product_price: float
    path_to_image: str

class ScrapingResponse(BaseModel):
    job_id: str
    status: str
    message: str