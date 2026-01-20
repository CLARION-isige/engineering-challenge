import asyncio
import random
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Union
import aiohttp
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from .logger import setup_logger

class ScraperBase(ABC):
    """Base class for all scrapers with async functionality."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = setup_logger(name)
        self.ua = UserAgent()
        
        # Configuration
        self.request_delay = float(os.getenv('REQUEST_DELAY', 1.0))
        self.max_retries = int(os.getenv('MAX_RETRIES', 5))
        self.timeout = int(os.getenv('TIMEOUT', 180))
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp ClientSession."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=False, limit=10) # limit=10 for concurrency control
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers=self._get_default_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self.session

    def _get_default_headers(self) -> Dict[str, str]:
        """Return default headers for the session."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.info("Aiohttp session closed.")

    async def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
        follow_redirects: bool = True,
        method: str = 'GET',
        headers: Optional[Dict] = None
    ) -> Optional[str]:
        """Make async HTTP request with retry logic and rate limiting."""
        session = await self._get_session()
        
        for attempt in range(self.max_retries):
            try:
                # Randomize user agent for each request
                request_headers = headers or {}
                request_headers['User-Agent'] = self.ua.random
                
                async with session.request(
                    method,
                    url,
                    params=params,
                    headers=request_headers,
                    allow_redirects=follow_redirects
                ) as response:
                    
                    if response.history:
                        redirect_chain = " -> ".join([str(r.url) for r in response.history])
                        self.logger.info(f"Redirected: {redirect_chain} -> {response.url}")
                    
                    if response.status == 429:
                        self.logger.warning(f"Rate limited (429) for {url}. Retrying...")
                        raise aiohttp.ClientResponseError(
                            response.request_info, response.history, status=429
                        )
                    
                    response.raise_for_status()
                    
                    # Rate limiting with jitter
                    if self.request_delay > 0:
                        await asyncio.sleep(self.request_delay + random.uniform(0, 0.5))
                    
                    return await response.text()
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                
                if isinstance(e, aiohttp.ClientResponseError) and 400 <= e.status < 500 and e.status != 429:
                    self.logger.error(f"Client error {e.status}, not retrying: {e}")
                    return None
                
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt
                    self.logger.info(f"Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                else:
                    self.logger.error(f"All attempts failed for {url}")
                    return None
        return None

    def _parse_html(self, html_content: str) -> Optional[BeautifulSoup]:
        """Parse HTML content."""
        if not html_content:
            return None
        try:
            return BeautifulSoup(html_content, 'lxml')
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")
            return None
    
    @abstractmethod
    async def scrape(self, **kwargs) -> Any:
        """Abstract method for scraping implementation."""
        pass
    
    @abstractmethod
    async def save_data(self, data: Any, filename: str) -> bool:
        """Abstract method for saving data."""
        pass
    