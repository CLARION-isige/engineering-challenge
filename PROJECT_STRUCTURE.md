# Project Structure

## Directory Layout

```
engineering-challenge/
├── README.md                    # Project overview and challenge description
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── DATABASE_SETUP.md            # Elasticsearch setup guide
├── USAGE.md                     # Usage instructions
├── PROJECT_STRUCTURE.md         # This file
├── src/                         # Source code directory
│   ├── __init__.py             # Package initialization
│   ├── utils/                  # Utility modules
│   │   ├── __init__.py
│   │   ├── logger.py           # Logging configuration
│   │   └── scraper_base.py     # Base scraper class
│   ├── config/                 # Configuration modules
│   │   └── elasticsearch.py    # Elasticsearch configuration
│   ├── case_extraction.py        # Basic case law extraction
│   ├── legislation.py           # Legislation database scraper
│   └── case_analysis.py          # Full-text case analysis scraper
├── tests/                      # Test suite
│   ├── __init__.py
│   └── test_scraper.py         # Scraper connectivity tests
├── output/                     # Generated output files
│   ├── cases_*.csv             # Case extraction results
│   ├── legislation_*.json       # Legislation results
│   ├── legislation_summary_*.json # Legislation statistics
│   ├── case_analysis_*.json     # Case analysis results
│   └── case_analysis_summary_*.json # Analysis statistics
└── logs/                       # Log files
    ├── case_extraction_*.log
    ├── legislation_*.log
    └── case_analysis_*.log
```

## Component Overview

### Core Scrapers

#### case_extraction.py
- **Purpose**: Basic case law extraction
- **Target**: Recent court judgments
- **Output**: CSV files with case metadata
- **Key Features**:
  - Extracts case name, citation, court, date, judges
  - Supports both old and new Kenya Law websites
  - Automatic fallback between sites
  - Elasticsearch integration

#### legislation.py
- **Purpose**: Comprehensive legislation database
- **Target**: Acts of Parliament and Bills
- **Output**: JSON files with categorization
- **Key Features**:
  - Extracts Act metadata and download URLs
  - Automatic legal categorization
  - Summary statistics generation
  - Chapter number and year extraction

#### case_analysis.py
- **Purpose**: Full-text judgment analysis
- **Target**: Complete case documents
- **Output**: JSON with structured analysis
- **Key Features**:
  - Full text extraction and cleaning
  - Legal issue identification
  - Party and advocate extraction
  - Precedent and principle identification
  - Unicode text handling

### Utility Modules

#### `utils/scraper_base.py`
- **Purpose**: Common scraping functionality
- **Features**:
  - HTTP session management
  - Rate limiting and retry logic
  - User agent rotation
  - Error handling

#### `utils/logger.py`
- **Purpose**: Centralized logging configuration
- **Features**:
  - File and console logging
  - Timestamped log files
  - Configurable log levels
  - Automatic log directory creation

#### `config/elasticsearch.py`
- **Purpose**: Database integration
- **Features**:
  - Connection management
  - Index creation and mapping
  - Document indexing
  - Search functionality
  - Authentication support

### Configuration

#### Environment Variables (`.env`)
```env
# Elasticsearch Configuration
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=kenya_law
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=

# Scraping Configuration
REQUEST_DELAY=1
MAX_RETRIES=3
TIMEOUT=30

# Logging
LOG_LEVEL=INFO
```

#### Dependencies (`requirements.txt`)
- **Web Scraping**: requests, beautifulsoup4, lxml, selenium, aiohttp
- **Data Processing**: pandas, numpy
- **Storage**: elasticsearch, python-dotenv
- **Text Processing**: nltk, spacy
- **Utilities**: fake-useragent, tqdm, python-dateutil

## Data Flow

### case_extraction Flow
1. Initialize scraper
2. Access Kenya Law website (new site first, fallback to old)
3. Parse case listings
4. Extract metadata for each case
5. Save to CSV and optionally Elasticsearch

### legislation Flow
1. Initialize scraper
2. Access legislation database
3. Parse Act listings
4. Extract metadata and categorize
5. Generate summary statistics
6. Save to JSON and optionally Elasticsearch

### case_analysis Flow
1. Initialize scraper
2. Get case URLs (from case_extraction or direct search)
3. Access individual case pages
4. Extract full judgment text
5. Perform structured analysis
6. Save analysis to JSON and optionally Elasticsearch

## Error Handling Strategy

### Network Errors
- Automatic retry with exponential backoff
- Fallback between old and new websites
- Connection timeout handling

### Parsing Errors
- Graceful degradation for missing elements
- Multiple selector strategies
- Logging of parsing failures

### Data Validation
- Type checking for extracted fields
- Minimum data quality requirements

## Extensibility

### Adding New Scrapers
1. Inherit from `ScraperBase`
2. Implement `scrape()` and `save_data()` methods
3. Add specific extraction logic
4. Configure output format

### Adding New Data Sources
1. Update base URLs in scraper
2. Add new parsing selectors
3. Implement source-specific logic
4. Test with sample data

### Custom Analysis
1. Extend text processing patterns
2. Add new legal categories
3. Implement custom extraction rules
4. Update output schemas

## Security Considerations

### Rate Limiting
- Configurable delays between requests
- Random additional delays
- Respect for robots.txt

### Data Privacy
- No personal data collection
- Public domain information only
- Secure credential handling

### Error Information
- No sensitive data in logs
- Sanitized error messages
- Secure connection handling
