import socket
from unittest.mock import patch

with patch.object(socket, 'getaddrinfo', return_value=[(None, None, None, None, ('127.0.0.1', 0))]):
    from layer1_ingestion.crawler.playwright_crawler import PlaywrightCrawler
    from layer1_ingestion.compliance.url_safety import validate_url_safety
    
    # Check if they're the same function
    crawler_val = PlaywrightCrawler.crawl_url.__globals__.get('validate_url_safety')
    print(f'crawl_url globals validate_url_safety: {crawler_val}')
    print(f'direct import validate_url_safety: {validate_url_safety}')
    print(f'Same object? {crawler_val is validate_url_safety}')
    
    # Try calling the one from crawl_url globals
    if crawler_val:
        try:
            crawler_val('http://127.0.0.1/')
            print('crawler_val: NO EXCEPTION')
        except Exception as e:
            print(f'crawler_val: {type(e).__name__} {e}')
