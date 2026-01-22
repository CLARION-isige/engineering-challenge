#!/usr/bin/env python3
"""Test improved scraper with multiple fallback strategies."""

import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from case_extraction import LawExtractionScraper

def test_improved_scraper():
    print("=== Improved Scraper Test ===")
    
    # Initialize scraper
    scraper = LawExtractionScraper()
    
    print(f"Configuration:")
    print(f"  Timeout: {scraper.timeout}s")
    print(f"  Max retries: {scraper.max_retries}")
    print(f"  Request delay: {scraper.request_delay}s")
    print()
    
    # Test with small number of cases
    print("Testing with 3 cases...")
    cases = scraper.scrape(num_cases=3)
    
    if cases:
        print(f"✓ Successfully extracted {len(cases)} cases:")
        for i, case in enumerate(cases, 1):
            print(f"  {i}. {case.get('case_name', 'Unknown')}")
            print(f"     URL: {case.get('source_url', 'No URL')}")
    else:
        print("✗ Failed to extract any cases")

if __name__ == "__main__":
    test_improved_scraper()
