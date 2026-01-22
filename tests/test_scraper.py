#!/usr/bin/env python3
"""Test script to verify scraper configuration and connectivity."""

import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from case_extraction import LawExtractionScraper

def test_scraper():
    print("=== Scraper Configuration Test ===")
    
    # Show environment variables
    print("Environment Variables:")
    print(f"  REQUEST_DELAY: {os.getenv('REQUEST_DELAY', 'not set')}")
    print(f"  MAX_RETRIES: {os.getenv('MAX_RETRIES', 'not set')}")
    print(f"  TIMEOUT: {os.getenv('TIMEOUT', 'not set')}")
    print()
    
    # Initialize scraper
    scraper = LawExtractionScraper()
    
    print("Scraper Configuration:")
    print(f"  Timeout: {scraper.timeout}s")
    print(f"  Max retries: {scraper.max_retries}")
    print(f"  Request delay: {scraper.request_delay}s")
    print()
    
    # Test basic connectivity
    print("=== Connectivity Test ===")
    
    # Test main site
    print("Testing main site...")
    response = scraper._make_request('https://kenyalaw.org')
    if response:
        print(f"✓ Main site accessible: {response.status_code}")
        print(f"  Final URL: {response.url}")
    else:
        print("✗ Main site failed")
    
    # Test old site case page
    print("\nTesting old case page...")
    response = scraper._make_request('https://kenyalaw.org/kl/index.php?id=87', follow_redirects=False)
    if response:
        print(f"✓ Old case page accessible: {response.status_code}")
    else:
        print("✗ Old case page failed")
    
    # Test new site feed
    print("\nTesting new site feed...")
    response = scraper._make_request('https://new.kenyalaw.org/feeds/all.xml')
    if response:
        print(f"✓ New site feed accessible: {response.status_code}")
    else:
        print("✗ New site feed failed")

if __name__ == "__main__":
    test_scraper()
