"""
Legislation Database Scraper
Builds a comprehensive Acts/Bills scraper for Kenya Laws database.
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

from utils.scraper_base import ScraperBase
from config.elasticsearch import ElasticsearchConfig

class LegislationScraper(ScraperBase):
    """Scraper for comprehensive Acts/Bills extraction."""
    
    def __init__(self):
        super().__init__("legislation")
        self.base_url = "https://kenyalaw.org/kl/"
        self.new_base_url = "https://new.kenyalaw.org"
        self.es_config = ElasticsearchConfig()
        
        # Legal categories for classification
        self.legal_categories = {
            'Criminal': ['criminal', 'penal', 'offence', 'prosecution', 'police'],
            'Civil': ['civil', 'contract', 'tort', 'property', 'family'],
            'Constitutional': ['constitution', 'bill of rights', 'fundamental', 'democracy'],
            'Commercial': ['commercial', 'business', 'trade', 'company', 'banking'],
            'Labor': ['labor', 'employment', 'work', 'occupation', 'trade union'],
            'Environmental': ['environment', 'conservation', 'pollution', 'natural resources'],
            'Health': ['health', 'medical', 'pharmacy', 'disease', 'hospital'],
            'Education': ['education', 'school', 'university', 'college', 'training'],
            'Tax': ['tax', 'revenue', 'customs', 'excise', 'income tax']
        }
        
        # Create output directory
        os.makedirs('output', exist_ok=True)
    
    def scrape(self, min_acts: int = 50) -> List[Dict]:
        """
        Scrape legislation data from Kenya Laws database.
        
        Args:
            min_acts: Minimum number of Acts to extract
            
        Returns:
            List of dictionaries containing Act information
        """
        self.logger.info(f"Starting scraping: Extracting at least {min_acts} Acts")
        
        # Try new site first, fallback to old site
        # acts = self._scrape_new_site(min_acts)
        # if acts:
        #    self.logger.info(f"Successfully extracted {len(acts)} Acts from new site")
        #    return acts
        
        self.logger.info("Skipping new site (unresponsive), trying old site...")
        acts = self._scrape_old_site(min_acts) # If new site is skipped, we need all acts from old site
        
        # Complete scraping
        if acts:
            self.logger.info(f"Successfully extracted {len(acts)} Acts")
            return acts
        else:
            self.logger.warning("Failed to extract any Acts")
            return []
    
    def _scrape_new_site(self, min_acts: int) -> List[Dict]:
        """Scrape from the new Kenya Law legislation database."""
        acts = []
        
        try:
            # Access legislation page
            url = f"{self.new_base_url}/legislation/"
            response = self._make_request(url)
            
            if not response:
                return acts
            
            soup = self._parse_html(response)
            if not soup:
                return acts
            
            # Find legislation listings
            act_elements = soup.find_all(['div', 'article', 'tr', 'li'], 
                                       class_=re.compile(r'act|legislation|statute|chapter', re.I))
            
            if not act_elements:
                # Try alternative selectors
                act_elements = soup.find_all('a', href=re.compile(r'act|legislation|chapter', re.I))
            
            for element in act_elements:
                if len(acts) >= min_acts:
                    break
                    
                act_data = self._extract_act_data_new(element)
                if act_data:
                    acts.append(act_data)
                    
        except Exception as e:
            self.logger.error(f"Error scraping new site: {e}")
        
        return acts
    
    def _scrape_old_site(self, min_acts: int) -> List[Dict]:
        """Scrape from the old Kenya Law legislation database (Recent Legislation)."""
        acts = []
        visited_urls = set()
        
        # Start with 2024 (Recent Legislation)
        # We will extract links for other years from the side menu
        start_url = f"{self.base_url}/index.php?id=12002"
        urls_to_scrape = [start_url]
        
        while urls_to_scrape and len(acts) < min_acts:
            url = urls_to_scrape.pop(0)
            if url in visited_urls:
                continue
                
            visited_urls.add(url)
            self.logger.info(f"Scraping legislation URL: {url}")
            
            try:
                response = self._make_request(url)
                if not response:
                    continue
                
                soup = self._parse_html(response)
                if not soup:
                    continue
                
                # Extract Acts from table
                rows = soup.select('table.contenttable tr')
                # Skip header row
                for row in rows[1:]:
                    if len(acts) >= min_acts:
                        break
                        
                    act_data = self._extract_act_data_table(row)
                    if act_data:
                        acts.append(act_data)
                
                # Find other years if we need more acts
                if len(acts) < min_acts:
                    # Look for year links in the side menu
                    year_links = soup.select('ul.vert-two li a')
                    for link in year_links:
                        href = link.get('href')
                        if href and 'id=' in href:
                            full_url = urljoin(self.base_url, href) if not href.startswith('http') else href
                            if full_url not in visited_urls and full_url not in urls_to_scrape:
                                urls_to_scrape.append(full_url)
                                
            except Exception as e:
                self.logger.error(f"Error scraping legislation URL {url}: {e}")
        
        return acts
    
    def _extract_act_data_new(self, element) -> Optional[Dict]:
        """Extract Act data from new site element."""
        try:
            act_data = {
                'act_title': '',
                'chapter_number': '',
                'year_enacted': '',
                'download_url': '',
                'last_revision': '',
                'legal_category': '',
                'source_url': '',
                'scraped_at': datetime.now().isoformat()
            }
            
            # Extract Act title
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a'], 
                                     class_=re.compile(r'title|name|act', re.I))
            if title_elem:
                act_data['act_title'] = title_elem.get_text(strip=True)
            
            # Extract chapter number
            chapter_elem = element.find(text=re.compile(r'Cap\.?\s*\d+|Chapter\s*\d+', re.I))
            if chapter_elem:
                chapter_match = re.search(r'\d+', chapter_elem)
                if chapter_match:
                    act_data['chapter_number'] = chapter_match.group()
            
            # Extract year
            year_elem = element.find(text=re.compile(r'\b(19|20)\d{2}\b'))
            if year_elem:
                year_match = re.search(r'\b(19|20)\d{2}\b', year_elem)
                if year_match:
                    act_data['year_enacted'] = year_match.group()
            
            # Extract download URL (PDF)
            pdf_elem = element.find('a', href=re.compile(r'\.pdf', re.I))
            if pdf_elem:
                href = pdf_elem['href']
                if not href.startswith(('http:', 'https:')):
                    act_data['download_url'] = urljoin(self.new_base_url, href)
                else:
                    act_data['download_url'] = href
            
            # Extract source URL
            link_elem = element.find('a', href=True)
            if link_elem and not link_elem['href'].endswith('.pdf'):
                href = link_elem['href']
                if not href.startswith(('http:', 'https:')):
                    act_data['source_url'] = urljoin(self.new_base_url, href)
                else:
                    act_data['source_url'] = href
            
            # Categorize by legal area
            act_data['legal_category'] = self._categorize_act(act_data['act_title'])
            
            # Check for duplicates before returning
            if act_data['act_title'] and not self.check_content_duplicate(str(act_data)):
                self.add_scraped_item(act_data['source_url'], act_data)
                return act_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting Act data: {e}")
            return None
    
    def _extract_act_data_table(self, row) -> Optional[Dict]:
        """Extract Act data from table row."""
        try:
            cols = row.find_all('td')
            if len(cols) < 2:
                return None
                
            act_data = {
                'act_title': '',
                'chapter_number': '',
                'year_enacted': '',
                'download_url': '',
                'last_revision': '',
                'legal_category': '',
                'source_url': '',
                'scraped_at': datetime.now().isoformat()
            }
            
            # Title is in first col
            title_text = cols[0].get_text(strip=True)
            act_data['act_title'] = title_text
            
            # Act No/Year in second col
            meta_text = cols[1].get_text(strip=True)
            # Try to extract year and number
            year_match = re.search(r'\b(19|20)\d{2}\b', meta_text)
            if year_match:
                act_data['year_enacted'] = year_match.group()
            
            # Download link
            link_elem = row.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                full_url = href
                if not href.startswith(('http:', 'https:')):
                    full_url = urljoin(self.base_url, href)
                
                act_data['download_url'] = full_url
                act_data['source_url'] = full_url
            
            # Categorize
            act_data['legal_category'] = self._categorize_act(act_data['act_title'])
            
            if act_data['act_title']:
                return act_data
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting Act data from table: {e}")
            return None

    def _extract_act_data_old(self, element) -> Optional[Dict]:
        """Extract Act data from old site element."""
        try:
            act_data = {
                'act_title': '',
                'chapter_number': '',
                'year_enacted': '',
                'download_url': '',
                'last_revision': '',
                'legal_category': '',
                'source_url': '',
                'scraped_at': datetime.now().isoformat()
            }
            
            text = element.get_text(strip=True)
            
            # Extract Act title (usually contains "Act")
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            for line in lines:
                if 'Act' in line or 'Cap.' in line:
                    act_data['act_title'] = line
                    break
            
            # Extract chapter number
            chapter_match = re.search(r'Cap\.?\s*(\d+)', text)
            if chapter_match:
                act_data['chapter_number'] = chapter_match.group(1)
            
            # Extract year
            year_match = re.search(r'\b(19|20)\d{2}\b', text)
            if year_match:
                act_data['year_enacted'] = year_match.group()
            
            # Extract links
            link_elem = element.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                full_url = href
                if not href.startswith(('http:', 'https:')):
                    full_url = urljoin(self.base_url, href)

                if href.endswith('.pdf'):
                    act_data['download_url'] = full_url
                else:
                    act_data['source_url'] = full_url
            
            # Categorize
            act_data['legal_category'] = self._categorize_act(act_data['act_title'])
            
            # Check for duplicates before returning
            if act_data['act_title'] and not self.check_content_duplicate(str(act_data)):
                self.add_scraped_item(act_data['source_url'], act_data)
                return act_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting Act data from old site: {e}")
            return None
    
    def _categorize_act(self, title: str) -> str:
        """Categorize Act based on title content."""
        if not title:
            return 'Other'
        
        title_lower = title.lower()
        
        for category, keywords in self.legal_categories.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return category
        
        return 'Other'
    
    def save_data(self, data: List[Dict], filename: str = None) -> bool:
        """
        Save scraped data to JSON file and optionally to Elasticsearch.
        
        Args:
            data: List of Act dictionaries
            filename: Output filename (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not data:
            self.logger.warning("No data to save")
            return False
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'output/legislation_{timestamp}.json'
        
        try:
            # Save to JSON
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(data)} Acts to {filename}")
            
            # Generate summary statistics
            self._generate_summary(data)
            
            # Save to Elasticsearch if configured
            if self.es_config.client:
                self._save_to_elasticsearch(data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
            return False
    
    def _generate_summary(self, data: List[Dict]):
        """Generate summary statistics for the scraped data."""
        try:
            summary = {
                'total_acts': len(data),
                'categories': {},
                'years': {},
                'chapters_with_numbers': 0,
                'with_pdf_links': 0,
                'scraped_at': datetime.now().isoformat()
            }
            
            for act in data:
                # Count categories
                category = act.get('legal_category', 'Other')
                summary['categories'][category] = summary['categories'].get(category, 0) + 1
                
                # Count years
                year = act.get('year_enacted', 'Unknown')
                summary['years'][year] = summary['years'].get(year, 0) + 1
                
                # Count chapters
                if act.get('chapter_number'):
                    summary['chapters_with_numbers'] += 1
                
                # Count PDF links
                if act.get('download_url'):
                    summary['with_pdf_links'] += 1
            
            # Save summary
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_file = f'output/legislation_summary_{timestamp}.json'
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            
            self.logger.info(f"Summary saved to {summary_file}")
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
    
    def _save_to_elasticsearch(self, data: List[Dict]):
        """Save data to Elasticsearch."""
        try:
            self.es_config.create_index()
            
            for i, act in enumerate(data):
                act['document_type'] = 'legislation'
                self.es_config.index_document(act, f"act_{i}")
            
            self.logger.info(f"Indexed {len(data)} Acts to Elasticsearch")
            
        except Exception as e:
            self.logger.error(f"Error saving to Elasticsearch: {e}")


def main():
    """Main function to run scraper."""
    scraper = LegislationScraper()
    acts = scraper.scrape(min_acts=50)
    
    if acts:
        scraper.save_data(acts)
        print(f"Successfully scraped and saved {len(acts)} Acts")
    else:
        print("Failed to scrape any Acts")


if __name__ == "__main__":
    main()
