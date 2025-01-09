# DentalStall Web Scraper

A FastAPI-based web scraping tool designed to collect product information from DentalStall's online shop. The scraper efficiently collects product names, prices, and images while providing caching capabilities and background job processing.

## Features

- **Automated Scraping**: Scrapes product information from DentalStall's shop
- **Background Processing**: Asynchronous job processing with status tracking
- **Caching**: Redis-based caching to avoid redundant updates
- **Proxy Support**: Optional proxy configuration for request routing
- **Authentication**: Token-based API security
- **Flexible Storage**: Modular storage system (currently JSON-based)
- **Notification System**: Configurable notification system for job status updates
- **Retry Mechanism**: Built-in retry logic for failed requests

## Requirements

- Python 3.8+
- Redis Server
- Rust (if using Pydantic 2.x)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd dentalstall-scraper
```

2. Create a virtual environment:

```bash
python -m venv venv

# On Windows:
.\venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file:

```env
APP_TOKEN=your-secure-token
REDIS_URL=redis://localhost:6379
DB_PATH=products.json
IMAGES_PATH=images/
RETRY_ATTEMPTS=3
RETRY_DELAY=5
```

## Usage

1. Start the Redis server:

```bash
redis-server
```

2. Start the FastAPI server:

```bash
uvicorn main:app --reload
```

3. Make API requests:

Start a scraping job:

```bash
curl -X POST "http://localhost:8000/scrape/" \
-H "Authorization: Bearer your-secure-token" \
-H "Content-Type: application/json" \
-d '{
    "page_limit": 5,
    "proxy": "http://proxy:8080"  # Optional
}'
```

Check job status:

```bash
curl -X GET "http://localhost:8000/job/{job_id}" \
-H "Authorization: Bearer your-secure-token"
```

## API Endpoints

### POST /scrape/

Starts a new scraping job.

Request body:

```json
{
  "page_limit": 5, // Optional: limit number of pages to scrape
  "proxy": "http://proxy:8080" // Optional: proxy server URL
}
```

Response:

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "accepted",
  "message": "Scraping job started successfully"
}
```

### GET /job/{job_id}

Retrieves the status of a scraping job.

Response:

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "message": "Job status: running"
}
```

## Project Structure

```
dentalstall-scraper/
├── config.py           # Configuration settings
├── dependencies.py     # FastAPI dependencies
├── main.py            # FastAPI application
├── models.py          # Pydantic models
├── requirements.txt   # Project dependencies
├── scraper/
│   └── scraper.py     # Core scraping logic
├── storage/
│   ├── base.py        # Storage strategy interface
│   └── json_storage.py # JSON storage implementation
└── notifications/
    ├── base.py        # Notification strategy interface
    └── console.py     # Console notification implementation
```

## Storage Strategy

The scraper saves product data in JSON format:

```json
[
  {
    "product_title": "Product Name",
    "product_price": 999.99,
    "path_to_image": "images/product-name.jpg"
  }
]
```

## Error Handling

- Retry mechanism for failed requests (configurable attempts and delay)
- Background job status tracking
- Comprehensive error logging
- Cache validation

## Limitations

- Single-threaded scraping (one page at a time)
- In-memory job status storage (resets on server restart)
- Basic console notifications
- Local file storage for images

## Future Improvements

- [ ] Redis-based job status storage
- [ ] Job cancellation endpoint
- [ ] Progress tracking
- [ ] Webhook notifications
- [ ] Proxy rotation
- [ ] Database storage option
- [ ] Rate limiting
- [ ] Concurrent page scraping
