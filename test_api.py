#!/usr/bin/env python3
"""
Simple script to test API connections for OpenAI and Gemini.
Use this to verify that your API keys are valid and working.
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv
import base64
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_openai_api():
    """Test connection to OpenAI API."""
    logger.info("Testing OpenAI API connection...")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return False
    
    logger.info("OpenAI API key found")
    
    try:
        # Import OpenAI library
        from openai import OpenAI
        
        # Initialize client
        client = OpenAI(api_key=api_key)
        
        # List models (simple API call to test connection)
        models = client.models.list()
        
        # Print available models for confirmation
        logger.info(f"OpenAI connection successful. Found {len(models.data)} models.")
        for i, model in enumerate(models.data[:5], 1):  # Print first 5 models
            logger.info(f"  {i}. {model.id}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing OpenAI API: {e}")
        logger.error(traceback.format_exc())
        return False

def test_gemini_api():
    """Test connection to Gemini API."""
    logger.info("Testing Gemini API connection...")
    
    # Check for API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        return False
    
    logger.info("Gemini API key found")
    
    try:
        # Import Google GenerativeAI library
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # List models (simple API call to test connection)
        models = genai.list_models()
        
        # Print available models for confirmation
        logger.info(f"Gemini connection successful. Found {len(models)} models.")
        for i, model in enumerate(models[:5], 1):  # Print first 5 models
            logger.info(f"  {i}. {model.name}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing Gemini API: {e}")
        logger.error(traceback.format_exc())
        return False

def test_simple_query():
    """Test a simple query to both APIs."""
    logger.info("Testing simple text query to both APIs...")
    
    # Test OpenAI simple query
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is the capital of France?"}
                ]
            )
            logger.info(f"OpenAI simple query response: {response.choices[0].message.content}")
        else:
            logger.warning("Skipping OpenAI simple query test (no API key)")
    except Exception as e:
        logger.error(f"Error in OpenAI simple query test: {e}")
    
    # Test Gemini simple query
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("What is the capital of France?")
            logger.info(f"Gemini simple query response: {response.text}")
        else:
            logger.warning("Skipping Gemini simple query test (no API key)")
    except Exception as e:
        logger.error(f"Error in Gemini simple query test: {e}")

def create_test_image():
    """Create a simple test image for testing vision APIs."""
    logger.info("Creating test image...")
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple test image
        width, height = 300, 200
        test_image = Image.new('RGB', (width, height), color=(240, 240, 240))
        d = ImageDraw.Draw(test_image)
        
        # Add a rectangle
        d.rectangle([(10, 10), (290, 190)], outline=(200, 200, 200), width=2)
        
        # Add text
        d.text((150, 100), "Test UI", fill=(0, 0, 0), anchor="mm")
        
        # Save the image
        test_image_path = "test_image.png"
        test_image.save(test_image_path)
        
        logger.info(f"Test image created at {test_image_path}")
        return test_image_path
    
    except Exception as e:
        logger.error(f"Error creating test image: {e}")
        logger.error(traceback.format_exc())
        return None

def main():
    """Main function to run all tests."""
    logger.info("Starting API tests")
    
    # Test OpenAI API
    openai_success = test_openai_api()
    logger.info(f"OpenAI API test: {'SUCCESS' if openai_success else 'FAILED'}")
    
    # Test Gemini API
    gemini_success = test_gemini_api()
    logger.info(f"Gemini API test: {'SUCCESS' if gemini_success else 'FAILED'}")
    
    # Test simple query
    test_simple_query()
    
    # Create test image
    test_image = create_test_image()
    
    if not test_image:
        logger.warning("Skipping vision API tests (no test image created)")
        return
    
    logger.info("Testing simple vision query not implemented - would require more complex code")
    
    logger.info("API tests completed")

if __name__ == "__main__":
    main() 