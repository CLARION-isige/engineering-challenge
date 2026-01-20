"""
Full-Text Case Analysis
Deep dive into judgment content with structured information extraction.
"""

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin
import unicodedata

from utils.scraper_base import ScraperBase
from config.elasticsearch import ElasticsearchConfig

class CaseAnalysisScraper(ScraperBase):
    """Scraper for full-text judgment analysis."""
    
    def __init__(self):
        super().__init__("case_analysis")
        self.base_url = "https://kenyalaw.org/kl"
        self.new_base_url = "https://new.kenyalaw.org"
        self.es_config = ElasticsearchConfig()
        
        # Legal patterns for extraction
        self.patterns = {
            'parties': re.compile(r'(?:Plaintiff|Petitioner|Applicant|Claimant|Complainant)\s+(?:vs|versus|v\.)\s+(?:Defendant|Respondent|Accused)', re.I),
            'judges': re.compile(r'(?:Before|Presided by|Delivered by|Coram):\s*([^.\n]+)', re.I),
            'advocates': re.compile(r'(?:Counsel|Advocates|Appearing|For):\s*([^.\n]+)', re.I),
            'legal_issues': re.compile(r'(?:Issue|Question|Determining|Whether|Whether or not)\s+([^.\n]+)', re.I),
            'holding': re.compile(r'(?:Held|Finding|Decision|Ruling|Order):\s*([^.\n]+)', re.I),
            'ratio': re.compile(r'(?:Ratio decidendi|Reasoning|Principle|Held that)\s+([^.\n]+)', re.I),
            'precedent': re.compile(r'(?:Followed|Applied|Cited|Referred to|As held in)\s+([^.\n]+)', re.I)
        }
        
        # Create output directory
        os.makedirs('output', exist_ok=True)
    
    def scrape(self, case_urls: List[str] = None, num_cases: int = 20) -> List[Dict]:
        """
        Scrape full judgment texts and perform deep analysis.
        
        Args:
            case_urls: List of specific case URLs to analyze (optional)
            num_cases: Number of cases to analyze if URLs not provided
            
        Returns:
            List of dictionaries containing detailed case analysis
        """
        self.logger.info(f"Starting scraping: Analyzing {num_cases} cases in detail")
        
        if not case_urls:
            # Get URLs from case_extraction scraper
            case_urls = self._get_case_urls(num_cases)
        
        analyzed_cases = []
        
        for i, url in enumerate(case_urls[:num_cases]):
            self.logger.info(f"Analyzing case {i+1}/{len(case_urls)}: {url}")
            
            case_analysis = self._analyze_case(url)
            if case_analysis:
                analyzed_cases.append(case_analysis)
        
        # Complete scraping
        if analyzed_cases:
            self.logger.info(f"Successfully analyzed {len(analyzed_cases)} cases")
            return analyzed_cases
        else:
            self.logger.error("Failed to analyze any cases")
            return []
    
    def _get_case_urls(self, num_cases: int) -> List[str]:
        """Get case URLs from case_extraction scraper or direct search."""
        urls = []
        
        try:
            # Import case_extraction scraper to get URLs
            from case_extraction import LawExtractionScraper
            
            level1_scraper = LawExtractionScraper()
            cases = level1_scraper.scrape(num_cases)
            
            for case in cases:
                if case.get('source_url'):
                    urls.append(case['source_url'])
                    
        except Exception as e:
            self.logger.warning(f"Could not get URLs from case_extraction: {e}")
            # Fallback: try to find URLs directly
            urls = self._find_case_urls_direct(num_cases)
        
        return urls
    
    def _find_case_urls_direct(self, num_cases: int) -> List[str]:
        """Find case URLs directly from website."""
        urls = []
        
        try:
            # Try new site first
            url = f"{self.new_base_url}/judgments/"
            response = self._make_request(url)
            
            if response:
                soup = self._parse_html(response)
                if soup:
                    links = soup.find_all('a', href=re.compile(r'judgment|case', re.I))
                    for link in links[:num_cases]:
                        href = link['href']
                        if href.startswith('/'):
                            urls.append(urljoin(self.new_base_url, href))
                        else:
                            urls.append(href)
                            
        except Exception as e:
            self.logger.error(f"Error finding case URLs: {e}")
        
        return urls
    
    def _analyze_case(self, case_url: str) -> Optional[Dict]:
        """Analyze a single case in detail."""
        try:
            response = self._make_request(case_url)
            if not response:
                return None
            
            soup = self._parse_html(response)
            if not soup:
                return None
            
            # Extract full text
            full_text = self._extract_full_text(soup)
            if not full_text:
                return None
            
            # Perform structured analysis
            analysis = {
                'source_url': case_url,
                'full_text': full_text,
                'parties': self._extract_parties(full_text),
                'case_summary': self._extract_case_summary(full_text),
                'legal_issues': self._extract_legal_issues(full_text),
                'decision': self._extract_decision(full_text),
                'legal_principles': self._extract_legal_principles(full_text),
                'precedents_cited': self._extract_precedents(full_text),
                'advocates': self._extract_advocates(full_text),
                'judges': self._extract_judges(full_text),
            }
            
            # Merge with "Document details" metadata if available
            doc_details = self._extract_metadata_from_details(soup)
            if doc_details:
                # Update/Overwrite with more reliable data
                analysis['citation'] = doc_details.get('citation', '')
                analysis['court'] = doc_details.get('court', '')
                analysis['court_station'] = doc_details.get('court_station', '')
                analysis['case_number'] = doc_details.get('case_number', '')
                analysis['judgment_date'] = doc_details.get('judgment_date', '')
                analysis['case_action'] = doc_details.get('case_action', '')
                
                # Merge judges if list is better
                if doc_details.get('judges'):
                     analysis['judges'] = doc_details['judges']

            # Add metadata info
            analysis['analysis_metadata'] = {
                    'text_length': len(full_text),
                    'word_count': len(full_text.split()),
                    'paragraph_count': len([p for p in full_text.split('\n') if p.strip()]),
                    'scraped_at': datetime.now().isoformat()
                }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing case {case_url}: {e}")
            return None
    
    def _extract_metadata_from_details(self, soup) -> Dict:
        """Extract metadata from the 'Document details' section."""
        metadata = {}
        try:
            # Try to find labels in the document details section
            # Typical structure based on screenshot: Label ... Value
            
            labels_map = {
                'Citation': 'citation',
                'Court': 'court',
                'Court Station': 'court_station',
                'Court station': 'court_station', 
                'Case Number': 'case_number',
                'Case number': 'case_number',
                'Judges': 'judges',
                'Judgment Date': 'judgment_date',
                'Judgment date': 'judgment_date',
                'Case Action': 'case_action',
                'Case action': 'case_action'
            }
            
            # Find all elements that might contain labels
            # Using specific classes if known, otherwise generic text search
            for label_text, key in labels_map.items():
                # Look for exact text match or starts with
                elements = soup.find_all(text=lambda t: t and label_text in t)
                
                for elem in elements:
                    # Check if this element effectively acts as a label
                    # It should be short
                    if len(elem.strip()) > 50:
                        continue
                        
                    value = None
                    parent = elem.parent
                    
                    # Case 1: Tabular data (common in details sections)
                    # <div class="row"><div class="label">Citation</div><div class="value">...</div></div>
                    # or <dt>Citation</dt><dd>...</dd>
                    
                    # Check next sibling element
                    next_elem = parent.find_next_sibling()
                    if next_elem:
                        value = next_elem.get_text(strip=True)
                        
                    # Check parent's next sibling (if label is inside a wrapper)
                    if not value:
                        next_parent = parent.parent.find_next_sibling() if parent.parent else None
                        if next_parent:
                            value = next_parent.get_text(strip=True)
                            
                    # Case 2: Key-Value pairs in text
                    # <b>Citation:</b> [2026] KEHC ...
                    if not value and ':' in parent.get_text():
                        parts = parent.get_text().split(':', 1)
                        if len(parts) > 1 and parts[0].strip() == label_text:
                            value = parts[1].strip()
                            
                    if value:
                        value = value.replace('Copy', '').strip()
                        if key == 'judges':
                            # Cleanup: "FR Olel" -> ["FR Olel"]
                            # Should handle potentially multiple judges
                            metadata[key] = [value]
                        elif key == 'judgment_date':
                            metadata[key] = self._normalize_date(value) or value
                        else:
                            metadata[key] = value
                        break # Found value for this key
                
        except Exception as e:
            self.logger.error(f"Error extracting document details: {e}")
            
        return metadata
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date string to ISO 8601 format."""
        if not date_str:
            return None
            
        try:
            # Try parsing "16 January 2026" format
            date_obj = datetime.strptime(date_str.strip(), "%d %B %Y")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            try:
                # Try parsing "Jan 16, 2026" or similar if needed, currently valid format is likely "16 January 2026"
                # If parsing fails, just return strict original or None? 
                # The error logs showed "16 January 2026", so the first format should cover it.
                # Let's add a few fallback formats just in case
                for fmt in ["%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
                     try:
                        return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
                     except ValueError:
                        continue
            except Exception:
                pass
            
            # self.logger.warning(f"Could not parse date: {date_str}")
            return None
    
    def _extract_full_text(self, soup) -> str:
        """Extract and clean full judgment text."""
        try:
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Find main content area
            content_selectors = [
                'div[class*="content"]',
                'div[class*="judgment"]',
                'div[class*="main"]',
                'article',
                'main',
                'div[id*="content"]',
                'div[id*="main"]'
            ]
            
            main_content = None
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                # Fallback to body
                main_content = soup.find('body')
            
            if main_content:
                text = main_content.get_text()
                # Clean text
                text = self._clean_text(text)
                return text
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Error extracting full text: {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        try:
            # Normalize Unicode
            text = unicodedata.normalize('NFKC', text)
            
            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove page numbers and headers
            text = re.sub(r'Page\s+\d+|\d+\s+of\s+\d+', '', text, flags=re.I)
            
            # Remove common legal document artifacts
            text = re.sub(r'\[.*?\]|\(.*?\)', '', text)
            
            # Clean line breaks
            text = re.sub(r'\n\s*\n', '\n\n', text)
            
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"Error cleaning text: {e}")
            return text
    
    def _extract_parties(self, text: str) -> Dict[str, str]:
        """Extract parties involved in the case."""
        parties = {'plaintiff': '', 'defendant': '', 'other_parties': []}
        
        try:
            # Find party patterns
            party_matches = self.patterns['parties'].findall(text)
            for match in party_matches:
                if 'vs' in match.lower() or 'v.' in match.lower():
                    parts = re.split(r'\s+(?:vs|versus|v\.)\s+', match, flags=re.I)
                    if len(parts) >= 2:
                        parties['plaintiff'] = parts[0].strip()
                        parties['defendant'] = parts[1].strip()
            
            # Look for other party mentions
            other_party_patterns = [
                r'(?:Applicant|Petitioner|Claimant):\s*([^,\n]+)',
                r'(?:Respondent|Defendant|Accused):\s*([^,\n]+)'
            ]
            
            for pattern in other_party_patterns:
                matches = re.findall(pattern, text, re.I)
                parties['other_parties'].extend([m.strip() for m in matches])
            
        except Exception as e:
            self.logger.error(f"Error extracting parties: {e}")
        
        return parties
    
    def _extract_case_summary(self, text: str) -> str:
        """Extract case summary or synopsis."""
        try:
            # Look for summary patterns
            summary_patterns = [
                r'(?:Summary|Synopsis|Overview|Brief facts?):\s*([^.\n]+(?:\s+[^.\n]+){0,5})',
                r'(?:The facts of the case|Facts of the matter|Background):\s*([^.\n]+(?:\s+[^.\n]+){0,5})',
                r'(?:This is an appeal|This matter concerns|The issue arises):\s*([^.\n]+(?:\s+[^.\n]+){0,5})'
            ]
            
            for pattern in summary_patterns:
                match = re.search(pattern, text, re.I | re.DOTALL)
                if match:
                    return match.group(1).strip()
            
            # Fallback: first paragraph after title
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            if len(paragraphs) > 1:
                return paragraphs[1][:500]  # First 500 chars of second paragraph
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Error extracting case summary: {e}")
            return ""
    
    def _extract_legal_issues(self, text: str) -> List[str]:
        """Extract legal issues presented."""
        issues = []
        
        try:
            # Find issue patterns
            issue_matches = self.patterns['legal_issues'].findall(text)
            issues.extend([match.strip() for match in issue_matches])
            
            # Additional patterns
            additional_patterns = [
                r'(?:The question is|The issue is|Whether):\s*([^.\n]+)',
                r'\d+\.\s*([^.\n]*?(?:issue|question|whether)[^.\n]*)'
            ]
            
            for pattern in additional_patterns:
                matches = re.findall(pattern, text, re.I)
                issues.extend([match.strip() for match in matches])
            
            # Remove duplicates and limit
            issues = list(set(issues))[:10]
            
        except Exception as e:
            self.logger.error(f"Error extracting legal issues: {e}")
        
        return issues
    
    def _extract_decision(self, text: str) -> str:
        """Extract court's decision or ruling."""
        try:
            # Look for decision patterns
            decision_patterns = [
                r'(?:Decision|Ruling|Order|Judgment):\s*([^.\n]+(?:\s+[^.\n]+){0,3})',
                r'(?:It is hereby ordered|The court orders|We therefore hold):\s*([^.\n]+(?:\s+[^.\n]+){0,3})',
                r'(?:Accordingly|In conclusion|Therefore):\s*([^.\n]+(?:\s+[^.\n]+){0,3})'
            ]
            
            for pattern in decision_patterns:
                match = re.search(pattern, text, re.I | re.DOTALL)
                if match:
                    return match.group(1).strip()
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Error extracting decision: {e}")
            return ""
    
    def _extract_legal_principles(self, text: str) -> List[str]:
        """Extract key legal principles cited."""
        principles = []
        
        try:
            # Find principle patterns
            principle_matches = self.patterns['ratio'].findall(text)
            principles.extend([match.strip() for match in principle_matches])
            
            # Additional patterns
            additional_patterns = [
                r'(?:The principle is|The law provides|It is established that):\s*([^.\n]+)',
                r'(?:Legal principle|Rule of law|Established principle):\s*([^.\n]+)'
            ]
            
            for pattern in additional_patterns:
                matches = re.findall(pattern, text, re.I)
                principles.extend([match.strip() for match in matches])
            
            # Remove duplicates and limit
            principles = list(set(principles))[:10]
            
        except Exception as e:
            self.logger.error(f"Error extracting legal principles: {e}")
        
        return principles
    
    def _extract_precedents(self, text: str) -> List[str]:
        """Extract precedents cited."""
        precedents = []
        
        try:
            # Find precedent patterns
            precedent_matches = self.patterns['precedent'].findall(text)
            precedents.extend([match.strip() for match in precedent_matches])
            
            # Look for case citations
            citation_patterns = [
                r'\b\d{4}\s+(?:KLR|EA|eKLR)\b',
                r'\b[A-Z]+\s+(?:vs|v\.)\s+[A-Z]+\s*\[\d{4}\]',
                r'\b\d{4}\s+\w+\s+\d+\s*\(\w+\)'
            ]
            
            for pattern in citation_patterns:
                matches = re.findall(pattern, text)
                precedents.extend(matches)
            
            # Remove duplicates and limit
            precedents = list(set(precedents))[:15]
            
        except Exception as e:
            self.logger.error(f"Error extracting precedents: {e}")
        
        return precedents
    
    def _extract_advocates(self, text: str) -> List[str]:
        """Extract advocates appearing in the case."""
        advocates = []
        
        try:
            # Find advocate patterns
            advocate_matches = self.patterns['advocates'].findall(text)
            advocates.extend([match.strip() for match in advocate_matches])
            
            # Additional patterns
            additional_patterns = [
                r'(?:For the (?:plaintiff|defendant|appellant|respondent)):\s*([^,\n]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+&\s+[A-Z][a-z]+\s+[A-Z][a-z]+)*)\s*(?:for|appearing|counsel)',
            ]
            
            for pattern in additional_patterns:
                matches = re.findall(pattern, text, re.I)
                advocates.extend([match.strip() for match in matches])
            
            # Remove duplicates
            advocates = list(set(advocates))
            
        except Exception as e:
            self.logger.error(f"Error extracting advocates: {e}")
        
        return advocates
    
    def _extract_judges(self, text: str) -> List[str]:
        """Extract judge(s) name(s)."""
        judges = []
        
        try:
            # Find judge patterns
            judge_matches = self.patterns['judges'].findall(text)
            judges.extend([match.strip() for match in judge_matches])
            
            # Additional patterns
            additional_patterns = [
                r'(?:J|JJ|Justice|Chief Justice|Judge)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
                r'Delivered by\s+([^.\n]+)',
                r'Presided over by\s+([^.\n]+)'
            ]
            
            for pattern in additional_patterns:
                matches = re.findall(pattern, text, re.I)
                judges.extend([match.strip() for match in matches])
            
            # Remove duplicates
            judges = list(set(judges))
            
        except Exception as e:
            self.logger.error(f"Error extracting judges: {e}")
        
        return judges
    
    def save_data(self, data: List[Dict], filename: str = None) -> bool:
        """
        Save analyzed data to JSON file and optionally to Elasticsearch.
        
        Args:
            data: List of analyzed case dictionaries
            filename: Output filename (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not data:
            self.logger.warning("No data to save")
            return False
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'output/case_analysis_{timestamp}.json'
        
        try:
            # Save to JSON
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(data)} analyzed cases to {filename}")
            
            # Generate analysis summary
            self._generate_analysis_summary(data)
            
            # Save to Elasticsearch if configured
            if self.es_config.client:
                self._save_to_elasticsearch(data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
            return False
    
    def _generate_analysis_summary(self, data: List[Dict]):
        """Generate summary statistics for the analyzed cases."""
        try:
            summary = {
                'total_cases_analyzed': len(data),
                'average_text_length': sum(case.get('analysis_metadata', {}).get('text_length', 0) for case in data) // len(data) if data else 0,
                'total_legal_issues': sum(len(case.get('legal_issues', [])) for case in data),
                'total_precedents_cited': sum(len(case.get('precedents_cited', [])) for case in data),
                'cases_with_parties': sum(1 for case in data if case.get('parties', {}).get('plaintiff')),
                'cases_with_decision': sum(1 for case in data if case.get('decision')),
                'scraped_at': datetime.now().isoformat()
            }
            
            # Save summary
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_file = f'output/case_analysis_summary_{timestamp}.json'
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            
            self.logger.info(f"Analysis summary saved to {summary_file}")
            
        except Exception as e:
            self.logger.error(f"Error generating analysis summary: {e}")
    
    def _save_to_elasticsearch(self, data: List[Dict]):
        """Save data to Elasticsearch."""
        try:
            self.es_config.create_index()
            
            for i, case in enumerate(data):
                case['document_type'] = 'case_analysis'
                self.es_config.index_document(case, f"analysis_{i}")
            
            self.logger.info(f"Indexed {len(data)} analyzed cases to Elasticsearch")
            
        except Exception as e:
            self.logger.error(f"Error saving to Elasticsearch: {e}")


def main():
    """Main function to run scraper."""
    scraper = CaseAnalysisScraper()
    analyzed_cases = scraper.scrape(num_cases=20)
    
    if analyzed_cases:
        scraper.save_data(analyzed_cases)
        print(f"Successfully analyzed and saved {len(analyzed_cases)} cases")
    else:
        print("Failed to analyze any cases")


if __name__ == "__main__":
    main()
