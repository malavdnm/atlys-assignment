from notifications.base import NotificationStrategy


class ConsoleNotification(NotificationStrategy):
    async def notify(self, message: str):
        print(f"Scraping notification: {message}")
