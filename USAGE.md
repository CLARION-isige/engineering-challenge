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
python main.py case_extraction --num-cases 25
```
- Extracts 25 recent cases concurrently
- Saves to `output/cases_[timestamp].csv`
- Automatically indexes to Elasticsearch if configured

#### Legislation Database
```bash
python main.py legislation --min-acts 25
```
- Extracts 25+ Acts with categorization
- Saves to `output/legislation_[timestamp].json`
- Generates summary statistics

#### Full-Text Case Analysis
```bash
python main.py case_analysis --num-cases 25
```
- Analyzes 25+ cases in detail concurrently
- Extracts structured information from full judgments
- Saves to `output/case_analysis_[timestamp].json`

#### Running all the scrapers 
```bash
python main.py all --num-cases 10 --min-acts 50 --concurrent
```


#### Run all Scrapers concurrently with default values
```bash
python main.py all --concurrent
```

#### Run all scrapers sequentially with default values
```bash
python main.py all 
```

## Advanced Usage (Async API)

All scrapers now support asynchronous operations for high-performance concurrent scraping.

#### Programmatic Usage (Async)
```python
import asyncio
from case_extraction import LawExtractionScraper

async def main():
    scraper = LawExtractionScraper()
    try:
        cases = await scraper.scrape(num_cases=25)
        await scraper.save_data(cases, 'my_cases.csv')
    finally:
        await scraper.close() # Close aiohttp session
        await scraper.es_config.close() # Close ES client

asyncio.run(main())
```

#### case_analysis - Concurrent Analysis
```python
import asyncio
from case_analysis import CaseAnalysisScraper

async def main():
    scraper = CaseAnalysisScraper()
    case_urls = [
        'https://new.kenyalaw.org/judgments/case/123',
        'https://new.kenyalaw.org/judgments/case/456'
    ]
    # Analysis happens concurrently
    analysis = await scraper.scrape(case_urls=case_urls)
    await scraper.save_data(analysis, 'specific_cases.json')
    await scraper.close()

asyncio.run(main())
```

### Using Elasticsearch (Async)
 
 1. **Setup Elasticsearch** (see DATABASE_SETUP.md)
 2. **Configure Environment** in `.env`
 3. **Run Scrapers**: Data is indexed asynchronously via `AsyncElasticsearch`.
 
 The system stores three types of documents in the same index, distinguishable by the `document_type` field:
 - `case_law`: Basic citation and metadata from `case_extraction`.
 - `legislation`: Act titles, chapters, and years from `legislation`.
 - `case_analysis`: Full text analysis, parties, and legal principles from `case_analysis`.
 
 #### Searching Data (Async)
 ```python
 import asyncio
 from config.elasticsearch import ElasticsearchConfig
 
 async def search():
     es = ElasticsearchConfig()
     await es.connect()
     # Example: Search for legislation only
     results = await es.search({
         "query": {
             "bool": {
                 "must": { "match": { "act_title": "constitution" } },
                 "filter": { "term": { "document_type": "legislation" } }
             }
         }
     })
     print(results)
     await es.close()
 
 asyncio.run(search())
 ```

## Performance Improvements
- **Concurrent Requests**: Multiple case details are fetched simultaneously using `asyncio.gather`.
- **Session Pooling**: Efficient reuse of TCP connections via `aiohttp.ClientSession`.
- **Non-blocking DB**: Elasticsearch indexing happens without blocking the scraping loop.
- **Resource Efficiency**: Significantly lower memory and CPU overhead compared to thread-based concurrency.

## Ethical Scraping
1. **Rate Limiting**: Integrated `asyncio.sleep` respects `REQUEST_DELAY`.
2. **Session Identification**: Automatic User-Agent rotation.
3. **Robots.txt**: Scrapers are designed to be respectful of server capacity.

**Good luck! Remember: scrape responsibly and ethically.** 🚀
