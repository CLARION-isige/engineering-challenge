import os
import glob
import sys

# Add parent directory to path to allow importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.elasticsearch import ElasticsearchConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup():
    """Clean up Elasticsearch index and output files."""
    logger.info("Starting cleanup...")
    
    # 1. Clean up Elasticsearch
    try:
        es_config = ElasticsearchConfig()
        if es_config.client:
            if es_config.delete_index():
                logger.info("Successfully deleted Elasticsearch index")
            else:
                logger.warning("Failed to delete Elasticsearch index (or it didn't exist)")
        else:
            logger.warning("Could not connect to Elasticsearch, skipping index deletion")
    except Exception as e:
        logger.error(f"Error during Elasticsearch cleanup: {e}")

    # 2. Clean up local files
    try:
        files = glob.glob('output/case_analysis_*.json')
        for f in files:
            try:
                os.remove(f)
                logger.info(f"Removed file: {f}")
            except OSError as e:
                logger.error(f"Error removing file {f}: {e}")
                
        logger.info(f"Removed {len(files)} output files")
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")
        
    logger.info("Cleanup complete")

if __name__ == "__main__":
    cleanup()
