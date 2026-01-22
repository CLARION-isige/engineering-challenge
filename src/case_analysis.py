import json
import os
import re
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin
import unicodedata

from utils.scraper_base import ScraperBase
from config.elasticsearch import ElasticsearchConfig

class CaseAnalysisScraper(ScraperBase):
    """Scraper for full-text judgment analysis (Async)."""
    
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
    
    async def scrape(self, case_urls: List[str] = None, num_cases: int = 20) -> List[Dict]:
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
            case_urls = await self._get_case_urls(num_cases)
        
        if not case_urls:
            self.logger.error("No case URLs found to analyze")
            return []

        # Analyze cases concurrently
        tasks = [self._analyze_case(url) for url in case_urls[:num_cases]]
        analyzed_cases_results = await asyncio.gather(*tasks)
        
        analyzed_cases = [res for res in analyzed_cases_results if res]
        
        # Complete scraping
        if analyzed_cases:
            self.logger.info(f"Successfully analyzed {len(analyzed_cases)} cases")
            return analyzed_cases
        else:
            self.logger.error("Failed to analyze any cases")
            return []
    
    async def _get_case_urls(self, num_cases: int) -> List[str]:
        """Get case URLs from case_extraction scraper or direct search."""
        urls = []
        
        try:
            # Import case_extraction scraper to get URLs
            from case_extraction import LawExtractionScraper
            
            level1_scraper = LawExtractionScraper()
            cases = await level1_scraper.scrape(num_cases)
            await level1_scraper.close()
            
            for case in cases:
                if case.get('source_url'):
                    urls.append(case['source_url'])
                    
        except Exception as e:
            self.logger.warning(f"Could not get URLs from case_extraction: {e}")
            # Fallback: try to find URLs directly
            urls = await self._find_case_urls_direct(num_cases)
        
        return urls
    
    async def _find_case_urls_direct(self, num_cases: int) -> List[str]:
        """Find case URLs directly from website."""
        urls = []
        
        try:
            # Try new site first
            url = f"{self.new_base_url}/judgments/"
            html_content = await self._make_request(url)
            
            if html_content:
                soup = self._parse_html(html_content)
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
    
    async def _analyze_case(self, case_url: str) -> Optional[Dict]:
        """Analyze a single case in detail."""
        try:
            html_content = await self._make_request(case_url)
            if not html_content:
                return None
            
            soup = self._parse_html(html_content)
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
                analysis['station'] = doc_details.get('station', '')
                analysis['case_number'] = doc_details.get('case_number', '')
                analysis['judgment_date'] = doc_details.get('judgment_date') or None
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
            labels_map = {
                'Citation': 'citation',
                'Court': 'court',
                'Court Station': 'station',
                'Court station': 'station', 
                'Case Number': 'case_number',
                'Case number': 'case_number',
                'Judges': 'judges',
                'Judgment Date': 'judgment_date',
                'Judgment date': 'judgment_date',
                'Case Action': 'case_action',
                'Case action': 'case_action'
            }
            
            for label_text, key in labels_map.items():
                elements = soup.find_all(string=lambda t: t and label_text in t)
                
                for elem in elements:
                    if len(elem.strip()) > 50:
                        continue
                        
                    value = None
                    parent = elem.parent
                    
                    next_elem = parent.find_next_sibling()
                    if next_elem:
                        value = next_elem.get_text(strip=True)
                        
                    if not value:
                        next_parent = parent.parent.find_next_sibling() if parent.parent else None
                        if next_parent:
                            value = next_parent.get_text(strip=True)
                            
                    if not value and ':' in parent.get_text():
                        parts = parent.get_text().split(':', 1)
                        if len(parts) > 1 and parts[0].strip() == label_text:
                            value = parts[1].strip()
                            
                    if value:
                        value = value.replace('Copy', '').strip()
                        if key == 'judges':
                            metadata[key] = [value]
                        elif key == 'judgment_date':
                            metadata[key] = self._normalize_date(value) or value
                        else:
                            metadata[key] = value
                        break
                
        except Exception as e:
            self.logger.error(f"Error extracting document details: {e}")
            
        return metadata
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date string to ISO 8601 format."""
        if not date_str:
            return None
            
        try:
            date_obj = datetime.strptime(date_str.strip(), "%d %B %Y")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            try:
                for fmt in ["%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
                     try:
                        return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
                     except ValueError:
                        continue
            except Exception:
                pass
            return None
    
    def _extract_full_text(self, soup) -> str:
        """Extract and clean full judgment text."""
        try:
            for script in soup(["script", "style"]):
                script.decompose()
            
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
                main_content = soup.find('body')
            
            if main_content:
                text = main_content.get_text()
                text = self._clean_text(text)
                return text
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Error extracting full text: {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        try:
            text = unicodedata.normalize('NFKC', text)
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'Page\s+\d+|\d+\s+of\s+\d+', '', text, flags=re.I)
            text = re.sub(r'\[.*?\]|\(.*?\)', '', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            return text.strip()
        except Exception as e:
            self.logger.error(f"Error cleaning text: {e}")
            return text
    
    def _extract_parties(self, text: str) -> Dict[str, str]:
        """Extract parties involved in the case."""
        parties = {'plaintiff': '', 'defendant': '', 'other_parties': []}
        try:
            party_matches = self.patterns['parties'].findall(text)
            for match in party_matches:
                if 'vs' in match.lower() or 'v.' in match.lower():
                    parts = re.split(r'\s+(?:vs|versus|v\.)\s+', match, flags=re.I)
                    if len(parts) >= 2:
                        parties['plaintiff'] = parts[0].strip()
                        parties['defendant'] = parts[1].strip()
            
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
            summary_patterns = [
                r'(?:Summary|Synopsis|Overview|Brief facts?):\s*([^.\n]+(?:\s+[^.\n]+){0,5})',
                r'(?:The facts of the case|Facts of the matter|Background):\s*([^.\n]+(?:\s+[^.\n]+){0,5})',
                r'(?:This is an appeal|This matter concerns|The issue arises):\s*([^.\n]+(?:\s+[^.\n]+){0,5})'
            ]
            for pattern in summary_patterns:
                match = re.search(pattern, text, re.I | re.DOTALL)
                if match:
                    return match.group(1).strip()
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            if len(paragraphs) > 1:
                return paragraphs[1][:500]
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting case summary: {e}")
            return ""
    
    def _extract_legal_issues(self, text: str) -> List[str]:
        """Extract legal issues presented."""
        issues = []
        try:
            issue_matches = self.patterns['legal_issues'].findall(text)
            issues.extend([match.strip() for match in issue_matches])
            additional_patterns = [
                r'(?:The question is|The issue is|Whether):\s*([^.\n]+)',
                r'\d+\.\s*([^.\n]*?(?:issue|question|whether)[^.\n]*)'
            ]
            for pattern in additional_patterns:
                matches = re.findall(pattern, text, re.I)
                issues.extend([match.strip() for match in matches])
            issues = list(set(issues))[:10]
        except Exception as e:
            self.logger.error(f"Error extracting legal issues: {e}")
        return issues
    
    def _extract_decision(self, text: str) -> str:
        """Extract court's decision or ruling."""
        try:
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
            principle_matches = self.patterns['ratio'].findall(text)
            principles.extend([match.strip() for match in principle_matches])
            additional_patterns = [
                r'(?:The principle is|The law provides|It is established that):\s*([^.\n]+)',
                r'(?:Legal principle|Rule of law|Established principle):\s*([^.\n]+)'
            ]
            for pattern in additional_patterns:
                matches = re.findall(pattern, text, re.I)
                principles.extend([match.strip() for match in matches])
            principles = list(set(principles))[:10]
        except Exception as e:
            self.logger.error(f"Error extracting legal principles: {e}")
        return principles
    
    def _extract_precedents(self, text: str) -> List[str]:
        """Extract precedents cited."""
        precedents = []
        try:
            precedent_matches = self.patterns['precedent'].findall(text)
            precedents.extend([match.strip() for match in precedent_matches])
            citation_patterns = [
                r'\b\d{4}\s+(?:KLR|EA|eKLR)\b',
                r'\b[A-Z]+\s+(?:vs|v\.)\s+[A-Z]+\s*\[\d{4}\]',
                r'\b\d{4}\s+\w+\s+\d+\s*\(\w+\)'
            ]
            for pattern in citation_patterns:
                matches = re.findall(pattern, text)
                precedents.extend(matches)
            precedents = list(set(precedents))[:15]
        except Exception as e:
            self.logger.error(f"Error extracting precedents: {e}")
        return precedents
    
    def _extract_advocates(self, text: str) -> List[str]:
        """Extract advocates appearing in the case."""
        advocates = []
        try:
            advocate_matches = self.patterns['advocates'].findall(text)
            advocates.extend([match.strip() for match in advocate_matches])
            additional_patterns = [
                r'(?:For the (?:plaintiff|defendant|appellant|respondent)):\s*([^,\n]+)',
                r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+&\s+[A-Z][a-z]+\s+[A-Z][a-z]+)*)\s*(?:for|appearing|counsel)',
            ]
            for pattern in additional_patterns:
                matches = re.findall(pattern, text, re.I)
                advocates.extend([match.strip() for match in matches])
            advocates = list(set(advocates))
        except Exception as e:
            self.logger.error(f"Error extracting advocates: {e}")
        return advocates
    
    def _extract_judges(self, text: str) -> List[str]:
        """Extract judge(s) name(s)."""
        judges = []
        try:
            judge_matches = self.patterns['judges'].findall(text)
            judges.extend([match.strip() for match in judge_matches])
            additional_patterns = [
                r'(?:J|JJ|Justice|Chief Justice|Judge)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',
                r'Delivered by\s+([^.\n]+)',
                r'Presided over by\s+([^.\n]+)'
            ]
            for pattern in additional_patterns:
                matches = re.findall(pattern, text, re.I)
                judges.extend([match.strip() for match in matches])
            judges = list(set(judges))
        except Exception as e:
            self.logger.error(f"Error extracting judges: {e}")
        return judges
    
    async def save_data(self, data: List[Dict], filename: str = None) -> bool:
        """Save analyzed data to JSON file and optionally to Elasticsearch."""
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
            await self._generate_analysis_summary(data)
            
            # Save to Elasticsearch
            await self._save_to_elasticsearch(data)
            
            return True
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
            return False
    
    async def _generate_analysis_summary(self, data: List[Dict]):
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
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_file = f'output/case_analysis_summary_{timestamp}.json'
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            self.logger.info(f"Analysis summary saved to {summary_file}")
        except Exception as e:
            self.logger.error(f"Error generating analysis summary: {e}")
    
    async def _save_to_elasticsearch(self, data: List[Dict]):
        """Save data to Elasticsearch."""
        try:
            await self.es_config.connect()
            if not self.es_config.client:
                return

            await self.es_config.create_index()
            
            tasks = []
            for i, case in enumerate(data):
                case['document_type'] = 'case_analysis'
                tasks.append(self.es_config.index_document(case))
            
            if tasks:
                await asyncio.gather(*tasks)
            
            self.logger.info(f"Indexed {len(data)} analyzed cases to Elasticsearch")
        except Exception as e:
            self.logger.error(f"Error saving to Elasticsearch: {e}")

async def main():
    """Main function to run scraper."""
    scraper = CaseAnalysisScraper()
    try:
        analyzed_cases = await scraper.scrape(num_cases=20)
        if analyzed_cases:
            await scraper.save_data(analyzed_cases)
            print(f"Successfully analyzed and saved {len(analyzed_cases)} cases")
        else:
            print("Failed to analyze any cases")
    finally:
        await scraper.close()
        if scraper.es_config.client:
            await scraper.es_config.close()

if __name__ == "__main__":
    asyncio.run(main())
