# Kenya Law Web Scraping Challenge 🇰🇪

## Overview
Kenya Law (kenyalaw.org) is the official repository of Kenya's laws, case law reports, and legal publications maintained by the National Council for Law Reporting. Your challenge is to build a robust web scraper to extract legal data from this important resource.

## Challenge Levels

### Level 1: Basic Case Law Extraction ⭐
**Objective**: Scrape recent court judgments/case law

**Tasks**:
- Navigate to the Kenya Law Reports section
- Extract the following for at least 25 recent cases:
  - Case name/title
  - Citation reference
  - Court name
  - Date of judgment
  - Judge(s) name(s)
- Save results to a CSV file

---

### Level 2: Legislation Database ⭐⭐
**Objective**: Build a comprehensive Acts/Bills scraper

**Tasks**:
- Access the Laws of Kenya database
- For each Act, extract:
  - Act title
  - Chapter number
  - Year enacted
  - Download URL (if PDF available)
  - Last revision date
- Categorize by legal area (e.g., Criminal, Civil, Constitutional)
- Store in a structured JSON format

**Success Criteria**: Extract metadata for 25+ Acts with proper categorization

---

### Level 3: Full-Text Case Analysis ⭐⭐⭐
**Objective**: Deep dive into judgment content

**Tasks**:
- Scrape full judgment text for 25+ cases
- Extract structured information:
  - Parties involved (plaintiff/defendant)
  - Case summary/synopsis
  - Legal issues presented
  - Court's decision/ruling
  - Key legal principles cited
- Implement text cleaning and paragraph separation
- Store with proper Unicode handling for special characters

**Success Criteria**: Clean, parsed judgment text with extracted elements

---

## Technical Implementation
This project has been fully migrated to an asynchronous architecture using `asyncio`, `aiohttp`, and `AsyncElasticsearch` for maximum performance and concurrent scraping.

### Stack
- **Languages**: Python 3.11+
- **Asynchronous IO**: `asyncio`, `aiohttp`, `aiofiles`
- **Scraping**: `BeautifulSoup4`, `lxml`
- **Storage**: Elasticsearch (Asynchronous indexing)
- **Utilities**: `fake-useragent`, `python-dateutil`

## Getting Started
1. Install dependencies: `pip install -r requirements.txt`
2. Configure Elasticsearch in `.env`
3. Run scrapers via `main.py`:
   - `python main.py case_extraction --num-cases 25`
   - `python main.py legislation --min-acts 25`
   - `python main.py case_analysis --num-cases 25`
   - `python main.py all --concurrent`

## Resources
- **Website**: http://www.kenyalaw.org/
- **Legal Database**: https://new.kenyalaw.org/

**Good luck! Remember: scrape responsibly and ethically.** 🚀
