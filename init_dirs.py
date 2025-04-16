#!/usr/bin/env python3
"""
Directory initialization script for Railway deployment.
Creates necessary directories before the bot starts.
"""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def init_directories():
    """Create necessary directories for the bot to operate."""
    directories = ["temp", "results"]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Directory created/verified: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
    
    # Test file write permission
    for directory in directories:
        test_file = os.path.join(directory, "test_write.txt")
        try:
            with open(test_file, 'w') as f:
                f.write("Test write permission")
            logger.info(f"Write test successful in {directory}")
            os.remove(test_file)
            logger.info(f"Test file removed from {directory}")
        except Exception as e:
            logger.error(f"Write permission test failed in {directory}: {e}")
    
    logger.info("Directory initialization completed")

if __name__ == "__main__":
    init_directories() 