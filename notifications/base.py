from abc import ABC, abstractmethod


class NotificationStrategy(ABC):
    @abstractmethod
    async def notify(self, message: str):
        pass


# notifications/console.py
from notifications.base import NotificationStrategy


class ConsoleNotification(NotificationStrategy):
    async def notify(self, message: str):
        print(f"Scraping notification: {message}")
