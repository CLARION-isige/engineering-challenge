# Database Setup Guide

## Elasticsearch Setup

### Installation

#### Option 1: Quick Start Script (Recommended for Beginners)
```bash
# Automatic setup with sensible defaults
curl -fsSL https://elastic.co/start-local | sh
```
- Access Elasticsearch at: http://localhost:9200/
- Automatically configured for local development

#### Option 2: Docker (Recommended for Development)
```bash
# Pull Elasticsearch Docker image
docker pull docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Run Elasticsearch container
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

#### Option 3: Local Installation
```bash
# Download and install Elasticsearch
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.11.0-linux-x86_64.tar.gz
tar -xzf elasticsearch-8.11.0-linux-x86_64.tar.gz
cd elasticsearch-8.11.0/

# Start Elasticsearch
./bin/elasticsearch
```

### Configuration

1. **Environment Variables**
   Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env`:
   ```env
   ELASTICSEARCH_HOST=localhost
   ELASTICSEARCH_PORT=9200
   ELASTICSEARCH_INDEX=kenya_law
   ELASTICSEARCH_USERNAME=
   ELASTICSEARCH_PASSWORD=
   ```

2. **Verify Installation**
   Test that Elasticsearch is running:
   ```bash
   curl -X GET "localhost:9200/"
   ```

3. **Check Health**
   Monitor Elasticsearch health:
   ```bash
   curl -X GET "localhost:9200/_cluster/health?pretty"
   ```
### Index Mappings
 
 The scrapers automatically create indices with the following mapping. All scrapers share the same index but are tagged with different `document_type` values (`case_law`, `legislation`, `case_analysis`).
 
 ```json
 {
   "mappings": {
     "properties": {
       "document_type": {"type": "keyword"},
       "scraped_at": {"type": "date"},
       "source_url": {"type": "keyword"},
       # Case Law Metadata
       "case_name": {"type": "text"},
       "citation": {"type": "keyword"},
       "court": {"type": "keyword"},
       "judgment_date": {"type": "date"},
       "judges": {"type": "text"},
       # Legislation (Acts/Bills) 
       "act_title": {"type": "text"},
       "chapter_number": {"type": "keyword"},
       "year_enacted": {"type": "integer"},
       "legal_category": {"type": "keyword"},
       # Full-Text Analysis
       "full_text": {"type": "text"},
       "parties": {"type": "object"},
       "legal_issues": {"type": "text"},
       "decision": {"type": "text"},
       "legal_principles": {"type": "text"}
     }
   }
 }
 ```

### Alternative Storage Options

If you prefer not to use Elasticsearch, the scrapers also save to:
- **case_extraction**: CSV files
- **legislation**: JSON files
- **case_analysis**: JSON files with full text analysis

### Kibana Setup (Optional)

For data visualization and management:
```bash
docker run -d \
  --name kibana \
  -p 5601:5601 \
  -e "ELASTICSEARCH_HOSTS=http://localhost:9200" \
  docker.elastic.co/kibana/kibana:8.11.0
```

Access Kibana at `http://localhost:5601`

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure Elasticsearch is running
   - Check host and port in `.env`
   - Verify firewall settings

2. **Memory Issues**
   - Increase heap size: `ES_JAVA_OPTS="-Xms1g -Xmx1g"`
   - Use Docker with sufficient memory allocation
   - Close unnecessary applications

3. **Index Creation Failed**
   - Check Elasticsearch logs
   - Verify permissions
   - Ensure sufficient disk space

4. **Port Already in Use**
   ```bash
   # Check what's using port 9200
   lsof -i :9200
   
   # Kill the process if needed
   kill -9 <PID>
   ```

### Monitoring

Check Elasticsearch status:
```bash
# Basic health check
curl -X GET "localhost:9200/_cluster/health?pretty"

# View indices
curl -X GET "localhost:9200/_cat/indices?v"

# Check node information
curl -X GET "localhost:9200/_nodes/info?pretty"
```

### Performance Tuning

For better performance with large datasets:
```bash
# Increase memory allocation
export ES_JAVA_OPTS="-Xms2g -Xmx2g"

# Or in Docker
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms2g -Xmx2g" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

## Security Notes

### Development Setup
- Security is disabled in the provided configurations
- Suitable for local development only
- Do not use in production without proper security

### Production Considerations
- Enable security features
- Configure authentication
- Use HTTPS
- Set up proper firewall rules
- Regular backups recommended
