# Kenya Law Web Scraping Challenge 🇰🇪

## Overview
Kenya Law (kenyalaw.org) is the official repository of Kenya's laws, case law reports, and legal publications maintained by the National Council for Law Reporting. Your challenge is to build a robust web scraper to extract legal data from this important resource.

## Challenge Levels

### Level 1: Basic Case Law Extraction ⭐
**Objective**: Scrape recent court judgments/case law

**Tasks**:
- Navigate to the Kenya Law Reports section
- Extract the following for at least 10 recent cases:
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

**Success Criteria**: Extract metadata for 50+ Acts with proper categorization

---

### Level 3: Full-Text Case Analysis ⭐⭐⭐
**Objective**: Deep dive into judgment content

**Tasks**:
- Scrape full judgment text for 20+ cases
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

## Technical Requirements

### Tools Suggested
- **Python**: aiohttp and BeautifulSoup4
- **Storage**: Elasticsearch


## Resources
- **Website**: http://www.kenyalaw.org/
- **Useful Python Libraries**: requests, BeautifulSoup4, lxml, pandas, selenium
- **Documentation**: robots.txt parser, rate limiting strategies

**Good luck! Remember: scrape responsibly and ethically.** 🚀
