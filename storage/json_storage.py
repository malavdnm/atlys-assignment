import json
import os
from typing import List
from models import Product
from storage.base import StorageStrategy


class JsonStorage(StorageStrategy):
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def save_products(self, products: List[Product]):
        with open(self.file_path, "w") as f:
            json.dump([product.dict() for product in products], f, indent=2)

    async def get_products(self) -> List[Product]:
        if not os.path.exists(self.file_path):
            return []
        with open(self.file_path, "r") as f:
            data = json.load(f)
            return [Product(**product) for product in data]
