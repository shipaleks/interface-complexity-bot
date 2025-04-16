#!/usr/bin/env python3
import os
import json
import base64
import logging
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "gpt-4-1106-vision-preview"
OPENAI_API_ENDPOINT = "https://api.openai.com/v1/chat/completions"

# Load the prompt template
def load_prompt_template(template_path="prompt_templates/complexity_analysis.txt"):
    if not os.path.exists(template_path):
        logger.warning(f"Prompt template not found at {template_path}, using default prompt")
        return """
        You are an expert UX analyzer specializing in interface complexity evaluation. 
        Analyze this UI screenshot and evaluate its complexity on a scale of 0-100.
        
        Provide a thorough analysis structured as JSON with these sections:
        - Overall score (0-100)
        - Analysis categories (visual organization, perceptual complexity, typography, etc.)
        - Problems identified in each category
        - Severity scores for each problem (0-100)
        - Recommendations for improvement
        
        Make your response valid, parseable JSON.
        """
    
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

# Encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Analyze the UI with GPT-4.1
def analyze_ui_with_gpt(image_path, prompt_template, model=DEFAULT_MODEL):
    logger.info(f"Analyzing UI image: {image_path}")
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    # Encode the image
    base64_image = encode_image(image_path)
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Prepare payload
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a UX expert focused on analyzing interface complexity. Provide your analysis in valid JSON format."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_template
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 4000
    }
    
    try:
        logger.info("Sending request to OpenAI API")
        response = requests.post(OPENAI_API_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        
        # Extract the JSON content from the response
        json_content = response_data["choices"][0]["message"]["content"]
        
        # Validate that it's proper JSON
        try:
            json_data = json.loads(json_content)
            return json_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response as JSON: {e}")
            logger.debug(f"Raw response: {json_content}")
            
            # Try to extract JSON from the response if it contains non-JSON text
            import re
            json_match = re.search(r'```json\n(.*?)```', json_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    json_data = json.loads(json_str)
                    return json_data
                except:
                    pass
            
            raise ValueError("Response could not be parsed as JSON") from e
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise

def save_analysis(analysis_data, output_path):
    logger.info(f"Saving analysis to {output_path}")
    
    # Add metadata
    analysis_data["meta"] = {
        "timestamp": datetime.now().isoformat(),
        "model": DEFAULT_MODEL,
        "version": "1.0"
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="Analyze UI screenshot with GPT-4.1")
    parser.add_argument("--screenshot", required=True, help="Path to the UI screenshot")
    parser.add_argument("--output", required=True, help="Path to save the analysis JSON")
    parser.add_argument("--prompt", help="Path to the prompt template file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="GPT model to use")
    
    args = parser.parse_args()
    
    try:
        # Validate the screenshot path
        if not os.path.exists(args.screenshot):
            logger.error(f"Screenshot does not exist: {args.screenshot}")
            return 1
        
        # Load the prompt template
        prompt_path = args.prompt if args.prompt else "prompt_templates/complexity_analysis.txt"
        prompt_template = load_prompt_template(prompt_path)
        
        # Analyze the UI
        analysis_data = analyze_ui_with_gpt(args.screenshot, prompt_template, args.model)
        
        # Save the analysis
        save_analysis(analysis_data, args.output)
        
        logger.info("Analysis completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main()) 