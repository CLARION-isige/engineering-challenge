"""
Base scraper class with common functionality for all scrapers.
"""

import time
import random
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from .logger import setup_logger

class ScraperBase(ABC):
    """Base class for all scrapers with common functionality."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = setup_logger(name)
        self.session = requests.Session()
        self.ua = UserAgent()
        
        # Configuration
        self.request_delay = float(os.getenv('REQUEST_DELAY', 3.0))
        self.max_retries = int(os.getenv('MAX_RETRIES', 5))
        self.timeout = int(os.getenv('TIMEOUT', 180))
        
        
        # Setup session
        self._setup_session()
        
        # SSL verification for problematic sites
        self.session.verify = False
        
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def _setup_session(self):
        """Setup session with headers and configuration."""
        self.session.headers.update({
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
        })
    
    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
        follow_redirects: bool = True,
    ) -> Optional[requests.Response]:
        """Make HTTP request with retry logic and rate limiting."""
        
        for attempt in range(self.max_retries):
            try:
                # Randomize user agent for each request
                self.session.headers['User-Agent'] = self.ua.random
                
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.timeout,
                    allow_redirects=follow_redirects
                )
                
                # Log redirects for debugging
                if response.history:
                    redirect_chain = " -> ".join([r.url for r in response.history])
                    self.logger.info(f"Redirected: {redirect_chain} -> {response.url}")
                
                response.raise_for_status()
                
                # Rate limiting with jitter
                time.sleep(self.request_delay + random.uniform(0, 0.5))
                
                return response
                
            except requests.Timeout as e:
                self.logger.warning(f"Attempt {attempt + 1} timeout for {url}: {e}")
                if attempt < self.max_retries - 1:
                    # Increase timeout progressively
                    backoff = 2 ** attempt
                    increased_timeout = self.timeout * (1 + attempt * 0.5)
                    self.logger.info(f"Retrying in {backoff}s with increased timeout ({increased_timeout:.0f}s)...")
                    time.sleep(backoff)
                    # Update timeout for next attempt
                    original_timeout = self.timeout
                    self.timeout = increased_timeout
                    try:
                        response = self.session.get(
                            url, 
                            params=params, 
                            timeout=self.timeout,
                            allow_redirects=follow_redirects
                        )
                        response.raise_for_status()
                        time.sleep(self.request_delay + random.uniform(0, 0.5))
                        self.timeout = original_timeout  # Restore original timeout
                        return response
                    except:
                        self.timeout = original_timeout  # Restore on failure
                        raise
                else:
                    self.logger.error(f"All attempts timed out for {url} (max timeout: {self.timeout}s)")
                    return None
                    
            except requests.HTTPError as e:
                self.logger.warning(f"Attempt {attempt + 1} HTTP error for {url}: {e}")
                # Don't retry 4xx errors except 429 (rate limit)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    self.logger.error(f"Client error, not retrying: {e}")
                    return None
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                else:
                    self.logger.error(f"All attempts failed for {url}")
                    return None
                    
            except requests.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                else:
                    self.logger.error(f"All attempts failed for {url}")
                    return None
    
    def _parse_html(self, response: requests.Response) -> Optional[BeautifulSoup]:
        """Parse HTML response."""
        try:
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {e}")
            return None
    
    @abstractmethod
    def scrape(self, **kwargs) -> Any:
        """Abstract method for scraping implementation."""
        pass
    
    @abstractmethod
    def save_data(self, data: Any, filename: str) -> bool:
        """Abstract method for saving data."""
        pass
    