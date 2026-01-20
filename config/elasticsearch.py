"""
Elasticsearch configuration and utilities for Kenya Law scraping project.
"""

import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import logging
import hashlib

load_dotenv()

logger = logging.getLogger(__name__)

class ElasticsearchConfig:
    """Elasticsearch configuration and connection management."""
    
    def __init__(self):
        self.host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        self.port = int(os.getenv('ELASTICSEARCH_PORT', 9200))
        self.index_name = os.getenv('ELASTICSEARCH_INDEX', 'kenya_law')
        self.username = os.getenv('ELASTICSEARCH_USERNAME')
        self.password = os.getenv('ELASTICSEARCH_PASSWORD')
        
        self.client = self._create_client()
    
    def _create_client(self):
        """Create and return Elasticsearch client."""
        try:
            if self.username and self.password:
                es = Elasticsearch(
                    hosts=[{'host': self.host, 'port': self.port, 'scheme': 'http'}],
                    http_auth=(self.username, self.password)
                )
            else:
                es = Elasticsearch(
                    hosts=[{'host': self.host, 'port': self.port, 'scheme': 'http'}]
                )
            
            # Test connection
            if es.ping():
                logger.info(f"Connected to Elasticsearch at {self.host}:{self.port}")
                return es
            else:
                logger.error("Failed to connect to Elasticsearch")
                return None
                
        except Exception as e:
            logger.error(f"Error connecting to Elasticsearch: {e}")
            return None
    
    def create_index(self, mapping=None):
        """Create index with mapping if it doesn't exist."""
        if not self.client:
            return False
            
        try:
            if not self.client.indices.exists(index=self.index_name):
                self.client.indices.create(
                    index=self.index_name,
                    body=mapping or self._get_default_mapping()
                )
                logger.info(f"Created index: {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return False

    def delete_index(self):
        """Delete the index if it exists."""
        if not self.client:
            return False
            
        try:
            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
                logger.info(f"Deleted index: {self.index_name}")
                return True
            else:
                logger.warning(f"Index {self.index_name} does not exist")
                return True # Consider it success if it doesn't exist
        except Exception as e:
            logger.error(f"Error deleting index: {e}")
            return False
    
    def _get_default_mapping(self):
        """Get default mapping for legal documents."""
        return {
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "document_type": {"type": "keyword"},
                    "citation": {"type": "keyword"},
                    "court": {"type": "keyword"},
                    "judges": {"type": "text"},
                    "judgment_date": {"type": "date"},
                    "act_title": {"type": "text"},
                    "chapter_number": {"type": "keyword"},
                    "year_enacted": {"type": "integer"},
                    "legal_category": {"type": "keyword"},
                    "source_url": {"type": "keyword"},
                    "scraped_at": {"type": "date"}
                }
            }
        }
    
    def index_document(self, doc, doc_id=None):
        """Index a document."""
        if not self.client:
            return False
        
        # Generate doc_id if not provided
        if not doc_id:
            doc_id = self._generate_doc_id(doc)
        
        try:
            response = self.client.index(
                index=self.index_name,
                body=doc,
                id=doc_id
            )
            logger.info(f"Indexed document with ID: {doc_id}")
            return response
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            return False
    
    def _generate_doc_id(self, doc):
        """Generate unique document ID from content."""
        try:
            import hashlib
            # Create a consistent ID from key fields
            content_parts = []
            if doc.get('case_name'):
                content_parts.append(doc['case_name'])
            if doc.get('citation'):
                content_parts.append(doc['citation'])
            if doc.get('act_title'):
                content_parts.append(doc['act_title'])
            if doc.get('chapter_number'):
                content_parts.append(doc['chapter_number'])
            
            content_string = '|'.join(content_parts)
            return hashlib.sha256(content_string.encode('utf-8')).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Error generating doc ID: {e}")
            return f"doc_{hashlib.md5(str(doc).encode('utf-8')).hexdigest()[:8]}"
    
    def search(self, query, size=10):
        """Search documents."""
        if not self.client:
            return []
            
        try:
            response = self.client.search(
                index=self.index_name,
                body=query,
                size=size
            )
            return response['hits']['hits']
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
