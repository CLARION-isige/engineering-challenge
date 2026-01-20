# Usage Guide

## Quick Start

### 1. Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd engineering-challenge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 2. Run Scrapers

#### Basic Case Law Extraction
```bash
python main.py case_extraction --num-cases 15
```
- Extracts 15 recent cases
- Saves to `output/cases_[timestamp].csv`
- Optional: Saves to Elasticsearch if configured

#### Legislation Database
```bash
python main.py legislation --min-acts 75
```
- Extracts 75+ Acts with categorization
- Saves to `output/legislation_[timestamp].json`
- Generates summary statistics

#### Full-Text Case Analysis
```bash
python main.py case_analysis --num-cases 25
```
- Analyzes 25+ cases in detail
- Extracts structured information from full judgments
- Saves to `output/case_analysis_[timestamp].json`

## Advanced Usage

### Custom Parameters

#### case_extraction - Custom Number of Cases
```python
from case_extraction import LawExtractionScraper

scraper = LawExtractionScraper()
cases = scraper.scrape(num_cases=25)  # Extract 25 cases
scraper.save_data(cases, 'my_cases.csv')

# Get session statistics
stats = scraper.get_session_stats()
print(f"Session duration: {stats['duration_seconds']:.1f}s")
print(f"Items processed: {stats['processed_items']}")
```

#### legislation - Custom Target
```python
from legislation import LegislationScraper

scraper = LegislationScraper()
acts = scraper.scrape(min_acts=100)  # Extract 100 Acts
scraper.save_data(acts, 'kenya_acts.json')
```

#### case_analysis - Specific Cases
```python
from case_analysis import CaseAnalysisScraper

scraper = CaseAnalysisScraper()
case_urls = [
    'https://new.kenyalaw.org/judgments/case/123',
    'https://new.kenyalaw.org/judgments/case/456'
]
analysis = scraper.scrape(case_urls=case_urls)
scraper.save_data(analysis, 'specific_cases.json')
```


### Using Elasticsearch

1. **Setup Elasticsearch** (see DATABASE_SETUP.md)

2. **Configure Environment**
```env
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=kenya_law
```

3. **Run Scrapers**
   Data will be automatically indexed to Elasticsearch

4. **Search Data**
```python
from config.elasticsearch import ElasticsearchConfig

es = ElasticsearchConfig()
results = es.search({
    "query": {
        "match": {
            "case_name": "constitution"
        }
    }
})
```

## Output Formats

#### CSV Structure
```csv
case_name,citation,court,judgment_date,judges,source_url,scraped_at
"John Doe v Republic","2023 KLR 123","High Court","2023-01-15","J. Smith","https://...","2023-01-20T10:30:00"
```

#### Legislation JSON Structure
```json
[
  {
    "act_title": "Constitution of Kenya",
    "chapter_number": "1",
    "year_enacted": "2010",
    "download_url": "https://...",
    "legal_category": "Constitutional",
    "source_url": "https://...",
    "scraped_at": "2023-01-20T10:30:00"
  }
]
```

#### Case Analysis JSON Structure
```json
[
  {
    "source_url": "https://...",
    "full_text": "Full judgment text...",
    "parties": {
      "plaintiff": "John Doe",
      "defendant": "Republic",
      "other_parties": []
    },
    "case_summary": "Brief summary...",
    "legal_issues": ["Issue 1", "Issue 2"],
    "decision": "Court decision...",
    "legal_principles": ["Principle 1"],
    "precedents_cited": ["Case 1", "Case 2"],
    "advocates": ["Advocate 1"],
    "judges": ["Judge 1"],
    "analysis_metadata": {
      "text_length": 15000,
      "word_count": 2500,
      "paragraph_count": 50
    }
  }
]
```

## Error Handling

### Common Issues and Solutions

1. **Connection Timeout**
   - Increase `TIMEOUT` in `.env`
   - Check internet connection
   - Verify website accessibility

2. **Rate Limiting**
   - Increase `REQUEST_DELAY` in `.env`
   - The scrapers include automatic rate limiting

3. **Memory Issues**
   - Process smaller batches
   - Increase system memory
   - Use Elasticsearch for large datasets

4. **Parsing Errors**
   - Website structure may have changed
   - Check logs for specific errors
   - Update selectors in scraper code

### Logging

All scrapers create detailed logs in the `logs/` directory:
- `case_extraction_[timestamp].log`
- `legislation_[timestamp].log`
- `case_analysis_[timestamp].log`

Log levels can be configured in `.env`:
```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## Performance Tips

1. **Parallel Processing**
   - Multiple scrapers can run simultaneously
   - Use different output directories

2. **Caching**
   - Scrapers include session management
   - Consider adding Redis cache for repeated requests

3. **Database Optimization**
   - Use Elasticsearch for large datasets
   - Create appropriate indices for searching

4. **Resource Management**
   - Monitor memory usage
   - Use appropriate `REQUEST_DELAY` settings
   - Consider using proxies for large-scale scraping

## Ethical Scraping

1. **Rate Limiting**
   - Default delay: 1 second between requests
   - Random additional delay: 0-0.5 seconds

2. **User Agents**
   - Rotating user agents
   - Respect robots.txt

3. **Data Usage**
   - For research and educational purposes
   - Respect copyright and licensing

4. **Server Load**
   - Avoid concurrent requests to same domain
   - Monitor server response times
