"""
Basic Case Law Extraction
Extracts recent court judgments/case law from Kenya Law website.
"""

import csv
import os
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import re

from bs4 import BeautifulSoup

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.scraper_base import ScraperBase
from config.elasticsearch import ElasticsearchConfig

class LawExtractionScraper(ScraperBase):
    """Scraper for basic case law extraction."""
    
    def __init__(self):
        super().__init__("case_extraction")
        self.base_url = "https://kenyalaw.org/kl"
        self.new_base_url = "https://new.kenyalaw.org"
        self.es_config = ElasticsearchConfig()
        
        # Create output directory
        os.makedirs('output', exist_ok=True)

    def _normalize_date(self, date_text: str) -> str:
        """Normalize date strings to YYYY-MM-DD when possible."""
        if not date_text:
            return ""

        cleaned = date_text.strip()
        for fmt in (
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%d %B %Y",
            "%d %b %Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
        ):
            try:
                return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        try:
            iso_candidate = cleaned.replace("Z", "+00:00")
            return datetime.fromisoformat(iso_candidate).strftime("%Y-%m-%d")
        except ValueError:
            return cleaned
    
    def scrape(self, num_cases: int = 10) -> List[Dict]:
        """
        Scrape recent case law data.
        
        Args:
            num_cases: Number of cases to extract
            
        Returns:
            List of dictionaries containing case information
        """
        self.logger.info(f"Starting scraping: Extracting {num_cases} recent cases")
        
        # Try multiple approaches in order of reliability
        cases = []
        
        # 1. Try new site first (Primary Source)
        try:
            self.logger.info("Attempting to scrape from new site...")
            cases = self._scrape_new_site(num_cases)
            if cases:
                self.logger.info(f"Successfully extracted {len(cases)} cases from new site")
                return cases
        except Exception as e:
            self.logger.warning(f"New site failed: {e}")

        # 2. Try old site main page (Fallback)
        try:
            self.logger.info("Attempting to scrape from old site main page...")
            cases = self._scrape_old_site_main_page(num_cases)
            if cases:
                self.logger.info(f"Successfully extracted {len(cases)} cases from old site main page")
                return cases
        except Exception as e:
            self.logger.warning(f"Old site main page failed: {e}")
        
        # Complete scraping
        if cases:
            self.logger.info(f"Successfully extracted {len(cases)} cases")
            return cases
        else:
            self.logger.warning("Failed to extract any cases from any source")
            return []

    def _scrape_new_site_feed(self, num_cases: int) -> List[Dict]:
        """Scrape recent judgments from the Kenya Law Atom feed."""
        cases: List[Dict] = []

        try:
            feed_url = f"{self.new_base_url}/feeds/all.xml"
            response = self._make_request(feed_url)
            if not response:
                return cases

            self.logger.info(
                "Feed fetch ok: status=%s content_type=%s size=%s",
                response.status_code,
                response.headers.get("Content-Type"),
                len(response.content),
            )

            soup = BeautifulSoup(response.content, "xml")
            entries = soup.find_all("entry")
            self.logger.info("Feed entries found: %s", len(entries))

            for entry in entries:
                link_elem = entry.find("link", href=True)
                if not link_elem:
                    continue

                link = link_elem.get("href", "")
                categories = entry.find_all("category")
                category_terms = {
                    (cat.get("term") or "").lower() for cat in categories
                }
                is_judgment_category = any(
                    term for term in category_terms
                    if "judgment" in term or "case law" in term or "case-law" in term
                )
                is_judgment_link = any(
                    marker in link.lower()
                    for marker in ("/judgments/", "/judgment/", "/akn/")
                )
                if not (is_judgment_category or is_judgment_link):
                    continue

                if len(cases) == 0:
                    self.logger.info("First judgment link from feed: %s", link)

                title_elem = entry.find("title")
                date_elem = entry.find("updated") or entry.find("published")

                case_data = {
                    "case_name": title_elem.get_text(strip=True) if title_elem else "",
                    "citation": "",
                    "court": "",
                    "judgment_date": self._normalize_date(
                        date_elem.get_text(strip=True) if date_elem else ""
                    ),
                    "judges": "",
                    "source_url": link,
                    "scraped_at": datetime.now().isoformat(),
                }

                if case_data["case_name"]:
                    # Fetch detailed metadata
                    if case_data.get('source_url'):
                         self.logger.info(f"Fetching details for case: {case_data['source_url']}")
                         details = self._fetch_case_details(case_data['source_url'])
                         if details:
                             case_data.update(details)
                    
                    cases.append(case_data)
                
                if len(cases) >= num_cases:
                    break

        except Exception as e:
            self.logger.error(f"Error scraping new site feed: {e}")

        return cases
    
    def _scrape_new_site(self, num_cases: int) -> List[Dict]:
        """Scrape from the new Kenya Law website."""
        cases = []
        
        try:
            feed_cases = self._scrape_new_site_feed(num_cases)
            if feed_cases:
                return feed_cases

            # Access judgments page
            url = f"{self.new_base_url}/judgments/"
            response = self._make_request(url)
            
            if not response:
                return cases
            
            soup = self._parse_html(response)
            if not soup:
                return cases
            
            # Find case listings (adjust selectors based on actual site structure)
            case_elements = soup.find_all(['div', 'article', 'tr'], 
                                        class_=re.compile(r'case|judgment|decision', re.I))
            
            if not case_elements:
                # Try alternative selectors
                case_elements = soup.find_all('a', href=re.compile(r'judgment|case', re.I))
            
            for element in case_elements[:num_cases]:
                case_data = self._extract_case_data_new(element)
                if case_data:
                    # Visit the case page to get more details
                    if case_data.get('source_url'):
                        self.logger.info(f"Fetching details for case: {case_data['source_url']}")
                        details = self._fetch_case_details(case_data['source_url'])
                        if details:
                            # Update with detailed info
                            case_data.update(details)
                            
                    cases.append(case_data)
                    
        except Exception as e:
            self.logger.error(f"Error scraping new site: {e}")
        
        return cases
    
    def _fetch_case_details(self, case_url: str) -> Dict:
        """Fetch and extract details from the specific case page."""
        details = {}
        try:
            response = self._make_request(case_url)
            if not response:
                return details
                
            soup = self._parse_html(response)
            if not soup:
                return details
                
            # Reuse the extraction logic (similar to case_analysis but simplified for this scraper)
            # Find document details section
            
            labels_map = {
                'Citation': 'citation',
                'Court': 'court',
                'Judges': 'judges',
                'Judgment Date': 'judgment_date',
            }
            
            for label_text, key in labels_map.items():
                elements = soup.find_all(text=lambda t: t and label_text in t)
                for elem in elements:
                    if len(elem.strip()) > 50:
                        continue
                    
                    value = None
                    parent = elem.parent
                    
                    # Case 1: Tabular data
                    next_elem = parent.find_next_sibling()
                    if next_elem:
                        value = next_elem.get_text(strip=True)
                        
                    if not value and parent.parent:
                        next_parent = parent.parent.find_next_sibling()
                        if next_parent:
                            value = next_parent.get_text(strip=True)
                            
                    # Case 2: Key-Value pairs
                    if not value and ':' in parent.get_text():
                        parts = parent.get_text().split(':', 1)
                        if len(parts) > 1 and parts[0].strip() == label_text:
                            value = parts[1].strip()
                            
                    if value:
                        value = value.replace('Copy', '').strip()
                        if key == 'judgment_date':
                             details[key] = self._normalize_date(value)
                        else:
                             details[key] = value
                        break

        except Exception as e:
            self.logger.warning(f"Error fetching details for {case_url}: {e}")
            
        return details
    
    def _scrape_old_site_main_page(self, num_cases: int) -> List[Dict]:
        """Scrape from the old Kenya Law website main page."""
        cases = []
        
        try:
            # Access main page
            url = f"{self.base_url}/"
            response = self._make_request(url, follow_redirects=False)
            
            if not response:
                self.logger.warning("Main site not accessible")
                return cases
            
            soup = self._parse_html(response)
            if not soup:
                return cases
            
            # Look for any links that might be recent cases or judgments
            # Try multiple selectors to find case-related content
            selectors = [
                'a[href*="judgment"]',
                'a[href*="case"]', 
                'a[href*="court"]',
                '.recent-cases a',
                '.latest-judgments a',
                'a[href*="kl/index.php?id="]'
            ]
            
            found_links = set()
            for selector in selectors:
                try:
                    links = soup.select(selector)
                    for link in links[:num_cases]:
                        href = link.get('href')
                        if href and href not in found_links:
                            found_links.add(href)
                            
                            # Create basic case data
                            case_data = {
                                'case_name': link.get_text(strip=True),
                                'citation': '',
                                'court': '',
                                'judgment_date': '',
                                'judges': '',
                                'source_url': urljoin(self.base_url, href) if href.startswith('/') else href,
                                'scraped_at': datetime.now().isoformat()
                            }
                            
                            if case_data['case_name']:
                                cases.append(case_data)
                                
                                if len(cases) >= num_cases:
                                    break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {e}")
                    continue
                
                if len(cases) >= num_cases:
                    break
                    
        except Exception as e:
            self.logger.error(f"Error scraping old site main page: {e}")
        
        return cases[:num_cases]
    
    def _scrape_old_site(self, num_cases: int) -> List[Dict]:
        """Scrape from the old Kenya Law website."""
        cases = []
        
        try:
            # Access main page first to avoid redirects
            main_url = f"{self.base_url}"
            main_response = self._make_request(main_url, follow_redirects=False)
            
            if not main_response:
                self.logger.warning("Main site not accessible")
                return cases
            
            # Try direct case search without following redirects
            url = f"{self.base_url}/index.php?id=87"
            response = self._make_request(url, follow_redirects=False)
            
            if not response:
                self.logger.warning("Case search page not accessible")
                return cases
            
            soup = self._parse_html(response)
            if not soup:
                return cases
            
            # Find recent cases (adjust selectors based on actual site structure)
            case_elements = soup.find_all(['div', 'tr', 'li'], 
                                        class_=re.compile(r'case|judgment|recent', re.I))
            
            for element in case_elements[:num_cases]:
                case_data = self._extract_case_data_old(element)
                if case_data:
                    cases.append(case_data)
                    
        except Exception as e:
            self.logger.error(f"Error scraping old site: {e}")
        
        return cases
    
    def _extract_case_data_new(self, element) -> Optional[Dict]:
        """Extract case data from new site element."""
        try:
            case_data = {
                'case_name': '',
                'citation': '',
                'court': '',
                'judgment_date': '',
                'judges': '',
                'source_url': '',
                'scraped_at': datetime.now().isoformat()
            }
            
            # Extract case name
            name_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a'], 
                                    class_=re.compile(r'title|name|case', re.I))
            if name_elem:
                case_data['case_name'] = name_elem.get_text(strip=True)
            
            # Extract citation
            citation_elem = element.find(text=re.compile(r'\d{4}.*?KLR|.*?\[.*?\]', re.I))
            if citation_elem:
                case_data['citation'] = citation_elem.strip()
            
            # Extract court
            court_elem = element.find(text=re.compile(r'(Court|Supreme|Appeal|High|Magistrate)', re.I))
            if court_elem:
                case_data['court'] = court_elem.strip()
            
            # Extract date
            date_elem = element.find(text=re.compile(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}', re.I))
            if date_elem:
                case_data['judgment_date'] = date_elem.strip()
            
            # Extract judges
            judges_elem = element.find(text=re.compile(r'(J|JJ|Judge|Justices)', re.I))
            if judges_elem:
                case_data['judges'] = judges_elem.strip()
            
            # Extract URL
            link_elem = element.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                if href.startswith('/'):
                    case_data['source_url'] = urljoin(self.new_base_url, href)
                else:
                    case_data['source_url'] = href
            
            # Check for duplicates before returning
            if case_data['case_name']:
                return case_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting case data: {e}")
            return None
    
    def _extract_case_data_old(self, element) -> Optional[Dict]:
        """Extract case data from old site element."""
        try:
            case_data = {
                'case_name': '',
                'citation': '',
                'court': '',
                'judgment_date': '',
                'judges': '',
                'source_url': '',
                'scraped_at': datetime.now().isoformat()
            }
            
            # Similar extraction logic for old site
            text = element.get_text(strip=True)
            
            # Extract case name (usually first part)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if lines:
                case_data['case_name'] = lines[0]
            
            # Extract citation using regex
            citation_match = re.search(r'\d{4}.*?KLR|.*?\[.*?\]', text)
            if citation_match:
                case_data['citation'] = citation_match.group()
            
            # Extract date
            date_match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}', text)
            if date_match:
                case_data['judgment_date'] = date_match.group()
            
            # Extract link
            link_elem = element.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                if href.startswith('/'):
                    case_data['source_url'] = urljoin(self.base_url, href)
                else:
                    case_data['source_url'] = href
            
            # Check for duplicates before returning
            if case_data['case_name']:
                return case_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting case data from old site: {e}")
            return None
    
    def save_data(self, data: List[Dict], filename: str = None) -> bool:
        """
        Save scraped data to CSV file and optionally to Elasticsearch.
        
        Args:
            data: List of case dictionaries
            filename: Output filename (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not data:
            self.logger.warning("No data to save")
            return False
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'output/cases_{timestamp}.csv'
        
        try:
            # Save to CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['case_name', 'citation', 'court', 'judgment_date', 
                            'judges', 'source_url', 'scraped_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for case in data:
                    writer.writerow(case)
            
            self.logger.info(f"Saved {len(data)} cases to {filename}")
            
            # Save to Elasticsearch if configured
            if self.es_config.client:
                self._save_to_elasticsearch(data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
            return False
    
    def _save_to_elasticsearch(self, data: List[Dict]):
        """Save data to Elasticsearch."""
        try:
            self.es_config.create_index()
            
            for i, case in enumerate(data):
                case['document_type'] = 'case_law'
                self.es_config.index_document(case, f"case_{i}")
            
            self.logger.info(f"Indexed {len(data)} cases to Elasticsearch")
            
        except Exception as e:
            self.logger.error(f"Error saving to Elasticsearch: {e}")


def main():
    """Main function to run scraper."""
    scraper = LawExtractionScraper()
    cases = scraper.scrape(num_cases=10)
    
    if cases:
        scraper.save_data(cases)
        print(f"Successfully scraped and saved {len(cases)} cases")
    else:
        print("Failed to scrape any cases")


if __name__ == "__main__":
    main()
