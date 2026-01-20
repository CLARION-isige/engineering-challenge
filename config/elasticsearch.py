import os
from elasticsearch import AsyncElasticsearch
from dotenv import load_dotenv
import logging
import hashlib
import asyncio

load_dotenv()

logger = logging.getLogger(__name__)

class ElasticsearchConfig:
    """Elasticsearch configuration and connection management (Async)."""
    
    def __init__(self):
        self.host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        self.port = int(os.getenv('ELASTICSEARCH_PORT', 9200))
        self.index_name = os.getenv('ELASTICSEARCH_INDEX', 'kenya_law')
        self.username = os.getenv('ELASTICSEARCH_USERNAME')
        self.password = os.getenv('ELASTICSEARCH_PASSWORD')
        
        self.client = None

    async def connect(self):
        """Initialize the async client."""
        if self.client:
            return self.client
            
        try:
            hosts = [{'host': self.host, 'port': self.port, 'scheme': 'http'}]
            if self.username and self.password:
                self.client = AsyncElasticsearch(
                    hosts=hosts,
                    http_auth=(self.username, self.password)
                )
            else:
                self.client = AsyncElasticsearch(hosts=hosts)
            
            # Test connection
            if await self.client.ping():
                logger.info(f"Connected to Elasticsearch at {self.host}:{self.port}")
            else:
                logger.error("Failed to connect to Elasticsearch")
                self.client = None
                
        except Exception as e:
            logger.error(f"Error connecting to Elasticsearch: {e}")
            self.client = None
        
        return self.client

    async def close(self):
        """Close the async client session."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Elasticsearch client connection closed.")

    async def create_index(self, mapping=None):
        """Create index with mapping if it doesn't exist."""
        if not self.client:
            await self.connect()
        if not self.client:
            return False
            
        try:
            if not await self.client.indices.exists(index=self.index_name):
                await self.client.indices.create(
                    index=self.index_name,
                    body=mapping or self._get_default_mapping()
                )
                logger.info(f"Created index: {self.index_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return False

    async def delete_index(self):
        """Delete the index if it exists."""
        if not self.client:
            await self.connect()
        if not self.client:
            return False
            
        try:
            if await self.client.indices.exists(index=self.index_name):
                await self.client.indices.delete(index=self.index_name)
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
    
    async def index_document(self, doc, doc_id=None):
        """Index a document."""
        if not self.client:
            await self.connect()
        if not self.client:
            return False
        
        # Generate doc_id if not provided
        if not doc_id:
            doc_id = self._generate_doc_id(doc)
        
        try:
            response = await self.client.index(
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
            # Prioritize source_url for unique identification
            if doc.get('source_url'):
                identifier = doc['source_url']
            else:
                # Fallback to key fields if source_url is missing
                content_parts = []
                if doc.get('case_name'):
                    content_parts.append(doc['case_name'])
                if doc.get('citation'):
                    content_parts.append(doc['citation'])
                if doc.get('act_title'):
                    content_parts.append(doc['act_title'])
                if doc.get('chapter_number'):
                    content_parts.append(doc['chapter_number'])
                
                identifier = '|'.join(content_parts)
            
            if not identifier:
                identifier = str(doc)
                
            return hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:24]
        except Exception as e:
            logger.warning(f"Error generating doc ID: {e}")
            return f"doc_{hashlib.md5(str(doc).encode('utf-8')).hexdigest()[:12]}"
    
    async def search(self, query, size=10):
        """Search documents."""
        if not self.client:
            await self.connect()
        if not self.client:
            return []
            
        try:
            response = await self.client.search(
                index=self.index_name,
                body=query,
                size=size
            )
            return response['hits']['hits']
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
