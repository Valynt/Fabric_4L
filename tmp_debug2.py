import socket
import asyncio
from unittest.mock import patch

with patch.object(socket, 'getaddrinfo', return_value=[(None, None, None, None, ('127.0.0.1', 0))]):
    from layer1_ingestion.crawler.playwright_crawler import PlaywrightCrawler
    from layer1_ingestion.compliance.url_safety import validate_url_safety, URLSafetyError

    # Test 1: validate_url_safety directly
    try:
        validate_url_safety('http://127.0.0.1/')
        print('validate_url_safety: NO EXCEPTION')
    except URLSafetyError as e:
        print(f'validate_url_safety: URLSafetyError {e.reason_code}')

    # Test 2: PlaywrightCrawler.crawl_url
    crawler = PlaywrightCrawler(enable_telemetry=False)
    async def test():
        try:
            await crawler.crawl_url('http://127.0.0.1/')
            print('crawl_url: NO EXCEPTION')
        except URLSafetyError as e:
            print(f'crawl_url: URLSafetyError {e.reason_code}')
        except TypeError as e:
            print(f'crawl_url: TypeError {e}')

    asyncio.run(test())
