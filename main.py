#!/usr/bin/env python3
"""
Main entry point for Kenya Law Web Scraping Challenge
Provides CLI interface to run all scrapers.
"""

import argparse
import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from case_extraction import LawExtractionScraper
from legislation import LegislationScraper
from case_analysis import CaseAnalysisScraper


def run_case_extraction(args):
    """Run case_extraction scraper."""
    print("Starting Basic Case Law Extraction")
    print(f"   Target: {args.num_cases} recent cases")
    
    scraper = LawExtractionScraper()
    cases = scraper.scrape(num_cases=args.num_cases)
    
    if cases:
        success = scraper.save_data(cases, args.output)
        if success:
            print(f"Successfully extracted and saved {len(cases)} cases")
            print(f"    Output: {args.output}")
        else:
            print("Failed to save data")
    else:
        print("Failed to extract any cases")


def run_legislation(args):
    """Run legislation scraper."""
    print("🚀 Starting Legislation Database")
    print(f"   Target: {args.min_acts}+ Acts")
    
    scraper = LegislationScraper()
    acts = scraper.scrape(min_acts=args.min_acts)
    
    if acts:
        success = scraper.save_data(acts, args.output)
        if success:
            print(f"✅ Successfully extracted and saved {len(acts)} Acts")
            print(f"   Output: {args.output}")
        else:
            print("Failed to save data")
    else:
        print("Failed to extract any Acts")


def run_case_analysis(args):
    """Run case_analysis scraper."""
    print("Starting Full-Text Case Analysis")
    print(f"    Target: {args.num_cases} cases")
    
    scraper = CaseAnalysisScraper()
    
    # Get case URLs if provided
    case_urls = None
    if args.urls:
        case_urls = args.urls
    
    analyzed_cases = scraper.scrape(case_urls=case_urls, num_cases=args.num_cases)
    
    if analyzed_cases:
        success = scraper.save_data(analyzed_cases, args.output)
        if success:
            print(f"Successfully analyzed and saved {len(analyzed_cases)} cases")
            print(f"   Output: {args.output}")
        else:
            print("Failed to save data")
    else:
        print("Failed to analyze any cases")


def run_all(args):
    """Run all scrapers sequentially."""
    print("Starting All Scrapers: Complete Kenya Law Scraping")
    print("=" * 60)
    
    # case_extraction
    print("\n📋 Basic Case Law Extraction")
    case_extraction_scraper = LawExtractionScraper()
    cases = case_extraction_scraper.scrape(num_cases=args.num_cases)
    
    if cases:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        case_extraction_output = f'output/cases_{timestamp}.csv'
        case_extraction_scraper.save_data(cases, case_extraction_output)
        print(f"Case extraction completed: {len(cases)} cases saved")
    else:
        print("Case extraction failed")
        return
    
    # legislation
    print("\n Legislation Database")
    legislation_scraper = LegislationScraper()
    acts = legislation_scraper.scrape(min_acts=args.min_acts)
    
    if acts:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        legislation_output = f'output/legislation_{timestamp}.json'
        legislation_scraper.save_data(acts, legislation_output)
        print(f"Legislation extraction completed: {len(acts)} Acts saved")
    else:
        print("Legislation extraction failed")
        return
    
    # case_analysis
    print("\n🔍 Full-Text Case Analysis")
    case_analysis_scraper = CaseAnalysisScraper()
    analyzed_cases = case_analysis_scraper.scrape(num_cases=args.num_cases)
    
    if analyzed_cases:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        case_analysis_output = f'output/case_analysis_{timestamp}.json'
        case_analysis_scraper.save_data(analyzed_cases, case_analysis_output)
        print(f"Case analysis completed: {len(analyzed_cases)} cases analyzed")
    else:
        print("Case analysis failed")
        return
    
    print("\n" + "=" * 60)
    print("All scrapers completed successfully!")
    print(f"Summary:")
    print(f"   Case Extraction: {len(cases)} cases extracted")
    print(f"   Legislation: {len(acts)} Acts extracted")
    print(f"   Case Analysis: {len(analyzed_cases)} cases analyzed")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Kenya Law Web Scraping Challenge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py case_extraction --num-cases 15
  python main.py legislation --min-acts 75 --output my_acts.json
  python main.py case_analysis --num-cases 25 --output analysis.json
  python main.py all --num-cases 10 --min-acts 50
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # case_extraction parser
    case_extraction_parser = subparsers.add_parser('case_extraction', help='Run case_extraction scraper')
    case_extraction_parser.add_argument('--num-cases', type=int, default=10,
                               help='Number of cases to extract (default: 10)')
    case_extraction_parser.add_argument('--output', type=str,
                               help='Output filename (default: auto-generated)')
    case_extraction_parser.set_defaults(func=run_case_extraction)
    
    # legislation parser
    legislation_parser = subparsers.add_parser('legislation', help='Run legislation scraper')
    legislation_parser.add_argument('--min-acts', type=int, default=50,
                               help='Minimum number of Acts to extract (default: 50)')
    legislation_parser.add_argument('--output', type=str,
                               help='Output filename (default: auto-generated)')
    legislation_parser.set_defaults(func=run_legislation)
    
    # case_analysis parser
    case_analysis_parser = subparsers.add_parser('case_analysis', help='Run case_analysis scraper')
    case_analysis_parser.add_argument('--num-cases', type=int, default=20,
                               help='Number of cases to analyze (default: 20)')
    case_analysis_parser.add_argument('--urls', nargs='*',
                               help='Specific case URLs to analyze')
    case_analysis_parser.add_argument('--output', type=str,
                               help='Output filename (default: auto-generated)')
    case_analysis_parser.set_defaults(func=run_case_analysis)
    
    # All scrapers parser
    all_parser = subparsers.add_parser('all', help='Run all scrapers')
    all_parser.add_argument('--num-cases', type=int, default=10,
                           help='Number of cases for case_extraction & case_analysis (default: 10)')
    all_parser.add_argument('--min-acts', type=int, default=50,
                           help='Minimum number of Acts for legislation (default: 50)')
    all_parser.set_defaults(func=run_all)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create output directory
    os.makedirs('output', exist_ok=True)
    
    # Run the appropriate function
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n Scraping interrupted by user")
    except Exception as e:
        print(f" Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
