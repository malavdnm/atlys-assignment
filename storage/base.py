from abc import ABC, abstractmethod
from typing import List
from models import Product


class StorageStrategy(ABC):
    @abstractmethod
    async def save_products(self, products: List[Product]):
        pass

    @abstractmethod
    async def get_products(self) -> List[Product]:
        pass
